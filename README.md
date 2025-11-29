# Ruler-Intelligence-Suite
Ruler Intelligence Suite (RIS) is a modular tool designed for Supreme Ruler 2030, built to improve strategic visibility and decision-making.

First Alpha.

Ruler Intelligence Suite
1. Starting the Tools
Launch the suite using the .exe.
The launcher loads your paths automatically and allows you to edit:
default-unit DEFAULT.UNIT --default-ttrx DEFAULT.TTRX --default-spotting Spotting.csv
Techs, units, spotting types and km ranges are read dynamically from these external files.
You can also launch the game directly from the same executable.
Logger (Economic Intelligence Division)
The logger is optional. You can enable it when needed.
•	At first launch, you must manually enter the scenario start date (e.g. “Jun 29 1914”).
•	This is required because, in the current version, the in-game date cannot be read directly from memory.
•	You can resume and reopen old logs at any time.
Keep main window open in order to use overlay 
2. Selecting Units (Overlay)
Open any unit blueprint in-game and press INS.
The tool automatically detects the currently selected unit and loads it as Unit B.
This works for any land, air or naval blueprint while the game window is active..
 
 3. Compare Up To Three Units
You can load up to three units in parallel: Left mouse click; Right mouse click; Middle click 
Unit B can be locked so it won’t be overwritten when scanning other units.
The three units are shown side-by-side with all statistics, tech effects, boolean flags, spotting, ranges, and logistic values.
4. Applying and Removing Techs (Overlay)
Each unit shows all the techs that can modify it.
•	Every tech appears as a small square checkbox.
•	Right-click on the square to toggle that tech on/off.
 
•	The values updated by techs turn green to make the change.
You can independently toggle techs for Units B, C and D.
The overlay reads the effects dynamically from the TTRX file (via tech_parser.py ) and applies them using apply_techs_to_unit from tech_effects.py .
5. Tech Impact Mode
Click on this tab
 
Switch to the TECH IMPACT tab to inspect everything a tech does:
•	Global bonuses (economy, military, production, national effects)
•	Units unlocked by this tech
•	Units modified by this tech, with percentage changes
•	Search filters for both techs and units
This view uses combined data from:
•	DEFAULT.TTRX (tech_parser.py)
•	DEFAULT.UNIT (unit_parser.py)
6. Logging (Economic Intelligence Division)
Starting a New Log. 
Enter the scenario start date.
The logger uses this date + in-game ticks to rebuild the full calendar.
Opening an Existing Log
All logs are stored in:
Documents/SR2030_Logger/logs/
You can browse, reload and switch between logs freely.
Analytics Features
•	Daily / weekly / monthly / yearly scaling
•	Night Ops / Paper theme toggle
•	Interactive charts with value labels
•	Resource comparison view
•	Plot export
•	Category and year filtering
•	“Last 20 entries” live table
All analytics are handled internally by analytics.py.
.7. Spotting System
Spotting types are loaded from Spotting.csv via spotting_parser.py.
The overlay automatically converts spotting IDs into visual and radar km ranges, which are shown in the unit’s Spotting section.
This replaces the old static table and supports custom modded spotting files.
Missing Features / Work in Progress



TO DO:
1. FIX Ground Range Mapping (km)
We need are still mapping the true in-game km values for all ground attack types:
•	Soft Attack
•	Hard Attack
•	Fort Attack
•	Naval Surface Attack
These are logged from memory via ongoing scanner, but the full table is incomplete.
Any help with capturing raw values from multiple units is welcome.
2. FIX: MISSILE Size missing in unit comp.
3 Air Range Mapping (km)
Air range (Air Low / Mid / High) is partially mapped.
We need more samples to confirm:
•	Raw km values
•	Multipliers applied by techs
•	Internal conversion differences between altitudes
4 Auto-Detected In-Game Date
The internal date pointer has not yet been located in memory.
For now, users must manually enter the start date.
When the pointer is found, the logger will become fully automatic.
5 Global treasury, pop, Debt included in logger

