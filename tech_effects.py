# tech_effects.py
import copy
from typing import Dict, Tuple, Set, Optional

from unit_parser import Unit


# Effects 140–170 = Unit Upgrade Tech (per-unit, via unituptech0..7)
EFFECT_MAP: Dict[int, Tuple[str, str]] = {
    # ---- 140–149: Attack modifiers ----
    140: ("soft", "mul"),
    141: ("hard", "mul"),
    142: ("fort", "mul"),
    143: ("air_low", "mul"),
    144: ("air_mid", "mul"),
    145: ("air_high", "mul"),
    146: ("naval_surf", "mul"),
    147: ("naval_sub", "mul"),
    148: ("close_combat", "mul"),

    # ---- 150–153: Attack Range modifiers ----
    150: ("range_ground", "mul"),
    151: ("range_air", "mul"),
    152: ("range_surf", "mul"),
    153: ("range_sub", "mul"),

    # ---- 154–157: Defense modifiers ----
    154: ("def_ground", "mul"),
    155: ("def_air", "mul"),
    156: ("def_indirect", "mul"),
    157: ("def_close", "mul"),

    # ---- 158–166: Speed / Stealth / Initiative / Fuel / Ammo ----
    158: ("speed", "mul"),
    159: ("stealth", "mul"),
    160: ("initiative", "mul"),
    161: ("combat_time", "mul"),
    162: ("fuel", "mul"),
    163: ("missile_cap", "add"),
    164: ("efficiency", "mul"),
    165: ("ammo", "add"),
    166: ("fuel", "add"),

    # ---- 167–170: Spotting modifiers ----
    167: ("spot1", "mul"),
    168: ("spot2", "mul"),
    169: ("spot1", "mul"),
    170: ("spot2", "mul"),
}

# Bool flags (201–231, 234)
BOOL_EFFECT_MAP: Dict[int, str] = {
    200: "dummy_flag",
    201: "sosus_enabled",
    202: "nuclear_weapons_enabled",
    203: "chemical_weapons_enabled",
    204: "biological_weapons_enabled",
    205: "comsat_enabled",
    206: "recon_sat_enabled",
    207: "mdi_sat_enabled",
    # 208–231: non usati in SR2030
    234: "ecm",  # ECM equipped
}


def apply_techs_to_unit(
    unit: Optional[Unit],
    tech_ids: Set[int],
    tech_light: Dict[int, dict],
) -> Optional[Unit]:
    """
    Restituisce una copia della unit con i bonus tech applicati.
    """
    if unit is None or not tech_ids or not tech_light:
        return unit

    modified = copy.deepcopy(unit)

    for tid in tech_ids:
        tech_info = tech_light.get(tid)
        if not tech_info:
            continue

        effects = tech_info.get("effects", [])
        for eff in effects:
            eid = eff.get("effect_id")
            val = eff.get("value", 0.0)

            if eid is None:
                continue

            # Bool flags
            if eid in BOOL_EFFECT_MAP:
                attr_flag = BOOL_EFFECT_MAP[eid]
                if hasattr(modified, attr_flag):
                    try:
                        if not getattr(modified, attr_flag, 0):
                            setattr(modified, attr_flag, 1)
                    except Exception:
                        pass
                continue

            # Numeric effects
            if eid not in EFFECT_MAP:
                continue

            attr, mode = EFFECT_MAP[eid]
            base = getattr(modified, attr, None)
            if base is None:
                continue

            try:
                if mode == "mul":
                    setattr(modified, attr, base * (1.0 + float(val)))
                else:
                    setattr(modified, attr, base + float(val))
            except Exception:
                continue

    return modified
