import csv
from pathlib import Path

def load_tech_file(path):
    """reads DEFAULT.TTRX / DEFAULT.TTR:
       - TECH_DATA_LIGHT  :  short title + effects
       - TECH_DATA_FULL   : all
    """

    TECH_DATA_LIGHT = {}
    TECH_DATA_FULL = {}

    with open(path, "r", encoding="Windows-1252") as f:
        lines = f.readlines()

    # find index &&TTR 
    start_index = None
    for i, line in enumerate(lines):
        if line.strip().startswith("&&TTR"):
            start_index = i + 1
            break

    if start_index is None:
        raise ValueError("Sezione &&TTR non trovata nel file tech.")

    # reads techs as CSV
    reader = csv.reader(lines[start_index:], delimiter=",")
    
    for row in reader:

        if len(row) < 30:
            continue
        if row[0].strip() == "":
            continue

        try:
            tech_id = int(row[0])
        except:
            continue

        # effects (ID)
        effect_ids = []
        for col in [6, 7, 8, 9]:
            if row[col].strip() != "":
                try:
                    val = int(row[col])
                    effect_ids.append(int(row[col]))
                except:
                    pass

        # values
        effect_values = []
        for col in [10, 11, 12, 13]:
            if row[col].strip() != "":
                try:
                    effect_values.append(float(row[col]))
                except:
                    pass

        # Short Title 
        short_title = ""
        comment_split = row[-1].split("//")
        if len(comment_split) > 1:
            short_title = comment_split[-1].strip()

        TECH_DATA_LIGHT[tech_id] = {
            "short_title": short_title,
            "effects": [
                {"effect_id": eid, "value": val}
                for eid, val in zip(effect_ids, effect_values)
            ]
        }

        # ==== complete ver
        TECH_DATA_FULL[tech_id] = {
            "id": tech_id,
            "category": row[1],
            "tech_level": row[2],
            "pic": row[3],
            "prereq_1": row[4],
            "prereq_2": row[5],
            "effect_ids": effect_ids,
            "effect_values": effect_values,
            "time_to_research": row[14],
            "cost": row[15],
            "pop_support": row[16],
            "world_support": row[17],
            "ai_interest": row[18],
            "tradeable": row[19],
            "set_by_default": row[20],
            "unit_requirement": row[21],
            "tech_requirement": row[22],
            "facility_requirement": row[23],
            "era_tech": row[24],
            "cabinet_ai": row[25],
            "start_exclude": row[26],
            "planetary_defense": row[27],
            "leads_to_1": row[28],
            "leads_to_2": row[29],
            "region_availability": row[30] if len(row) > 30 else "",
            "short_title": short_title
        }

    return TECH_DATA_LIGHT, TECH_DATA_FULL
