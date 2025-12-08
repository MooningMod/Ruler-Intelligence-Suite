import sys
import ctypes
import subprocess
import time
from pathlib import Path

from PyQt5.QtCore import Qt, QRect, QTimer
from PyQt5.QtGui import QPainter, QColor, QFont
from PyQt5.QtWidgets import QWidget, QApplication

# =============================================================================
# OPTIONAL IMPORTS (Graceful degradation)
# =============================================================================

# IPC Bridge for communication with Tech Analyzer
try:
    from ipc_bridge import IPCClient, wait_for_server
    IPC_AVAILABLE = True
except ImportError:
    IPCClient = None
    wait_for_server = None
    IPC_AVAILABLE = False
    print("[System] WARNING: ipc_bridge.py not found. Tech Analyzer integration limited.")

try:
    # Import official effect logic from your updated tech_effects.py
    from tech_effects import EFFECT_MAP as CORE_EFFECT_MAP, BOOL_EFFECT_MAP
except ImportError:
    CORE_EFFECT_MAP = {}
    BOOL_EFFECT_MAP = {}
    print("[System] WARNING: tech_effects.py not found. Effect details will be limited.")

try:
    import pymem
    import pymem.process
except ImportError:
    pymem = None
    print("[Memory] WARNING: pymem is not installed. Selected unit reading is disabled.")

from unit_parser import parse_default_unit, Unit, load_range_database
from tech_parser import load_tech_file
from spotting_parser import load_spotting_file
from painters import draw_unit_list, draw_comparison_table
from events import handle_mouse_press, handle_wheel

# =============================================================================
# TECH LABEL MAP (Complete)
# =============================================================================
TECH_LABEL_MAP = {
    # --- Attack Values ---
    140: "Soft Attack", 
    141: "Hard Attack", 
    142: "Fortification Att.",
    143: "Low Air Attack", 
    144: "Mid Air Attack", 
    145: "High Air Attack",
    146: "Naval Surface Att.", 
    147: "Submarine Att.",     
    148: "Close Combat",

    # --- Ranges ---
    150: "Ground Range", 
    151: "Air Range", 
    152: "Naval Range", 
    153: "Sub Range",

    # --- Defense ---
    154: "Ground Defense", 
    155: "Tactical Air Defense", 
    156: "Indirect Def (Art)", 
    157: "Close Defense",

    # --- Specs ---
    158: "Speed (km/h)", 
    159: "Stealth Rating", 
    160: "Initiative", 
    161: "Combat Time (Ammo)",

    # --- Logistics ---
    162: "Fuel Consumption",  
    163: "Missile Capacity", 
    164: "Unit Efficiency",   
    165: "Ammo Capacity",
    166: "Fuel Tank Size",     

    # --- Spotting ---
    167: "Spotting Range (Vis)", 
    168: "Spotting Range (Rad)",
    169: "Spotting Str (Vis)",    
    170: "Spotting Str (Rad)",
}

class OverlayINS(QWidget):
    """
    Supreme Ruler 2030 - 3-way unit comparison overlay.
    """

    # --- MEMORY OFFSETS ---
    # Blueprint Offset (Menu di costruzione)
    SELECTED_UNIT_OFFSET_BLUEPRINT = 0x1767628

    # Worldmap click offset (Unità sulla mappa)
    SELECTED_UNIT_OFFSET_WORLD = 0x1769714
    
    # Selected Technology Offset
    SELECTED_TECH_OFFSET = 0x17676D8

    def __init__(self, 
                 default_unit_path: str | None = None, 
                 default_ttrx_path: str | None = None,
                 default_spotting_path: str | None = None,
                 range_database_path: str | None = None):
        super().__init__()
        
        # Memory State
        self.last_unit_blueprint_id = None
        self.last_unit_world_id = None
        self.current_selected_unit_id = None  
        self.previous_selected_unit_id = None

        self.prev_raw_blue = -1
        self.prev_raw_world = -1
        self.active_source = "world"  # Può essere 'world' o 'blue'        
        
        # Process Tracking for Tech Analyzer
        self.analyzer_process = None

        # --- Tech Impact Scrollbar State ---
        self.techimpact_dragging = False
        self.techimpact_drag_offset = 0

        # Data Containers
        self.units: list[Unit] = []
        self.filtered_units: list[Unit] = []
        self.tech_unlocks: dict[int, list[Unit]] = {}

        # Selection slots (Comparison Columns)
        self.selected_unit_b: Unit | None = None
        self.selected_unit_c: Unit | None = None
        self.selected_unit_d: Unit | None = None

        # Tech data (from DEFAULT.TTRX)
        self.tech_light: dict[int, dict] = {}
        self.tech_full: dict[int, dict] = {}

        # Active techs for B/C/D columns
        self.active_techs: dict[str, set[int]] = {
            "b": set(),
            "c": set(),
            "d": set(),
        }

        # Checkbox rects for techs
        self.tech_checkbox_rects: dict[str, dict[int, QRect]] = {
            "b": {},
            "c": {},
            "d": {},
        }

        # Lock & control buttons
        self.lock_b: bool = False
        self.manual_selection_b: bool = False  # True when user clicked unit in overlay list
        self.btn_lock_rect = QRect()
        self.btn_b_to_c_rect = QRect()
        self.btn_c_to_d_rect = QRect()

        # Filters Main Unit List
        self.search_query: str = ""
        self.selected_category: str = "all"
        self.focus_search: bool = False
        
        # Scrolling State
        self.line_height = 22
        self.unit_scroll_offset = 0       
        self.stats_scroll_offset = 0      
        self.max_stats_scroll = 0         

        # Rects Definitions
        self.close_btn_rect = QRect()
        self.unit_list_rect = QRect()
        self.search_rect = QRect()
        self.stats_rect = QRect()
        self.category_button_rects = []

        # Tabs & tech impact
        self.view_mode: str = "compare"            
        self.selected_tech_for_impact: int | None = None
        self.tab_compare_rect = QRect()
        self.tab_tech_rect = QRect()
        
        # --- Tech Search Box (Find Tech) ---
        self.tech_search = ""
        self.tech_search_focus = False
        self.tech_search_results = []    
        self.tech_search_max_display = 6 
        self.tech_search_rect = QRect()
        self.tech_search_result_rects = []
        
        # --- Impact Unit Filter (Filter units in Tech View) ---
        self.impact_unit_search = ""
        self.focus_impact_unit_search = False
        self.impact_unit_search_rect = QRect()

        self.techimpact_unit_rects = {}
        self.techimpact_scroll_offset = 0
        self.techimpact_max_scroll = 0
        
        # Scrollbar Rects (Initialize empty)
        self.techimpact_scrollbar_track_rect = QRect()
        self.techimpact_scrollbar_handle_rect = QRect()

        # Visibility & Input State
        self.menu_visible = False
        self.key_was_pressed = False
        self.alt_t_was_pressed = False
        
        # Alt+T Cooldown System (prevents duplicate launches)
        self.alt_t_cooldown_ms = 1000  # Minimum ms between Alt+T triggers
        self.alt_t_last_trigger = 0    # Timestamp of last successful trigger

        # Memory Handlers
        self.pm = None
        self.base_addr = None
        self.last_raw_selected_id: int | None = None

        # Initialization Routine
        self.init_window()
        
        # 1. Load Range Database FIRST (so parser can use it)
        self.load_range_database(range_database_path)
        
        # 2. Load Spotting Data SECOND (so units can use it)
        self.load_spotting(default_spotting_path)
        
        # 3. Load Units
        self.load_units(default_unit_path)
        
        # 4. Load Techs
        self.load_techs(default_ttrx_path)
        
        # Calculate tech dependencies
        self._calculate_tech_unlocks()
 
        self.update_filter()
        self._attach_process()

        # Timer loop (30ms = approx 33 FPS)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.game_loop)
        self.timer.start(30) 
        
        self.last_selected_tech_id: int | None = None

        print("-" * 60)
        print("SR2030 - INS Overlay Initialized")
        print("-" * 60)

        
    def _calculate_tech_unlocks(self):
        """Map which techs unlock which units for fast lookup."""
        self.tech_unlocks = {}
        for u in self.units:
            tid = getattr(u, 'req_tech_id', 0) or getattr(u, 'tech_req', 0)
            if tid > 0:
                if tid not in self.tech_unlocks:
                    self.tech_unlocks[tid] = []
                self.tech_unlocks[tid].append(u)
        print(f"[System] Mapped unlocks for {len(self.tech_unlocks)} technologies.")

    # ------------------------------------------------------------------ 
    # MEMORY READING
    # ------------------------------------------------------------------ 
    def _attach_process(self):
        if pymem is None:
            return
        try:
            self.pm = pymem.Pymem("SupremeRuler2030.exe")
            mod = pymem.process.module_from_name(self.pm.process_handle, "SupremeRuler2030.exe")
            self.base_addr = mod.lpBaseOfDll
            print(f"[Memory] Attached to SR2030, base = {hex(self.base_addr)}")
        except Exception as e:
            self.pm = None
            self.base_addr = None

    def _read_selected_unit_raw(self) -> int | None:
        if pymem is None:
            return None
        if not self.pm or not self.base_addr:
            self._attach_process()
            if not self.pm or not self.base_addr:
                return None

        try:
            addr_blue = self.base_addr + self.SELECTED_UNIT_OFFSET_BLUEPRINT
            val_blue = self.pm.read_int(addr_blue)

            addr_world = self.base_addr + self.SELECTED_UNIT_OFFSET_WORLD
            val_world = self.pm.read_int(addr_world)

            blue_changed = (val_blue != self.prev_raw_blue)
            world_changed = (val_world != self.prev_raw_world)

            self.prev_raw_blue = val_blue
            self.prev_raw_world = val_world

            if world_changed and val_world > 0:
                self.active_source = "world"
                self.last_raw_selected_id = val_world
                return val_world

            if blue_changed and val_blue > 0:
                self.active_source = "blue"
                self.last_raw_selected_id = val_blue
                return val_blue

            if self.active_source == "blue" and val_blue > 0:
                self.last_raw_selected_id = val_blue
                return val_blue
            
            self.active_source = "world"
            self.last_raw_selected_id = val_world
            return val_world

        except Exception as e:
            self.pm = None
            self.base_addr = None
            return None

    def _read_selected_tech_id(self) -> int | None:
        """Read the currently selected tech ID from game memory."""
        if not self.pm or not self.base_addr:
            self._attach_process()
        if not self.pm or not self.base_addr:
            return None
        try:
            addr = self.base_addr + self.SELECTED_TECH_OFFSET
            tech_id = self.pm.read_int(addr)
            if tech_id > 0 and tech_id < 200000:  
                return tech_id
            return None
        except Exception as e:
            print(f"[Memory] Tech read error: {e}")
            return None
        
    def _read_selected_unit_obj(self) -> Unit | None:
        uid = self._read_selected_unit_raw()
        if uid is None:
            return None
        for u in self.units:
            if u.id == uid:
                return u
        return None

    # ------------------------------------------------------------ 
    # MAIN LOOP
    # ------------------------------------------------------------ 
    def game_loop(self):
        # 1. Check INS Key (Toggle Menu)
        try:
            # 0x2D = INS key
            pressed_ins = (ctypes.windll.user32.GetAsyncKeyState(0x2D) & 0x8000)
            if pressed_ins:
                if not self.key_was_pressed:
                    self.toggle_menu()
                    self.key_was_pressed = True
            else:
                self.key_was_pressed = False
        except Exception:
            pass

        # 2. Check Alt + T (Tech Analyzer Shortcut)
        try:
            # 0x12 = ALT, 0x54 = T
            pressed_alt = (ctypes.windll.user32.GetAsyncKeyState(0x12) & 0x8000)
            pressed_t = (ctypes.windll.user32.GetAsyncKeyState(0x54) & 0x8000)

            if pressed_alt and pressed_t:
                if not self.alt_t_was_pressed:
                    # Check cooldown to prevent rapid-fire triggers
                    current_time = int(time.time() * 1000)
                    if current_time - self.alt_t_last_trigger >= self.alt_t_cooldown_ms:
                        print("[Overlay] Detected Alt+T shortcut!")
                        self._open_techtree_with_selected()
                        self.alt_t_last_trigger = current_time
                    else:
                        print("[Overlay] Alt+T cooldown active, ignoring...")
                    self.alt_t_was_pressed = True
            else:
                self.alt_t_was_pressed = False
        except Exception as e:
            print(f"[Overlay] Alt+T check error: {e}")

        # 3. Update Selected Unit (Column B) from in-game selection
        # Skip if: menu hidden, locked, or user made manual selection in overlay
        if self.menu_visible and not self.lock_b and not self.manual_selection_b:
            u = self._read_selected_unit_obj()
            if u:
                if self.selected_unit_b is None or self.selected_unit_b.id != u.id:
                    # Auto-shift: old B becomes C
                    if self.selected_unit_b:
                        self.selected_unit_c = self.selected_unit_b
                    self.selected_unit_b = u
                    self.active_techs["b"] = set(u.tech_ids) if hasattr(u, 'tech_ids') else set()
                    self.update()

    # ------------------------------------------------------------- 
    # INITIALIZATION & LOADING
    # ------------------------------------------------------------- 
    def init_window(self):
        screen = QApplication.primaryScreen()
        g = screen.geometry() if screen else QRect(0, 0, 1920, 1080)
        self.setGeometry(g)
        self.setWindowTitle("Intelligence Division")

        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.hide()

    def load_spotting(self, default_spotting_path: str | None):
        paths = []
        if default_spotting_path:
            paths.append(Path(default_spotting_path))
        
        # Standard Steam path
        paths.append(Path(r"C:\Program Files (x86)\Steam\steamapps\common\Supreme Ruler 2030\Maps\DATA\Spotting.csv"))
        # Local fallback
        paths.append(Path(__file__).with_name("Spotting.csv"))

        for p in paths:
            if p and p.exists():
                load_spotting_file(str(p))
                return
        
        print("[Spotting] WARNING: Spotting.csv not found. Radar ranges will be 0.")

    def load_range_database(self, range_database_path: str | None):
        """Load unit range stats database from CSV (silent if not found)"""
        paths = []
        if range_database_path:
            paths.append(Path(range_database_path))
        
        # Same directory as overlay script/exe
        paths.append(Path(__file__).parent / "unit_rangestats_database.csv")
        # Current working directory
        paths.append(Path.cwd() / "unit_rangestats_database.csv")
        
        for p in paths:
            if p and p.exists():
                load_range_database(str(p))
                return

    def load_units(self, default_unit_path: str | None):
        paths = [
            Path(default_unit_path) if default_unit_path else None,
            Path(r"C:/Program Files (x86)/Steam/steamapps/common/Supreme Ruler 2030/Maps/DATA/DEFAULT.UNIT"),
            Path(__file__).with_name("DEFAULT.UNIT"),
        ]
        for p in paths:
            if p and p.exists():
                try:
                    self.units = parse_default_unit(str(p))
                    print(f"[Units] Loaded {len(self.units)} units from {p}")
                    return
                except Exception as e:
                    print(f"[Units] Error loading units from {p}: {e}")
        print("[Units] WARNING: no DEFAULT.UNIT loaded")

    def load_techs(self, default_ttrx_path: str | None = None):
        paths = []
        if default_ttrx_path:
            paths.append(Path(default_ttrx_path))
        paths.append(Path(r"C:\Program Files (x86)\Steam\steamapps\common\Supreme Ruler 2030\Maps\DATA\DEFAULT.TTRX"))
        paths.append(Path(__file__).with_name("DEFAULT.TTRX"))
        
        for p in paths:
            if p and p.exists():
                try:
                    self.tech_light, self.tech_full = load_tech_file(str(p))
                    print(f"[Tech] Loaded {len(self.tech_light)} techs from {p}")
                    return
                except Exception as e:
                    print(f"[Tech] Error loading techs from {p}: {e}")
                    
        print("[Tech] WARNING: no DEFAULT.TTRX loaded, tech bonuses disabled.")

    # --------------------------------------------------------------- 
    # FILTERING
    # --------------------------------------------------------------- 
    def _unit_category(self, u: Unit) -> str:
        c = u.class_num
        if 0 <= c <= 6:
            return "land"
        if 7 <= c <= 14:
            return "air"
        if 15 <= c <= 20:
            return "naval"
        return "unknown"

    def update_filter(self):
        q = self.search_query.strip().lower()
        cat = self.selected_category
        res: list[Unit] = []
        
        if not q and cat == "all":
            self.filtered_units = list(self.units)
            self.unit_scroll_offset = 0
            return

        for u in self.units:
            if cat != "all" and self._unit_category(u) != cat:
                continue
            if q and not u.matches(q):
                continue
            res.append(u)
        self.filtered_units = res
        self.unit_scroll_offset = 0

    # -------------------------------------------------------------- 
    # UI ACTIONS
    # -------------------------------------------------------------- 
    def toggle_menu(self):
        if not self.menu_visible:
            self.menu_visible = True
            self.manual_selection_b = False  # Reset manual flag on open
            # Force read on open to grab current selection immediately
            u = self._read_selected_unit_obj()
            if u:
                self.selected_unit_b = u
                self.active_techs["b"] = set(u.tech_ids) if hasattr(u, 'tech_ids') else set()
            self.show()
            self.activateWindow()
            self.raise_()
        else:
            self.menu_visible = False
            self.hide()
            self.focus_search = False
            # Reset special focus fields
            self.tech_search_focus = False
            self.focus_impact_unit_search = False

    # ------------------------------------------------------------- 
    # INPUT EVENTS
    # ------------------------------------------------------------- 
    def keyPressEvent(self, event):
        if not self.menu_visible:
            return
        
        key = event.key()
        modifiers = event.modifiers()
        
        # Check if any text box has focus
        no_focus_active = not (self.focus_search or self.tech_search_focus or self.focus_impact_unit_search)

        # Toggle Lock B (L key)
        if no_focus_active and event.key() == Qt.Key_L:
            self.lock_b = not self.lock_b
            self.update()
            return
        
        # Reset/Sync with in-game selection (R key)
        if no_focus_active and event.key() == Qt.Key_R:
            self.manual_selection_b = False  # Clear manual flag
            # Force immediate sync with in-game selection
            u = self._read_selected_unit_obj()
            if u:
                self.selected_unit_b = u
                self.active_techs["b"] = set(u.tech_ids) if hasattr(u, 'tech_ids') else set()
            self.update()
            return

        # ----------------------------------------
        # 1. Main Unit Search (Filter)
        # ----------------------------------------
        if self.focus_search:
            key = event.key()
            if key in (Qt.Key_Return, Qt.Key_Enter):
                self.focus_search = False
            elif key == Qt.Key_Escape:
                self.search_query = ""
                self.update_filter()
                self.focus_search = False 
            elif key == Qt.Key_Backspace:
                self.search_query = self.search_query[:-1]
                self.update_filter()
            else:
                ch = event.text()
                if ch and ch.isprintable():
                    self.search_query += ch
                    self.update_filter()
            self.update()
            return
            
        # ----------------------------------------
        # 2. Tech Search (Find Tech by ID/Name)
        # ----------------------------------------
        elif self.tech_search_focus and self.view_mode == "tech_impact":
             key = event.key()
             if key in (Qt.Key_Return, Qt.Key_Enter):
                # If results exist, select the first one on Enter
                if self.tech_search_results:
                    self.selected_tech_for_impact = self.tech_search_results[0][0]
                self.update()
                return
             elif key == Qt.Key_Backspace:
                self.tech_search = self.tech_search[:-1]
                self.update()
                return
             elif key == Qt.Key_Escape:
                self.tech_search = ""
                self.tech_search_results = []
                self.update()
                return
             else:
                ch = event.text()
                if ch and ch.isprintable():
                    self.tech_search += ch
                    self.update()
             return

        # ----------------------------------------
        # 3. Impact Unit Filter (Find unit in Tech view)
        # ----------------------------------------
        elif self.focus_impact_unit_search and self.view_mode == "tech_impact":
             key = event.key()
             if key in (Qt.Key_Return, Qt.Key_Enter):
                self.focus_impact_unit_search = False
                self.update()
                return
             elif key == Qt.Key_Backspace:
                self.impact_unit_search = self.impact_unit_search[:-1]
                self.techimpact_scroll_offset = 0 
                self.update()
                return
             elif key == Qt.Key_Escape:
                self.impact_unit_search = ""
                self.focus_impact_unit_search = False
                self.techimpact_scroll_offset = 0
                self.update()
                return
             else:
                ch = event.text()
                if ch and ch.isprintable():
                    self.impact_unit_search += ch
                    self.techimpact_scroll_offset = 0
                    self.update()
             return
             
        # ----------------------------------------
        # GLOBAL SHORTCUTS
        # ----------------------------------------
        if key == Qt.Key_T and (modifiers & Qt.AltModifier):
            self._open_techtree_with_selected()
            return

    def wheelEvent(self, event):
        if not self.menu_visible:
            return
        handle_wheel(self, event)

    # -------------------------------------------------------------
    # MOUSE EVENTS
    # -------------------------------------------------------------
    def mousePressEvent(self, event):
        if not self.menu_visible:
            return

        pos = event.pos()

        # ==============================================================
        # 1. Tech Dropdown Selection (Priority)
        # ==============================================================
        if self.view_mode == "tech_impact" and self.tech_search_focus:
            for rect, tid in getattr(self, "tech_search_result_rects", []):
                if rect.contains(pos):
                    # Apply Selection
                    self.selected_tech_for_impact = tid
                    
                    # Update text box info
                    info = self.tech_light.get(tid, {})
                    self.tech_search = info.get("short_title", f"Tech {tid}")

                    # Close dropdown
                    self.tech_search_results = []
                    self.tech_search_result_rects = []
                    self.tech_search_focus = False

                    self.update()
                    return 

        # ------------------------------------------------------------------
        # 2. Focus Handling
        # ------------------------------------------------------------------
        if self.search_rect.contains(pos):
            self.focus_search = True
            self.tech_search_focus = False
            self.focus_impact_unit_search = False

        elif self.view_mode == "tech_impact" and self.tech_search_rect.contains(pos):
            self.focus_search = False
            self.tech_search_focus = True
            self.focus_impact_unit_search = False

        elif self.view_mode == "tech_impact" and hasattr(self, "impact_unit_search_rect") \
             and self.impact_unit_search_rect.contains(pos):
            self.focus_search = False
            self.tech_search_focus = False
            self.focus_impact_unit_search = True

        else:
            # Click elsewhere clears focus
            self.focus_search = False
            self.tech_search_focus = False
            self.focus_impact_unit_search = False

        # ------------------------------------------------------------------
        # 3. Unit List Click (with manual selection flag)
        # ------------------------------------------------------------------
        if self.view_mode == "compare" and self.unit_list_rect.contains(pos):
            # Calculate which unit was clicked
            btn = event.button()
            local_y = pos.y() - self.unit_list_rect.top()
            idx = (local_y // self.line_height) + self.unit_scroll_offset
            
            if 0 <= idx < len(self.filtered_units):
                u = self.filtered_units[idx]
                if btn == Qt.LeftButton:
                    # Manual selection - sets flag to prevent memory override
                    self.select_unit_b_manual(u)
                elif btn == Qt.RightButton:
                    self.selected_unit_c = u
                    self.active_techs["c"] = set(u.tech_ids) if hasattr(u, 'tech_ids') else set()
                elif btn == Qt.MiddleButton:
                    self.selected_unit_d = u
                    self.active_techs["d"] = set(u.tech_ids) if hasattr(u, 'tech_ids') else set()
                self.update()
                return  # Don't pass to handle_mouse_press

        # ------------------------------------------------------------------
        # 4. Standard Interactions (Tabs, Buttons, etc. - but not unit list)
        # ------------------------------------------------------------------
        handle_mouse_press(self, event)

        # ------------------------------------------------------------------
        # 4. Tech Impact Mode Interactions
        # ------------------------------------------------------------------
        if self.view_mode == "tech_impact":

            # A) Scrollbar Handle
            if hasattr(self, "techimpact_scrollbar_handle_rect") and \
               not self.techimpact_scrollbar_handle_rect.isNull() and \
               self.techimpact_scrollbar_handle_rect.contains(pos):
               
                self.techimpact_dragging = True
                self.techimpact_drag_offset = pos.y() - self.techimpact_scrollbar_handle_rect.top()
                self.update()
                return

            # B) Scrollbar Track
            if hasattr(self, "techimpact_scrollbar_track_rect") and \
               not self.techimpact_scrollbar_track_rect.isNull() and \
               self.techimpact_scrollbar_track_rect.contains(pos):
               
                track_top = self.techimpact_scrollbar_track_rect.top()
                track_h = self.techimpact_scrollbar_track_rect.height()
                
                if track_h > 0:
                    rel_y = pos.y() - track_top
                    ratio = rel_y / track_h
                    self.techimpact_scroll_offset = int(ratio * self.techimpact_max_scroll)
                    self.update()
                return

            # C) Unit Selection in Tech List
            btn = event.button()
            for uid, rect in self.techimpact_unit_rects.items():
                if rect.contains(pos):
                    u = self._get_unit_by_id(uid)
                    if btn == Qt.LeftButton:
                        self.selected_unit_b = u
                        self.manual_selection_b = True  # Mark as manual selection
                        self.active_techs["b"] = set(u.tech_ids) if hasattr(u, 'tech_ids') else set()
                    elif btn == Qt.RightButton:
                        self.selected_unit_d = u
                    elif btn == Qt.MiddleButton:
                        self.selected_unit_c = u
                    
                    self.focus_impact_unit_search = False
                    self.update()
                    return

        self.update()

    def mouseMoveEvent(self, event):
        if not self.menu_visible:
            return
        
        # Handle Scrollbar Drag
        if self.view_mode == "tech_impact" and self.techimpact_dragging:
            pos = event.pos()
            if hasattr(self, "techimpact_scroll_start_y"):
                relative_y = pos.y() - self.techimpact_scroll_start_y - self.techimpact_drag_offset
                track_h = self.techimpact_scrollbar_track_rect.height()
                handle_h = self.techimpact_scrollbar_handle_rect.height()
                available_h = track_h - handle_h
                
                if available_h > 0:
                    ratio = relative_y / available_h
                    ratio = max(0.0, min(1.0, ratio))
                    new_offset = int(ratio * self.techimpact_max_scroll)
                    if new_offset != self.techimpact_scroll_offset:
                        self.techimpact_scroll_offset = new_offset
                        self.update()
            return

    def mouseReleaseEvent(self, event):
        if self.techimpact_dragging:
            self.techimpact_dragging = False
            self.techimpact_drag_offset = 0
            self.update()

    # ------------------------------------------------------------- 
    # PAINTING
    # ------------------------------------------------------------- 
    def paintEvent(self, event):
        if not self.menu_visible:
            return

        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, False)

        full = self.rect()
        panel_w = 1100
        panel_h = full.height() - 60
        px = full.width() - panel_w - 20
        py = 30

        # Background
        bg_rect = QRect(px, py, panel_w, panel_h)
        p.setBrush(QColor(20, 25, 30, 240))
        p.setPen(QColor(0, 100, 160))
        p.drawRect(bg_rect)

        # Close button
        btn_size = 24
        self.close_btn_rect = QRect(px + panel_w - btn_size - 6, py + 6, btn_size, btn_size)
        p.setBrush(QColor(170, 40, 40))
        p.setPen(Qt.NoPen)
        p.drawRect(self.close_btn_rect)
        p.setPen(Qt.white)
        p.setFont(QFont("Segoe UI", 10, QFont.Bold))
        p.drawText(self.close_btn_rect, Qt.AlignCenter, "X")

        # Debug line
        debug_rect = QRect(px + 10, py + 6, panel_w - btn_size - 30, 20)
        p.setPen(QColor(170, 170, 170))
        p.setFont(QFont("Consolas", 9))
        rid = self.last_raw_selected_id if self.last_raw_selected_id is not None else "-"
        lock_txt = "LOCK" if self.lock_b else "lock"
        sync_txt = "MANUAL" if self.manual_selection_b else "SYNC"
        p.drawText(
            debug_rect,
            Qt.AlignVCenter | Qt.AlignLeft,
            f"ID:{rid} | B:{sync_txt} | L={lock_txt} | [L]ock [R]eset",
        )

        # Search bar (Units)
        self.search_rect = QRect(px + 10, py + 30, panel_w - 50, 26)
        p.setBrush(QColor(10, 10, 10))
        p.setPen(QColor(255, 200, 0) if self.focus_search else QColor(100, 100, 100))
        p.drawRect(self.search_rect)
        p.setPen(Qt.white)
        p.setFont(QFont("Consolas", 10))
        
        display_text = self.search_query
        # Blinking cursor effect
        if self.focus_search and (len(display_text) == 0 or (ctypes.windll.kernel32.GetTickCount() // 500) % 2 == 0):
             display_text += "|"
        elif not self.focus_search and not self.search_query:
             display_text = "Search Unit..."
             p.setPen(QColor(150, 150, 150))

        p.drawText(
            self.search_rect.adjusted(6, 0, 0, 0),
            Qt.AlignVCenter,
            display_text,
        )

        # Category buttons
        cats = ["all", "land", "air", "sea"]
        cx = px + 10
        cy = py + 30 + 26 + 4
        btn_w = (panel_w - 20) // 4
        self.category_button_rects = []
        p.setFont(QFont("Segoe UI", 9, QFont.Bold))
        for c in cats:
            cid = "naval" if c == "sea" else c
            r = QRect(cx, cy, btn_w - 2, 22)
            self.category_button_rects.append((r, cid))
            p.setBrush(QColor(0, 100, 180) if self.selected_category == cid else QColor(40, 40, 40))
            p.setPen(Qt.NoPen)
            p.drawRect(r)
            p.setPen(Qt.white)
            p.drawText(r, Qt.AlignCenter, c.upper())
            cx += btn_w

        # Unit list (Left Sidebar)
        list_y = cy + 22 + 4
        list_h = int(panel_h * 0.23)
        self.unit_list_rect = QRect(px + 10, list_y, panel_w - 20, list_h)
        p.setBrush(QColor(15, 15, 20))
        p.setPen(QColor(55, 55, 65))
        p.drawRect(self.unit_list_rect)
        draw_unit_list(self, p)

        # Stats area (Right Side)
        stats_y = list_y + list_h + 8
        stats_h = panel_h - (stats_y - py) - 8
        self.stats_rect = QRect(px + 10, stats_y, panel_w - 20, stats_h)
        p.setBrush(QColor(10, 12, 16))
        p.setPen(QColor(55, 55, 65))
        p.drawRect(self.stats_rect)
        draw_comparison_table(self, p, self.stats_rect)

    # -------------------------------------------------------------
    # HELPERS
    # -------------------------------------------------------------
    def _get_unit_by_id(self, uid: int):
        for u in self.units:
            if u.id == uid:
                return u
        return None
    
    def select_unit_b_manual(self, unit):
        """
        Select a unit in column B via manual click (from search list).
        Sets the manual_selection flag to prevent memory override.
        """
        if unit is None:
            return
        self.selected_unit_b = unit
        self.manual_selection_b = True
        if hasattr(unit, 'tech_ids'):
            self.active_techs["b"] = set(unit.tech_ids)
        self.update()
        
    def get_tech_modified_stats(self, unit, tech_id):
        """
        Returns only the unit values modified by the tech.
        Format: (attr, label, base, boosted)
        """
        info = self.tech_light.get(tech_id)
        if not info:
            return []

        rows = []

        for eff in info["effects"]:
            eid = eff["effect_id"]
            val = eff["value"]

            # --- CASE A: Boolean Effects (On/Off) ---
            if eid in BOOL_EFFECT_MAP:
                attr = BOOL_EFFECT_MAP[eid]
                base = getattr(unit, attr, 0)
                if base == 0:
                    label = TECH_LABEL_MAP.get(eid, attr.replace("_", " ").title())
                    rows.append((attr, label, 0.0, 1.0))
                continue

            # --- CASE B: Numeric Effects (Attack, Defense, etc.) ---
            if eid not in CORE_EFFECT_MAP:
                continue

            attr, mode = CORE_EFFECT_MAP[eid]
            label = TECH_LABEL_MAP.get(eid, f"{attr.capitalize()} ({eid})")

            base = getattr(unit, attr, None)
            if base is None:
                continue
            
            try:
                if mode == "mul":
                    boosted = base * (1.0 + float(val))
                else:
                    boosted = base + float(val)
            except Exception:
                continue

            if abs(boosted - base) < 0.001:
                continue

            rows.append((attr, label, base, boosted))

        return rows
        
    def build_tech_impact_unit_list(self, tech_id):
        """
        Returns a clean merged list of:
        - units affected by the tech (effects)
        - units unlocked by the tech (req_tech_id)
        Deduplicated, sorted, and labeled.
        """
        effect_units = []
        unlock_units = []

        # 1) Units with EFFECTS
        for u in self.units:
            effects = self.get_tech_modified_stats(u, tech_id)
            if effects:
                effect_units.append((u, effects))

        # 2) Units UNLOCKED by tech
        unlock_list = self.tech_unlocks.get(tech_id, [])
        for u in unlock_list:
            unlock_units.append((u, []))

        # 3) Merge + dedupe
        merged = {}

        # Units with effects first
        for u, eff in effect_units:
            merged[u.id] = {
                "unit": u,
                "effects": eff,
                "unlock": False
            }

        # Add unlocked units
        for u, eff in unlock_units:
            if u.id not in merged:
                merged[u.id] = {
                    "unit": u,
                    "effects": [],
                    "unlock": True
                }
            else:
                merged[u.id]["unlock"] = True

        # 4) Sort: effects first, then unlock
        final_list = list(merged.values())
        final_list.sort(key=lambda x: (not x["effects"], not x["unlock"], x["unit"].id))

        return final_list
        
    def _open_techtree_with_selected(self):
        """
        Open Tech Tree Analyzer and navigate to the selected tech.
        Uses file-based IPC for communication if analyzer is already running.
        Works both in development (Python) and compiled exe mode.
        """
        # Debug: show memory state
        print(f"[Overlay] Alt+T triggered. Reading tech from memory...")
        print(f"[Overlay]   pm={self.pm is not None}, base={hex(self.base_addr) if self.base_addr else 'None'}")
        
        tech_id = self._read_selected_tech_id()
        
        if tech_id is None:
            print("[Overlay] No tech selected in game (tech_id=None)")
            print("[Overlay]   Make sure you have a tech selected in the research screen")
            return
        
        print(f"[Overlay] Tech ID read from memory: {tech_id}")
        
        # --- Strategy 1: Use IPC if analyzer is already running ---
        if IPC_AVAILABLE and IPCClient.is_server_running():
            print("[Overlay] Analyzer already running, sending NAVIGATE via IPC...")
            if IPCClient.send_navigate(tech_id):
                print(f"[Overlay] SUCCESS: Sent NAVIGATE:{tech_id} (includes focus)")
                return
            else:
                print("[Overlay] IPC write failed, will launch new instance")
        else:
            if not IPC_AVAILABLE:
                print("[Overlay] IPC not available (ipc_bridge.py missing)")
            else:
                print("[Overlay] Analyzer not running, will launch new instance")
        
        # --- Strategy 2: Launch new analyzer process ---
        
        # Clean up previous process if dead
        if self.analyzer_process is not None:
            if self.analyzer_process.poll() is not None:
                # Process has terminated, clear reference
                self.analyzer_process = None
        
        # If process is still running but IPC failed, terminate it
        if self.analyzer_process is not None:
            if self.analyzer_process.poll() is None:
                print("[Overlay] Terminating unresponsive analyzer process...")
                try:
                    self.analyzer_process.terminate()
                    self.analyzer_process.wait(timeout=2)
                except Exception:
                    try:
                        self.analyzer_process.kill()
                    except:
                        pass
                self.analyzer_process = None
        
        # --- Detect if running as compiled exe ---
        is_frozen = getattr(sys, 'frozen', False)
        
        if is_frozen:
            # Running as compiled exe - look for tech_tree_analyzer.exe
            # PyInstaller sets sys._MEIPASS for temp extraction, but exe is in original dir
            exe_dir = Path(sys.executable).parent
            
            exe_candidates = [
                exe_dir / "tech_tree_analyzer" / "tech_tree_analyzer.exe",  # Subfolder (build_all.bat)
                exe_dir / "tech_tree_analyzer.exe",                          # Same folder
            ]
            
            analyzer_exe = None
            for p in exe_candidates:
                print(f"[Overlay] Checking for analyzer exe: {p}")
                if p.exists():
                    analyzer_exe = str(p)
                    break
            
            if not analyzer_exe:
                print("[Overlay] ERROR: tech_tree_analyzer.exe not found!")
                print(f"[Overlay]   Searched in: {exe_dir}")
                return
            
            try:
                print(f"[Overlay] Launching compiled analyzer: {analyzer_exe}")
                self.analyzer_process = subprocess.Popen([
                    analyzer_exe,
                    "--select-tech", str(tech_id)
                ])
                
                # Wait for IPC server
                if IPC_AVAILABLE and wait_for_server:
                    if wait_for_server(timeout=5.0):
                        print("[Overlay] Analyzer IPC server is ready")
                    else:
                        print("[Overlay] Analyzer started but IPC server not responding")
                        
            except Exception as e:
                print(f"[Overlay] Failed to launch analyzer exe: {e}")
                self.analyzer_process = None
        
        else:
            # Running as Python script - use sys.executable (Python interpreter)
            script_candidates = [
                Path(__file__).parent / "tech_tree_analyzer.py",
                Path(__file__).parent / "tech_tree_analyzer_v2_1.py",
            ]
            
            script_path = None
            for p in script_candidates:
                if p.exists():
                    script_path = str(p)
                    break
            
            if not script_path:
                print("[Overlay] ERROR: Tech Tree Analyzer script not found.")
                return
            
            try:
                print(f"[Overlay] Launching Tech Tree Analyzer: {script_path}")
                self.analyzer_process = subprocess.Popen([
                    sys.executable,
                    script_path,
                    "--select-tech", str(tech_id)
                ])
                
                # If IPC available, wait for server to come up for future commands
                if IPC_AVAILABLE and wait_for_server:
                    if wait_for_server(timeout=5.0):
                        print("[Overlay] Analyzer IPC server is ready")
                    else:
                        print("[Overlay] Analyzer started but IPC server not responding")
                        
            except Exception as e:
                print(f"[Overlay] Failed to launch Tech Tree Analyzer: {e}")
                self.analyzer_process = None

if __name__ == "__main__":
    app = QApplication(sys.argv)
    overlay = OverlayINS()
    sys.exit(app.exec_())