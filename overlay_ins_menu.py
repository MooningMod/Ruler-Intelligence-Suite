import sys
import ctypes
from pathlib import Path

from PyQt5.QtCore import Qt, QRect, QTimer
from PyQt5.QtGui import QPainter, QColor, QFont
from PyQt5.QtWidgets import QWidget, QApplication

try:
    import pymem
    import pymem.process
except ImportError:
    pymem = None
    print("[Memory] WARNING: pymem is not installed. Selected unit reading is disabled.")

from unit_parser import parse_default_unit, Unit
from tech_parser import load_tech_file

from painters import draw_unit_list, draw_comparison_table
# Gestione eventi
from events import handle_mouse_press, handle_wheel

class OverlayINS(QWidget):
    """
    Supreme Ruler 2030 - 3-way unit comparison overlay.
    """

    SELECTED_UNIT_OFFSET = 0x1767628  # from Cheat Engine

    def __init__(self, default_unit_path: str | None = None, default_ttrx_path: str | None = None):
        super().__init__()

        # Data
        self.units: list[Unit] = []
        self.filtered_units: list[Unit] = []

        # Selection slots
        self.selected_unit_b: Unit | None = None
        self.selected_unit_c: Unit | None = None
        self.selected_unit_d: Unit | None = None

        # Tech data (da DEFAULT.TTRX)
        self.tech_light: dict[int, dict] = {}
        self.tech_full: dict[int, dict] = {}

        # Stato tech attive per B/C/D
        self.active_techs: dict[str, set[int]] = {
            "b": set(),
            "c": set(),
            "d": set(),
        }

        # Checkbox rects per tech
        self.tech_checkbox_rects: dict[str, dict[int, QRect]] = {
            "b": {},
            "c": {},
            "d": {},
        }

        # Lock & control buttons
        self.lock_b: bool = False
        self.btn_lock_rect = QRect()
        self.btn_b_to_c_rect = QRect()
        self.btn_c_to_d_rect = QRect()

        # Filters
        self.search_query: str = ""
        self.selected_category: str = "all"
        self.focus_search: bool = False
        
        # Scrolling
        self.line_height = 22
        self.unit_scroll_offset = 0       
        self.stats_scroll_offset = 0      
        self.max_stats_scroll = 0         

        # Rects
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
        
        # Tech Search Box 
        self.tech_search = ""
        self.tech_search_focus = False
        self.tech_search_results = []    
        self.tech_search_max_display = 6 
        
        self.tech_search_rect = QRect()
        self.tech_search_result_rects = []
        self.techimpact_unit_rects = {}
        
        # Scroll Tech Impact
        self.techimpact_scroll_offset = 0
        self.techimpact_max_scroll = 0

        # Visibility & input
        self.menu_visible = False
        self.key_was_pressed = False

        # Memory
        self.pm = None
        self.base_addr = None
        self.last_raw_selected_id: int | None = None

        # Init
        self.init_window()
        self.load_units(default_unit_path)
        # FIX: passiamo l'argomento alla funzione load_techs
        self.load_techs(default_ttrx_path)
        self.update_filter()
        self._attach_process()

        # Timer loop (RIPORTATO A 30ms per fluidità interfaccia)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.game_loop)
        self.timer.start(30) 

        print("-" * 60)
        print("SR2030 - INS Overlay (Fixed Version)")
        print("-" * 60)

    # ------------------------------------------------------------------ Memory
    def _attach_process(self):
        if pymem is None:
            return
        try:
            self.pm = pymem.Pymem("SupremeRuler2030.exe")
            mod = pymem.process.module_from_name(self.pm.process_handle, "SupremeRuler2030.exe")
            self.base_addr = mod.lpBaseOfDll
            print(f"[Memory] Attached to SR2030, base = {hex(self.base_addr)}")
        except Exception as e:
            print(f"[Memory] Could not attach to process: {e}")
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
            addr = self.base_addr + self.SELECTED_UNIT_OFFSET
            val = self.pm.read_int(addr)
            self.last_raw_selected_id = val
            if val <= 0:
                return None
            return val
        except Exception as e:
            self.pm = None
            self.base_addr = None
            return None

    def _read_selected_unit_obj(self) -> Unit | None:
        uid = self._read_selected_unit_raw()
        if uid is None:
            return None
        for u in self.units:
            if u.id == uid:
                return u
        return None

    # ------------------------------------------------------------ Game / loop
    def game_loop(self):
        # Hotkey (INS)
        try:
            pressed = (ctypes.windll.user32.GetAsyncKeyState(0x2D) & 0x8000)
            if pressed:
                if not self.key_was_pressed:
                    self.toggle_menu()
                    self.key_was_pressed = True
            else:
                self.key_was_pressed = False
        except Exception:
            pass

        # Aggiorna colonna B dalla unit selezionata in gioco SOLO se non lockata
        if self.menu_visible and not self.lock_b:
            u = self._read_selected_unit_obj()
            if u:
                if self.selected_unit_b is None or self.selected_unit_b.id != u.id:
                    self.selected_unit_b = u
                    self.active_techs["b"] = set(u.tech_ids)
                    self.update()

    # ------------------------------------------------------------- Init / load
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
        """Carica il tech tree. Accetta un path opzionale."""
        paths = []
        
        # 1. Path passato da argomento
        if default_ttrx_path:
            paths.append(Path(default_ttrx_path))
            
        # 2. Path standard di Steam
        paths.append(Path(r"C:\Program Files (x86)\Steam\steamapps\common\Supreme Ruler 2030\Maps\DATA\DEFAULT.TTRX"))
        
        # 3. Path locale
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

    # --------------------------------------------------------------- Filtering
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

    # -------------------------------------------------------------- Toggle UI
    def toggle_menu(self):
        if not self.menu_visible:
            self.menu_visible = True
            u = self._read_selected_unit_obj()
            if u:
                self.selected_unit_b = u
                self.active_techs["b"] = set(u.tech_ids)
            self.show()
            self.activateWindow()
            self.raise_()
        else:
            self.menu_visible = False
            self.hide()
            self.focus_search = False

    # ------------------------------------------------------------- Qt events
    def keyPressEvent(self, event):
        if not self.menu_visible:
            return

        # Toggle Lock B
        if not self.focus_search and not self.tech_search_focus and event.key() == Qt.Key_L:
            self.lock_b = not self.lock_b
            self.update()
            return

        # Gestione Search Bar Units
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
            
        # Tech Search Box Focus
        if self.tech_search_focus and self.view_mode == "tech_impact":
             
             key = event.key()
             if key in (Qt.Key_Return, Qt.Key_Enter):
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

    def wheelEvent(self, event):
        if not self.menu_visible:
            return
        handle_wheel(self, event)

    def mousePressEvent(self, event):
        if not self.menu_visible:
            return
        
        pos = event.pos()
        
        # Check focus search units
        if self.search_rect.contains(pos):
            self.focus_search = True
            self.tech_search_focus = False
            self.update()
            return
        else:
            self.focus_search = False

        handle_mouse_press(self, event)
        self.update()
        
        # click in tech impact
        if self.view_mode == "tech_impact":
            for uid, rect in self.techimpact_unit_rects.items():
                if rect.contains(pos):
                    u = self._get_unit_by_id(uid)
                    btn = event.button()

                    if btn == Qt.LeftButton:
                        # LEFT → B
                        self.selected_unit_b = u

                    elif btn == Qt.RightButton:
                        # RIGHT → D
                        self.selected_unit_d = u

                    elif btn == Qt.MiddleButton:
                        # REAL MIDDLE CLICK → C
                        self.selected_unit_c = u

                    if event.buttons() & Qt.MiddleButton:
                        self.selected_unit_c = u
                        
                    self.update()
                    return
    # ------------------------------------------------------------- Painting UI
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
        lock_txt = "LOCK B: ON" if self.lock_b else "LOCK B: OFF"
        p.drawText(
            debug_rect,
            Qt.AlignVCenter | Qt.AlignLeft,
            f"Selected ID (raw): {rid}   | {lock_txt}   | L=B  R=C  M=D",
        )

        # Search bar (normale)
        self.search_rect = QRect(px + 10, py + 30, panel_w - 50, 26)
        p.setBrush(QColor(10, 10, 10))
        # Bordo giallo se attivo
        p.setPen(QColor(255, 200, 0) if self.focus_search else QColor(100, 100, 100))
        p.drawRect(self.search_rect)
        p.setPen(Qt.white)
        p.setFont(QFont("Consolas", 10))
        
        display_text = self.search_query
        if self.focus_search and (len(display_text) == 0 or (ctypes.windll.kernel32.GetTickCount() // 500) % 2 == 0):
             display_text += "|"
        elif not self.focus_search and not self.search_query:
             display_text = "Search Name or ID..."
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

        # Unit list
        list_y = cy + 22 + 4
        list_h = int(panel_h * 0.23)
        self.unit_list_rect = QRect(px + 10, list_y, panel_w - 20, list_h)
        p.setBrush(QColor(15, 15, 20))
        p.setPen(QColor(55, 55, 65))
        p.drawRect(self.unit_list_rect)
        draw_unit_list(self, p)

        # Stats area
        stats_y = list_y + list_h + 8
        stats_h = panel_h - (stats_y - py) - 8
        self.stats_rect = QRect(px + 10, stats_y, panel_w - 20, stats_h)
        p.setBrush(QColor(10, 12, 16))
        p.setPen(QColor(55, 55, 65))
        p.drawRect(self.stats_rect)
        draw_comparison_table(self, p, self.stats_rect)
    def _get_unit_by_id(self, uid: int):
        """Return unit object by SR2030 ID"""
        for u in self.units:
            if u.id == uid:
                return u
        return None

        
if __name__ == "__main__":
    app = QApplication(sys.argv)
    overlay = OverlayINS()
    sys.exit(app.exec_())