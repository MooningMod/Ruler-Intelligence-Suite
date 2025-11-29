import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import subprocess
import psutil
import json
import os
import sys
import threading
import logging
import time
import csv
import atexit
import psutil
from datetime import datetime, timedelta
from pathlib import Path

# ---- External Dependencies ----
# Optional but strongly recommended:
#   pip install Pillow
try:
    from PIL import Image, ImageTk
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

# ---- Local modules ----
from memory_reader import MemoryReader
from data_logger import log_to_csv, get_log_file_path, get_existing_logs
from analytics import show_simple_analytics

# ---- Constants ----
PROCESS_NAME = "SupremeRuler2030.exe"
STEAM_APP_ID = "2093410"

BASE_DIR = Path.home() / "Documents" / "SR2030_Logger"
LOGS_DIR = BASE_DIR / "logs"
ASSETS_DIR = BASE_DIR  # Where we expect background.png

BASE_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

CONFIG_PATH = BASE_DIR / "config.json"
LOG_FILE_PATH = BASE_DIR / "debug.log"
BACKGROUND_IMAGE_PATH = ASSETS_DIR / "background.png"

# ---- Logging setup ----
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE_PATH, encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)
logging.getLogger("pymem").setLevel(logging.WARNING)

# ---- Global state ----
logging_active = False
logging_started = False
stop_event = threading.Event()
overlay_process = None
current_csv_path = None

# Shared config between UI and worker thread
live_config = {}

# ============================================================
# CONFIG MANAGEMENT
# ============================================================

def load_config():
    """Load configuration from disk, falling back to sane defaults."""
    defaults = {
        "steam_id": STEAM_APP_ID,
        "default_unit_path": r"C:/Program Files (x86)/Steam/steamapps/common/Supreme Ruler 2030/Maps/DATA/DEFAULT.UNIT",
        "default_ttrx_path": r"C:/Program Files (x86)/Steam/steamapps/common/Supreme Ruler 2030/Maps/DATA/DEFAULT.TTRX",
        "default_spotting_path": r"C:/Program Files (x86)/Steam/steamapps/common/Supreme Ruler 2030/Maps/DATA/Spotting.csv",
        "save_mode": "Daily",
        "polling_interval": 1.0,  # Default polling, works well even at higher game speeds
        "game_version": "FastTrack",
        "start_date": "2030-01-01",
        "current_date": "2030-01-01",
        "game_name": "",
        "nation": "",
        "enable_overlay": True,
        "enable_logger": True,
    }

    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                saved = json.load(f)
                defaults.update(saved)
        except Exception:
            logger.error("Config file looks corrupted. Using defaults and overwriting on next save.")

    global live_config
    live_config = defaults.copy()
    return defaults


def save_config(config: dict):
    """Persist configuration and keep the in-memory copy in sync."""
    try:
        global live_config
        live_config = config.copy()
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4)
        logger.info("Configuration saved successfully.")
    except Exception as e:
        logger.error(f"Failed to save config: {e}")

# ============================================================
# HELPER FUNCTIONS
# ============================================================

def set_high_priority():
    """Raise this process to high priority to reduce throttling when minimized."""
    try:
        p = psutil.Process(os.getpid())
        p.nice(psutil.HIGH_PRIORITY_CLASS)
        logger.info("Process priority set to HIGH.")
    except Exception as e:
        logger.warning(f"Could not set high priority: {e}")


def is_game_running() -> bool:
    """Return True if the Supreme Ruler 2030 process is currently alive."""
    try:
        return any((p.info.get('name') or '').lower() == PROCESS_NAME.lower()
                   for p in psutil.process_iter(['name']))
    except Exception:
        return False


def launch_game_steam(app_id: str) -> bool:
    """Ask Steam to start the game using the steam:// URI."""
    try:
        os.startfile(f"steam://run/{app_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to launch via Steam: {e}")
        return False


def day_signature(sample: dict) -> str:
    """
    Build a simple "signature" for the current day based on game stats.
    As Treasury and Population change deterministically, this is enough
    to detect a day rollover without accessing the in-game date.
    """
    t = sample.get("Treasury")
    p = sample.get("Population")
    if t is None or p is None:
        return "N/A"
    try:
        return f"T:{int(float(t))}_P:{int(float(p))}"
    except Exception:
        return "N/A"


def get_last_date_from_csv(file_path: Path) -> str | None:
    """
    Inspect the last non-empty line of the CSV and try to parse the game date.
    This is used when resuming a previous campaign log.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f.readlines() if line.strip()]

        if len(lines) < 2:
            return None

        last_line = lines[-1].lstrip("\ufeff")
        parts = last_line.split(",")

        # GameDate should be column index 2
        if len(parts) >= 3:
            candidate = parts[2].replace('"', "").replace("'", "").strip()
            try:
                datetime.strptime(candidate, "%Y-%m-%d")
                return candidate
            except ValueError:
                pass
        return None
    except Exception as e:
        logger.error(f"Error reading CSV date: {e}")
        return None


def should_save(mode: str, current_date: str, last_saved_date: str | None) -> bool:
    """
    Decide whether to write a new row depending on the chosen save granularity.
    Modes: Daily, Weekly, Monthly.
    """
    if not last_saved_date:
        return True

    try:
        d_curr = datetime.strptime(current_date, "%Y-%m-%d")
        d_last = datetime.strptime(last_saved_date, "%Y-%m-%d")

        if mode == "Daily":
            return d_curr > d_last
        elif mode == "Weekly":
            return (d_curr.isocalendar()[1], d_curr.year) != (d_last.isocalendar()[1], d_last.year)
        elif mode == "Monthly":
            return (d_curr.month, d_curr.year) != (d_last.month, d_last.year)
        return False
    except Exception:
        # If parsing fails, err on the side of saving.
        return True

# ============================================================
# OVERLAY MANAGEMENT
# ============================================================

def launch_overlay(config: dict):
    """
    Start the INS overlay process if it is not already running.
    Passes DEFAULT.UNIT, DEFAULT.TTRX, and Spotting.csv paths when available.
    """
    global overlay_process
    
    logger.info("=" * 60)
    logger.info("OVERLAY LAUNCH REQUESTED")
    logger.info("=" * 60)
    
    try:
        # Check if already running
        if overlay_process and overlay_process.poll() is None:
            logger.info("Overlay process already running, skipping launch.")
            return

        # Find run_overlay.py
        script_dir = Path(__file__).parent
        run_overlay = script_dir / "run_overlay.py"
        
        logger.info(f"Script directory: {script_dir}")
        logger.info(f"Looking for: {run_overlay}")
        logger.info(f"File exists: {run_overlay.exists()}")
        
        if not run_overlay.exists():
            logger.error("run_overlay.py not found, overlay will not be started.")
            logger.error(f"Expected location: {run_overlay}")
            return

        # Build command
        cmd = [sys.executable, str(run_overlay)]
        logger.info(f"Python executable: {sys.executable}")

        # Add paths only if they exist
        unit_path = config.get("default_unit_path", "")
        logger.info(f"Unit path from config: '{unit_path}'")
        if unit_path and os.path.exists(unit_path):
            cmd.extend(["--default-unit", unit_path])
            logger.info(f"✓ Passing DEFAULT.UNIT: {unit_path}")
        else:
            logger.info(f"✗ Unit path not valid or not found")

        ttrx_path = config.get("default_ttrx_path", "")
        logger.info(f"TTRX path from config: '{ttrx_path}'")
        if ttrx_path and os.path.exists(ttrx_path):
            cmd.extend(["--default-ttrx", ttrx_path])
            logger.info(f"✓ Passing DEFAULT.TTRX: {ttrx_path}")
        else:
            logger.info(f"✗ TTRX path not valid or not found")

        spotting_path = config.get("default_spotting_path", "")
        logger.info(f"Spotting path from config: '{spotting_path}'")
        if spotting_path and os.path.exists(spotting_path):
            cmd.extend(["--default-spotting", spotting_path])
            logger.info(f"✓ Passing Spotting.csv: {spotting_path}")
        else:
            logger.info(f"✗ Spotting path not configured or not found, overlay will use fallback paths")

        logger.info(f"Full command: {cmd}")
        logger.info(f"Working directory: {script_dir}")
        
        # Launch process
        logger.info("Attempting to start overlay process...")
        
        if os.name == 'nt':
            import subprocess
            CREATE_NO_WINDOW = 0x08000000
            overlay_process = subprocess.Popen(
                cmd, 
                cwd=str(script_dir),
                creationflags=CREATE_NO_WINDOW,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
        else:
            overlay_process = subprocess.Popen(
                cmd, 
                cwd=str(script_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
        
        logger.info(f"✓ Overlay process started with PID: {overlay_process.pid}")
        
        # Check if process is still alive after a moment
        time.sleep(0.5)
        poll_result = overlay_process.poll()
        if poll_result is not None:
            logger.error(f"✗ Overlay process terminated immediately with exit code: {poll_result}")
            stdout, stderr = overlay_process.communicate()
            if stdout:
                logger.error(f"STDOUT: {stdout.decode('utf-8', errors='replace')}")
            if stderr:
                logger.error(f"STDERR: {stderr.decode('utf-8', errors='replace')}")
        else:
            logger.info("✓ Overlay process is running successfully")
            
    except Exception as e:
        logger.error(f"✗ Failed to launch overlay: {e}")
        import traceback
        logger.error(traceback.format_exc())
    
    logger.info("=" * 60)

# ============================================================
# LOGGING THREAD
# ============================================================

def logging_worker(initial_config: dict, app_instance):
    """
    Main logging loop running in a separate thread.
    - Attaches once to the game process.
    - Polls memory at a configurable interval.
    - Detects day changes via a signature.
    - Writes periodic snapshots to CSV.
    """
    global logging_active, stop_event, current_csv_path, live_config

    set_high_priority()

    logging_active = True
    stop_event.clear()

    current_conf = live_config.copy()

    game_name = current_conf.get("game_name", "").strip()
    nation = current_conf.get("nation", "").strip()
    current_date_str = current_conf.get("current_date", "2030-01-01")

    try:
        current_date_obj = datetime.strptime(current_date_str, "%Y-%m-%d")
    except ValueError:
        current_date_obj = datetime(2030, 1, 1)

    csv_path = get_log_file_path(game_name, nation, use_timestamp=False)
    current_csv_path = csv_path

    last_sig = None
    last_saved_date = None

    reader = MemoryReader(PROCESS_NAME, current_conf.get("game_version", "FastTrack"))
    if not reader.attach():
        logger.info("Waiting for game process to attach...")

    logger.info("🚀 Logger started.")
    logger.info(f"📅 Start Date: {current_date_str}")

    while not stop_event.is_set():
        poll_interval = float(live_config.get("polling_interval", 1.0))
        save_mode = live_config.get("save_mode", "Daily")

        if not is_game_running():
            logger.info("⚠️ Game process not found anymore. Stopping logger.")
            break

        data = reader.read_snapshot()

        if data and data.get("Treasury") is not None:
            sig = day_signature(data)

            # First sample: just initialize the reference signature.
            if last_sig is None:
                last_sig = sig
                time.sleep(poll_interval)
                continue

            # New day detected
            if sig != last_sig:
                current_date_obj += timedelta(days=1)
                current_date_str = current_date_obj.strftime("%Y-%m-%d")

                # Update UI in the main thread
                app_instance.root.after(0, lambda d=current_date_str: app_instance.date_var.set(d))
                live_config["current_date"] = current_date_str

                # Only save when required by the selected mode
                if should_save(save_mode, current_date_str, last_saved_date):
                    payload = data.copy()
                    payload["game_name"] = game_name
                    payload["nation"] = nation

                    if log_to_csv(csv_path, payload, current_date_str):
                        last_saved_date = current_date_str
                        app_instance.root.after(
                            0,
                            lambda d=current_date_str: app_instance.update_last_saved(d),
                        )
                    else:
                        logger.error(f"❌ Failed to save row for day {current_date_str}")

                last_sig = sig

        time.sleep(poll_interval)

    logger.info("🛑 Logger stopped.")

    # Persist final date back into config.
    live_config["current_date"] = current_date_str
    save_config(live_config)

    logging_active = False
    current_csv_path = None
    app_instance.root.after(0, app_instance.on_logger_stopped)

# ============================================================
# SETTINGS DIALOG
# ============================================================

class SettingsDialog:
    """Small modal window for advanced logger parameters."""

    def __init__(self, parent, config):
        self.config = config
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Ruler Intelligence Suite – Settings")
        self.dialog.geometry("500x530")
        self.dialog.transient(parent)
        self.dialog.grab_set()

        main = ttk.Frame(self.dialog, padding=20)
        main.pack(fill=tk.BOTH, expand=True)

        # Save mode
        ttk.Label(main, text="Save Protocol:", font=("Courier New", 10, "bold")).grid(
            row=0, column=0, sticky="w", pady=5
        )
        mode_var = tk.StringVar(value=config.get("save_mode", "Daily"))
        ttk.Radiobutton(main, text="Daily", variable=mode_var, value="Daily").grid(
            row=1, column=0, sticky="w", padx=20
        )
        ttk.Radiobutton(main, text="Weekly", variable=mode_var, value="Weekly").grid(
            row=2, column=0, sticky="w", padx=20
        )
        ttk.Radiobutton(main, text="Monthly", variable=mode_var, value="Monthly").grid(
            row=3, column=0, sticky="w", padx=20
        )

        # Polling interval
        ttk.Label(
            main,
            text="Polling Interval (seconds):",
            font=("Courier New", 10, "bold"),
        ).grid(row=4, column=0, sticky="w", pady=(15, 5))
        ttk.Label(
            main,
            text="Lower = smoother days, higher CPU (0.1s–10.0s).",
            font=("Courier New", 8),
            foreground="gray",
        ).grid(row=5, column=0, sticky="w", padx=20)

        interval_var = tk.DoubleVar(value=config.get("polling_interval", 1.0))
        scale = ttk.Scale(
            main,
            from_=0.1,
            to=10.0,
            variable=interval_var,
            orient="horizontal",
            length=200,
        )
        scale.grid(row=6, column=0, sticky="w", padx=20)

        val_label = ttk.Label(main, text=f"{interval_var.get():.2f}s")
        val_label.grid(row=6, column=1)

        def update_lbl(val):
            val_label.config(text=f"{float(val):.2f}s")

        scale.configure(command=update_lbl)

        # Game version
        ttk.Label(
            main,
            text="Target Version:",
            font=("Courier New", 10, "bold"),
        ).grid(row=7, column=0, sticky="w", pady=(15, 5))
        version_var = tk.StringVar(value=config.get("game_version", "FastTrack"))
        ttk.Combobox(
            main,
            textvariable=version_var,
            values=["FastTrack", "BasePatch"],
            state="readonly",
            width=15,
        ).grid(row=8, column=0, sticky="w", padx=20)

        # Paths
        # DEFAULT.UNIT PATH
        ttk.Label(
            main,
            text="DEFAULT.UNIT path:",
            font=("Courier New", 10, "bold"),
        ).grid(row=9, column=0, sticky="w", pady=(15, 5))

        unit_var = tk.StringVar(value=config.get("default_unit_path", ""))

        unit_frame = ttk.Frame(main)
        unit_frame.grid(row=10, column=0, columnspan=2, sticky="ew", padx=20)

        ttk.Entry(unit_frame, textvariable=unit_var, width=40).pack(side="left", fill="x", expand=True)
        ttk.Button(unit_frame, text="Browse...", command=lambda: self.browse_unit(unit_var)).pack(side="left", padx=(10, 0))

        # DEFAULT.TTRX PATH
        ttk.Label(
            main,
            text="DEFAULT.TTRX path:",
            font=("Courier New", 10, "bold"),
        ).grid(row=11, column=0, sticky="w", pady=(15, 5))

        ttrx_var = tk.StringVar(value=config.get("default_ttrx_path", ""))

        ttrx_frame = ttk.Frame(main)
        ttrx_frame.grid(row=12, column=0, columnspan=2, sticky="ew", padx=20)

        ttk.Entry(ttrx_frame, textvariable=ttrx_var, width=40).pack(side="left", fill="x", expand=True)
        ttk.Button(ttrx_frame, text="Browse...", command=lambda: self.browse_ttrx(ttrx_var)).pack(side="left", padx=(10, 0))

        # SPOTTING.CSV PATH
        ttk.Label(
            main,
            text="Spotting.csv path:",
            font=("Courier New", 10, "bold"),
        ).grid(row=13, column=0, sticky="w", pady=(15, 5))

        spotting_var = tk.StringVar(value=config.get("default_spotting_path", ""))

        spotting_frame = ttk.Frame(main)
        spotting_frame.grid(row=14, column=0, columnspan=2, sticky="ew", padx=20)

        ttk.Entry(spotting_frame, textvariable=spotting_var, width=40).pack(side="left", fill="x", expand=True)
        ttk.Button(spotting_frame, text="Browse...", command=lambda: self.browse_spotting(spotting_var)).pack(side="left", padx=(10, 0))


        def save():
            config["save_mode"] = mode_var.get()
            config["polling_interval"] = round(interval_var.get(), 2)
            config["game_version"] = version_var.get()
            config["default_unit_path"] = unit_var.get()
            config["default_ttrx_path"] = ttrx_var.get()
            config["default_spotting_path"] = spotting_var.get()
            save_config(config)
            messagebox.showinfo("Saved", "Configuration updated.")
            self.dialog.destroy()

        btn_frame = ttk.Frame(self.dialog)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)
        ttk.Button(btn_frame, text="Confirm", command=save).pack(side=tk.RIGHT)
        ttk.Button(btn_frame, text="Abort", command=self.dialog.destroy).pack(
            side=tk.RIGHT, padx=5
        )

    def browse_unit(self, var):
        filepath = filedialog.askopenfilename(
            title="Select DEFAULT.UNIT",
            filetypes=[("UNIT file", "*.UNIT"), ("All files", "*.*")]
        )
        if filepath:
            var.set(filepath)
            self.config["default_unit_path"] = filepath
            save_config(self.config)

    def browse_ttrx(self, var):
        filepath = filedialog.askopenfilename(
            title="Select DEFAULT.TTRX",
            filetypes=[("TTRX file", "*.TTRX"), ("All files", "*.*")]
        )
        if filepath:
            var.set(filepath)
            self.config["default_ttrx_path"] = filepath
            save_config(self.config)

    def browse_spotting(self, var):
        filepath = filedialog.askopenfilename(
            title="Select Spotting.csv",
            filetypes=[("CSV file", "*.csv"), ("All files", "*.*")]
        )
        if filepath:
            var.set(filepath)
            self.config["default_spotting_path"] = filepath
            save_config(self.config)

# ============================================================
# MAIN APP
# ============================================================

class App:
    """Main Tkinter application for the Ruler Intelligence Suite."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Ruler Intelligence Suite | Strategic Analysis Directorate. ALPHA v.0.1. By Mooning")
        # Sized to match the vertical clipboard / paper background
        self.root.geometry("600x730")
        self.root.resizable(False, False)

        self.config = load_config()
        self.is_monitoring = False
        self.game_running = False
        self.bg_image_ref = None  # keep a reference to avoid GC

        self.date_var = tk.StringVar(value=self.config.get("current_date", "2030-01-01"))
        self.game_name_var = tk.StringVar(value=self.config.get("game_name", ""))
        self.nation_var = tk.StringVar(value=self.config.get("nation", ""))
        self.overlay_var = tk.BooleanVar(value=self.config.get("enable_overlay", True))
        self.last_saved_var = tk.StringVar(value="No data acquired")

        self.setup_style()
        self.setup_ui()

    # ---------------- UI STYLE ----------------

    def setup_style(self):
        """Configure a simple 'classified dossier' style: paper, typewriter, stamps."""
        style = ttk.Style()
        style.theme_use("clam")  # works well with custom colors

        PAPER_COLOR = "#E3DAC9"   # warm paper
        TEXT_COLOR = "#2A2A2A"    # ink
        BUTTON_COLOR = "#D1C7B7"  # slightly darker paper
        ACTIVE_COLOR = "#C0B5A5"  # pressed button

        style.configure(".", background=PAPER_COLOR, foreground=TEXT_COLOR, font=("Courier New", 10))
        style.configure("TLabel", background=PAPER_COLOR, foreground=TEXT_COLOR)
        style.configure("TFrame", background=PAPER_COLOR)
        style.configure("TLabelframe", background=PAPER_COLOR, bordercolor="#555555")
        style.configure(
            "TLabelframe.Label",
            background=PAPER_COLOR,
            foreground="#550000",
            font=("Courier New", 12, "bold"),
        )

        style.configure(
            "TButton",
            background=BUTTON_COLOR,
            foreground=TEXT_COLOR,
            borderwidth=1,
            font=("Courier New", 10, "bold"),
        )
        style.map("TButton", background=[("active", ACTIVE_COLOR)])

        style.configure("TSeparator", background="#555555")
        style.configure("TCheckbutton", background=PAPER_COLOR)

    # ---------------- UI LAYOUT ----------------

    def setup_ui(self):
        """Build the entire intelligence-themed UI using compact mode."""

        # ============================================================
        # 1) BACKGROUND (paper image or fallback color)
        # ============================================================
        self._add_background()

        # ============================================================
        # 2) MAIN CONTAINER (reduced margins for compact mode)
        # ============================================================
        main_container = ttk.Frame(self.root)
        main_container.pack(fill=tk.BOTH, expand=True, padx=25, pady=25)

        # Store reference for subsequent block builders
        self._main_container = main_container

        # ============================================================
        # 3) HEADER AREA (title + status + launch button)
        # ============================================================
        self._add_header_area()

        # ============================================================
        # 4) LOGGER AREA (mission parameters)
        # ============================================================
        self._add_logger_area()

        # ============================================================
        # 5) TOOLS AREA (config + analytics)
        # ============================================================
        self._add_tools_area()


    # =====================================================================
    # BACKGROUND LAYER
    #=====================================================================

    def _add_background(self):
        """Place the paper background or fallback to plain color."""
        if HAS_PIL and BACKGROUND_IMAGE_PATH.exists():
            try:
                raw_img = Image.open(BACKGROUND_IMAGE_PATH)
                raw_img = raw_img.resize((600, 800), Image.Resampling.LANCZOS)
                self.bg_image_ref = ImageTk.PhotoImage(raw_img)

                bg_label = tk.Label(self.root, image=self.bg_image_ref)
                bg_label.place(x=0, y=0, relwidth=1, relheight=1)
            except Exception as e:
                logger.error(f"Failed to load background image: {e}")
                self.root.configure(bg="#E3DAC9")
        else:
            self.root.configure(bg="#E3DAC9")


    # =====================================================================
    # HEADER / TITLE / STATUS / LAUNCH
    # =====================================================================

    def _add_header_area(self):
        """Add the title area, status line, and launch button."""

        container = self._main_container

        # Compact spacer 
        header_spacer = ttk.Frame(container, height=20)
        header_spacer.pack(fill=tk.X)

       # 🔴 TAG RESTRICTED 
        top_row = ttk.Frame(container)
        top_row.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(
            top_row,
            text="RESTRICTED",
            font=("Courier New", 10, "bold"),
            foreground="#7A1C5A",   # viola / rosso timbro
        ).pack(side=tk.RIGHT, padx=5)

        # Title
        ttk.Label(
            container,
            text="RULER INTELLIGENCE SUITE",
            font=("Courier New", 18, "bold"),
            foreground="#333333",
        ).pack(pady=(5, 2))

        # Subtitle
        ttk.Label(
            container,
            text="STRATEGIC ANALYSIS LOGGER",
            font=("Courier New", 10),
            foreground="#666666",
        ).pack(pady=(0, 15))

              # Status row
        status_frame = ttk.Frame(container)
        status_frame.pack(pady=5)

        self.status_game = ttk.Label(
            status_frame,
            text="TARGET: LOST",
            foreground="#8B0000",
            font=("Courier New", 12, "bold"),
        )
        self.status_game.grid(row=0, column=0, padx=15)

        self.status_log = ttk.Label(
            status_frame,
            text="LINK: OFFLINE",
            foreground="#555555",
            font=("Courier New", 12, "bold"),
        )
        self.status_log.grid(row=0, column=1, padx=15)

        # Launch button
        self.launch_btn = ttk.Button(
            container,
            text="[ INITIATE SEQUENCE (STEAM) ]",
            command=self._launch_game,
        )
        self.launch_btn.pack(pady=15, ipadx=10, ipady=5)

        ttk.Separator(container, orient="horizontal").pack(fill=tk.X, padx=10, pady=10)


    # =====================================================================
    # LOGGER AREA
    # =====================================================================

    def _add_logger_area(self):
        """Add the 'Mission Parameters' block with all fields."""

        container = self._main_container

        self.logger_frame = ttk.LabelFrame(
            container,
            text=" MISSION PARAMETERS ",
            padding=10,  # compact
        )
        self.logger_frame.pack(fill=tk.BOTH, expand=True, pady=(5, 15))

        # Top bar with LOAD DOSSIER
        top_bar = ttk.Frame(self.logger_frame)
        top_bar.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(top_bar, text="Operation Mode:").pack(side=tk.LEFT)
        ttk.Button(top_bar, text="LOAD DOSSIER", command=self._load_session).pack(side=tk.RIGHT)

        form_frame = ttk.Frame(self.logger_frame)
        form_frame.pack(fill=tk.X)

        # Operation name
        ttk.Label(form_frame, text="Operation Name:", font=("Courier New", 10, "bold")).grid(row=0, column=0, sticky="w", pady=5)
        self.game_name_entry = ttk.Entry(form_frame, textvariable=self.game_name_var, font=("Courier New", 11), width=22, state="disabled")
        self.game_name_entry.grid(row=0, column=1, sticky="ew", padx=10)

        # Nation
        ttk.Label(form_frame, text="Region/Nation:", font=("Courier New", 10, "bold")).grid(row=1, column=0, sticky="w", pady=5)
        self.nation_entry = ttk.Entry(form_frame, textvariable=self.nation_var, font=("Courier New", 11), width=22, state="disabled")
        self.nation_entry.grid(row=1, column=1, sticky="ew", padx=10)

        # Date
        ttk.Label(form_frame, text="Date (YYYY-MM-DD):", font=("Courier New", 10, "bold")).grid(row=2, column=0, sticky="w", pady=5)
        self.date_entry = ttk.Entry(form_frame, textvariable=self.date_var, font=("Courier New", 11), width=15, state="disabled")
        self.date_entry.grid(row=2, column=1, sticky="w", padx=10)

        # CSV preview
        self.csv_preview = ttk.Label(form_frame, text="FILE: PENDING...", foreground="#555555", font=("Courier New", 8))
        self.csv_preview.grid(row=3, column=0, columnspan=3, pady=8)

        # Last saved
        ttk.Label(form_frame, text="Last Contact:", font=("Courier New", 9)).grid(row=4, column=0, sticky="w", pady=5)
        ttk.Label(form_frame, textvariable=self.last_saved_var, font=("Courier New", 9)).grid(row=4, column=1, sticky="w", padx=10)

        # Engage / Abort monitoring
        self.log_btn = ttk.Button(
            self.logger_frame,
            text="[ ENGAGE MONITORING ]",
            command=self._toggle_logging,
            state="disabled",
        )
        self.log_btn.pack(pady=(10, 5), ipadx=20, ipady=5)

        # Force update intel
        self.update_btn = ttk.Button(
            self.logger_frame,
            text="Force Update Intel",
            command=self._update_info_live,
            state="disabled",
        )
        self.update_btn.pack(pady=(0, 5))

        ttk.Separator(self.logger_frame, orient="horizontal").pack(fill=tk.X, pady=10)


    # =====================================================================
    # TOOLS AREA (Overlay + Config + Analytics)
    # =====================================================================

    def _add_tools_area(self):
        """Add overlay checkbox, config button, archives and analytics buttons."""

        tools_frame = ttk.Frame(self.logger_frame)
        tools_frame.pack(fill=tk.X, pady=5)

        # Left side
        options_frame = ttk.Frame(tools_frame)
        options_frame.pack(side=tk.LEFT)
        ttk.Checkbutton(options_frame, text="Overlay", variable=self.overlay_var).pack(side=tk.LEFT, padx=5)
        ttk.Button(options_frame, text="CONFIG", command=self._open_settings).pack(side=tk.LEFT, padx=5)

        # Right side
        actions_frame = ttk.Frame(tools_frame)
        actions_frame.pack(side=tk.RIGHT)
        ttk.Button(actions_frame, text="ARCHIVES", command=lambda: os.startfile(str(LOGS_DIR))).pack(side=tk.LEFT, padx=5)

        # Analytics themed button
        style = ttk.Style()
        style.configure("Analytics.TButton", foreground="#004400", background="#AACCBB")
        ttk.Button(actions_frame, text="INTEL ANALYSIS", style="Analytics.TButton", command=show_simple_analytics).pack(side=tk.LEFT, padx=5)


    # ---------------- UI EVENTS / LOGIC BINDINGS ----------------

    def _open_settings(self):
        SettingsDialog(self.root, self.config)

    def _launch_game(self):
        """Launch the game via Steam and start watching for the process."""
        self.launch_btn.config(state="disabled", text="INITIATING...")
        launch_game_steam(STEAM_APP_ID)
        if not self.is_monitoring:
            self.is_monitoring = True
            threading.Thread(target=self._monitor_game_start, daemon=True).start()

    def _monitor_game_start(self):
        """Look for the game process for up to ~2 minutes."""
        logger.info("Scanning for game process signature...")
        for _ in range(120):
            if is_game_running():
                self.root.after(0, self._on_game_found)
                return
            time.sleep(1)

        # Timeout
        self.root.after(
            0, lambda: self.launch_btn.config(state="normal", text="[ INITIATE SEQUENCE (STEAM) ]")
        )
        self.root.after(0, lambda: messagebox.showerror("Timeout", "Target process not acquired."))
        self.is_monitoring = False

    def _on_game_found(self):
        """Hooked when the Supreme Ruler process is detected."""
        logger.info("Target acquired.")
        self.game_running = True
        self.status_game.config(text="TARGET: ACTIVE", foreground="#006400")
        self.launch_btn.config(text="SYSTEMS ENGAGED", state="disabled")

        # Unlock fields and actions
        self.game_name_entry.config(state="normal")
        self.nation_entry.config(state="normal")
        self.date_entry.config(state="normal")
        self.log_btn.config(state="normal")
        self.update_btn.config(state="normal")

        if self.overlay_var.get():
            launch_overlay(self.config)

        threading.Thread(target=self._monitor_game_exit, daemon=True).start()

    def _monitor_game_exit(self):
        """Monitor the game process until it closes."""
        while is_game_running():
            time.sleep(2)
        self.root.after(0, self._on_game_exit)

    def _on_game_exit(self):
        """Clean up UI state once the game is no longer running."""
        self.game_running = False
        self.status_game.config(text="TARGET: LOST", foreground="#8B0000")
        self.launch_btn.config(state="normal", text="[ INITIATE SEQUENCE (STEAM) ]")
        self.is_monitoring = False

        if logging_active:
            global stop_event
            stop_event.set()
            self.status_log.config(text="LINK: TERMINATED", foreground="#8B0000")

        # Lock fields again
        self.game_name_entry.config(state="disabled")
        self.nation_entry.config(state="disabled")
        self.date_entry.config(state="disabled")
        self.log_btn.config(state="disabled")
        self.update_btn.config(state="disabled")

    def _load_session(self):
        """Ask the user for a previous CSV log and resume from its last date."""
        file_path = filedialog.askopenfilename(
            initialdir=LOGS_DIR,
            title="Select Classified Log",
            filetypes=[("CSV Files", "*.csv")],
        )
        if not file_path:
            return

        path_obj = Path(file_path)
        filename = path_obj.stem

        # Expecting SR2030_<GameName>_<Nation>.csv, but we are lenient.
        if filename.startswith("SR2030_"):
            clean_name = filename.replace("SR2030_", "")
            parts = clean_name.rsplit("_", 1)
            if len(parts) == 2:
                self.game_name_var.set(parts[0])
                self.nation_var.set(parts[1])
            else:
                self.game_name_var.set(clean_name)

        last_date = get_last_date_from_csv(path_obj)
        if last_date:
            self.date_var.set(last_date)
            self.last_saved_var.set(f"{last_date} (Retrieved)")
            self.csv_preview.config(text=f"FILE: {path_obj.name}", foreground="#006400")
            messagebox.showinfo("Dossier Loaded", f"Resuming operation from: {last_date}")
        else:
            messagebox.showwarning("Data Error", "Unable to read date from dossier.")

    def _toggle_logging(self):
        """Start/stop the background logging thread."""
        global logging_started

        if not logging_active:
            # We are about to start logging
            if not self.date_var.get().strip():
                messagebox.showerror("Input Error", "Date parameter required.")
                return
            try:
                datetime.strptime(self.date_var.get(), "%Y-%m-%d")
            except ValueError:
                messagebox.showerror("Format Error", "Date must be YYYY-MM-DD.")
                return

            self.config["current_date"] = self.date_var.get()
            self.config["game_name"] = self.game_name_var.get().strip()
            self.config["nation"] = self.nation_var.get().strip()
            save_config(self.config)

            csv_path = get_log_file_path(
                self.config["game_name"], self.config["nation"], use_timestamp=False
            )
            self.csv_preview.config(text=f"FILE: {csv_path.name}", foreground="#006400")

            self.status_log.config(text="LINK: ESTABLISHED", foreground="#006400")
            self.log_btn.config(text="[ ABORT MONITORING ]")

            logging_started = True
            threading.Thread(
                target=logging_worker, args=(self.config, self), daemon=True
            ).start()
        else:
            # Request stop
            global stop_event
            stop_event.set()
            self.log_btn.config(text="[ ENGAGE MONITORING ]")

    def _update_info_live(self):
        """Manually push new date/game/nation into the config while logging."""
        new_date = self.date_var.get()
        try:
            datetime.strptime(new_date, "%Y-%m-%d")
            self.config["current_date"] = new_date
            self.config["game_name"] = self.game_name_var.get().strip()
            self.config["nation"] = self.nation_var.get().strip()
            save_config(self.config)
            messagebox.showinfo("Confirmed", "Intel parameters updated.")
        except ValueError:
            messagebox.showerror("Error", "Invalid Date Format. Use YYYY-MM-DD.")

    # ---------------- UI CALLBACKS FROM WORKER ----------------

    def update_last_saved(self, date: str):
        """Called from the logger thread (via .after) when a new row is written."""
        self.last_saved_var.set(date)

    def on_logger_stopped(self):
        """Reset UI bits when logging has been stopped."""
        self.status_log.config(text="LINK: OFFLINE", foreground="#555555")
        self.log_btn.config(text="[ ENGAGE MONITORING ]")
        global logging_started
        logging_started = False

def kill_overlay():
    global overlay_process
    if overlay_process and overlay_process.poll() is None:
        try:
            psutil.Process(overlay_process.pid).terminate()
        except Exception:
            pass

atexit.register(kill_overlay)
# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()
