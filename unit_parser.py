import csv
from dataclasses import dataclass, field

def parse_int(value: str) -> int:
    """Parse string to int, returning 0 on error/empty."""
    try:
        value = value.strip()
        if not value:
            return 0
        return int(float(value))
    except Exception:
        return 0


def parse_float(value: str) -> float:
    """Parse string to float, returning 0.0 on error/empty."""
    try:
        value = value.strip()
        if not value:
            return 0.0
        return float(value)
    except Exception:
        return 0.0


@dataclass
class Unit:
    """
    Rappresentazione di una unità SR2030 basata su DEFAULT.UNIT.

    I valori sono "puri", direttamente dal file:
    - nessun bonus da tech / dottrina
    - nessun arrotondamento
    - alcune grandezze (Days, Cost, Weight, Supply) sono già per battaglione.
    """

    # identity
    id: int = 0
    name: str = ""
    class_num: int = 0
    year: str = "N/A"
    region: str = ""

    # strength / personnel
    strength: int = 1
    crew: int = 0
    personnel: int = 0

    # economy / production (per battaglione)
    days: int = 0
    cost: float = 0.0
    weight: int = 0

    # movement / supply
    speed: int = 0               # km/h
    move_range: int = 0          # km
    fuel: float = 0.0            # t
    combat_time: int = 0
    supply_t: float = 0.0        # t per battaglione (es. 7.2 t)

    # initiative / stealth / spotting (raw)
    initiative: int = 0
    stealth: int = 0
    spot1: int = 0               # SpotType1 (valore base)
    spot2: int = 0               # SpotType2 (spesso 0)

    # capacities
    missile_cap: int = 0
    transport_cap: int = 0
    cargo_cap: int = 0
    carrier_cap: int = 0
    
    # missile details
    missile_size_max: int = 0      # MisislePtsValue
    launch_type: int = 0           # LaunchType (bitmask)
    launch_types_str: str = ""     # es. "Land, Air"

    # combat values (attack)
    soft: float = 0.0
    hard: float = 0.0
    fort: float = 0.0
    air_low: float = 0.0
    air_mid: float = 0.0
    air_high: float = 0.0
    naval_surf: float = 0.0
    naval_sub: float = 0.0
    close_combat: float = 0.0

    # defense values
    def_ground: float = 0.0
    def_air: float = 0.0
    def_indirect: float = 0.0
    def_close: float = 0.0

    # ranges (km)
    range_ground: int = 0
    range_air: int = 0
    range_surf: int = 0
    range_sub: int = 0

    # flags (0/1, mostrati come ✔ nell'overlay)
    indirect_fire: int = 0
    ballistic_art: int = 0
    nbc: int = 0
    ecm: int = 0
    no_eff_loss_move: int = 0
    ftl: int = 0
    survey: int = 0
    river_xing: int = 0
    airdrop: int = 0
    air_tanker: int = 0
    air_refuel: int = 0
    amph: int = 0
    bridge_build: int = 0
    engineering: int = 0
    stand_off: int = 0
    move_fire_penalty: int = 0
    no_land_cap: int = 0
    has_production: int = 0
    
    tech_ids: list[int] = field(default_factory=list)


    def matches(self, query: str) -> bool:
        """Ricerca per UI (nome o ID)."""
        q = query.lower()
        return q in self.name.lower() or q == str(self.id)


def parse_default_unit(file_path: str) -> list[Unit]:
    """
    Parsea DEFAULT.UNIT in una lista di Unit.

    Mappatura delle colonne allineata al commento di intestazione ufficiale.
    """

    units: list[Unit] = []

    try:
        with open(file_path, "r", encoding="latin-1", errors="replace") as f:
            lines = f.readlines()

        # Individua la sezione &&UNITS
        start_index = 0
        for i, line in enumerate(lines):
            if line.strip().startswith("&&UNITS"):
                start_index = i + 1
                break

        csv_reader = csv.reader(lines[start_index:], delimiter=",", quotechar='"')

        for row in csv_reader:
            if not row:
                continue

            # salta commenti
            if row[0].strip().startswith("//"):
                continue

            # ci servono almeno ~90 colonne
            if len(row) < 90:
                continue

            try:
                u = Unit()

                # identity
                u.id = parse_int(row[0])
                u.name = row[1].strip().strip('"')
                u.class_num = parse_int(row[2])

                year_val = parse_int(row[4])  # (YearAvail - 1900)
                u.year = str(1900 + year_val) if year_val > 0 else "N/A"

                u.region = row[12].strip()    # Regions

                # strength / personnel
                u.strength = parse_int(row[13]) or 1      # NumSquadInBatt
                u.crew = parse_int(row[14])               # Crew
                u.personnel = u.strength * u.crew

                # initiative / stealth
                u.initiative = parse_int(row[9])          # Initiative
                u.stealth = parse_int(row[10])            # StealthStr

                # capacities / spotting
                u.carrier_cap = parse_int(row[11])        # CarrierCapacity
                u.missile_cap = parse_int(row[20])        # MisislePtsCapacity
                u.spot1 = parse_int(row[21])              # SpotType1
                u.spot2 = parse_int(row[22])              # SpotType2
                u.cargo_cap = parse_int(row[30])          # SupplyLevel (usato spesso come cap carico soft)
                u.transport_cap = parse_int(row[31])      # TransportCap

                # economy (per battaglione: valore per unit * strength)
                days_per_unit = parse_float(row[25])      # DaysToBuild
                cost_per_unit = parse_float(row[26])      # Cost
                weight_per_unit = parse_float(row[29])    # Weight

                u.days = int(days_per_unit * u.strength)
                u.cost = cost_per_unit * u.strength
                u.weight = int(weight_per_unit * u.strength)

                # movement / supply
                u.speed = parse_int(row[19])              # Speed (km/h)
                u.move_range = parse_int(row[32])         # MoveRange (km)
                u.fuel = parse_float(row[34])             # FuelCap (t)
                u.combat_time = parse_int(row[35])        # CombatTime

                # SupplyCap è per "unità base", lo riportiamo a livello battaglione
                supply_cap_per_unit = parse_float(row[36])  # SupplyCap
                if supply_cap_per_unit:
                    u.supply_t = round(supply_cap_per_unit * u.strength, 2)

                # combat values (attack)
                u.soft = parse_float(row[37])             # SoftAttack
                u.hard = parse_float(row[38])             # HardAttack
                u.fort = parse_float(row[39])             # FortAttack
                u.air_low = parse_float(row[40])          # LowAirAttack
                u.air_mid = parse_float(row[41])          # MidAirAttack
                u.air_high = parse_float(row[42])         # HighAirAttack
                u.naval_surf = parse_float(row[43])       # NavalSurfaceAttack
                u.naval_sub = parse_float(row[44])        # NavalSubAttack
                u.close_combat = parse_float(row[45])     # CloseCombatAttack

                # defense
                u.def_ground = parse_float(row[46])       # GroundDefense
                u.def_air = parse_float(row[47])          # TacAirDefense
                u.def_indirect = parse_float(row[48])     # IndirectDefense
                u.def_close = parse_float(row[49])        # CloseDefense

                # ranges (km)
                u.range_ground = parse_int(row[50])       # GroundAttRange
                u.range_air = parse_int(row[51])          # AirAttRange
                u.range_surf = parse_int(row[52])         # SurfaceAttRange
                u.range_sub = parse_int(row[53])          # SubAttRange

                # flags principali
                u.indirect_fire = parse_int(row[56])      # IndirectFlag
                u.ballistic_art = parse_int(row[57])      # BalisticArt
                u.nbc = parse_int(row[58])                # NBCProt

                # altri flag più sparsi
                u.ecm = parse_int(row[65]) if len(row) > 65 else 0          # ECMEquipped
                u.no_eff_loss_move = parse_int(row[66]) if len(row) > 66 else 0
                u.ftl = parse_int(row[67]) if len(row) > 67 else 0
                u.survey = parse_int(row[68]) if len(row) > 68 else 0
                u.river_xing = parse_int(row[69]) if len(row) > 69 else 0
                u.airdrop = parse_int(row[70]) if len(row) > 70 else 0
                u.air_tanker = parse_int(row[71]) if len(row) > 71 else 0
                u.air_refuel = parse_int(row[72]) if len(row) > 72 else 0
                u.amph = parse_int(row[75]) if len(row) > 75 else 0
                u.bridge_build = parse_int(row[78]) if len(row) > 78 else 0
                u.engineering = parse_int(row[80]) if len(row) > 80 else 0
                u.stand_off = parse_int(row[82]) if len(row) > 82 else 0
                u.move_fire_penalty = parse_int(row[83]) if len(row) > 83 else 0
                u.no_land_cap = parse_int(row[84]) if len(row) > 84 else 0
                u.has_production = parse_int(row[85]) if len(row) > 85 else 0
                
                # --- Missile extra: LaunchType + Max Missile Size ---
                # LaunchType è alla colonna 109, MisislePtsValue alla 110 (0-based)
                if len(row) > 110:
                    u.launch_type = parse_int(row[109])        # LaunchType
                    u.missile_size_max = parse_int(row[110])   # MisislePtsValue

                    # Decodifica in stringa leggibile: "Land, Air, Naval, Sub"
                    lt = u.launch_type
                    types = []
                    if lt & 1:
                        types.append("Land")
                    if lt & 2:
                        types.append("Air")
                    if lt & 4:
                        types.append("Naval")
                    if lt & 8:
                        types.append("Sub")

                    u.launch_types_str = ", ".join(types) if types else "-"
                else:
                    u.launch_type = 0
                    u.missile_size_max = 0
                    u.launch_types_str = "-"
                    
                        # --- Tech collegate all'unità (unituptech0..7) ---
                        # Nel DEFAULT.UNIT le ultime 9 colonne sono:
                    # 8 tech (unituptech0..7) + UnitDesc
                if len(row) >= 9:
                    raw_techs = row[-9:-1]  # esclude l'ultima (descrizione)
                    tech_ids: list[int] = []
                    for t in raw_techs:
                        t = t.strip()
                        if not t:
                            continue
                        try:
                            tid = int(t)
                        except ValueError:
                            continue
                        if tid != 0:
                            tech_ids.append(tid)
                    u.tech_ids = tech_ids

                units.append(u)

            except Exception:
                # riga malformata → la ignoriamo
                continue

    except FileNotFoundError:
        print(f"File not found: {file_path}")
        return []

    return units
