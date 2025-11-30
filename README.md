# Ruler Intelligence Suite - Alpha 0,1 (testing)

https://www.youtube.com/watch?v=HUjywlrrUwY

An unofficial memory reading and overlay tool for **Supreme Ruler 2030**. This suite provides real-time unit comparison, technology impact analysis, and detailed economic logging.
## Features
*   **Live Unit Comparison:** Compare up to three units side-by-side with all stats, tech effects, and spotting ranges.
*   **Dynamic Tech Application:** Toggle techs on/off in the overlay to see their immediate impact on unit stats.
*   **Tech Impact Viewer:** Inspect everything a tech does - from global bonuses to specific unit modifications.
*   **Economic Intelligence Logger:** Track your nation's economy with powerful analytics and interactive charts.
*   **Mod Support:** Loads data dynamically from game files (`DEFAULT.UNIT`, `DEFAULT.TTRX`, `Spotting.csv`).

## Installation
1.  Download the latest release.
2.  Extract the ZIP file to a folder of your choice.
3.  Run "LAUNCH_SUITE.exe`.
*Requires Windows 10/11 and .NET Framework 4.8 or later.*

## Usage
### Starting the Tools
Launch the suite using the `.exe` file. The launcher will load your paths automatically and allows you to edit them:
`--default-unit DEFAULT.UNIT --default-ttrx DEFAULT.TTRX --default-spotting Spotting.csv`

You can also launch the game directly from the same executable.

### Selecting Units (Overlay)
Open any unit blueprint in-game and press `INS`. The tool automatically detects the currently selected unit and loads it for comparison.

### Compare Units
You can load up to three units in parallel:
*   **Left mouse click**
*   **Right mouse click**
*   **Middle click**

Unit B can be locked to prevent it from being overwritten.

### Applying and Removing Techs
Each unit panel shows all applicable techs as small checkboxes.
*   **Click** to toggle a tech on/off.
*   Modified values turn **green** to highlight the change.

### Tech Impact Mode
Switch to the **TECH IMPACT** tab to inspect:
*   Global bonuses (economy, military, production)
*   Units unlocked and modified by a tech
*   Use search filters to find specific techs or units

### Logging (Economic Intelligence Division)
At first launch, you must manually enter the scenario start date (e.g., “Jun 29 1914”). This is required because the in-game date cannot be read directly from memory in the current version.

All logs are stored in: `Documents/SR2030_Logger/logs/`

**Analytics Features:**
*   Daily / weekly / monthly / yearly scaling
*   Interactive charts with value labels
*   Resource comparison view
*   Plot export and data filtering

## To do

Help is welcome to complete the following features:
- Map true in-game km values for all ground attack types (Soft, Hard, Fort, Naval Surface Attack).
- Complete the air range (Air Low / Mid / High) mapping.
- Locate the in-game date pointer in memory for automatic logging.
- Add global treasury, population, and debt data to the logger.
- Fix missing missile size in unit composition.

Note: No Game Files Included: This tool does not distribute any original game assets, data files (such as DEFAULT.UNIT or Spotting.csv), or proprietary content belonging to BattleGoat Studios.
