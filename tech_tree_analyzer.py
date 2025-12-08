import sys
import csv
import json
import math
import pickle
import hashlib
import argparse
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Tuple
from collections import defaultdict, Counter
from datetime import datetime

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGraphicsView, QGraphicsScene, QGraphicsRectItem, QGraphicsTextItem,
    QGraphicsLineItem, QGraphicsPathItem, QGraphicsEllipseItem,QGraphicsItem,
    QGraphicsDropShadowEffect, QGraphicsOpacityEffect,
    QLabel, QComboBox, QLineEdit, QPushButton, QScrollArea, QFrame,
    QSplitter, QTreeWidget, QTreeWidgetItem, QHeaderView, QGroupBox,
    QCheckBox, QSlider, QMessageBox, QFileDialog, QToolTip, QSizePolicy,
    QTabWidget, QListWidget, QListWidgetItem, QTableWidget, QTableWidgetItem,
    QProgressBar, QStatusBar, QMenuBar, QMenu, QAction, QToolBar,
    QDockWidget, QTextEdit, QSpinBox, QDoubleSpinBox, QGridLayout,
    QStackedWidget, QButtonGroup, QRadioButton, QDialog, QDialogButtonBox,
    QAbstractItemView, QShortcut, QCompleter, QStyledItemDelegate
)
from PyQt5.QtCore import (
    Qt, QRectF, QPointF, QLineF, pyqtSignal, QTimer, QPropertyAnimation,
    QEasingCurve, QParallelAnimationGroup, QSequentialAnimationGroup,
    QSize, QSortFilterProxyModel, QStringListModel, QThread, QObject,QVariantAnimation
)

from PyQt5.QtGui import (
    QColor, QPen, QBrush, QFont, QPainterPath, QLinearGradient, QRadialGradient,
    QPainter, QFontMetrics, QCursor, QWheelEvent, QIcon, QPixmap,
    QPalette, QKeySequence, QFontDatabase
)

# =============================================================================
# IPC SERVER (Communication with Overlay)
# =============================================================================
try:
    from ipc_bridge import IPCServer
    IPC_AVAILABLE = True
except ImportError:
    IPCServer = None
    IPC_AVAILABLE = False
    print("[System] WARNING: ipc_bridge.py not found. Overlay integration disabled.")

# =============================================================================
# CONSTANTS & STYLING
# =============================================================================

VERSION = "2.1.0"
APP_NAME = "Supreme Ruler 2030 Tech Tree Analyzer beta"

# Dark theme colors
COLORS = {
    'bg_dark': '#0d1117',
    'bg_medium': '#161b22',
    'bg_light': '#21262d',
    'bg_hover': '#30363d',
    'border': '#30363d',
    'border_light': '#484f58',
    'text_primary': '#f0f6fc',
    'text_secondary': '#8b949e',
    'text_muted': '#6e7681',
    'accent_blue': '#58a6ff',
    'accent_green': '#3fb950',
    'accent_red': '#f85149',
    'accent_orange': '#d29922',
    'accent_purple': '#a371f7',
    'accent_pink': '#db61a2',
    'accent_cyan': '#39c5cf',
}

# Category definitions with icons and colors
#from wiki
CATEGORIES = {
    1: {'name': 'Warfare',        'icon': '⚔', 'color': '#f85149', 'bg': '#3d1a1a'},  # Military/Weaponry
    2: {'name': 'Transportation', 'icon': '⛟', 'color': '#d29922', 'bg': '#3d2a1a'},  # Infrastructure/Logistics
    3: {'name': 'Science',        'icon': '⚗', 'color': '#3fb950', 'bg': '#1a3d1a'},  # Physics/Chemistry
    4: {'name': 'Technology',     'icon': '⚙', 'color': '#58a6ff', 'bg': '#1a2a3d'},  # Industrial/Engineering
    5: {'name': 'Medical',        'icon': '✚', 'color': '#db61a2', 'bg': '#3d1a2a'},  # Health/Bio
    6: {'name': 'Society',        'icon': '🏛', 'color': '#a371f7', 'bg': '#2a1a3d'},  # Culture/Politics
}

# -----------------------------------------------------------------------------
# UNIT CLASS DEFINITIONS (NATO)
# -----------------------------------------------------------------------------
CLASS_INFO = {
    1:  {'name': 'Reconnaissance',      'icon': '◉'}, # Scope / Target
    2:  {'name': 'Armor / Tank',        'icon': '▭'}, # Flattened rectangle (Tracks)
    3:  {'name': 'Anti-Tank',           'icon': '⟁'}, # Triangle (Directional)
    4:  {'name': 'Infantry',            'icon': '⊠'}, # Box with X (Standard NATO)
    5:  {'name': 'Artillery',           'icon': '⊙'}, # Dot in Circle (Standard NATO)
    6:  {'name': 'Air Defense',         'icon': '⌒'}, # Dome / Radar Coverage
    7:  {'name': 'Helicopter',          'icon': '✕'}, # Rotor blade
    8:  {'name': 'Missile',             'icon': '⇡'}, # Upward trajectory
    9:  {'name': 'Fighter',             'icon': '↛'}, # Interception
    10: {'name': 'Attack Aircraft',     'icon': '↣'}, # Direct Attack
    11: {'name': 'Interceptor',         'icon': '↟'}, # Fast climb/High alt
    12: {'name': 'Bomber',              'icon': '▼'}, # Drop payload
    13: {'name': 'ASW Aircraft',        'icon': '∿'}, # Wave/Sonar
    14: {'name': 'Transport Aircraft',  'icon': '□'}, # Cargo Capacity
    15: {'name': 'Submarine',           'icon': '∩'}, # Hull profile
    16: {'name': 'Aircraft Carrier',    'icon': '⌧'}, # Flat deck
    17: {'name': 'Capital Ship',        'icon': '▇'}, # Heavy mass
    18: {'name': 'Destroyer/Escort',    'icon': 'shield'}, # Using shape or 🛡 if supported
    19: {'name': 'Patrol Craft',        'icon': '⌖'}, # Radar/Light
    20: {'name': 'Transport Ship',      'icon': '⫷'}, # Cargo
    21: {'name': 'Installation',        'icon': '⌂'}, # Base/Facility
}

# -----------------------------------------------------------------------------
# EFFECT DEFINITIONS (Comprehensive Wiki Mapping)
# -----------------------------------------------------------------------------
EFFECT_DEFINITIONS = {
    # --- Global / Economic Effects ---
    2:  {'name': 'Finished Goods Fac. Cost',   'category': 'Industry',    'icon': '🏗'},
    3:  {'name': 'Facility Material Usage',    'category': 'Industry',    'icon': '🧱'},
    5:  {'name': 'Research Efficiency',        'category': 'Science',     'icon': '⚗'},
    6:  {'name': 'Counter-Intel Efficiency',   'category': 'Intel',       'icon': '⊘'},
    7:  {'name': 'Intelligence Efficiency',    'category': 'Intel',       'icon': '👁'},
    8:  {'name': 'Military Efficiency',        'category': 'Military',    'icon': '⚔'},
    9:  {'name': 'Power Generation Output',    'category': 'Energy',      'icon': '⚡'},
    13: {'name': 'Fuel Consumption Rate',      'category': 'Logistics',   'icon': '⛽'},
    14: {'name': 'Motorized Unit Cost',        'category': 'Production',  'icon': '⛟'},
    15: {'name': 'Unit Build Speed',           'category': 'Production',  'icon': '⏱'},
    16: {'name': 'Facility Build Speed',       'category': 'Production',  'icon': '🏗'},
    18: {'name': 'Finished Goods Efficiency',  'category': 'Industry',    'icon': '⚙'},
    19: {'name': 'Finished Goods Cost',        'category': 'Industry',    'icon': '💲'},
    20: {'name': 'Transportation Improvement', 'category': 'Logistics',    'icon': '⛽'},
    21: {'name': 'Space Knowledge',            'category': 'Space',       'icon': '☄'},
    22: {'name': 'Nuclear Plant Maint.',       'category': 'Energy',      'icon': '☢'},

    # --- Resource Usage (Raw Material to Finished Goods) ---
    24: {'name': 'Agri Usage (Mfg)',           'category': 'Resource',    'icon': '🌾'},
    25: {'name': 'Rubber Usage (Mfg)',         'category': 'Resource',    'icon': '⚫'},
    27: {'name': 'Petrol Usage (Mfg)',         'category': 'Resource',    'icon': '🛢'},
    29: {'name': 'Ore Usage (Mfg)',            'category': 'Resource',    'icon': '⛏'},
    33: {'name': 'Industrial Raw Usage',       'category': 'Resource',    'icon': '🔩'},
    34: {'name': 'Military Raw Usage',         'category': 'Resource',    'icon': '🛡'},

    # --- Production Output (Facilities) ---
    35: {'name': 'Synth. Rubber Production',   'category': 'Output',      'icon': '⚗'},
    38: {'name': 'Synth. Fuel Production',     'category': 'Output',      'icon': '🛢'},
    40: {'name': 'Nuclear Power Output',       'category': 'Energy',      'icon': '☢'},
    44: {'name': 'Consumer Goods Output',      'category': 'Output',      'icon': '🛍'},
    45: {'name': 'Industrial Goods Output',    'category': 'Output',      'icon': '🏭'},
    46: {'name': 'Military Goods Output',      'category': 'Output',      'icon': '🔫'},

    # --- Races / Milestones ---
    56: {'name': 'Atomic Race Capability',     'category': 'Strategic',   'icon': '☢'},
    57: {'name': 'Bio/Pandemic Research',      'category': 'Strategic',   'icon': '☣'},
    58: {'name': 'Internet Infrastructure',    'category': 'Strategic',   'icon': '🌐'},
    59: {'name': 'Mars/Space Mission',         'category': 'Strategic',   'icon': '🚀'},

    # --- Population Usage Modifiers (60-71) ---
    63: {'name': 'Pop. Petrol Usage',          'category': 'Society',     'icon': '⛽'},
    67: {'name': 'Pop. Power Usage',           'category': 'Society',     'icon': '⚡'},
    68: {'name': 'Pop. Consumer Goods Usage',  'category': 'Society',     'icon': '🛒'},

    # --- Resource Output Modifiers (72-83) ---
    72: {'name': 'Agriculture Output',         'category': 'Economy',     'icon': '🌾'},
    75: {'name': 'Petroleum Output',           'category': 'Economy',     'icon': '🛢'},
    77: {'name': 'Ore Output',                 'category': 'Economy',     'icon': '⛏'},
    79: {'name': 'Power Output (All)',         'category': 'Economy',     'icon': '⚡'},

    # --- Resource Efficiency Modifiers (84-94) ---
    84: {'name': 'Agriculture Efficiency',     'category': 'Economy',     'icon': '📈'},
    87: {'name': 'Petroleum Efficiency',       'category': 'Economy',     'icon': '📈'},
    93: {'name': 'Industrial Efficiency',      'category': 'Economy',     'icon': '📈'},
    94: {'name': 'Military Goods Efficiency',  'category': 'Economy',     'icon': '📈'},
    96: {'name': 'Garrison Infantry Level',  'category': 'Defense',     'icon': '🛡'},
    97: {'name': 'Locomotive Unit Level',  'category': 'Logistics',     'icon': '⛽'},

    # --- Social Ratings & Costs (100-115) ---
    100: {'name': 'Healthcare Rating',         'category': 'Social',      'icon': '✚'},
    101: {'name': 'Education Rating',          'category': 'Social',      'icon': '🎓'},
    102: {'name': 'Infrastructure Rating',     'category': 'Social',      'icon': '🛣'},
    103: {'name': 'Environment Rating',        'category': 'Social',      'icon': '🌲'},
    105: {'name': 'Law Enforcement Rating',    'category': 'Social',      'icon': '⚖'},
    108: {'name': 'Healthcare Cost',           'category': 'Finance',     'icon': '💲'},
    109: {'name': 'Education Cost',            'category': 'Finance',     'icon': '💲'},
    113: {'name': 'Law Enforcement Cost',      'category': 'Finance',     'icon': '💲'},

    # --- Global Military Stats (116-127) ---
    116: {'name': 'Hard Target Defense (All)', 'category': 'Defense',     'icon': '🛡'},
    117: {'name': 'Soft Target Defense (All)', 'category': 'Defense',     'icon': '🛡'},
    118: {'name': 'Ground Attack (All)',       'category': 'Offense',     'icon': '⚔'},
    119: {'name': 'Anti-Air Attack (All)',     'category': 'Offense',     'icon': '⇡'},
    120: {'name': 'Anti-Ship Attack (All)',    'category': 'Offense',     'icon': '⚓'},
    122: {'name': 'Ballistic/Arty Range',      'category': 'Range',       'icon': '⤳'},
    123: {'name': 'Missile Accuracy',          'category': 'Combat',      'icon': '🎯'},
    124: {'name': 'Stealth Level (All)',       'category': 'Stealth',     'icon': '👻'},
    125: {'name': 'Spotting Range (All)',      'category': 'Intel',       'icon': '🔭'},
    127: {'name': 'Fortification Defense',     'category': 'Defense',     'icon': '🏰'},

    # --- Space / Futuristic (128-139) ---
    128: {'name': 'FTL Range',                 'category': 'Space',       'icon': '🌌'},
    130: {'name': 'Space Beam Defense',        'category': 'Space',       'icon': '🛡'},
    132: {'name': 'Space Beam Attack',         'category': 'Space',       'icon': '⚡'},
    135: {'name': 'Shield Efficiency',         'category': 'Tech',        'icon': '🛡'},

    # --- Unit Upgrade Techs (140-149: Attack Modifiers) ---
    140: {'name': 'Soft Attack Upgrade',       'category': 'Offense',     'icon': '⨂'},
    141: {'name': 'Hard Attack Upgrade',       'category': 'Offense',     'icon': '⨂'},
    142: {'name': 'Fortification Attack',      'category': 'Offense',     'icon': '⌖'},
    143: {'name': 'Low-Air Attack',            'category': 'Offense',     'icon': '⇡'},
    144: {'name': 'Mid-Air Attack',            'category': 'Offense',     'icon': '⇡'},
    145: {'name': 'High-Air Attack',           'category': 'Offense',     'icon': '⇡'},
    146: {'name': 'Naval Surface Attack',      'category': 'Offense',     'icon': '⚓'},
    147: {'name': 'Submarine Attack',          'category': 'Offense',     'icon': '⇝'},
    148: {'name': 'Close Combat Attack',       'category': 'Offense',     'icon': '⚔'},

    # --- Unit Upgrade Techs (150-153: Range Modifiers) ---
    150: {'name': 'Ground Range Upgrade',      'category': 'Range',       'icon': '↦'},
    151: {'name': 'Air Range Upgrade',         'category': 'Range',       'icon': '↝'},
    152: {'name': 'Naval Range Upgrade',       'category': 'Range',       'icon': '〰'},

    # --- Unit Upgrade Techs (154-157: Defense Modifiers) ---
    154: {'name': 'Ground Defense Upgrade',    'category': 'Defense',     'icon': '🛡'},
    155: {'name': 'Air Defense Upgrade',       'category': 'Defense',     'icon': '☂'},
    156: {'name': 'Indirect Defense',          'category': 'Defense',     'icon': '⛨'},
    157: {'name': 'Close Defense Upgrade',     'category': 'Defense',     'icon': '🛡'},

    # --- Unit Specs & Logistics (158-170) ---
    158: {'name': 'Unit Speed',                'category': 'Mobility',    'icon': '⏩'},
    159: {'name': 'Unit Stealth',              'category': 'Stealth',     'icon': '∅'},
    160: {'name': 'Unit Initiative',           'category': 'Combat',      'icon': '⚡'},
    161: {'name': 'Combat Time/Ammo Eff.',     'category': 'Logistics',   'icon': '📦'},
    162: {'name': 'Air/Sea Fuel Usage',        'category': 'Logistics',   'icon': '⛽'},
    163: {'name': 'Missile Capacity',          'category': 'Loadout',     'icon': '🚀'},
    164: {'name': 'Unit Efficiency',           'category': 'Combat',      'icon': '⭐'},
    165: {'name': 'Ammo Capacity',             'category': 'Loadout',     'icon': '▮'},
    166: {'name': 'Fuel Capacity',             'category': 'Logistics',   'icon': '🛢'},
    167: {'name': 'Spotting Range 1',          'category': 'Intel',       'icon': '👁'},

    # --- Boolean Flags / Unlocks (200+) ---
    201: {'name': 'Enable SOSUS Spotting',     'category': 'Unlock',      'icon': '〰'},
    202: {'name': 'Enable Nuclear Weapons',    'category': 'Unlock',      'icon': '☢'},
    203: {'name': 'Enable Chemical Weapons',   'category': 'Unlock',      'icon': '☠'},
    204: {'name': 'Enable Bio Weapons',        'category': 'Unlock',      'icon': '☣'},
    205: {'name': 'Enable ComSat',             'category': 'Space',       'icon': '📡'},
    206: {'name': 'Enable ReconSat',           'category': 'Space',       'icon': '🛰'},
    209: {'name': 'Enable Cyberattack',        'category': 'Intel',       'icon': '💻'},
    232: {'name': 'Enable Shields',            'category': 'Tech',        'icon': '🛡'},
    233: {'name': 'Enable Beam Weapons',       'category': 'Tech',        'icon': '⚡'},
    234: {'name': 'Unit ECM Equipped',         'category': 'Electronic',  'icon': '📶'},
}


STYLESHEET = f"""
QMainWindow {{
    background-color: {COLORS['bg_dark']};
}}

QWidget {{
    background-color: {COLORS['bg_dark']};
    color: {COLORS['text_primary']};
    font-family: 'Segoe UI', 'SF Pro Display', sans-serif;
}}

QMenuBar {{
    background-color: {COLORS['bg_medium']};
    border-bottom: 1px solid {COLORS['border']};
    padding: 4px;
}}

QMenuBar::item:selected {{
    background-color: {COLORS['bg_hover']};
    border-radius: 4px;
}}

QMenu {{
    background-color: {COLORS['bg_medium']};
    border: 1px solid {COLORS['border']};
    border-radius: 8px;
    padding: 8px;
}}

QMenu::item {{
    padding: 8px 24px;
    border-radius: 4px;
}}

QMenu::item:selected {{
    background-color: {COLORS['bg_hover']};
}}

QToolBar {{
    background-color: {COLORS['bg_medium']};
    border: none;
    border-bottom: 1px solid {COLORS['border']};
    padding: 8px;
    spacing: 8px;
}}

QToolButton {{
    background-color: transparent;
    border: 1px solid transparent;
    border-radius: 6px;
    padding: 8px 12px;
    color: {COLORS['text_secondary']};
}}

QToolButton:hover {{
    background-color: {COLORS['bg_hover']};
    border-color: {COLORS['border_light']};
    color: {COLORS['text_primary']};
}}

QToolButton:pressed {{
    background-color: {COLORS['bg_light']};
}}

QPushButton {{
    background-color: {COLORS['bg_light']};
    border: 1px solid {COLORS['border']};
    border-radius: 6px;
    padding: 8px 16px;
    color: {COLORS['text_primary']};
    font-weight: 500;
}}

QPushButton:hover {{
    background-color: {COLORS['bg_hover']};
    border-color: {COLORS['border_light']};
}}

QPushButton:pressed {{
    background-color: {COLORS['bg_medium']};
}}

QPushButton#primaryButton {{
    background-color: {COLORS['accent_blue']};
    border-color: {COLORS['accent_blue']};
    color: white;
}}

QPushButton#primaryButton:hover {{
    background-color: #4090e0;
}}

QPushButton#dangerButton {{
    background-color: {COLORS['accent_red']};
    border-color: {COLORS['accent_red']};
    color: white;
}}

QLineEdit, QComboBox, QSpinBox {{
    background-color: {COLORS['bg_medium']};
    border: 1px solid {COLORS['border']};
    border-radius: 6px;
    padding: 8px 12px;
    color: {COLORS['text_primary']};
    selection-background-color: {COLORS['accent_blue']};
}}

QLineEdit:focus, QComboBox:focus {{
    border-color: {COLORS['accent_blue']};
}}

QComboBox::drop-down {{
    border: none;
    width: 30px;
}}

QComboBox QAbstractItemView {{
    background-color: {COLORS['bg_medium']};
    border: 1px solid {COLORS['border']};
    border-radius: 8px;
    selection-background-color: {COLORS['bg_hover']};
}}

QTabWidget::pane {{
    background-color: {COLORS['bg_medium']};
    border: 1px solid {COLORS['border']};
    border-radius: 8px;
    top: -1px;
}}

QTabBar::tab {{
    background-color: {COLORS['bg_dark']};
    border: 1px solid {COLORS['border']};
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    padding: 10px 20px;
    margin-right: 4px;
    color: {COLORS['text_secondary']};
}}

QTabBar::tab:selected {{
    background-color: {COLORS['bg_medium']};
    color: {COLORS['text_primary']};
    border-bottom: 2px solid {COLORS['accent_blue']};
}}

QTabBar::tab:hover:!selected {{
    background-color: {COLORS['bg_light']};
}}

QTreeWidget, QListWidget, QTableWidget {{
    background-color: {COLORS['bg_medium']};
    border: 1px solid {COLORS['border']};
    border-radius: 8px;
    outline: none;
    alternate-background-color: {COLORS['bg_light']};
}}

QTreeWidget::item, QListWidget::item {{
    padding: 8px;
    border-radius: 4px;
    margin: 1px 2px;
}}

QTreeWidget::item:hover, QListWidget::item:hover {{
    background-color: {COLORS['bg_hover']};
}}

QTreeWidget::item:selected, QListWidget::item:selected {{
    background-color: {COLORS['bg_light']};
    color: {COLORS['accent_blue']};
}}

QHeaderView::section {{
    background-color: {COLORS['bg_light']};
    border: none;
    border-right: 1px solid {COLORS['border']};
    border-bottom: 1px solid {COLORS['border']};
    padding: 10px;
    font-weight: 600;
    color: {COLORS['text_secondary']};
}}

QScrollBar:vertical {{
    background-color: {COLORS['bg_dark']};
    width: 12px;
    border-radius: 6px;
}}

QScrollBar::handle:vertical {{
    background-color: {COLORS['border']};
    border-radius: 6px;
    min-height: 30px;
}}

QScrollBar::handle:vertical:hover {{
    background-color: {COLORS['border_light']};
}}

QScrollBar:horizontal {{
    background-color: {COLORS['bg_dark']};
    height: 12px;
    border-radius: 6px;
}}

QScrollBar::handle:horizontal {{
    background-color: {COLORS['border']};
    border-radius: 6px;
    min-width: 30px;
}}

QScrollBar::add-line, QScrollBar::sub-line {{
    width: 0px;
    height: 0px;
}}

QGroupBox {{
    font-weight: 600;
    font-size: 12px;
    border: 1px solid {COLORS['border']};
    border-radius: 8px;
    margin-top: 16px;
    padding: 8px;
    padding-top: 20px;
    color: {COLORS['text_secondary']};
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    left: 12px;
    top: 4px;
    padding: 0 8px;
    background-color: {COLORS['bg_dark']};
}}

QProgressBar {{
    background-color: {COLORS['bg_light']};
    border: none;
    border-radius: 4px;
    height: 8px;
    text-align: center;
}}

QProgressBar::chunk {{
    background-color: {COLORS['accent_blue']};
    border-radius: 4px;
}}

QSplitter::handle {{
    background-color: {COLORS['border']};
}}

QSplitter::handle:horizontal {{
    width: 2px;
}}

QSplitter::handle:vertical {{
    height: 2px;
}}

QDockWidget {{
    titlebar-close-icon: none;
    titlebar-normal-icon: none;
}}

QDockWidget::title {{
    background-color: {COLORS['bg_light']};
    padding: 10px;
    font-weight: 600;
}}

QToolTip {{
    background-color: {COLORS['bg_light']};
    border: 1px solid {COLORS['border']};
    border-radius: 6px;
    padding: 8px 12px;
    color: {COLORS['text_primary']};
}}

QStatusBar {{
    background-color: {COLORS['bg_medium']};
    border-top: 1px solid {COLORS['border']};
}}

QLabel#statValue {{
    font-size: 22px;
    font-weight: bold;
    color: {COLORS['accent_blue']};
    padding: 4px;
}}

QLabel#statLabel {{
    color: {COLORS['text_muted']};
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 1px;
}}

QFrame#card {{
    background-color: {COLORS['bg_medium']};
    border: 1px solid {COLORS['border']};
    border-radius: 12px;
    padding: 16px;
}}

QFrame#techCard {{
    background-color: {COLORS['bg_medium']};
    border: 1px solid {COLORS['border']};
    border-radius: 8px;
}}

QFrame#techCard:hover {{
    border-color: {COLORS['accent_blue']};
    background-color: {COLORS['bg_light']};
}}
"""


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class TechData:
    id: int = 0
    category: int = 0
    tech_level: int = 0
    short_title: str = ""
    prereq_1: int = 0
    prereq_2: int = 0
    leads_to_1: int = 0
    leads_to_2: int = 0
    effects: List[Tuple[int, float]] = field(default_factory=list)
    time_to_research: int = 0
    cost: float = 0.0
    pop_support: float = 0.0
    set_by_default: int = 0
    unlocks_units: List['UnitData'] = field(default_factory=list)
    prerequisite_of: List[int] = field(default_factory=list)
    # Computed fields
    depth: int = 0  # Distance from root techs
    chain_cost: float = 0.0  # Total cost including prerequisites


@dataclass
class NodePosition:
    """Position data for a single node"""
    x: float = 0.0
    y: float = 0.0
    layer: int = 0
    position_in_layer: int = 0
    cluster_id: int = 0

@dataclass  
class UnitData:
    id: int = 0
    name: str = ""
    class_num: int = 0
    year: str = ""
    req_tech_id: int = 0
    cost: float = 0.0
    region: str = ""

@dataclass  
class LayoutResult:
    """Complete layout computation result"""
    positions: Dict[int, NodePosition] = field(default_factory=dict)
    width: float = 0.0
    height: float = 0.0
    layer_positions: Dict[int, float] = field(default_factory=dict)
    clusters: Dict[int, Set[int]] = field(default_factory=dict)
    cluster_colors: Dict[int, str] = field(default_factory=dict)


class GridLayoutEngine:
    """Layout engine che usa tech_level come colonne"""
    
    NODE_WIDTH = 200
    NODE_HEIGHT = 70
    H_SPACING = 320
    V_SPACING = 130
    MARGIN = 50
    TOP_MARGIN = 120
    
    def compute(self, techs: dict, category_filter: int = 0) -> LayoutResult:
        result = LayoutResult()
        
        filtered = {
            tid: t for tid, t in techs.items()
            if category_filter == 0 or t.category == category_filter
        }
        
        if not filtered:
            return result
        
        by_level = defaultdict(list)
        for tid, tech in filtered.items():
            by_level[tech.tech_level].append(tid)
        
        for level in by_level:
            by_level[level].sort(key=lambda t: (filtered[t].category, filtered[t].short_title))
        
        levels = sorted(by_level.keys())
        max_in_level = max(len(by_level[l]) for l in levels) if levels else 1
        
        for col, level in enumerate(levels):
            x = self.MARGIN + col * self.H_SPACING
            center_x = x + self.NODE_WIDTH / 2
            result.layer_positions[level] = center_x
            
            for row, tid in enumerate(by_level[level]):
                y = self.TOP_MARGIN + row * self.V_SPACING
                result.positions[tid] = NodePosition(x=x, y=y, layer=level, position_in_layer=row)
        
        if result.positions:
            max_x = max(p.x for p in result.positions.values())
            max_y = max(p.y for p in result.positions.values())
            result.width = max_x + self.NODE_WIDTH + self.MARGIN
            result.height = max_y + self.NODE_HEIGHT + self.MARGIN
        
        return result


class SugiyamaLayoutEngine:
    """Sugiyama hierarchical layout con crossing minimization"""
    
    NODE_WIDTH = 200
    NODE_HEIGHT = 70
    H_SPACING = 280
    V_SPACING = 100
    MARGIN = 80
    TOP_MARGIN = 120
    
    def __init__(self, use_tech_level_as_layer: bool = True):
        self.use_tech_level_as_layer = use_tech_level_as_layer
    
    def compute(self, techs: dict, category_filter: int = 0) -> LayoutResult:
        result = LayoutResult()
        
        filtered = {
            tid: t for tid, t in techs.items()
            if category_filter == 0 or t.category == category_filter
        }
        
        if not filtered:
            return result
        
        # Step 1: Layer assignment
        layers = self._assign_layers(filtered)
        
        # Step 2: Initial ordering
        layer_order = self._initial_ordering(filtered, layers)
        
        # Step 3: Crossing minimization (4 passes)
        layer_order = self._minimize_crossings(filtered, layers, layer_order, passes=4)
        
        # Step 4: Coordinate assignment
        positions = self._assign_coordinates(filtered, layers, layer_order)
        
        # Step 5: Detect clusters
        clusters, cluster_colors = self._detect_clusters(filtered)
        
        # Build result
        for tid, (x, y) in positions.items():
            layer = layers[tid]
            pos_in_layer = layer_order[layer].index(tid) if tid in layer_order.get(layer, []) else 0
            cluster_id = next((cid for cid, members in clusters.items() if tid in members), 0)
            
            result.positions[tid] = NodePosition(
                x=x, y=y, layer=layer, 
                position_in_layer=pos_in_layer,
                cluster_id=cluster_id
            )
        
        for layer, tids in layer_order.items():
            if tids and tids[0] in positions:
                result.layer_positions[layer] = positions[tids[0]][0] + self.NODE_WIDTH / 2
        
        result.clusters = clusters
        result.cluster_colors = cluster_colors
        
        if positions:
            max_x = max(p[0] for p in positions.values())
            max_y = max(p[1] for p in positions.values())
            result.width = max_x + self.NODE_WIDTH + self.MARGIN
            result.height = max_y + self.NODE_HEIGHT + self.MARGIN
        
        return result
    
    def _assign_layers(self, techs: dict) -> Dict[int, int]:
        if self.use_tech_level_as_layer:
            return {tid: t.tech_level for tid, t in techs.items()}
        
        layers = {}
        def get_layer(tid):
            if tid in layers:
                return layers[tid]
            if tid not in techs:
                return 0
            tech = techs[tid]
            prereq_layers = []
            if tech.prereq_1 and tech.prereq_1 in techs:
                prereq_layers.append(get_layer(tech.prereq_1))
            if tech.prereq_2 and tech.prereq_2 in techs:
                prereq_layers.append(get_layer(tech.prereq_2))
            layer = (max(prereq_layers) + 1) if prereq_layers else 0
            layers[tid] = layer
            return layer
        
        for tid in techs:
            get_layer(tid)
        return layers
    
    def _initial_ordering(self, techs: dict, layers: Dict[int, int]) -> Dict[int, List[int]]:
        layer_order: Dict[int, List[int]] = defaultdict(list)
        for tid, layer in layers.items():
            layer_order[layer].append(tid)
        
        for layer in layer_order:
            layer_order[layer].sort(key=lambda t: (techs[t].category, techs[t].short_title))
        
        return dict(layer_order)
    
    def _minimize_crossings(self, techs: dict, layers: Dict[int, int], 
                           layer_order: Dict[int, List[int]], passes: int = 4) -> Dict[int, List[int]]:
        sorted_layers = sorted(layer_order.keys())
        
        for _ in range(passes):
            # Forward sweep
            for i in range(1, len(sorted_layers)):
                prev_layer = sorted_layers[i - 1]
                curr_layer = sorted_layers[i]
                layer_order[curr_layer] = self._reorder_by_barycenter(
                    techs, layers, layer_order, curr_layer, prev_layer, forward=True
                )
            
            # Backward sweep
            for i in range(len(sorted_layers) - 2, -1, -1):
                next_layer = sorted_layers[i + 1]
                curr_layer = sorted_layers[i]
                layer_order[curr_layer] = self._reorder_by_barycenter(
                    techs, layers, layer_order, curr_layer, next_layer, forward=False
                )
        
        return layer_order
    
    def _reorder_by_barycenter(self, techs: dict, layers: Dict[int, int],
                               layer_order: Dict[int, List[int]], 
                               curr_layer: int, ref_layer: int, forward: bool) -> List[int]:
        curr_nodes = layer_order.get(curr_layer, [])
        ref_nodes = layer_order.get(ref_layer, [])
        
        if not curr_nodes or not ref_nodes:
            return curr_nodes
        
        ref_pos = {tid: i for i, tid in enumerate(ref_nodes)}
        barycenters = []
        
        for tid in curr_nodes:
            tech = techs[tid]
            connected_positions = []
            
            if forward:
                for prereq in [tech.prereq_1, tech.prereq_2]:
                    if prereq and prereq in ref_pos:
                        connected_positions.append(ref_pos[prereq])
            else:
                for other_tid, other_tech in techs.items():
                    if layers.get(other_tid) == ref_layer:
                        if other_tech.prereq_1 == tid or other_tech.prereq_2 == tid:
                            if other_tid in ref_pos:
                                connected_positions.append(ref_pos[other_tid])
            
            if connected_positions:
                barycenter = sum(connected_positions) / len(connected_positions)
            else:
                barycenter = curr_nodes.index(tid)
            
            barycenters.append((tid, barycenter))
        
        barycenters.sort(key=lambda x: x[1])
        return [tid for tid, _ in barycenters]
    
    def _assign_coordinates(self, techs: dict, layers: Dict[int, int],
                           layer_order: Dict[int, List[int]]) -> Dict[int, Tuple[float, float]]:
        positions = {}
        sorted_layers = sorted(layer_order.keys())
        max_in_any_layer = max(len(layer_order[l]) for l in sorted_layers) if sorted_layers else 1
        
        for i, layer in enumerate(sorted_layers):
            x = self.MARGIN + i * self.H_SPACING
            nodes = layer_order[layer]
            
            total_height = len(nodes) * self.V_SPACING
            start_y = self.TOP_MARGIN + (max_in_any_layer * self.V_SPACING - total_height) / 2
            
            for j, tid in enumerate(nodes):
                y = self._compute_median_y(tid, techs, positions, start_y + j * self.V_SPACING)
                positions[tid] = (x, y)
        
        positions = self._resolve_overlaps(positions, layer_order)
        return positions
    
    def _compute_median_y(self, tid: int, techs: dict, 
                         existing_positions: Dict[int, Tuple[float, float]],
                         default_y: float) -> float:
        tech = techs[tid]
        connected_ys = []
        
        for prereq in [tech.prereq_1, tech.prereq_2]:
            if prereq and prereq in existing_positions:
                connected_ys.append(existing_positions[prereq][1])
        
        if connected_ys:
            return sum(connected_ys) / len(connected_ys)
        return default_y
    
    def _resolve_overlaps(self, positions: Dict[int, Tuple[float, float]],
                         layer_order: Dict[int, List[int]]) -> Dict[int, Tuple[float, float]]:
        for layer, nodes in layer_order.items():
            if len(nodes) <= 1:
                continue
            
            nodes_with_y = [(tid, positions[tid][1]) for tid in nodes if tid in positions]
            nodes_with_y.sort(key=lambda x: x[1])
            
            for i in range(1, len(nodes_with_y)):
                prev_tid, prev_y = nodes_with_y[i - 1]
                curr_tid, curr_y = nodes_with_y[i]
                
                min_y = prev_y + self.V_SPACING
                if curr_y < min_y:
                    x = positions[curr_tid][0]
                    positions[curr_tid] = (x, min_y)
                    nodes_with_y[i] = (curr_tid, min_y)
        
        return positions
    
    def _detect_clusters(self, techs: dict) -> Tuple[Dict[int, Set[int]], Dict[int, str]]:
        adjacency: Dict[int, Set[int]] = defaultdict(set)
        for tid, tech in techs.items():
            if tech.prereq_1 and tech.prereq_1 in techs:
                adjacency[tid].add(tech.prereq_1)
                adjacency[tech.prereq_1].add(tid)
            if tech.prereq_2 and tech.prereq_2 in techs:
                adjacency[tid].add(tech.prereq_2)
                adjacency[tech.prereq_2].add(tid)
        
        visited = set()
        clusters: Dict[int, Set[int]] = {}
        cluster_id = 0
        
        for tid in techs:
            if tid in visited:
                continue
            
            component = set()
            queue = [tid]
            while queue:
                current = queue.pop(0)
                if current in visited:
                    continue
                visited.add(current)
                component.add(current)
                for neighbor in adjacency[current]:
                    if neighbor not in visited:
                        queue.append(neighbor)
            
            if component:
                clusters[cluster_id] = component
                cluster_id += 1
        
        cluster_palette = [
            '#58a6ff20', '#3fb95020', '#f8514920', '#d2992220',
            '#a371f720', '#db61a220', '#39c5cf20', '#8b949e20'
        ]
        
        cluster_colors = {
            cid: cluster_palette[cid % len(cluster_palette)]
            for cid in clusters
        }
        
        return clusters, cluster_colors


# =============================================================================
# CLUSTER BACKGROUND
# =============================================================================

class ClusterBackground(QGraphicsRectItem):
    """Visual background for a cluster of related techs"""
    
    def __init__(self, bounds: QRectF, color: str, cluster_id: int):
        padded = bounds.adjusted(-25, -25, 25, 25)
        super().__init__(padded)
        
        self.cluster_id = cluster_id
        self.setZValue(-10)
        
        self.setBrush(QBrush(QColor(color)))
        border_color = color.replace('20', '50')  # Slightly more opaque border
        self.setPen(QPen(QColor(border_color), 1, Qt.DashLine))
    
    def paint(self, painter, option, widget):
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(self.pen())
        painter.setBrush(self.brush())
        painter.drawRoundedRect(self.rect(), 16, 16)


# =============================================================================
# CHAIN ANIMATOR
# =============================================================================

class ChainAnimator(QObject):
    """Gestisce animazioni smooth per chain highlight"""
    
    animation_complete = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.animations: List[QVariantAnimation] = []
        self.main_group = None
        self.is_running = False
    
    def animate_chain(self, nodes: List['TechNode'], connections: List,
                     duration_per_node: int = 100):
        """Anima chain con fade-in progressivo"""
        self.stop()
        
        if not nodes:
            return
        
        self.is_running = True
        
        # Imposta nodi a opacity bassa iniziale
        for node in nodes:
            node.setOpacity(0.2)
            node.is_in_chain = True
        
        # Crea animazione sequenziale
        self.main_group = QSequentialAnimationGroup(self)
        self.main_group.finished.connect(self._on_complete)
        
        for node in nodes:
            anim = QVariantAnimation(self)
            anim.setStartValue(0.2)
            anim.setEndValue(1.0)
            anim.setDuration(duration_per_node)
            anim.setEasingCurve(QEasingCurve.OutCubic)
            
            node_ref = node
            anim.valueChanged.connect(lambda v, n=node_ref: n.setOpacity(v))
            
            self.main_group.addAnimation(anim)
        
        self.main_group.start()
    
    def stop(self):
        """Ferma tutte le animazioni"""
        if self.main_group:
            self.main_group.stop()
        for anim in self.animations:
            anim.stop()
        self.animations.clear()
        self.is_running = False
    
    def _on_complete(self):
        self.is_running = False
        self.animation_complete.emit()


# =============================================================================
# MINIMAP WIDGET
# =============================================================================

class MiniMapWidget(QFrame):
    """Overview miniatura del tech tree con navigazione click"""
    
    viewport_changed = pyqtSignal(QPointF)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(220, 160)
        self.setStyleSheet("""
            MiniMapWidget {
                background-color: #0d1117;
                border: 1px solid #30363d;
                border-radius: 8px;
            }
        """)
        
        self.scene_rect = QRectF()
        self.viewport_rect = QRectF()
        self.node_positions: List[Tuple[float, float, QColor]] = []
        self.scale_factor = 1.0
        
        self.category_colors = {
            1: '#f85149', 2: '#58a6ff', 3: '#3fb950',
            4: '#d29922', 5: '#a371f7', 6: '#db61a2'
        }
    
    def update_scene(self, scene_rect: QRectF, nodes: Dict[int, 'TechNode'], techs: dict):
        self.scene_rect = scene_rect
        
        if scene_rect.width() > 0 and scene_rect.height() > 0:
            scale_x = (self.width() - 20) / scene_rect.width()
            scale_y = (self.height() - 20) / scene_rect.height()
            self.scale_factor = min(scale_x, scale_y)
        
        self.node_positions = []
        for tid, node in nodes.items():
            if tid in techs:
                cat = techs[tid].category
                color = QColor(self.category_colors.get(cat, '#888888'))
                self.node_positions.append((node.pos().x(), node.pos().y(), color))
        
        self.update()
    
    def update_viewport(self, viewport_rect: QRectF):
        """Aggiorna rettangolo viewport"""
        self.viewport_rect = viewport_rect
        self.update()
    
    def paintEvent(self, event):
        super().paintEvent(event)
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor('#0d1117'))
        
        if self.scene_rect.isEmpty():
            painter.setPen(QColor('#6e7681'))
            painter.drawText(self.rect(), Qt.AlignCenter, "Load data")
            return
        
        offset_x = 10
        offset_y = 10
        
        # Disegna nodi come punti
        for x, y, color in self.node_positions:
            px = offset_x + (x - self.scene_rect.x()) * self.scale_factor
            py = offset_y + (y - self.scene_rect.y()) * self.scale_factor
            
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(color))
            painter.drawEllipse(QPointF(px, py), 3, 3)
        
        # Disegna viewport rect
        if not self.viewport_rect.isEmpty():
            vx = offset_x + (self.viewport_rect.x() - self.scene_rect.x()) * self.scale_factor
            vy = offset_y + (self.viewport_rect.y() - self.scene_rect.y()) * self.scale_factor
            vw = self.viewport_rect.width() * self.scale_factor
            vh = self.viewport_rect.height() * self.scale_factor
            
            painter.setPen(QPen(QColor('#58a6ff'), 2))
            painter.setBrush(QBrush(QColor('#58a6ff30')))
            painter.drawRect(QRectF(vx, vy, vw, vh))
    
    def mousePressEvent(self, event):
        """Click per navigare"""
        if self.scene_rect.isEmpty():
            return
        
        offset_x = 10
        offset_y = 10
        
        scene_x = self.scene_rect.x() + (event.pos().x() - offset_x) / self.scale_factor
        scene_y = self.scene_rect.y() + (event.pos().y() - offset_y) / self.scale_factor
        
        self.viewport_changed.emit(QPointF(scene_x, scene_y))


# =============================================================================
# LAYOUT SELECTOR
# =============================================================================

class LayoutSelector(QFrame):
    """Widget per selezionare layout algorithm"""
    
    layout_changed = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            LayoutSelector {
                background-color: transparent;
            }
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        layout.addWidget(QLabel("Layout:"))
        
        self.combo = QComboBox()
        self.combo.addItem("📅 By Year", "grid")
        self.combo.addItem("🌳 Hierarchical", "sugiyama")
        self.combo.setMinimumWidth(140)
        self.combo.currentIndexChanged.connect(self._on_changed)
        layout.addWidget(self.combo)
    
    def _on_changed(self):
        engine = self.combo.currentData()
        self.layout_changed.emit(engine)
        

# =============================================================================
# PARSERS
# =============================================================================

def parse_int(v: str) -> int:
    try: return int(float(v.strip())) if v.strip() else 0
    except: return 0

def parse_float(v: str) -> float:
    try: return float(v.strip()) if v.strip() else 0.0
    except: return 0.0


def load_tech_tree(path: str) -> Dict[int, TechData]:
    techs = {}
    try:
        with open(path, "r", encoding="Windows-1252", errors="replace") as f:
            lines = f.readlines()
    except Exception as e:
        print(f"Error reading file: {e}")
        return techs
    
    start_idx = next((i+1 for i, l in enumerate(lines) if l.strip().startswith("&&TTR")), 0)
    
    count = 0  # <--- NUOVO: Inizializza contatore
    
    for row in csv.reader(lines[start_idx:], delimiter=","):
        count += 1  # <--- NUOVO: Incrementa
        
        # <--- NUOVO: Stampa ogni 1000 righe per far vedere che è vivo
        if count % 1000 == 0:
            print(f"Reading row {count}...") 
            
        if len(row) < 30 or not row[0].strip():
            continue
        try:
            tid = parse_int(row[0])
            if tid <= 0: continue
            
            t = TechData(id=tid)
            t.category = parse_int(row[1])
            t.tech_level = parse_int(row[2])
            t.prereq_1 = parse_int(row[4])
            t.prereq_2 = parse_int(row[5])
            
            for ec, vc in [(6,10), (7,11), (8,12), (9,13)]:
                eid = parse_int(row[ec])
                if eid > 0:
                    t.effects.append((eid, parse_float(row[vc])))
            
            t.time_to_research = parse_int(row[14])
            t.cost = parse_float(row[15])
            t.pop_support = parse_float(row[16])
            t.set_by_default = parse_int(row[20])
            
            if len(row) > 28: t.leads_to_1 = parse_int(row[28])
            if len(row) > 29: t.leads_to_2 = parse_int(row[29])
            
            if "//" in row[-1]:
                t.short_title = row[-1].split("//")[-1].strip()
            
            techs[tid] = t
        except: continue
    
    # Build reverse links
    print("Building reverse links...") # <--- NUOVO: Debug info
    for tid, tech in techs.items():
        for prereq in [tech.prereq_1, tech.prereq_2]:
            if prereq and prereq in techs:
                techs[prereq].prerequisite_of.append(tid)
    
    # Calculate depths
    print("Calculating depths...") # <--- N: Debug 
    _calculate_depths(techs)
    
    print("Tech tree loaded successfully.") #
    return techs


def _calculate_depths(techs: Dict[int, TechData]):
    """Calculate depth (distance from root) for each tech - OPTIMIZED"""
    depth_cache = {}
    path_visited = set()
    
    sys.setrecursionlimit(5000)
    
    def get_depth(tid: int) -> int:
        if tid not in techs:
            return 0
            
        if tid in depth_cache:
            return depth_cache[tid]
            
        if tid in path_visited:
            return 0
            
        path_visited.add(tid)
        tech = techs[tid]
        
        d1 = get_depth(tech.prereq_1) if tech.prereq_1 else 0
        d2 = get_depth(tech.prereq_2) if tech.prereq_2 else 0
        
        res = max(d1, d2) + 1
        
        depth_cache[tid] = res
        path_visited.remove(tid)
        
        tech.depth = res
        return res
    
    for tid in techs:
        get_depth(tid)


def load_units(path: str) -> Dict[int, UnitData]:
    units = {}
    try:
        with open(path, "r", encoding="latin-1", errors="replace") as f:
            lines = f.readlines()
    except: return units
    
    start_idx = next((i+1 for i, l in enumerate(lines) if l.strip().startswith("&&UNITS")), 0)
    
    for row in csv.reader(lines[start_idx:], delimiter=",", quotechar='"'):
        if not row or len(row) < 30 or row[0].strip().startswith("//"):
            continue
        try:
            u = UnitData()
            u.id = parse_int(row[0])
            u.name = row[1].strip().strip('"')
            u.class_num = parse_int(row[2])
            year_val = parse_int(row[4])
            u.year = str(1900 + year_val) if year_val > 0 else ""
            
            # Tech Requirement is at column 23
            u.req_tech_id = parse_int(row[23]) if len(row) > 23 else 0
            u.region = row[12].strip() if len(row) > 12 else ""
            
            # Strength (numero soldati/veicoli) è alla colonna 13
            strength = parse_int(row[13]) or 1
            
            # --- CORREZIONE DEFINITIVA ---
            # 1. Usiamo la colonna 26 (come nel tuo file per Pennsylvania, Moltke, ecc.)
            # 2. Moltiplichiamo per 1.000.000 (il file dice "11.1" per 11.1 Milioni)
            # 3. Moltiplichiamo per strength (il costo nel file è solitamente per singolo pezzo)
            cost_per_unit_m = parse_float(row[26]) if len(row) > 26 else 0.0
            u.cost = cost_per_unit_m * 1000000.0 * strength
            # -----------------------------
            
            if u.id > 0:
                units[u.id] = u
        except: continue
    
    return units


def link_units_to_techs(techs: Dict[int, TechData], units: Dict[int, UnitData]):
    for u in units.values():
        if u.req_tech_id and u.req_tech_id in techs:
            techs[u.req_tech_id].unlocks_units.append(u)


# =============================================================================
# CACHE SYSTEM
# =============================================================================

CACHE_DIR = Path.home() / "Documents" / "SR2030_Logger" / "cache"
CACHE_VERSION = 2  # Increment if data structure changes

def _get_file_hash(path: str) -> str:
    """Get modification time + size as a quick hash"""
    try:
        p = Path(path)
        stat = p.stat()
        return f"{stat.st_mtime}_{stat.st_size}"
    except:
        return ""

def _get_cache_path(ttrx_path: str, unit_path: str) -> Path:
    """Generate cache filename based on source files"""
    # Use hash of paths for unique cache file
    key = f"{ttrx_path}|{unit_path}"
    hash_name = hashlib.md5(key.encode()).hexdigest()[:12]
    return CACHE_DIR / f"techcache_{hash_name}.pkl"

def load_from_cache(ttrx_path: str, unit_path: str) -> Optional[Tuple[Dict[int, TechData], Dict[int, UnitData]]]:
    """Try to load data from cache if valid"""
    cache_path = _get_cache_path(ttrx_path, unit_path)
    
    if not cache_path.exists():
        return None
    
    try:
        with open(cache_path, 'rb') as f:
            cache_data = pickle.load(f)
        
        # Validate cache
        if cache_data.get('version') != CACHE_VERSION:
            return None
        if cache_data.get('ttrx_hash') != _get_file_hash(ttrx_path):
            return None
        if cache_data.get('unit_hash') != _get_file_hash(unit_path):
            return None
        
        return cache_data['techs'], cache_data['units']
    except:
        return None

def save_to_cache(ttrx_path: str, unit_path: str, techs: Dict[int, TechData], units: Dict[int, UnitData]):
    """Save parsed data to cache"""
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        
        cache_data = {
            'version': CACHE_VERSION,
            'ttrx_hash': _get_file_hash(ttrx_path),
            'unit_hash': _get_file_hash(unit_path),
            'ttrx_path': ttrx_path,
            'unit_path': unit_path,
            'cached_at': datetime.now().isoformat(),
            'techs': techs,
            'units': units,
        }
        
        cache_path = _get_cache_path(ttrx_path, unit_path)
        with open(cache_path, 'wb') as f:
            pickle.dump(cache_data, f, protocol=pickle.HIGHEST_PROTOCOL)
        
        return True
    except Exception as e:
        print(f"Cache save failed: {e}")
        return False

def clear_cache():
    """Clear all cached data"""
    try:
        if CACHE_DIR.exists():
            for f in CACHE_DIR.glob("techcache_*.pkl"):
                f.unlink()
        return True
    except:
        return False


# =============================================================================
# ANALYSIS FUNCTIONS
# =============================================================================

def get_full_prereq_chain(tech_id: int, techs: Dict[int, TechData]) -> Set[int]:
    """Get all prerequisites recursively"""
    chain = set()
    visited = set()
    
    def traverse(tid):
        if tid in visited or tid not in techs:
            return
        visited.add(tid)
        chain.add(tid)
        t = techs[tid]
        if t.prereq_1: traverse(t.prereq_1)
        if t.prereq_2: traverse(t.prereq_2)
    
    if tech_id in techs:
        t = techs[tech_id]
        if t.prereq_1: traverse(t.prereq_1)
        if t.prereq_2: traverse(t.prereq_2)
    
    return chain


def get_all_descendants(tech_id: int, techs: Dict[int, TechData]) -> Set[int]:
    """Get all techs that eventually require this one"""
    descendants = set()
    visited = set()
    
    def traverse(tid):
        if tid in visited or tid not in techs:
            return
        visited.add(tid)
        descendants.add(tid)
        for child in techs[tid].prerequisite_of:
            traverse(child)
    
    if tech_id in techs:
        for child in techs[tech_id].prerequisite_of:
            traverse(child)
    
    return descendants


def calculate_chain_cost(tech_id: int, techs: Dict[int, TechData]) -> float:
    """Calculate total cost including all prerequisites"""
    chain = get_full_prereq_chain(tech_id, techs)
    chain.add(tech_id)
    return sum(techs[tid].cost for tid in chain if tid in techs)


def find_orphan_techs(techs: Dict[int, TechData]) -> List[int]:
    """Find techs with missing prerequisites"""
    orphans = []
    for tid, tech in techs.items():
        if tech.prereq_1 and tech.prereq_1 not in techs:
            orphans.append((tid, tech.prereq_1, 'prereq_1'))
        if tech.prereq_2 and tech.prereq_2 not in techs:
            orphans.append((tid, tech.prereq_2, 'prereq_2'))
    return orphans


def find_techs_by_effect(effect_id: int, techs: Dict[int, TechData]) -> List[Tuple[int, float]]:
    """Find all techs that have a specific effect"""
    results = []
    for tid, tech in techs.items():
        for eid, val in tech.effects:
            if eid == effect_id:
                results.append((tid, val))
    return sorted(results, key=lambda x: x[1], reverse=True)


# =============================================================================
# GRAPHICS: TECH NODE
# =============================================================================

class TechNode(QGraphicsRectItem):
    """Visual node for a single technology - optimized for performance"""
    
    WIDTH = 200
    HEIGHT = 70
    
    def __init__(self, tech: TechData, view: 'TechTreeView'):
        super().__init__(0, 0, self.WIDTH, self.HEIGHT)
        self.tech = tech
        self.view = view
        self.setAcceptHoverEvents(True)
        self.setFlag(QGraphicsRectItem.ItemIsSelectable)
        self.setZValue(10)
        
        self.is_highlighted = False
        self.is_in_chain = False
        self.is_dimmed = False
        
        cat = CATEGORIES.get(tech.category, {'color': '#888', 'bg': '#333', 'icon': '?'})
        self.cat_color = QColor(cat['color'])
        self.cat_bg = QColor(cat['bg'])
        self.cat_icon = cat['icon']
        
        # Pre-calculate display strings
        self.title_text = tech.short_title[:22] + "…" if len(tech.short_title) > 22 else tech.short_title
        self.info_text = f"ID: {tech.id}  •  Lvl {tech.tech_level}"
        cost_str = f"${tech.cost/1e9:.1f}B" if tech.cost >= 1e9 else f"${tech.cost/1e6:.0f}M"
        self.detail_text = f"{cost_str}  •  {tech.time_to_research}d"
        self.unit_count = len(tech.unlocks_units)
        self.has_effects = bool(tech.effects)
        
        self.setPen(QPen(QColor(COLORS['border']), 1))
        self.setBrush(QBrush(QColor(COLORS['bg_medium'])))
        self.setCacheMode(QGraphicsItem.DeviceCoordinateCache)
        
        self._opacity = 1.0
        self.cluster_id = 0
        
    def setOpacity(self, opacity: float):
        self._opacity = max(0.0, min(1.0, opacity))
        self.update()
        
    def setOpacity(self, opacity: float):
        self._opacity = opacity
        self.update()
    
    def opacity(self) -> float:
        return self._opacity
    
    def paint(self, painter, option, widget):
        painter.setOpacity(self._opacity)

    def paint(self, painter, option, widget):
        painter.setOpacity(self._opacity)
        
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.TextAntialiasing)
        
        rect = self.rect()
        
        # Determine background color
        if self.is_dimmed:
            bg_color = QColor(COLORS['bg_dark'])
            bg_color.setAlpha(100)
        elif self.is_highlighted:
            bg_color = self.cat_bg
        elif self.is_in_chain:
            bg_color = QColor(COLORS['bg_light'])
        else:
            bg_color = QColor(COLORS['bg_medium'])
        
        # Selection glow
        if self.isSelected():
            glow = QColor(self.cat_color)
            glow.setAlpha(80)
            painter.setPen(QPen(self.cat_color, 3))
            painter.setBrush(QBrush(glow))
            painter.drawRoundedRect(rect.adjusted(-3, -3, 3, 3), 10, 10)
        
        # Main background
        painter.setBrush(QBrush(bg_color))
        border_color = self.cat_color if self.isSelected() or self.is_highlighted else QColor(COLORS['border'])
        painter.setPen(QPen(border_color, 2 if self.isSelected() else 1))
        painter.drawRoundedRect(rect, 8, 8)
        
        # Category bar (left edge)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(self.cat_color))
        painter.drawRoundedRect(QRectF(0, 0, 4, self.HEIGHT), 2, 2)
        
        # Category icon
        painter.setFont(QFont("Segoe UI Emoji", 14))
        painter.setPen(QColor(COLORS['text_primary']))
        painter.drawText(QRectF(10, 6, 30, 24), Qt.AlignCenter, self.cat_icon)
        
        # Title
        painter.setFont(QFont("Segoe UI", 10, QFont.Bold))
        painter.setPen(QColor(COLORS['text_primary']))
        painter.drawText(QRectF(38, 8, self.WIDTH - 50, 20), Qt.AlignLeft | Qt.AlignVCenter, self.title_text)
        
        # Info line
        painter.setFont(QFont("Segoe UI", 8))
        painter.setPen(QColor(COLORS['text_muted']))
        painter.drawText(QRectF(38, 26, self.WIDTH - 50, 16), Qt.AlignLeft | Qt.AlignVCenter, self.info_text)
        
        # Details line
        painter.setPen(QColor(COLORS['text_secondary']))
        painter.drawText(QRectF(38, 44, self.WIDTH - 70, 16), Qt.AlignLeft | Qt.AlignVCenter, self.detail_text)
        
        # Units badge
        if self.unit_count > 0:
            badge_x = self.WIDTH - 35
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(self.cat_color))
            painter.setOpacity(0.8)
            painter.drawRoundedRect(QRectF(badge_x, 45, 28, 18), 4, 4)
            painter.setOpacity(1.0)
            
            painter.setFont(QFont("Segoe UI", 9, QFont.Bold))
            painter.setPen(QColor("white"))
            painter.drawText(QRectF(badge_x, 44, 28, 18), Qt.AlignCenter, str(self.unit_count))
        
        # Effects indicator
        if self.has_effects:
            painter.setFont(QFont("Segoe UI Emoji", 10))
            painter.setPen(QColor(COLORS['accent_orange']))
            painter.drawText(QRectF(self.WIDTH - 25, 6, 20, 20), Qt.AlignCenter, "⚡")
            
        painter.setOpacity(1.0)
    
    def hoverEnterEvent(self, event):
        self.setCursor(Qt.PointingHandCursor)
        self.view.show_tooltip(self.tech, event.screenPos())
        super().hoverEnterEvent(event)
    
    def hoverLeaveEvent(self, event):
        QToolTip.hideText()
        super().hoverLeaveEvent(event)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.view.on_tech_clicked(self.tech)
        super().mousePressEvent(event)
    
    def mouseDoubleClickEvent(self, event):
        self.view.on_tech_double_clicked(self.tech)
        super().mouseDoubleClickEvent(event)
        
        
    


class ConnectionLine(QGraphicsPathItem):
    """Bezier connection between nodes"""
    
    def __init__(self, start: QPointF, end: QPointF, highlight: bool = False):
        super().__init__()
        self.setZValue(1)
        
        color = QColor(COLORS['accent_green'] if highlight else COLORS['border'])
        width = 2.5 if highlight else 1.5
        
        if highlight:
            color.setAlpha(200)
        else:
            color.setAlpha(100)
        
        self.setPen(QPen(color, width, Qt.SolidLine, Qt.RoundCap))
        
        path = QPainterPath()
        path.moveTo(start)
        
        dx = end.x() - start.x()
        ctrl = min(abs(dx) * 0.4, 60)
        
        path.cubicTo(
            QPointF(start.x() + ctrl, start.y()),
            QPointF(end.x() - ctrl, end.y()),
            end
        )
        
        self.setPath(path)

class TimelineRuler(QGraphicsItem):
    """Draws a timeline bar at the TOP"""
    
    def __init__(self, level_positions: Dict[int, float], graph_height: float, width: float):
        super().__init__()
        self.level_positions = level_positions
        self.graph_height = graph_height # We need to know how deep the graph is
        self.total_width = width
        self.setZValue(-1) 
        
    def boundingRect(self):
        # The bounding rect now covers the whole height to allow drawing grid lines
        return QRectF(0, 0, self.total_width, self.graph_height)
        
    def paint(self, painter, option, widget):
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Header background for the years (optional, makes it look like a bar)
        header_rect = QRectF(0, 0, self.total_width, 40)
        # painter.setBrush(QBrush(QColor(COLORS['bg_medium']))) # Optional background
        # painter.setPen(Qt.NoPen)
        # painter.drawRect(header_rect)
        
        # Font for the year
        font = QFont("Segoe UI", 12, QFont.Bold)
        painter.setFont(font)
        
        sorted_levels = sorted(self.level_positions.keys())
        
        for level in sorted_levels:
            x = self.level_positions[level]
            year = 1900 + level 
            
            # 1. Draw Year Box at the Top
            text_rect = QRectF(x - 25, 5, 50, 25) # Position: Top (Y=5)
            
            # Dark bubble background
            painter.setBrush(QBrush(QColor(COLORS['bg_dark']))) 
            painter.setPen(QPen(QColor(COLORS['border']), 1))
            painter.drawRoundedRect(text_rect, 4, 4)
            
            # Text
            painter.setPen(QColor(COLORS['accent_blue']))
            painter.drawText(text_rect, Qt.AlignCenter, str(year))
            
            # 2. Draw vertical tick just below the text
            painter.setPen(QPen(QColor(COLORS['text_muted']), 1))
            painter.drawLine(QPointF(x, 30), QPointF(x, 40))
            
            # 3. Draw Grid Line going DOWNWARDS
            grid_pen = QPen(QColor(COLORS['border']))
            grid_pen.setStyle(Qt.DashLine)
            grid_pen.setWidthF(0.5)
            
            painter.setPen(grid_pen)
            # Draw from top (Y=40) down to the bottom of the graph
            painter.drawLine(QPointF(x, 40), QPointF(x, self.graph_height))




# =============================================================================
# TECH TREE VIEW
# =============================================================================

class TechTreeView(QGraphicsView):
    """Main tech tree visualization - con layout multipli e animazioni"""
    
    viewport_changed = pyqtSignal(QRectF)
    tech_selected = pyqtSignal(object)
    tech_double_clicked = pyqtSignal(object)
    
    def __init__(self):
        super().__init__()
        self.scene = QGraphicsScene()
        self.setScene(self.scene)
        
        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.TextAntialiasing)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.setBackgroundBrush(QBrush(QColor(COLORS['bg_dark'])))
        
        self.techs: Dict[int, TechData] = {}
        self.nodes: Dict[int, TechNode] = {}
        self.connections: List[ConnectionLine] = []
        self.cluster_backgrounds: List[ClusterBackground] = []
        
        self.category_filter = 0
        self.search_filter = ""
        self.effect_filter = 0
        self.highlighted_chain: Set[int] = set()
        
        self._zoom = 1.0
        
        # Layout engines
        self.layout_engines = {
            'grid': GridLayoutEngine(),
            'sugiyama': SugiyamaLayoutEngine(use_tech_level_as_layer=True),
        }
        self.current_layout = 'grid'
        
        # Animator per chain highlight
        self.animator = ChainAnimator(self)
        
        # Timer per aggiornare minimap
        self._viewport_timer = QTimer()
        self._viewport_timer.timeout.connect(self._emit_viewport_update)
        self._viewport_timer.setInterval(100)
    
    def load_data(self, techs: Dict[int, TechData]):
        self.techs = techs
        self.rebuild()
    
    def set_layout_engine(self, engine_name: str):
        """Cambia algoritmo di layout"""
        if engine_name in self.layout_engines:
            self.current_layout = engine_name
            self.rebuild()
    
    def rebuild(self):
        self.scene.clear()
        self.nodes.clear()
        self.connections.clear()
        self.cluster_backgrounds.clear()
        
        # Apply filters
        filtered = self._apply_filters()
        
        if not filtered:
            text = self.scene.addText("No technologies match current filters", 
                                      QFont("Segoe UI", 16))
            text.setDefaultTextColor(QColor(COLORS['text_muted']))
            return
        
        self.scene.setItemIndexMethod(QGraphicsScene.NoIndex)
        
        # Layout nodes 
        if self.current_layout == 'sugiyama':
            self._layout_nodes_sugiyama(filtered)
        else:
            self._layout_nodes_grid(filtered)
        
        # Draw connections
        self._draw_connections(filtered)
        
        # Apply highlighting
        self._apply_highlighting()
        
        self.scene.setItemIndexMethod(QGraphicsScene.BspTreeIndex)
        self.scene.setSceneRect(self.scene.itemsBoundingRect().adjusted(-100, -100, 100, 100))
        
        # Avvia viewport tracking per minimap
        self._viewport_timer.start()
    
    def _layout_nodes_grid(self, techs: Dict[int, TechData]):
        """Layout GRID originale - per anno/tech_level"""
        by_level = defaultdict(list)
        for tech in techs.values():
            by_level[tech.tech_level].append(tech)
        
        H_SPACE = 320  
        V_SPACE = 130
        TOP_MARGIN = 120 
        
        col = 0
        count = 0
        level_x_positions = {}
        max_rows = 0 
        
        for level in sorted(by_level.keys()):
            level_techs = sorted(by_level[level], key=lambda t: (t.category, t.id))
            
            center_x = 50 + col * H_SPACE + (TechNode.WIDTH / 2)
            level_x_positions[level] = center_x
            
            if len(level_techs) > max_rows:
                max_rows = len(level_techs)
            
            for row, tech in enumerate(level_techs):
                x = 50 + col * H_SPACE
                y = TOP_MARGIN + (row * V_SPACE)
                
                node = TechNode(tech, self)
                node.setPos(x, y)
                self.scene.addItem(node)
                self.nodes[tech.id] = node
                
                count += 1
                if count % 1000 == 0:
                    QApplication.processEvents()
            
            col += 1
        
        # Timeline
        total_graph_height = TOP_MARGIN + (max_rows * V_SPACE) + 100
        total_width = 50 + (col * H_SPACE)
        timeline = TimelineRuler(level_x_positions, total_graph_height, total_width)
        self.scene.addItem(timeline)
    
    def _layout_nodes_sugiyama(self, techs: Dict[int, TechData]):
        """Layout SUGIYAMA gerarchico con cluster visualization"""
        engine = self.layout_engines['sugiyama']
        layout = engine.compute(self.techs, self.category_filter)
        
        if not layout.positions:
            return
        
        #  cluster backgrounds 
        #self._draw_cluster_backgrounds(layout)
        
        # nodes
        count = 0
        for tid, pos in layout.positions.items():
            if tid not in techs:
                continue
            
            tech = techs[tid]
            node = TechNode(tech, self)
            node.setPos(pos.x, pos.y)
            node.cluster_id = pos.cluster_id  # Save
            self.scene.addItem(node)
            self.nodes[tid] = node
            
            count += 1
            if count % 1000 == 0:
                QApplication.processEvents()
        
        # Timeline
        if layout.layer_positions:
            timeline = TimelineRuler(
                layout.layer_positions, 
                layout.height, 
                layout.width
            )
            self.scene.addItem(timeline)
    
    def _draw_cluster_backgrounds(self, layout: LayoutResult):
        for cluster_id, tech_ids in layout.clusters.items():
            if len(tech_ids) < 3:
                continue
            
            positions = [
                layout.positions[tid] 
                for tid in tech_ids 
                if tid in layout.positions
            ]
            
            if not positions:
                continue
            
            min_x = min(p.x for p in positions)
            min_y = min(p.y for p in positions)
            max_x = max(p.x for p in positions) + TechNode.WIDTH
            max_y = max(p.y for p in positions) + TechNode.HEIGHT
            
            bounds = QRectF(min_x, min_y, max_x - min_x, max_y - min_y)
            color = layout.cluster_colors.get(cluster_id, '#88888820')
            
            bg = ClusterBackground(bounds, color, cluster_id)
            self.cluster_backgrounds.append(bg)
            self.scene.addItem(bg)
    
    def _apply_filters(self) -> Dict[int, TechData]:
        result = {}
        for tid, tech in self.techs.items():
            if self.category_filter and tech.category != self.category_filter:
                continue
            
            if self.search_filter:
                q = self.search_filter.lower()
                if q not in tech.short_title.lower() and str(tid) != self.search_filter:
                    continue
            
            if self.effect_filter:
                if not any(eid == self.effect_filter for eid, _ in tech.effects):
                    continue
            
            result[tid] = tech
        
        return result
    
    def _draw_connections(self, techs: Dict[int, TechData]):
        for tid, tech in techs.items():
            if tid not in self.nodes:
                continue
            
            node = self.nodes[tid]
            end_pt = QPointF(node.pos().x(), node.pos().y() + TechNode.HEIGHT / 2)
            
            for prereq_id in [tech.prereq_1, tech.prereq_2]:
                if prereq_id and prereq_id in self.nodes:
                    prereq_node = self.nodes[prereq_id]
                    start_pt = QPointF(
                        prereq_node.pos().x() + TechNode.WIDTH,
                        prereq_node.pos().y() + TechNode.HEIGHT / 2
                    )
                    
                    highlight = tid in self.highlighted_chain and prereq_id in self.highlighted_chain
                    line = ConnectionLine(start_pt, end_pt, highlight)
                    self.scene.addItem(line)
                    self.connections.append(line)
    
    def _apply_highlighting(self):
        for tid, node in self.nodes.items():
            if self.highlighted_chain:
                node.is_in_chain = tid in self.highlighted_chain
                node.is_dimmed = tid not in self.highlighted_chain
            else:
                node.is_in_chain = False
                node.is_dimmed = False
            node.update()
    
    # =========================================================================
    # ANIMATED CHAIN HIGHLIGHT
    # =========================================================================
    
    def highlight_chain_animated(self, tech_id: int):
        """Evidenzia chain con animazione progressiva fade-in"""
        # Stop animazioni precedenti e clear
        self.animator.stop()
        self.highlighted_chain.clear()
        
        if tech_id not in self.techs:
            return
        
        # Ottieni chain in ordine topologico (dai prerequisiti al target)
        chain = self._get_ordered_chain(tech_id)
        self.highlighted_chain = set(chain)
        
        # Prepara nodi per animazione
        chain_nodes = [self.nodes[tid] for tid in chain if tid in self.nodes]
        
        # Dim tutti i nodi non in chain
        for tid, node in self.nodes.items():
            if tid not in self.highlighted_chain:
                node.is_dimmed = True
                node.setOpacity(0.25)
                node.update()
            else:
                node.is_in_chain = True
                node.is_dimmed = False
        
        # Lancia animazione
        if chain_nodes:
            self.animator.animate_chain(chain_nodes, [], duration_per_node=100)
        
        # Ridisegna connessioni con highlight
        self._redraw_connections_only()
    
    def _get_ordered_chain(self, target_id: int) -> List[int]:
        """Restituisce prerequisiti in ordine topologico (root -> target)"""
        chain = []
        visited = set()
        
        def visit(tid):
            if tid in visited or tid not in self.techs:
                return
            visited.add(tid)
            tech = self.techs[tid]
            if tech.prereq_1:
                visit(tech.prereq_1)
            if tech.prereq_2:
                visit(tech.prereq_2)
            chain.append(tid)
        
        visit(target_id)
        return chain
    
    def _redraw_connections_only(self):
        """Ridisegna solo le connessioni (per update highlight senza rebuild completo)"""
        # Rimuovi vecchie connessioni
        for conn in self.connections:
            self.scene.removeItem(conn)
        self.connections.clear()
        
        # Ridisegna
        self._draw_connections(self._apply_filters())
    
    # =========================================================================
    # STANDARD HIGHLIGHT (istantaneo, senza animazione)
    # =========================================================================
    
    def highlight_chain(self, tech_id: int, include_descendants: bool = False):
        """Highlight istantaneo della chain (senza animazione)"""
        self.highlighted_chain = get_full_prereq_chain(tech_id, self.techs)
        self.highlighted_chain.add(tech_id)
        
        if include_descendants:
            self.highlighted_chain |= get_all_descendants(tech_id, self.techs)
        
        self._apply_highlighting()
        self._redraw_connections_only()
    
    def clear_highlight(self):
        """Pulisce tutti gli highlight e resetta opacity"""
        self.animator.stop()
        self.highlighted_chain.clear()
        
        for node in self.nodes.values():
            node.is_highlighted = False
            node.is_in_chain = False
            node.is_dimmed = False
            node.setOpacity(1.0)
            node.update()
        
        self._redraw_connections_only()
    
    # =========================================================================
    # VIEWPORT & MINIMAP
    # =========================================================================
    
    def _emit_viewport_update(self):
        """Emette il rect della viewport corrente per la minimap"""
        viewport_rect = self.mapToScene(self.viewport().rect()).boundingRect()
        self.viewport_changed.emit(viewport_rect)
    
    def scrollContentsBy(self, dx, dy):
        """Override per notificare minimap quando si scrolla"""
        super().scrollContentsBy(dx, dy)
        self._emit_viewport_update()
    
    def wheelEvent(self, event):
        """Zoom con rotella + notifica minimap"""
        factor = 1.15 if event.angleDelta().y() > 0 else 1/1.15
        new_zoom = self._zoom * factor
        
        if 0.15 <= new_zoom <= 4.0:
            self._zoom = new_zoom
            self.scale(factor, factor)
            self._emit_viewport_update()
    
    # =========================================================================
    # FILTERS & NAVIGATION
    # =========================================================================
    
    def set_category(self, cat: int):
        self.category_filter = cat
        self.rebuild()
    
    def set_search(self, text: str):
        self.search_filter = text
        self.rebuild()
    
    def set_effect_filter(self, eff_id: int):
        self.effect_filter = eff_id
        self.rebuild()
    
    def center_on_tech(self, tech_id: int):
        if tech_id in self.nodes:
            self.centerOn(self.nodes[tech_id])
            self.nodes[tech_id].setSelected(True)
    
    # =========================================================================
    # TOOLTIP & EVENTS
    # =========================================================================
    
    def show_tooltip(self, tech: TechData, pos):
        cat = CATEGORIES.get(tech.category, {'name': '?', 'icon': '?', 'color': '#888'})
        
        html = f"""
        <div style='font-family: Segoe UI; padding: 8px;'>
            <div style='font-size: 14px; font-weight: bold; color: {cat['color']};'>
                {cat['icon']} {tech.short_title}
            </div>
            <div style='color: #888; margin: 4px 0;'>
                ID: {tech.id} | Level: {tech.tech_level} | {cat['name']}
            </div>
            <hr style='border-color: #444;'>
            <div>💰 Cost: ${tech.cost:,.0f}</div>
            <div>⏱️ Time: {tech.time_to_research} days</div>
            <div>👥 Support: {tech.pop_support*100:.1f}%</div>
        """
        
        if tech.effects:
            html += "<hr style='border-color: #444;'><div style='color: #58a6ff;'>Effects:</div>"
            for eid, val in tech.effects:
                eff = EFFECT_DEFINITIONS.get(eid, {'name': f'Effect {eid}', 'icon': '•'})
                sign = '+' if val >= 0 else ''
                val_str = f"{sign}{val*100:.0f}%" if abs(val) < 10 else f"{sign}{val:.1f}"
                color = '#3fb950' if val >= 0 else '#f85149'
                html += f"<div style='color: {color};'>{eff['icon']} {eff['name']}: {val_str}</div>"
        
        if tech.unlocks_units:
            html += f"<hr style='border-color: #444;'><div style='color: #d29922;'>🔧 Unlocks {len(tech.unlocks_units)} units</div>"
        
        html += "</div>"
        
        QToolTip.showText(pos, html)
    
    def on_tech_clicked(self, tech: TechData):
        self.tech_selected.emit(tech)
    
    def on_tech_double_clicked(self, tech: TechData):
        """Double click = highlight animato della chain"""
        self.highlight_chain_animated(tech.id)
        self.tech_double_clicked.emit(tech)

# =============================================================================
# SIDE PANELS
# =============================================================================

class TechDetailPanel(QWidget):
    """Detailed tech information panel"""
    
    navigate_to_tech = pyqtSignal(int)
    
    def __init__(self):
        super().__init__()
        self.techs: Dict[int, TechData] = {}
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Header (Tech Title)
        header = QFrame()
        header.setObjectName("card")
        header.setStyleSheet(f"QFrame#card {{ background-color: {COLORS['bg_medium']}; border-bottom: 1px solid {COLORS['border']}; padding: 20px; }}")
        header_layout = QVBoxLayout(header)
        header_layout.setSpacing(8)
        
        self.icon_label = QLabel("🔬")
        self.icon_label.setFont(QFont("Segoe UI Emoji", 36))
        self.icon_label.setAlignment(Qt.AlignCenter)
        
        self.title_label = QLabel("Select a Technology")
        self.title_label.setFont(QFont("Segoe UI", 18, QFont.Bold))
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setWordWrap(True)
        
        self.subtitle_label = QLabel("")
        self.subtitle_label.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 13px;")
        self.subtitle_label.setAlignment(Qt.AlignCenter)
        
        header_layout.addWidget(self.icon_label)
        header_layout.addWidget(self.title_label)
        header_layout.addWidget(self.subtitle_label)
        
        layout.addWidget(header)
        
        # Scroll area for content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet(f"QScrollArea {{ background-color: {COLORS['bg_dark']}; border: none; }}")
        
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(20)
        content_layout.setContentsMargins(15, 20, 15, 20)
        
        # Stats grid
        stats_frame = QFrame()
        stats_frame.setObjectName("card")
        stats_grid = QGridLayout(stats_frame)
        stats_grid.setVerticalSpacing(15)
        
        self.cost_value = QLabel("-")
        self.cost_value.setObjectName("statValue")
        self.time_value = QLabel("-")
        self.time_value.setObjectName("statValue")
        self.chain_cost_value = QLabel("-")
        self.chain_cost_value.setObjectName("statValue")
        self.support_value = QLabel("-")
        self.support_value.setObjectName("statValue")
        
        stats = [
            ("💰 Cost", self.cost_value, 0, 0),
            ("⏱️ Time", self.time_value, 0, 1),
            ("🔗 Chain Cost", self.chain_cost_value, 1, 0),
            ("👥 Support", self.support_value, 1, 1),
        ]
        
        for label_text, value_widget, row, col in stats:
            cell = QVBoxLayout()
            lbl = QLabel(label_text)
            lbl.setObjectName("statLabel")
            cell.addWidget(value_widget)
            cell.addWidget(lbl)
            stats_grid.addLayout(cell, row, col)
        
        content_layout.addWidget(stats_frame)
        
        # --- TAB WIDGET ---
        self.info_tabs = QTabWidget()
        self.info_tabs.setStyleSheet("QTabWidget::pane { border: 0; }")
        
        # Tab 1: Links
        tab_relations = QWidget()
        rel_layout = QVBoxLayout(tab_relations)
        rel_layout.setContentsMargins(5, 15, 5, 5)
        
        rel_layout.addWidget(QLabel("Requires:"))
        self.prereq_list = QListWidget()
        self.prereq_list.setMaximumHeight(100)
        self.prereq_list.itemDoubleClicked.connect(self._on_prereq_clicked)
        rel_layout.addWidget(self.prereq_list)
        
        rel_layout.addWidget(QLabel("Leads To / Required By:"))
        self.leads_list = QListWidget()
        self.leads_list.setMinimumHeight(150)
        self.leads_list.itemDoubleClicked.connect(self._on_lead_clicked)
        rel_layout.addWidget(self.leads_list)
        
        self.info_tabs.addTab(tab_relations, "🔗 Links")
        
        # Tab 2: Effects
        tab_effects = QWidget()
        eff_layout = QVBoxLayout(tab_effects)
        eff_layout.setContentsMargins(5, 15, 5, 5)
        self.effects_list = QListWidget()
        self.effects_list.setAlternatingRowColors(True)
        eff_layout.addWidget(self.effects_list)
        self.info_tabs.addTab(tab_effects, "⚡ Effects")
        
        # Tab 3: Units
        tab_units = QWidget()
        units_layout = QVBoxLayout(tab_units)
        units_layout.setContentsMargins(0, 15, 0, 0)
        
        self.units_tree = QTreeWidget()
        self.units_tree.setHeaderLabels(["Unit Name", "Class", "Cost"])
        self.units_tree.setAlternatingRowColors(True)
        self.units_tree.setRootIsDecorated(False)
        self.units_tree.setMinimumHeight(300)
        
        header = self.units_tree.header()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setDefaultAlignment(Qt.AlignLeft)
        
        units_layout.addWidget(self.units_tree)
        self.info_tabs.addTab(tab_units, "🔧 Units")
        
        content_layout.addWidget(self.info_tabs)
        content_layout.addStretch()
        
        scroll.setWidget(content)
        layout.addWidget(scroll)

    def set_techs(self, techs: Dict[int, TechData]):
        self.techs = techs
    
    def show_tech(self, tech: TechData):
        cat = CATEGORIES.get(tech.category, {'name': '?', 'icon': '?', 'color': '#888'})
        
        self.icon_label.setText(cat['icon'])
        self.title_label.setText(tech.short_title)
        self.title_label.setStyleSheet(f"color: {cat['color']};")
        self.subtitle_label.setText(f"ID: {tech.id}  •  Level: {tech.tech_level}  •  {cat['name']}")
        
        # Stats
        if tech.cost >= 1e9:
            self.cost_value.setText(f"${tech.cost/1e9:.2f}B")
        else:
            self.cost_value.setText(f"${tech.cost/1e6:.1f}M")
        
        self.time_value.setText(f"{tech.time_to_research}d")
        
        chain_cost = calculate_chain_cost(tech.id, self.techs)
        if chain_cost >= 1e9:
            self.chain_cost_value.setText(f"${chain_cost/1e9:.2f}B")
        else:
            self.chain_cost_value.setText(f"${chain_cost/1e6:.1f}M")
        
        self.support_value.setText(f"{tech.pop_support*100:.1f}%")
        
        # Prerequisites
        self.prereq_list.clear()
        for prereq_id in [tech.prereq_1, tech.prereq_2]:
            if prereq_id and prereq_id in self.techs:
                prereq = self.techs[prereq_id]
                item = QListWidgetItem(f"  {prereq.short_title}  (ID: {prereq_id})")
                item.setData(Qt.UserRole, prereq_id)
                self.prereq_list.addItem(item)
        
        if self.prereq_list.count() == 0:
            self.prereq_list.addItem("  No prerequisites (root technology)")
        
        # Effects
        self.effects_list.clear()
        for eid, val in tech.effects:
            eff = EFFECT_DEFINITIONS.get(eid, {'name': f'Effect {eid}', 'icon': '•', 'category': '?'})
            sign = '+' if val >= 0 else ''
            val_str = f"{sign}{val*100:.0f}%" if abs(val) < 10 else f"{sign}{val:.1f}"
            
            item = QListWidgetItem(f"  {eff['icon']} {eff['name']}: {val_str}")
            color = COLORS['accent_green'] if val >= 0 else COLORS['accent_red']
            item.setForeground(QBrush(QColor(color)))
            self.effects_list.addItem(item)
        
        if self.effects_list.count() == 0:
            self.effects_list.addItem("  No direct effects")
        
        # Units
        self.units_tree.clear()
        for unit in tech.unlocks_units:
            cls = CLASS_INFO.get(unit.class_num, {'name': f'{unit.class_num}', 'icon': '?'})
            cost_str = f"${unit.cost/1e6:.1f}M" if unit.cost else "-"
            
            item = QTreeWidgetItem([
                f"  {unit.name}",
                f"{cls['icon']} {cls['name']}",
                cost_str
            ])
            self.units_tree.addTopLevelItem(item)
        
        # Leads to
        self.leads_list.clear()
        
        # Direct leads_to from file
        for lead_id in [tech.leads_to_1, tech.leads_to_2]:
            if lead_id and lead_id in self.techs:
                lead = self.techs[lead_id]
                item = QListWidgetItem(f"➡️ Leads to: {lead.short_title}  (ID: {lead_id})")
                item.setData(Qt.UserRole, lead_id)
                item.setForeground(QBrush(QColor(COLORS['accent_green'])))
                self.leads_list.addItem(item)
        
        # Techs that require this one (Required By)
        for child_id in tech.prerequisite_of:
            if child_id in self.techs:
                child = self.techs[child_id]
                child_cat = CATEGORIES.get(child.category, {'icon': '?'})
                item = QListWidgetItem(f"←  Required by: {child_cat['icon']} {child.short_title}  (ID: {child_id})")
                item.setData(Qt.UserRole, child_id)
                item.setForeground(QBrush(QColor(COLORS['accent_blue'])))
                self.leads_list.addItem(item)
        
        if self.leads_list.count() == 0:
            item = QListWidgetItem("  No dependent technologies")
            item.setForeground(QBrush(QColor(COLORS['text_muted'])))
            self.leads_list.addItem(item)

        # Tab Selection Logic
        if tech.unlocks_units:
            self.info_tabs.setCurrentIndex(2) 
        elif tech.effects:
            self.info_tabs.setCurrentIndex(1)
        else:
            self.info_tabs.setCurrentIndex(0)
    
    def _on_prereq_clicked(self, item):
        tid = item.data(Qt.UserRole)
        if tid:
            self.navigate_to_tech.emit(tid)
    
    def _on_lead_clicked(self, item):
        tid = item.data(Qt.UserRole)
        if tid:
            self.navigate_to_tech.emit(tid)


class AnalysisPanel(QWidget):
    """Analytics and statistics panel"""
    
    def __init__(self):
        super().__init__()
        self.techs: Dict[int, TechData] = {}
        self.units: Dict[int, UnitData] = {}
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        
        tabs = QTabWidget()
        
        # Overview tab
        overview = QWidget()
        overview_layout = QVBoxLayout(overview)
        overview_layout.setContentsMargins(8, 8, 8, 8)
        overview_layout.setSpacing(12)
        
        # Stats cards
        stats_grid = QGridLayout()
        stats_grid.setSpacing(8)
        
        self.total_techs = self._create_stat_card("0", "Total Techs")
        self.total_units = self._create_stat_card("0", "Total Units")
        self.linked_units = self._create_stat_card("0", "Linked Units")
        self.orphan_count = self._create_stat_card("0", "Broken Links")
        
        stats_grid.addWidget(self.total_techs, 0, 0)
        stats_grid.addWidget(self.total_units, 0, 1)
        stats_grid.addWidget(self.linked_units, 1, 0)
        stats_grid.addWidget(self.orphan_count, 1, 1)
        
        overview_layout.addLayout(stats_grid)
        
        # Category breakdown
        cat_group = QGroupBox("Category Distribution")
        cat_layout = QVBoxLayout(cat_group)
        cat_layout.setContentsMargins(8, 16, 8, 8)
        self.cat_tree = QTreeWidget()
        self.cat_tree.setHeaderLabels(["Category", "Count", "With Units", "Effects"])
        self.cat_tree.setAlternatingRowColors(True)
        self.cat_tree.setMinimumHeight(180)
        cat_layout.addWidget(self.cat_tree)
        overview_layout.addWidget(cat_group)
        
        tabs.addTab(overview, "📊 Overview")
        
        # Effects tab
        effects = QWidget()
        effects_layout = QVBoxLayout(effects)
        effects_layout.setContentsMargins(8, 8, 8, 8)
        effects_layout.setSpacing(8)
        
        effects_layout.addWidget(QLabel("Select an effect to find all techs that modify it:"))
        
        self.effect_combo = QComboBox()
        self.effect_combo.addItem("-- Select Effect --", 0)
        for eid, info in sorted(EFFECT_DEFINITIONS.items(), key=lambda x: x[1]['name']):
            self.effect_combo.addItem(f"{info['icon']} {info['name']}", eid)
        effects_layout.addWidget(self.effect_combo)
        
        self.effect_results = QTreeWidget()
        self.effect_results.setHeaderLabels(["Tech", "Value", "Category"])
        self.effect_results.setAlternatingRowColors(True)
        self.effect_results.setMinimumHeight(200)
        self.effect_results.header().setSectionResizeMode(0, QHeaderView.Stretch)
        effects_layout.addWidget(self.effect_results)
        
        self.effect_combo.currentIndexChanged.connect(self._on_effect_selected)
        
        tabs.addTab(effects, "⚡ Effect Finder")
        
        # Validation tab
        validation = QWidget()
        validation_layout = QVBoxLayout(validation)
        validation_layout.setContentsMargins(8, 8, 8, 8)
        validation_layout.setSpacing(8)
        
        validate_btn = QPushButton("🔍 Run Validation")
        validate_btn.clicked.connect(self._run_validation)
        validation_layout.addWidget(validate_btn)
        
        self.validation_results = QTextEdit()
        self.validation_results.setReadOnly(True)
        self.validation_results.setFont(QFont("Consolas", 10))
        self.validation_results.setMinimumHeight(200)
        validation_layout.addWidget(self.validation_results)
        
        tabs.addTab(validation, "✅ Validation")
        
        layout.addWidget(tabs)
    
    def _create_stat_card(self, value: str, label: str) -> QFrame:
        card = QFrame()
        card.setObjectName("card")
        card.setMinimumHeight(70)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(8, 12, 8, 12)
        layout.setSpacing(4)
        
        val = QLabel(value)
        val.setObjectName("statValue")
        val.setAlignment(Qt.AlignCenter)
        
        lbl = QLabel(label)
        lbl.setObjectName("statLabel")
        lbl.setAlignment(Qt.AlignCenter)
        
        layout.addWidget(val)
        layout.addWidget(lbl)
        
        card.value_label = val
        return card
    
    def update_data(self, techs: Dict[int, TechData], units: Dict[int, UnitData]):
        self.techs = techs
        self.units = units
        self._refresh_stats()
    
    def _refresh_stats(self):
        # Basic stats
        self.total_techs.value_label.setText(str(len(self.techs)))
        self.total_units.value_label.setText(str(len(self.units)))
        
        linked = sum(len(t.unlocks_units) for t in self.techs.values())
        self.linked_units.value_label.setText(str(linked))
        
        orphans = find_orphan_techs(self.techs)
        self.orphan_count.value_label.setText(str(len(orphans)))
        if orphans:
            self.orphan_count.value_label.setStyleSheet(f"color: {COLORS['accent_red']}; font-size: 24px; font-weight: bold;")
        else:
            self.orphan_count.value_label.setStyleSheet(f"color: {COLORS['accent_green']}; font-size: 24px; font-weight: bold;")
        
        # Category breakdown
        self.cat_tree.clear()
        cat_stats = defaultdict(lambda: {'count': 0, 'with_units': 0, 'effects': 0})
        
        for tech in self.techs.values():
            cat_stats[tech.category]['count'] += 1
            if tech.unlocks_units:
                cat_stats[tech.category]['with_units'] += 1
            cat_stats[tech.category]['effects'] += len(tech.effects)
        
        for cat_id, stats in sorted(cat_stats.items()):
            cat = CATEGORIES.get(cat_id, {'name': f'Category {cat_id}', 'icon': '?'})
            item = QTreeWidgetItem([
                f"  {cat['icon']} {cat['name']}",
                str(stats['count']),
                str(stats['with_units']),
                str(stats['effects'])
            ])
            self.cat_tree.addTopLevelItem(item)
    
    def _on_effect_selected(self, index):
        eff_id = self.effect_combo.itemData(index)
        self.effect_results.clear()
        
        if not eff_id:
            return
        
        results = find_techs_by_effect(eff_id, self.techs)
        
        for tid, val in results:
            tech = self.techs[tid]
            cat = CATEGORIES.get(tech.category, {'name': '?', 'icon': '?'})
            
            sign = '+' if val >= 0 else ''
            val_str = f"{sign}{val*100:.0f}%" if abs(val) < 10 else f"{sign}{val:.1f}"
            
            item = QTreeWidgetItem([
                f"  {tech.short_title} (ID: {tid})",
                val_str,
                f"{cat['icon']} {cat['name']}"
            ])
            
            color = COLORS['accent_green'] if val >= 0 else COLORS['accent_red']
            item.setForeground(1, QBrush(QColor(color)))
            
            self.effect_results.addTopLevelItem(item)
    
    def _run_validation(self):
        lines = ["=" * 50, "TECH TREE VALIDATION REPORT", "=" * 50, ""]
        
        # Check orphan techs
        orphans = find_orphan_techs(self.techs)
        if orphans:
            lines.append(f"⚠️  BROKEN PREREQUISITE LINKS: {len(orphans)}")
            for tid, missing_id, field in orphans:
                tech = self.techs[tid]
                lines.append(f"   Tech {tid} ({tech.short_title}): {field} references missing tech {missing_id}")
            lines.append("")
        else:
            lines.append("✅ All prerequisite links valid")
            lines.append("")
        
        # Check for cycles (basic)
        lines.append("Checking for circular dependencies...")
        cycles_found = False
        for tid, tech in self.techs.items():
            chain = get_full_prereq_chain(tid, self.techs)
            if tid in chain:
                lines.append(f"⚠️  CYCLE DETECTED: Tech {tid} ({tech.short_title})")
                cycles_found = True
        
        if not cycles_found:
            lines.append("✅ No circular dependencies found")
        lines.append("")
        
        # Unlinked units
        unlinked_units = [u for u in self.units.values() if u.req_tech_id and u.req_tech_id not in self.techs]
        if unlinked_units:
            lines.append(f"⚠️  UNITS WITH MISSING TECH REQUIREMENTS: {len(unlinked_units)}")
            for u in unlinked_units[:10]:
                lines.append(f"   Unit {u.id} ({u.name}): requires missing tech {u.req_tech_id}")
            if len(unlinked_units) > 10:
                lines.append(f"   ... and {len(unlinked_units) - 10} more")
            lines.append("")
        else:
            lines.append("✅ All unit tech requirements valid")
            lines.append("")
        
        # Summary
        lines.append("=" * 50)
        issues = len(orphans) + (1 if cycles_found else 0) + len(unlinked_units)
        if issues == 0:
            lines.append("✅ VALIDATION PASSED - No issues found")
        else:
            lines.append(f"⚠️  VALIDATION COMPLETE - {issues} issue(s) found")
        
        self.validation_results.setText("\n".join(lines))


# =============================================================================
# ADVANCED MODDING TOOLS
# =============================================================================

class PathFinderDialog(QDialog):
    """Find optimal research path to a target tech"""
    
    def __init__(self, techs: Dict[int, TechData], parent=None):
        super().__init__(parent)
        self.techs = techs
        self.setWindowTitle("🎯 Optimal Path Finder")
        self.setMinimumSize(600, 500)
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Target selection
        target_layout = QHBoxLayout()
        target_layout.addWidget(QLabel("Target Tech:"))
        
        self.target_combo = QComboBox()
        self.target_combo.setEditable(True)
        for tid, tech in sorted(self.techs.items(), key=lambda x: x[1].short_title):
            self.target_combo.addItem(f"{tech.short_title} (ID: {tid})", tid)
        target_layout.addWidget(self.target_combo, 1)
        
        layout.addLayout(target_layout)
        
        # Options
        options_layout = QHBoxLayout()
        self.optimize_cost = QRadioButton("Minimize Cost")
        self.optimize_cost.setChecked(True)
        self.optimize_time = QRadioButton("Minimize Time")
        options_layout.addWidget(self.optimize_cost)
        options_layout.addWidget(self.optimize_time)
        options_layout.addStretch()
        layout.addLayout(options_layout)
        
        # Calculate button
        calc_btn = QPushButton("🔍 Calculate Optimal Path")
        calc_btn.setObjectName("primaryButton")
        calc_btn.clicked.connect(self._calculate_path)
        layout.addWidget(calc_btn)
        
        # Results
        self.results_tree = QTreeWidget()
        self.results_tree.setHeaderLabels(["Step", "Tech", "Cost", "Time", "Cumulative"])
        self.results_tree.header().setSectionResizeMode(1, QHeaderView.Stretch)
        layout.addWidget(self.results_tree)
        
        # Summary
        self.summary_label = QLabel("")
        self.summary_label.setStyleSheet(f"color: {COLORS['accent_green']}; font-weight: bold; padding: 10px;")
        layout.addWidget(self.summary_label)
    
    def _calculate_path(self):
        tid = self.target_combo.currentData()
        if not tid or tid not in self.techs:
            return
        
        # Get full prerequisite chain with topological sort
        chain = self._get_ordered_chain(tid)
        
        self.results_tree.clear()
        total_cost = 0
        total_time = 0
        
        for i, tech_id in enumerate(chain, 1):
            tech = self.techs[tech_id]
            total_cost += tech.cost
            total_time += tech.time_to_research
            
            cost_str = f"${tech.cost/1e6:.1f}M"
            cum_str = f"${total_cost/1e6:.1f}M / {total_time}d"
            
            cat = CATEGORIES.get(tech.category, {'icon': '?'})
            item = QTreeWidgetItem([
                str(i),
                f"{cat['icon']} {tech.short_title}",
                cost_str,
                f"{tech.time_to_research}d",
                cum_str
            ])
            
            if tech_id == tid:
                item.setForeground(1, QBrush(QColor(COLORS['accent_green'])))
                item.setForeground(0, QBrush(QColor(COLORS['accent_green'])))
            
            self.results_tree.addTopLevelItem(item)
        
        self.summary_label.setText(
            f"📊 Total: {len(chain)} techs | 💰 ${total_cost/1e9:.2f}B | ⏱️ {total_time} days ({total_time/365:.1f} years)"
        )
    
    def _get_ordered_chain(self, target_id: int) -> List[int]:
        """Get prerequisites in research order (topological sort)"""
        chain = []
        visited = set()
        
        def visit(tid):
            if tid in visited or tid not in self.techs:
                return
            visited.add(tid)
            tech = self.techs[tid]
            if tech.prereq_1: visit(tech.prereq_1)
            if tech.prereq_2: visit(tech.prereq_2)
            chain.append(tid)
        
        visit(target_id)
        return chain


class BalanceAnalyzerDialog(QDialog):
    """Analyze tech tree balance for modders"""
    
    def __init__(self, techs: Dict[int, TechData], parent=None):
        super().__init__(parent)
        self.techs = techs
        self.setWindowTitle("⚖️ Balance Analyzer")
        self.setMinimumSize(800, 600)
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Analysis tabs
        tabs = QTabWidget()
        
        # Cost/Effect ratio analysis
        ratio_tab = QWidget()
        ratio_layout = QVBoxLayout(ratio_tab)
        
        ratio_layout.addWidget(QLabel("Techs with unusual cost-to-effect ratios (potential balance issues):"))
        
        self.ratio_tree = QTreeWidget()
        self.ratio_tree.setHeaderLabels(["Tech", "Cost", "Effects", "Score", "Assessment"])
        self.ratio_tree.header().setSectionResizeMode(0, QHeaderView.Stretch)
        ratio_layout.addWidget(self.ratio_tree)
        
        tabs.addTab(ratio_tab, "💰 Cost Analysis")
        
        # Dead-end techs
        deadend_tab = QWidget()
        deadend_layout = QVBoxLayout(deadend_tab)
        
        deadend_layout.addWidget(QLabel("Techs that lead nowhere (no dependent techs, no unit unlocks):"))
        
        self.deadend_tree = QTreeWidget()
        self.deadend_tree.setHeaderLabels(["Tech", "Category", "Level", "Has Effects"])
        self.deadend_tree.header().setSectionResizeMode(0, QHeaderView.Stretch)
        deadend_layout.addWidget(self.deadend_tree)
        
        tabs.addTab(deadend_tab, "🛑 Dead Ends")
        
        # Bottleneck techs
        bottleneck_tab = QWidget()
        bottleneck_layout = QVBoxLayout(bottleneck_tab)
        
        bottleneck_layout.addWidget(QLabel("Critical techs that many others depend on:"))
        
        self.bottleneck_tree = QTreeWidget()
        self.bottleneck_tree.setHeaderLabels(["Tech", "Dependents", "Total Chain", "Category"])
        self.bottleneck_tree.header().setSectionResizeMode(0, QHeaderView.Stretch)
        bottleneck_layout.addWidget(self.bottleneck_tree)
        
        tabs.addTab(bottleneck_tab, "🔗 Bottlenecks")
        
        # Unit value analysis
        unit_tab = QWidget()
        unit_layout = QVBoxLayout(unit_tab)
        
        unit_layout.addWidget(QLabel("Tech cost vs units unlocked (value assessment):"))
        
        self.unit_tree = QTreeWidget()
        self.unit_tree.setHeaderLabels(["Tech", "Tech Cost", "Units", "Avg Unit Cost", "Value Score"])
        self.unit_tree.header().setSectionResizeMode(0, QHeaderView.Stretch)
        unit_layout.addWidget(self.unit_tree)
        
        tabs.addTab(unit_tab, "🔧 Unit Value")
        
        layout.addWidget(tabs)
        
        # Analyze button
        analyze_btn = QPushButton("🔍 Run Full Analysis")
        analyze_btn.setObjectName("primaryButton")
        analyze_btn.clicked.connect(self._run_analysis)
        layout.addWidget(analyze_btn)
        
        # Auto-run
        QTimer.singleShot(100, self._run_analysis)
    
    def _run_analysis(self):
        self._analyze_cost_ratio()
        self._find_dead_ends()
        self._find_bottlenecks()
        self._analyze_unit_value()
    
    def _analyze_cost_ratio(self):
        self.ratio_tree.clear()
        
        # Calculate effect scores
        scores = []
        for tid, tech in self.techs.items():
            effect_score = sum(abs(val) for _, val in tech.effects)
            if tech.cost > 0:
                ratio = effect_score / (tech.cost / 1e9) if tech.cost > 0 else 0
                scores.append((tid, tech, effect_score, ratio))
        
        # Sort by ratio (high = cheap for effects, low = expensive)
        scores.sort(key=lambda x: x[3], reverse=True)
        
        # Show extremes
        for tid, tech, effect_score, ratio in scores[:15]:  # Best value
            cat = CATEGORIES.get(tech.category, {'icon': '?'})
            item = QTreeWidgetItem([
                f"{cat['icon']} {tech.short_title} (ID: {tid})",
                f"${tech.cost/1e6:.0f}M",
                f"{len(tech.effects)} ({effect_score:.2f})",
                f"{ratio:.4f}",
                "🟢 Great Value"
            ])
            item.setForeground(4, QBrush(QColor(COLORS['accent_green'])))
            self.ratio_tree.addTopLevelItem(item)
        
        # Separator
        sep = QTreeWidgetItem(["─" * 20, "─" * 10, "─" * 10, "─" * 10, "─" * 15])
        self.ratio_tree.addTopLevelItem(sep)
        
        for tid, tech, effect_score, ratio in scores[-15:]:  # Worst value
            if effect_score == 0:
                continue
            cat = CATEGORIES.get(tech.category, {'icon': '?'})
            item = QTreeWidgetItem([
                f"{cat['icon']} {tech.short_title} (ID: {tid})",
                f"${tech.cost/1e6:.0f}M",
                f"{len(tech.effects)} ({effect_score:.2f})",
                f"{ratio:.4f}",
                "🔴 Expensive"
            ])
            item.setForeground(4, QBrush(QColor(COLORS['accent_red'])))
            self.ratio_tree.addTopLevelItem(item)
    
    def _find_dead_ends(self):
        self.deadend_tree.clear()
        
        for tid, tech in self.techs.items():
            # Check if it leads nowhere
            if not tech.prerequisite_of and not tech.unlocks_units:
                cat = CATEGORIES.get(tech.category, {'name': '?', 'icon': '?'})
                item = QTreeWidgetItem([
                    f"{cat['icon']} {tech.short_title} (ID: {tid})",
                    cat['name'],
                    str(tech.tech_level),
                    "Yes" if tech.effects else "No"
                ])
                if not tech.effects:
                    item.setForeground(3, QBrush(QColor(COLORS['accent_red'])))
                self.deadend_tree.addTopLevelItem(item)
    
    def _find_bottlenecks(self):
        self.bottleneck_tree.clear()
        
        # Count total descendants for each tech
        bottlenecks = []
        for tid, tech in self.techs.items():
            descendants = get_all_descendants(tid, self.techs)
            if len(descendants) > 5:  # Significant bottleneck
                bottlenecks.append((tid, tech, len(tech.prerequisite_of), len(descendants)))
        
        # Sort by total chain size
        bottlenecks.sort(key=lambda x: x[3], reverse=True)
        
        for tid, tech, direct, total in bottlenecks[:30]:
            cat = CATEGORIES.get(tech.category, {'name': '?', 'icon': '?'})
            item = QTreeWidgetItem([
                f"{cat['icon']} {tech.short_title} (ID: {tid})",
                str(direct),
                str(total),
                cat['name']
            ])
            # Color by importance
            if total > 50:
                item.setForeground(2, QBrush(QColor(COLORS['accent_red'])))
            elif total > 20:
                item.setForeground(2, QBrush(QColor(COLORS['accent_orange'])))
            else:
                item.setForeground(2, QBrush(QColor(COLORS['accent_green'])))
            
            self.bottleneck_tree.addTopLevelItem(item)
    
    def _analyze_unit_value(self):
        self.unit_tree.clear()
        
        # Calculate value for techs that unlock units
        values = []
        for tid, tech in self.techs.items():
            if tech.unlocks_units:
                total_unit_cost = sum(u.cost for u in tech.unlocks_units)
                avg_unit_cost = total_unit_cost / len(tech.unlocks_units) if tech.unlocks_units else 0
                # Value = units unlocked * avg unit cost / tech cost
                if tech.cost > 0:
                    value = (len(tech.unlocks_units) * avg_unit_cost) / tech.cost
                else:
                    value = float('inf')
                values.append((tid, tech, avg_unit_cost, value))
        
        values.sort(key=lambda x: x[3], reverse=True)
        
        for tid, tech, avg_cost, value in values[:40]:
            cat = CATEGORIES.get(tech.category, {'icon': '?'})
            item = QTreeWidgetItem([
                f"{cat['icon']} {tech.short_title}",
                f"${tech.cost/1e6:.0f}M",
                str(len(tech.unlocks_units)),
                f"${avg_cost/1e6:.1f}M" if avg_cost else "-",
                f"{value:.2f}"
            ])
            self.unit_tree.addTopLevelItem(item)


class TechDiffDialog(QDialog):
    """Compare two tech tree files"""
    
    def __init__(self, base_techs: Dict[int, TechData], parent=None):
        super().__init__(parent)
        self.base_techs = base_techs
        self.mod_techs: Dict[int, TechData] = {}
        self.setWindowTitle("📊 Tech Tree Diff Tool")
        self.setMinimumSize(900, 700)
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        # File selection
        file_layout = QHBoxLayout()
        file_layout.addWidget(QLabel("Compare with MOD file:"))
        
        self.mod_path_edit = QLineEdit()
        self.mod_path_edit.setPlaceholderText("Select modded TTRX file...")
        file_layout.addWidget(self.mod_path_edit, 1)
        
        browse_btn = QPushButton("...")
        browse_btn.setMaximumWidth(40)
        browse_btn.clicked.connect(self._browse_mod)
        file_layout.addWidget(browse_btn)
        
        compare_btn = QPushButton("🔍 Compare")
        compare_btn.setObjectName("primaryButton")
        compare_btn.clicked.connect(self._run_diff)
        file_layout.addWidget(compare_btn)
        
        layout.addLayout(file_layout)
        
        # Results tabs
        self.tabs = QTabWidget()
        
        # Added techs
        self.added_tree = QTreeWidget()
        self.added_tree.setHeaderLabels(["ID", "Name", "Category", "Level", "Cost"])
        self.tabs.addTab(self.added_tree, "➕ Added")
        
        # Removed techs
        self.removed_tree = QTreeWidget()
        self.removed_tree.setHeaderLabels(["ID", "Name", "Category", "Level", "Cost"])
        self.tabs.addTab(self.removed_tree, "➖ Removed")
        
        # Modified techs
        self.modified_tree = QTreeWidget()
        self.modified_tree.setHeaderLabels(["ID", "Name", "Field", "Old Value", "New Value"])
        self.modified_tree.header().setSectionResizeMode(1, QHeaderView.Stretch)
        self.tabs.addTab(self.modified_tree, "📝 Modified")
        
        layout.addWidget(self.tabs)
        
        # Summary
        self.summary_label = QLabel("Load a mod file to compare")
        self.summary_label.setStyleSheet(f"padding: 10px; background: {COLORS['bg_medium']}; border-radius: 8px;")
        layout.addWidget(self.summary_label)
    
    def _browse_mod(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Mod TTRX File", "",
            "TTRX Files (*.ttrx *.csv);;All Files (*)"
        )
        if path:
            self.mod_path_edit.setText(path)
    
    def _run_diff(self):
        mod_path = self.mod_path_edit.text().strip()
        if not mod_path:
            return
        
        self.mod_techs = load_tech_tree(mod_path)
        if not self.mod_techs:
            QMessageBox.warning(self, "Error", "Failed to load mod file")
            return
        
        self._compare()
    
    def _compare(self):
        self.added_tree.clear()
        self.removed_tree.clear()
        self.modified_tree.clear()
        
        base_ids = set(self.base_techs.keys())
        mod_ids = set(self.mod_techs.keys())
        
        added = mod_ids - base_ids
        removed = base_ids - mod_ids
        common = base_ids & mod_ids
        
        # Added techs
        for tid in sorted(added):
            tech = self.mod_techs[tid]
            cat = CATEGORIES.get(tech.category, {'name': '?', 'icon': '?'})
            item = QTreeWidgetItem([
                str(tid),
                f"{cat['icon']} {tech.short_title}",
                cat['name'],
                str(tech.tech_level),
                f"${tech.cost/1e6:.0f}M"
            ])
            item.setForeground(0, QBrush(QColor(COLORS['accent_green'])))
            self.added_tree.addTopLevelItem(item)
        
        # Removed techs
        for tid in sorted(removed):
            tech = self.base_techs[tid]
            cat = CATEGORIES.get(tech.category, {'name': '?', 'icon': '?'})
            item = QTreeWidgetItem([
                str(tid),
                f"{cat['icon']} {tech.short_title}",
                cat['name'],
                str(tech.tech_level),
                f"${tech.cost/1e6:.0f}M"
            ])
            item.setForeground(0, QBrush(QColor(COLORS['accent_red'])))
            self.removed_tree.addTopLevelItem(item)
        
        # Modified techs
        modified_count = 0
        for tid in sorted(common):
            base = self.base_techs[tid]
            mod = self.mod_techs[tid]
            
            changes = []
            if base.cost != mod.cost:
                changes.append(("Cost", f"${base.cost/1e6:.0f}M", f"${mod.cost/1e6:.0f}M"))
            if base.time_to_research != mod.time_to_research:
                changes.append(("Time", f"{base.time_to_research}d", f"{mod.time_to_research}d"))
            if base.prereq_1 != mod.prereq_1:
                changes.append(("Prereq 1", str(base.prereq_1), str(mod.prereq_1)))
            if base.prereq_2 != mod.prereq_2:
                changes.append(("Prereq 2", str(base.prereq_2), str(mod.prereq_2)))
            if base.tech_level != mod.tech_level:
                changes.append(("Level", str(base.tech_level), str(mod.tech_level)))
            if base.effects != mod.effects:
                changes.append(("Effects", str(len(base.effects)), str(len(mod.effects))))
            
            if changes:
                modified_count += 1
                cat = CATEGORIES.get(base.category, {'icon': '?'})
                
                for i, (field, old, new) in enumerate(changes):
                    item = QTreeWidgetItem([
                        str(tid) if i == 0 else "",
                        f"{cat['icon']} {base.short_title}" if i == 0 else "",
                        field,
                        old,
                        new
                    ])
                    item.setForeground(3, QBrush(QColor(COLORS['accent_red'])))
                    item.setForeground(4, QBrush(QColor(COLORS['accent_green'])))
                    self.modified_tree.addTopLevelItem(item)
        
        # Update tabs with counts
        self.tabs.setTabText(0, f"➕ Added ({len(added)})")
        self.tabs.setTabText(1, f"➖ Removed ({len(removed)})")
        self.tabs.setTabText(2, f"📝 Modified ({modified_count})")
        
        self.summary_label.setText(
            f"📊 Comparison: {len(self.base_techs)} base techs vs {len(self.mod_techs)} mod techs | "
            f"➕ {len(added)} added | ➖ {len(removed)} removed | 📝 {modified_count} modified"
        )


class TechGeneratorDialog(QDialog):
    """Generate new tech entries for modding"""
    
    def __init__(self, techs: Dict[int, TechData], parent=None):
        super().__init__(parent)
        self.techs = techs
        self.setWindowTitle("🔧 Tech Generator")
        self.setMinimumSize(700, 600)
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        form_layout = QGridLayout()
        row = 0
        
        # Tech ID
        form_layout.addWidget(QLabel("Tech ID:"), row, 0)
        self.id_spin = QSpinBox()
        self.id_spin.setRange(1, 99999)
        self.id_spin.setValue(max(self.techs.keys()) + 1 if self.techs else 1)
        form_layout.addWidget(self.id_spin, row, 1)
        row += 1
        
        # Name
        form_layout.addWidget(QLabel("Name:"), row, 0)
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Advanced Tank Armor")
        form_layout.addWidget(self.name_edit, row, 1)
        row += 1
        
        # Category
        form_layout.addWidget(QLabel("Category:"), row, 0)
        self.cat_combo = QComboBox()
        for cid, info in CATEGORIES.items():
            self.cat_combo.addItem(f"{info['icon']} {info['name']}", cid)
        form_layout.addWidget(self.cat_combo, row, 1)
        row += 1
        
        # Level
        form_layout.addWidget(QLabel("Tech Level:"), row, 0)
        self.level_spin = QSpinBox()
        self.level_spin.setRange(1, 20)
        self.level_spin.setValue(5)
        form_layout.addWidget(self.level_spin, row, 1)
        row += 1
        
        # Cost
        form_layout.addWidget(QLabel("Cost (millions):"), row, 0)
        self.cost_spin = QDoubleSpinBox()
        self.cost_spin.setRange(0, 999999)
        self.cost_spin.setValue(1000)
        self.cost_spin.setSuffix(" M")
        form_layout.addWidget(self.cost_spin, row, 1)
        row += 1
        
        # Time
        form_layout.addWidget(QLabel("Research Time (days):"), row, 0)
        self.time_spin = QSpinBox()
        self.time_spin.setRange(1, 9999)
        self.time_spin.setValue(365)
        form_layout.addWidget(self.time_spin, row, 1)
        row += 1
        
        # Prerequisites
        form_layout.addWidget(QLabel("Prerequisite 1:"), row, 0)
        self.prereq1_combo = QComboBox()
        self.prereq1_combo.addItem("None", 0)
        for tid, tech in sorted(self.techs.items(), key=lambda x: x[1].short_title):
            self.prereq1_combo.addItem(f"{tech.short_title} ({tid})", tid)
        form_layout.addWidget(self.prereq1_combo, row, 1)
        row += 1
        
        form_layout.addWidget(QLabel("Prerequisite 2:"), row, 0)
        self.prereq2_combo = QComboBox()
        self.prereq2_combo.addItem("None", 0)
        for tid, tech in sorted(self.techs.items(), key=lambda x: x[1].short_title):
            self.prereq2_combo.addItem(f"{tech.short_title} ({tid})", tid)
        form_layout.addWidget(self.prereq2_combo, row, 1)
        row += 1
        
        layout.addLayout(form_layout)
        
        # Effects
        effects_group = QGroupBox("Effects (up to 4)")
        effects_layout = QGridLayout(effects_group)
        
        self.effect_combos = []
        self.effect_values = []
        
        for i in range(4):
            combo = QComboBox()
            combo.addItem("None", 0)
            for eid, info in sorted(EFFECT_DEFINITIONS.items(), key=lambda x: x[1]['name']):
                combo.addItem(f"{info['icon']} {info['name']}", eid)
            
            value = QDoubleSpinBox()
            value.setRange(-10, 10)
            value.setSingleStep(0.01)
            value.setValue(0)
            
            effects_layout.addWidget(QLabel(f"Effect {i+1}:"), i, 0)
            effects_layout.addWidget(combo, i, 1)
            effects_layout.addWidget(value, i, 2)
            
            self.effect_combos.append(combo)
            self.effect_values.append(value)
        
        layout.addWidget(effects_group)
        
        # Generate button
        gen_btn = QPushButton("📋 Generate TTRX Entry")
        gen_btn.setObjectName("primaryButton")
        gen_btn.clicked.connect(self._generate)
        layout.addWidget(gen_btn)
        
        # Output
        self.output_text = QTextEdit()
        self.output_text.setFont(QFont("Consolas", 10))
        self.output_text.setPlaceholderText("Generated TTRX entry will appear here...")
        layout.addWidget(self.output_text)
        
        # Copy button
        copy_btn = QPushButton("📋 Copy to Clipboard")
        copy_btn.clicked.connect(self._copy)
        layout.addWidget(copy_btn)
    
    def _generate(self):
        # Build TTRX row
        fields = [""] * 30
        
        fields[0] = str(self.id_spin.value())
        fields[1] = str(self.cat_combo.currentData())
        fields[2] = str(self.level_spin.value())
        fields[3] = "0"  # branch
        fields[4] = str(self.prereq1_combo.currentData() or 0)
        fields[5] = str(self.prereq2_combo.currentData() or 0)
        
        # Effects
        effect_idx = 0
        for combo, value in zip(self.effect_combos, self.effect_values):
            eid = combo.currentData()
            val = value.value()
            if eid and val != 0:
                fields[6 + effect_idx] = str(eid)
                fields[10 + effect_idx] = str(val)
                effect_idx += 1
        
        fields[14] = str(self.time_spin.value())
        fields[15] = str(int(self.cost_spin.value() * 1e6))
        fields[16] = "0.5"  # pop support
        fields[17] = "0"  # military
        fields[18] = "0"  # world market
        fields[19] = "100"  # world market threshold
        fields[20] = "0"  # set by default
        
        # Name in comment
        name = self.name_edit.text() or "New Technology"
        
        line = ",".join(fields) + f"// {name}"
        
        self.output_text.setText(line)
    
    def _copy(self):
        QApplication.clipboard().setText(self.output_text.toPlainText())
        QMessageBox.information(self, "Copied", "Entry copied to clipboard!")


# =============================================================================
# MAIN WINDOW
# =============================================================================

class MainWindow(QMainWindow):
    """Main application window"""
    
    def __init__(self):
        super().__init__()
        
        self.techs: Dict[int, TechData] = {}
        self.units: Dict[int, UnitData] = {}
        
        # IPC Server for receiving commands from overlay
        self.ipc_server = None
        self.ipc_timer = None
        self._setup_ipc_server()
        
        self.setWindowTitle(f"{APP_NAME} v{VERSION}")
        self.setMinimumSize(1400, 900)
        self.setStyleSheet(STYLESHEET)
        
        self._setup_menu()
        self._setup_toolbar()
        self._setup_ui()
        self._setup_shortcuts()
        
        self.statusBar().showMessage("Ready - Load TTRX and UNIT files to begin")
    
    def _setup_ipc_server(self):
        """Initialize file-based IPC server for overlay communication."""
        if not IPC_AVAILABLE or IPCServer is None:
            print("[IPC] Server not available (ipc_bridge.py missing)")
            return
        
        self.ipc_server = IPCServer(
            on_navigate=self._ipc_navigate_to_tech,
            on_focus=self._bring_window_to_front
        )
        
        if self.ipc_server.start():
            # Start polling timer for command file
            self.ipc_timer = QTimer(self)
            self.ipc_timer.timeout.connect(self.ipc_server.check_commands)
            self.ipc_timer.start(300)  # Check every 300ms
            print("[IPC] Tech Analyzer server started (polling active)")
        else:
            print("[IPC] Could not start server (another instance running?)")
            self.ipc_server = None
    
    def _ipc_navigate_to_tech(self, tech_id: int):
        """Handle navigate command from overlay - brings window to front first."""
        print(f"[IPC] Processing navigate to tech {tech_id}")
        self._bring_window_to_front()
        # Small delay to ensure window is visible before navigating
        QTimer.singleShot(150, lambda: self._navigate_to_tech(tech_id))
    
    def _bring_window_to_front(self):
        """
        Bring this window to the foreground using aggressive Windows methods.
        Games often have exclusive focus, so we need multiple techniques.
        """
        try:
            import ctypes
            
            user32 = ctypes.windll.user32
            kernel32 = ctypes.windll.kernel32  # GetCurrentThreadId is in kernel32!
            hwnd = int(self.winId())
            
            # Constants
            SW_RESTORE = 9
            SW_SHOW = 5
            HWND_TOPMOST = -1
            HWND_NOTOPMOST = -2
            SWP_NOMOVE = 0x0002
            SWP_NOSIZE = 0x0001
            SWP_SHOWWINDOW = 0x0040
            
            # 1. First restore if minimized (Qt side)
            if self.isMinimized():
                self.showNormal()
            
            # 2. Show and restore via Windows API
            user32.ShowWindow(hwnd, SW_RESTORE)
            user32.ShowWindow(hwnd, SW_SHOW)
            
            # 3. Simulate ALT key press to unlock foreground lock
            user32.keybd_event(0x12, 0, 0, 0)  # ALT down
            user32.keybd_event(0x12, 0, 2, 0)  # ALT up
            
            # 4. Get foreground thread and attach
            foreground_hwnd = user32.GetForegroundWindow()
            foreground_thread = user32.GetWindowThreadProcessId(foreground_hwnd, None)
            current_thread = kernel32.GetCurrentThreadId()  # Fixed: use kernel32
            
            attached = False
            if foreground_thread != current_thread:
                attached = user32.AttachThreadInput(foreground_thread, current_thread, True)
            
            # 5. Set as TOPMOST (will stay on top)
            user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, 
                               SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW)
            
            # 6. Multiple focus attempts
            user32.SetForegroundWindow(hwnd)
            user32.BringWindowToTop(hwnd)
            user32.SetActiveWindow(hwnd)
            
            # 7. Use SwitchToThisWindow (more aggressive)
            try:
                user32.SwitchToThisWindow(hwnd, True)
            except:
                pass
            
            # 8. Detach thread
            if attached:
                user32.AttachThreadInput(foreground_thread, current_thread, False)
            
            # 9. Remove TOPMOST after a delay (so it doesn't block game permanently)
            def remove_topmost():
                try:
                    user32.SetWindowPos(hwnd, HWND_NOTOPMOST, 0, 0, 0, 0, 
                                       SWP_NOMOVE | SWP_NOSIZE)
                except:
                    pass
            
            QTimer.singleShot(500, remove_topmost)
            
            print("[IPC] Window brought to front via Windows API")
            
        except Exception as e:
            print(f"[IPC] Windows API bring to front failed: {e}")
        
        # Qt methods as fallback/reinforcement
        self.setWindowState(self.windowState() & ~Qt.WindowMinimized)
        self.show()
        self.raise_()
        self.activateWindow()
    
    def closeEvent(self, event):
        """Clean up IPC server on close."""
        if self.ipc_timer:
            self.ipc_timer.stop()
        if self.ipc_server:
            print("[IPC] Stopping server...")
            self.ipc_server.stop()
        super().closeEvent(event)
    
    def _setup_menu(self):
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("&File")
        
        open_action = QAction("📂 &Open Files...", self)
        open_action.setShortcut(QKeySequence.Open)
        open_action.triggered.connect(self._open_files)
        file_menu.addAction(open_action)
        
        file_menu.addSeparator()
        
        export_menu = file_menu.addMenu("📤 Export")
        export_menu.addAction("Export Tech List (CSV)").triggered.connect(self._export_csv)
        export_menu.addAction("Export Full Report (JSON)").triggered.connect(self._export_json)
        export_menu.addAction("Export Balance Report (HTML)").triggered.connect(self._export_html_report)
        
        file_menu.addSeparator()
        file_menu.addAction("🗑️ Clear Cache").triggered.connect(self._clear_cache)
        
        file_menu.addSeparator()
        file_menu.addAction("❌ Exit").triggered.connect(self.close)
        
        # View menu
        view_menu = menubar.addMenu("&View")
        view_menu.addAction("🔍 Zoom In").triggered.connect(lambda: self.tree_view.scale(1.2, 1.2))
        view_menu.addAction("🔍 Zoom Out").triggered.connect(lambda: self.tree_view.scale(0.8, 0.8))
        view_menu.addAction("🔍 Reset Zoom (1:1)").triggered.connect(self._reset_zoom)
        view_menu.addAction("📐 Fit to View").triggered.connect(self._fit_view)
        view_menu.addSeparator()
        view_menu.addAction("🔄 Refresh").triggered.connect(self._refresh)

        # Tools menu (NEW!)
        tools_menu = menubar.addMenu("&Tools")
        tools_menu.addAction("🎯 Optimal Path Finder...").triggered.connect(self._show_path_finder)
        tools_menu.addAction("⚖️ Balance Analyzer...").triggered.connect(self._show_balance_analyzer)
        tools_menu.addAction("📊 Diff Tool (Compare Mods)...").triggered.connect(self._show_diff_tool)
        tools_menu.addSeparator()
        tools_menu.addAction("🔧 Tech Generator...").triggered.connect(self._show_tech_generator)
        
        # Help menu
        help_menu = menubar.addMenu("&Help")
        help_menu.addAction("📖 Keyboard Shortcuts").triggered.connect(self._show_shortcuts)
        help_menu.addAction("ℹ️ About").triggered.connect(self._show_about)
    
    def _setup_toolbar(self):
        toolbar = QToolBar()
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        
        # File path inputs
        toolbar.addWidget(QLabel("  TTRX: "))
        self.ttrx_edit = QLineEdit()
        self.ttrx_edit.setPlaceholderText("Path to DEFAULT.TTRX...")
        self.ttrx_edit.setMinimumWidth(200)
        toolbar.addWidget(self.ttrx_edit)
        
        browse_ttrx = QPushButton("...")
        browse_ttrx.setMaximumWidth(40)
        browse_ttrx.clicked.connect(lambda: self._browse_file(self.ttrx_edit, "TTRX"))
        toolbar.addWidget(browse_ttrx)
        
        toolbar.addWidget(QLabel("  UNIT: "))
        self.unit_edit = QLineEdit()
        self.unit_edit.setPlaceholderText("Path to DEFAULT.UNIT...")
        self.unit_edit.setMinimumWidth(200)
        toolbar.addWidget(self.unit_edit)
        
        browse_unit = QPushButton("...")
        browse_unit.setMaximumWidth(40)
        browse_unit.clicked.connect(lambda: self._browse_file(self.unit_edit, "UNIT"))
        toolbar.addWidget(browse_unit)
        
        load_btn = QPushButton("  Load  ")
        load_btn.setObjectName("primaryButton")
        load_btn.clicked.connect(self._load_files)
        toolbar.addWidget(load_btn)
        
        toolbar.addSeparator()
        
        # Category filter
        toolbar.addWidget(QLabel("  Category: "))
        self.cat_combo = QComboBox()
        self.cat_combo.setMinimumWidth(150)
        self.cat_combo.addItem("🌐  All Categories", 0)
        for cid, info in CATEGORIES.items():
            self.cat_combo.addItem(f"{info['icon']}  {info['name']}", cid)
        self.cat_combo.currentIndexChanged.connect(self._on_category_changed)
        toolbar.addWidget(self.cat_combo)
        
        toolbar.addSeparator()
        
        # Layout selector
        self.layout_selector = LayoutSelector()
        toolbar.addWidget(self.layout_selector)
        
        # Search
        toolbar.addWidget(QLabel("  Search: "))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Name or ID...")
        self.search_edit.setMinimumWidth(150)
        self.search_edit.textChanged.connect(self._on_search_changed)
        toolbar.addWidget(self.search_edit)
        
        #  1:1
        reset_btn = QPushButton("  1:1  ")
        reset_btn.setToolTip("Reset Zoom to 100%")
        reset_btn.clicked.connect(self._reset_zoom)
        toolbar.addWidget(reset_btn)

        #  Fit
        fit_btn = QPushButton("  Fit  ")
        fit_btn.setToolTip("Fit All to View")
        fit_btn.clicked.connect(self._fit_view)
        toolbar.addWidget(fit_btn)
        
        toolbar.addSeparator()
        
        # Clear highlights button
        clear_btn = QPushButton("  Clear Highlight  ")
        clear_btn.clicked.connect(self._clear_highlight)
        toolbar.addWidget(clear_btn)
    
    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Main splitter
        splitter = QSplitter(Qt.Horizontal)
        
        # Left: Tree view
        self.tree_view = TechTreeView()
        self.tree_view.tech_selected.connect(self._on_tech_selected)
        self.tree_view.tech_double_clicked.connect(self._on_tech_double_clicked)
        splitter.addWidget(self.tree_view)
        
        self.layout_selector.layout_changed.connect(self.tree_view.set_layout_engine)
      
        
                # Minimap (overlay)
        #self.minimap = MiniMapWidget()
        #self.minimap.setParent(self.tree_view)
        #self.minimap.viewport_changed.connect(self._on_minimap_click)
        #self.tree_view.viewport_changed.connect(self._update_minimap_viewport)
        
        #QTimer.singleShot(100, self._position_minimap)
        
        # Right: Tabs for detail and analysis
        right_tabs = QTabWidget()
        
        self.detail_panel = TechDetailPanel()
        self.detail_panel.navigate_to_tech.connect(self._navigate_to_tech)
        right_tabs.addTab(self.detail_panel, "📋 Details")
        
        self.analysis_panel = AnalysisPanel()
        right_tabs.addTab(self.analysis_panel, "📊 Analysis")
        
        right_tabs.setMinimumWidth(400)
        #right_tabs.setMaximumWidth(520)
        splitter.addWidget(right_tabs)
        
        splitter.setSizes([1000, 400])
        layout.addWidget(splitter)
           
    def resizeEvent(self, event):
        super().resizeEvent(event)

    def _setup_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+F"), self, self.search_edit.setFocus)
        QShortcut(QKeySequence("Escape"), self, self._clear_highlight)
    
    def _browse_file(self, edit: QLineEdit, file_type: str):
        path, _ = QFileDialog.getOpenFileName(
            self, f"Select {file_type} File", "",
            f"{file_type} Files (*.{file_type.lower()} *.csv);;All Files (*)"
        )
        if path:
            edit.setText(path)
    
    def _open_files(self):
        self._browse_file(self.ttrx_edit, "TTRX")
        if self.ttrx_edit.text():
            self._browse_file(self.unit_edit, "UNIT")
            if self.unit_edit.text():
                self._load_files()
    
    def _load_files(self):
        ttrx = self.ttrx_edit.text().strip()
        unit = self.unit_edit.text().strip()
        
        if not ttrx or not unit:
            QMessageBox.warning(self, "Missing Files", "Please select both TTRX and UNIT files.")
            return
        
        # Try cache first
        self.statusBar().showMessage("Checking cache...")
        QApplication.processEvents()
        
        cached = load_from_cache(ttrx, unit)
        
        if cached:
            self.techs, self.units = cached
            self.statusBar().showMessage(f"⚡ Loaded from cache ({len(self.techs)} techs)")
            QApplication.processEvents()
        else:
            # Parse files
            self.statusBar().showMessage("Parsing tech tree...")
            QApplication.processEvents()
            
            self.techs = load_tech_tree(ttrx)
            if not self.techs:
                QMessageBox.critical(self, "Error", f"Failed to load tech file:\n{ttrx}")
                return
            
            self.statusBar().showMessage(f"Loaded {len(self.techs)} techs. Parsing units...")
            QApplication.processEvents()
            
            self.units = load_units(unit)
            link_units_to_techs(self.techs, self.units)
            
            # Save to cache for next time
            self.statusBar().showMessage("Saving to cache...")
            QApplication.processEvents()
            save_to_cache(ttrx, unit, self.techs, self.units)
        
        self.statusBar().showMessage(f"Building visualization ({len(self.techs)} nodes)...")
        QApplication.processEvents()
        
        self.tree_view.load_data(self.techs)
        self.detail_panel.set_techs(self.techs)
        self.analysis_panel.update_data(self.techs, self.units)
        
        linked = sum(len(t.unlocks_units) for t in self.techs.values())
        cache_status = "⚡ cached" if cached else "💾 cached"
        self.statusBar().showMessage(
            f"✅ {len(self.techs)} techs, {len(self.units)} units ({linked} linked) [{cache_status}]"
        )

    def _on_category_changed(self, index):
        cat = self.cat_combo.itemData(index)
        self.tree_view.set_category(cat)
    
    def _on_search_changed(self, text):
        self.tree_view.set_search(text)
    
    def _on_tech_selected(self, tech: TechData):
        self.detail_panel.show_tech(tech)
    
    def _on_tech_double_clicked(self, tech: TechData):
        """Double-click to highlight full prerequisite chain"""
        self.tree_view.highlight_chain(tech.id, include_descendants=True)
        self.statusBar().showMessage(
            f"Highlighting chain for: {tech.short_title} ({len(self.tree_view.highlighted_chain)} techs)"
        )
    
    def _navigate_to_tech(self, tech_id: int):
        if tech_id in self.techs:
            self.tree_view.center_on_tech(tech_id)
            self.detail_panel.show_tech(self.techs[tech_id])
    
    def _clear_highlight(self):
        self.tree_view.clear_highlight()
        self.statusBar().showMessage("Highlight cleared")
    
    def _fit_view(self):
        if not self.tree_view.scene.items():
            return
            
        self.tree_view.fitInView(self.tree_view.scene.sceneRect(), Qt.KeepAspectRatio)
        current_scale = self.tree_view.transform().m11()
        self.tree_view._zoom = current_scale
        
    def _reset_zoom(self):
        """Resets the view scale to 100% (1.0)"""
        self.tree_view.resetTransform() # Resetta scala e rotazione
        self.tree_view._zoom = 1.0      # Resetta la variabile interna dello zoom
        
        # Opzionale: Centra la vista sul centro della scena o sul nodo selezionato
        if self.tree_view.scene.items():
            # Se c'è un nodo selezionato, centra su quello, altrimenti al centro del grafico
            items = self.tree_view.scene.selectedItems()
            if items:
                self.tree_view.centerOn(items[0])
            else:
                self.tree_view.centerOn(self.tree_view.scene.sceneRect().center())
    
    def _refresh(self):
        self.tree_view.rebuild()
    
    def _export_csv(self):
        if not self.techs:
            QMessageBox.warning(self, "No Data", "Load files first.")
            return
        
        path, _ = QFileDialog.getSaveFileName(self, "Export CSV", "tech_list.csv", "CSV Files (*.csv)")
        if not path:
            return
        
        with open(path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['ID', 'Name', 'Category', 'Level', 'Cost', 'Time', 'Prereq1', 'Prereq2', 'Effects', 'Units'])
            
            for tech in sorted(self.techs.values(), key=lambda t: t.id):
                cat = CATEGORIES.get(tech.category, {'name': '?'})
                effects_str = "; ".join(f"{eid}:{val}" for eid, val in tech.effects)
                units_str = "; ".join(u.name for u in tech.unlocks_units)
                
                writer.writerow([
                    tech.id, tech.short_title, cat['name'], tech.tech_level,
                    tech.cost, tech.time_to_research, tech.prereq_1, tech.prereq_2,
                    effects_str, units_str
                ])
        
        QMessageBox.information(self, "Export Complete", f"Exported to:\n{path}")
    
    def _export_json(self):
        if not self.techs:
            QMessageBox.warning(self, "No Data", "Load files first.")
            return
        
        path, _ = QFileDialog.getSaveFileName(self, "Export JSON", "tech_report.json", "JSON Files (*.json)")
        if not path:
            return
        
        report = {
            'generated': datetime.now().isoformat(),
            'stats': {
                'total_techs': len(self.techs),
                'total_units': len(self.units),
                'linked_units': sum(len(t.unlocks_units) for t in self.techs.values()),
            },
            'techs': {}
        }
        
        for tid, tech in self.techs.items():
            report['techs'][tid] = {
                'name': tech.short_title,
                'category': CATEGORIES.get(tech.category, {'name': '?'})['name'],
                'level': tech.tech_level,
                'cost': tech.cost,
                'time': tech.time_to_research,
                'prereqs': [p for p in [tech.prereq_1, tech.prereq_2] if p],
                'effects': [{'id': eid, 'value': val} for eid, val in tech.effects],
                'units': [{'id': u.id, 'name': u.name} for u in tech.unlocks_units],
            }
        
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2)
        
        QMessageBox.information(self, "Export Complete", f"Exported to:\n{path}")
    
    def _show_about(self):
        QMessageBox.about(self, "About", f"""
<h2>{APP_NAME}</h2>
<p>Version {VERSION}</p>
<p>Professional tech tree analysis tool for Supreme Ruler modders.</p>
<hr>
<p><b>Features:</b></p>
<ul>
<li>Interactive tech tree visualization</li>
<li>Full prerequisite chain analysis</li>
<li>Effect impact finder</li>
<li>Unit unlock browser</li>
<li>Validation & export tools</li>
<li>Optimal path calculator</li>
<li>Balance analyzer</li>
<li>Mod diff tool</li>
<li>Tech generator</li>
</ul>
<hr>
<p>Made by Mooning for the SR modding community</p>
        """)
    
    def _show_shortcuts(self):
        QMessageBox.information(self, "Keyboard Shortcuts", """
<h3>Navigation</h3>
<ul>
<li><b>Ctrl+F</b> - Focus search</li>
<li><b>Escape</b> - Clear highlight</li>
<li><b>Ctrl+O</b> - Open files</li>
<li><b>Mouse wheel</b> - Zoom</li>
<li><b>Click + drag</b> - Pan view</li>
</ul>
<h3>Tech Selection</h3>
<ul>
<li><b>Single click</b> - Select tech, show details</li>
<li><b>Double click</b> - Highlight full chain</li>
<li><b>Double click in lists</b> - Navigate to tech</li>
</ul>
        """)
    
    def _clear_cache(self):
        if clear_cache():
            QMessageBox.information(self, "Cache Cleared", 
                f"Cache cleared successfully.\n\nLocation: {CACHE_DIR}")
        else:
            QMessageBox.warning(self, "Error", "Failed to clear cache.")
    
    def _show_path_finder(self):
        if not self.techs:
            QMessageBox.warning(self, "No Data", "Load files first.")
            return
        dialog = PathFinderDialog(self.techs, self)
        dialog.exec_()
    
    def _show_balance_analyzer(self):
        if not self.techs:
            QMessageBox.warning(self, "No Data", "Load files first.")
            return
        dialog = BalanceAnalyzerDialog(self.techs, self)
        dialog.exec_()
    
    def _show_diff_tool(self):
        if not self.techs:
            QMessageBox.warning(self, "No Data", "Load base files first.")
            return
        dialog = TechDiffDialog(self.techs, self)
        dialog.exec_()
    
    def _show_tech_generator(self):
        if not self.techs:
            QMessageBox.warning(self, "No Data", "Load files first for reference.")
            return
        dialog = TechGeneratorDialog(self.techs, self)
        dialog.exec_()
    
    def _export_html_report(self):
        if not self.techs:
            QMessageBox.warning(self, "No Data", "Load files first.")
            return
        
        path, _ = QFileDialog.getSaveFileName(self, "Export HTML Report", "tech_report.html", "HTML Files (*.html)")
        if not path:
            return
        
        # Generate comprehensive HTML report
        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Tech Tree Report</title>
    <style>
        body {{ font-family: 'Segoe UI', sans-serif; background: #0d1117; color: #f0f6fc; padding: 40px; }}
        h1 {{ color: #58a6ff; border-bottom: 2px solid #30363d; padding-bottom: 10px; }}
        h2 {{ color: #8b949e; margin-top: 30px; }}
        table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
        th, td {{ border: 1px solid #30363d; padding: 12px; text-align: left; }}
        th {{ background: #161b22; color: #58a6ff; }}
        tr:hover {{ background: #21262d; }}
        .stat {{ display: inline-block; background: #161b22; padding: 20px; margin: 10px; border-radius: 12px; min-width: 150px; text-align: center; }}
        .stat-value {{ font-size: 32px; font-weight: bold; color: #58a6ff; }}
        .stat-label {{ color: #8b949e; font-size: 14px; }}
        .cat-1 {{ color: #f85149; }} .cat-2 {{ color: #58a6ff; }} .cat-3 {{ color: #3fb950; }}
        .cat-4 {{ color: #d29922; }} .cat-5 {{ color: #a371f7; }} .cat-6 {{ color: #db61a2; }}
    </style>
</head>
<body>
    <h1>🔬 Supreme Ruler Tech Tree Report</h1>
    <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
    
    <div class="stats">
        <div class="stat"><div class="stat-value">{len(self.techs)}</div><div class="stat-label">Total Techs</div></div>
        <div class="stat"><div class="stat-value">{len(self.units)}</div><div class="stat-label">Total Units</div></div>
        <div class="stat"><div class="stat-value">{sum(len(t.unlocks_units) for t in self.techs.values())}</div><div class="stat-label">Tech-Unit Links</div></div>
    </div>
    
    <h2>📊 Category Breakdown</h2>
    <table>
        <tr><th>Category</th><th>Count</th><th>With Units</th><th>Total Effects</th></tr>
"""
        
        cat_stats = defaultdict(lambda: {'count': 0, 'with_units': 0, 'effects': 0})
        for tech in self.techs.values():
            cat_stats[tech.category]['count'] += 1
            if tech.unlocks_units:
                cat_stats[tech.category]['with_units'] += 1
            cat_stats[tech.category]['effects'] += len(tech.effects)
        
        for cat_id, stats in sorted(cat_stats.items()):
            cat = CATEGORIES.get(cat_id, {'name': f'Cat {cat_id}', 'icon': '?'})
            html += f"""<tr class="cat-{cat_id}">
                <td>{cat['icon']} {cat['name']}</td>
                <td>{stats['count']}</td>
                <td>{stats['with_units']}</td>
                <td>{stats['effects']}</td>
            </tr>"""
        
        html += """</table>
    
    <h2>📋 All Technologies</h2>
    <table>
        <tr><th>ID</th><th>Name</th><th>Category</th><th>Level</th><th>Cost</th><th>Time</th><th>Effects</th><th>Units</th></tr>
"""
        
        for tid, tech in sorted(self.techs.items()):
            cat = CATEGORIES.get(tech.category, {'name': '?', 'icon': '?'})
            cost = f"${tech.cost/1e6:.0f}M"
            effects = len(tech.effects)
            units = len(tech.unlocks_units)
            
            html += f"""<tr>
                <td>{tid}</td>
                <td class="cat-{tech.category}">{tech.short_title}</td>
                <td>{cat['icon']} {cat['name']}</td>
                <td>{tech.tech_level}</td>
                <td>{cost}</td>
                <td>{tech.time_to_research}d</td>
                <td>{effects}</td>
                <td>{units}</td>
            </tr>"""
        
        html += """</table>
</body>
</html>"""
        
        with open(path, 'w', encoding='utf-8') as f:
            f.write(html)
        
        QMessageBox.information(self, "Export Complete", f"Report exported to:\n{path}")


# =============================================================================
# CONFIGURATION MANAGEMENT
# =============================================================================

# Config paths
LAUNCHER_CONFIG_PATH = Path.home() / "Documents" / "SR2030_Logger" / "config.json"
ANALYZER_CONFIG_PATH = Path.home() / "Documents" / "SR2030_Logger" / "analyzer_config.json"


def load_launcher_config() -> dict:
    """Load launcher config to get default paths."""
    try:
        if LAUNCHER_CONFIG_PATH.exists():
            with open(LAUNCHER_CONFIG_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"[Config] Could not read launcher config: {e}")
    return {}


def load_analyzer_config() -> dict:
    """Load analyzer-specific preferences (user overrides)."""
    try:
        if ANALYZER_CONFIG_PATH.exists():
            with open(ANALYZER_CONFIG_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"[Config] Could not read analyzer config: {e}")
    return {}


def save_analyzer_config(config: dict):
    """Save analyzer preferences."""
    try:
        ANALYZER_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(ANALYZER_CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4)
        print(f"[Config] Saved analyzer preferences to {ANALYZER_CONFIG_PATH}")
    except Exception as e:
        print(f"[Config] Failed to save analyzer config: {e}")


def get_effective_paths() -> tuple:
    """
    Determine which paths to use, in priority order:
    1. User overrides from analyzer_config.json
    2. Launcher defaults from config.json
    3. Auto-discovery
    """
    launcher_cfg = load_launcher_config()
    analyzer_cfg = load_analyzer_config()
    
    # Priority: analyzer override > launcher default > auto-discovery
    ttrx_path = (analyzer_cfg.get('ttrx_path') or 
                 launcher_cfg.get('default_ttrx_path') or 
                 None)
    
    unit_path = (analyzer_cfg.get('unit_path') or 
                 launcher_cfg.get('default_unit_path') or 
                 None)
    
    # Validate paths exist
    if ttrx_path and not Path(ttrx_path).exists():
        print(f"[Config] TTRX path not found: {ttrx_path}")
        ttrx_path = None
    
    if unit_path and not Path(unit_path).exists():
        print(f"[Config] UNIT path not found: {unit_path}")
        unit_path = None
    
    # Auto-discovery fallback
    if not ttrx_path or not unit_path:
        for base in [
            Path(r"C:/Program Files (x86)/Steam/steamapps/common/Supreme Ruler 2030/Maps/DATA"),
            Path(r"C:/Program Files (x86)/Steam/steamapps/common/Supreme Ruler Ultimate/Maps/DATA"),
            Path.home() / "Documents" / "SR2030_Logger",
        ]:
            if base.exists():
                ttrx = base / "DEFAULT.TTRX"
                unit = base / "DEFAULT.UNIT"
                if ttrx.exists() and unit.exists():
                    if not ttrx_path:
                        ttrx_path = str(ttrx)
                    if not unit_path:
                        unit_path = str(unit)
                    break
    
    return ttrx_path, unit_path


# =============================================================================
# ENTRY POINT
# =============================================================================

def main():
    # 1. Parse Arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("ttrx_path", nargs="?", default=None)
    parser.add_argument("unit_path", nargs="?", default=None)
    parser.add_argument("--select-tech", type=int, default=None, help="Tech ID to select on startup")
    args = parser.parse_args()
    
    # 2. Setup Application
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    # 3. Determine Paths
    # Command line args take highest priority
    if args.ttrx_path and args.unit_path:
        final_ttrx = args.ttrx_path
        final_unit = args.unit_path
    else:
        # Get from config/auto-discovery
        final_ttrx, final_unit = get_effective_paths()
    
    print(f"[Config] Using TTRX: {final_ttrx}")
    print(f"[Config] Using UNIT: {final_unit}")
    
    # 4. Initialize Window
    window = MainWindow()
    
    # Store reference to save config on path change
    window._analyzer_config = load_analyzer_config()
    
    # Override _load_files to save user's path choice
    original_load_files = window._load_files
    def load_files_with_save():
        original_load_files()
        # Check if paths differ from launcher defaults
        launcher_cfg = load_launcher_config()
        current_ttrx = window.ttrx_edit.text().strip()
        current_unit = window.unit_edit.text().strip()
        launcher_ttrx = launcher_cfg.get('default_ttrx_path', '')
        launcher_unit = launcher_cfg.get('default_unit_path', '')
        
        # Save if different from launcher defaults
        if current_ttrx != launcher_ttrx or current_unit != launcher_unit:
            window._analyzer_config['ttrx_path'] = current_ttrx
            window._analyzer_config['unit_path'] = current_unit
            save_analyzer_config(window._analyzer_config)
        elif 'ttrx_path' in window._analyzer_config:
            # User went back to defaults, clear overrides
            window._analyzer_config.pop('ttrx_path', None)
            window._analyzer_config.pop('unit_path', None)
            save_analyzer_config(window._analyzer_config)
    
    window._load_files = load_files_with_save
    
    # 5. Populate fields if we found paths
    if final_ttrx and final_unit:
        window.ttrx_edit.setText(final_ttrx)
        window.unit_edit.setText(final_unit)
        
        def load_and_select():
            window._load_files()
            if args.select_tech and hasattr(window, 'techs') and args.select_tech in window.techs:
                # Navigate to the tech
                QTimer.singleShot(500, lambda: window._navigate_to_tech(args.select_tech))
        
        QTimer.singleShot(100, load_and_select)
    
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
