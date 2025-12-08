# SR2030 Intelligence Suite

An unofficial memory reading and overlay tool for Supreme Ruler 2030. Real-time unit comparison, technology impact analysis, tech tree visualization, and economic logging.

**Video Demo:** https://www.youtube.com/watch?v=HUjywlrrUwY

---

## Features

### Live Unit Comparison (INS key)
- Compare up to three units side-by-side with all stats
- Auto-syncs with in-game selection (build menu or worldmap click)
- Dynamic tech application: toggle techs on/off to see immediate impact
- Modified values turn green to highlight changes
- Unit B can be locked to prevent overwriting

### Tech Impact Viewer
- Inspect everything a tech does - global bonuses to specific unit modifications
- See all units unlocked and modified by any tech
- Search filters to find specific techs or units
- Right-click any tech checkbox to jump to its impact view

### Tech Tree Analyzer (Alt+T)
- Full visualization of 1400+ technologies
- Press Alt+T in-game to jump directly to the selected tech
- Prerequisites, dependencies, unit unlocks
- Category clustering (Warfare, Science, Medical, Technology, Transportation, Society)
- IPC integration: Overlay and Analyzer communicate in real-time

### Economic Intelligence Logger
- Track 60+ variables: Treasury, GDP, Population, Resources, Trade, Production costs
- Daily / weekly / monthly / yearly scaling options
- Interactive charts with value labels
- Resource comparison view
- Plot export and data filtering
- All logs stored in: `Documents/SR2030_Logger/logs/`

### Mod Support
Loads data dynamically from game files:
- `DEFAULT.UNIT` - Unit definitions
- `DEFAULT.TTRX` - Tech tree
- `Spotting.csv` - Radar/sonar ranges

---

## Installation

1. Download the latest release
2. Extract the ZIP file anywhere
3. Run `SR2030_Suite.exe`

Requires Windows 10/11.

---

## Usage

### Starting the Tools
Launch the suite using the .exe file. The launcher loads paths automatically and allows editing them in Settings.

You can also launch the game directly from the launcher.

### Hotkeys

| Key | Action |
|-----|--------|
| **INS** | Toggle Overlay |
| **Alt+T** | Open Tech Tree at selected tech |
| **L** | Lock/Unlock column B |
| **R** | Reset to in-game selection |

### Selecting Units (Overlay)
Open any unit blueprint in-game and press INS. The tool automatically detects the currently selected unit.

Load up to three units:
- **Left click** → Unit B
- **Right click** → Unit C
- **Middle click** → Unit D

### Applying and Removing Techs
Each unit panel shows applicable techs as checkboxes:
- Click to toggle a tech on/off
- Modified values turn green

### Logging
At first launch, manually enter the scenario start date (e.g., "2030-01-01"). Required because in-game date cannot be read from memory yet.

---

## To Do

Help is welcome to complete the following:

- [ ] Map true in-game km values for all ground attack types (Soft, Hard, Fort, Naval Surface)
- [ ] Complete the air range (Air Low / Mid / High) mapping
- [ ] Locate the in-game date pointer in memory for automatic logging
- [ ] Add global treasury, population, and debt data to the logger
- [ ] Fix missing missile size value

---

## For Modders

### Memory Offsets (FastTrack patch)
```
Base Pointer:              0x00F14EB8
Selected Unit (blueprint): 0x1767628
Selected Unit (worldmap):  0x1769714
Selected Tech:             0x17676D8
Market Prices:             0x01AF5868
```

### Building from Source
```bash
pip install PyQt5 pymem pandas Pillow pyinstaller
build_all.bat
```

---

## Antivirus Notice – False Positives Expected

This tool uses:
- Memory reading (via pymem)
- Process scanning
- PyQt overlay
- PyInstaller executables

Because of this, some antivirus systems — especially **Norton, Avast, AVG and Windows Defender** — may show warnings such as:
- "Unknown Publisher"
- "Low community reputation"

**These are false positives** and are commonly triggered by new unsigned executables that interact with other processes.

### Why It's Safe

- **100% open-source**: Full source code visible and auditable on GitHub
- **Reproducible builds**: Anyone can compile using the included build scripts
- **No file modifications**: Does not alter game files or save data
- **Read-only operations**: Memory access is strictly non-invasive, no DLLs injected
- **No internet communication**: No telemetry, no data sent or received
- **No admin privileges required**: Runs under normal user permissions

---

## Disclaimer

**No Game Files Included**: This tool does not distribute any original game assets, data files (such as DEFAULT.UNIT or Spotting.csv), or proprietary content belonging to BattleGoat Studios.

Not affiliated with BattleGoat Studios. Supreme Ruler 2030 is a trademark of BattleGoat Studios.

Use at your own risk. Single-player use only.

---

## License

MIT License - Do whatever you want with it.
