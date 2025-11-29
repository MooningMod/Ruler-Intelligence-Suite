SPOTTING_DB = {
    # --- RADAR / OPTICAL TYPES (1-235) ---
    1: (50, 200),   # Command Radar
    2: (5, 60),     # No radar (Optical mostly)
    5: (10, 120),   # Defensive radar
    7: (7, 150),    # RP-9U
    8: (10, 120),   # Leg AA and AT units
    9: (10, 80),    # Transport Radar
    10: (10, 150),  # Standard Land 10km
    11: (11, 150),  # RP-22
    12: (12, 150),  # Cyrano etc
    13: (10, 150),  # Unknown Sub Radar
    14: (14, 150),  # BPS-704 etc
    15: (15, 150),  # Standard Land 15km
    16: (16, 150),  # Calypso III
    19: (20, 100),  # Launch truck radar
    20: (20, 150),  # Standard Land 20km
    21: (20, 180),  # 20 km Recon
    22: (20, 120),  # Advanced Artillery Radar
    23: (22, 150),  # AIDA
    24: (24, 150),  # Band Stand etc
    25: (25, 150),  # Standard Land 25km
    26: (25, 180),  # ZPQ-1 TESAE
    28: (16, 150),  # Decca 1200 (was 28 before, doc says 16 range now?) - teniamo 16 come da doc
    29: (30, 160),  # Enhanced land
    30: (30, 150),  # Standard Land 30km
    31: (31, 180),  # 30 km Recon
    34: (35, 170),  # Helicopter, unspecified (IL TUO CASO: ID 34 -> 35km)
    35: (35, 150),  # Standard Land 35km
    36: (35, 180),  # 35km recon Mig-25
    37: (36, 150),  # Smerch-A
    38: (38, 150),  # MR-310 Angara
    40: (40, 150),  # Standard Land 40km
    41: (40, 180),  # 40km recon
    42: (42, 150),  # N-019M Topaz
    43: (43, 150),  # RTS-6400
    44: (44, 140),  # EL/M-2055 UAV
    45: (45, 150),  # Standard Land 45km
    46: (45, 180),  # 45km recon
    47: (47, 150),  # Basic Anti-ship helo
    48: (48, 150),  # N-001 Mech
    50: (50, 150),  # Land based 50km
    51: (50, 180),  # 50km recon
    53: (53, 70),   # Air defense radar
    54: (54, 150),  # Agave
    55: (55, 150),  # Standard 55km
    56: (55, 180),  # 55km recon
    59: (59, 150),  # DRBV 15A
    60: (60, 150),  # Standard Land 60km
    61: (61, 180),  # 60km recon
    63: (63, 150),  # MR-302 Fut-B
    65: (65, 150),  # RAN-20S
    66: (66, 150),  # KLJ-3 J-10
    67: (66, 180),  # Super Searcher
    68: (68, 90),   # Air defense radar
    70: (70, 150),  # RBE2, Big Net
    71: (70, 180),  # Rec
    72: (72, 150),  # RP-31 Zaslon
    73: (73, 150),  # JH-7 Radar
    74: (74, 150),  # Foxhunter
    75: (75, 150),  # APG-68
    76: (76, 180),  # Air recon 75km
    77: (76, 200),  # APS-116 P-3C
    78: (78, 150),  # Anti-ship helo
    79: (79, 150),  # OPS-14
    80: (80, 150),  # Generic
    81: (80, 180),  # Oko radar
    82: (82, 150),  # AWG-9
    83: (83, 150),  # Radar 965
    84: (84, 150),  # RBE2, APG-73
    89: (89, 150),  # DA.08
    92: (92, 62),   # Air defense radar
    94: (94, 150),  # DRBV-11
    96: (96, 200),  # APS-134
    97: (97, 150),  # ECR-90 Captor
    99: (70, 120),  # Large ship radar (Note: ID 99 -> 70km per doc)
    100: (100, 110),# Israeli Air Defense
    101: (101, 130),# Tu-22M PNA
    102: (102, 120),# APG-71
    104: (104, 150),# APG-77
    106: (106, 150),# LW.08
    109: (109, 150),# DRBV 26A
    111: (110, 180),# Mobile Radar
    112: (112, 150),# SPS-40
    113: (113, 65), # Air defense radar
    114: (114, 150),# MR-800 Flag
    116: (116, 200),# APS-137 S-3 Viking
    117: (117, 150),# SMART-L
    119: (119, 150),# SPS-48
    122: (122, 175),# Chinese AEGIS
    126: (126, 200),# APS-504
    129: (129, 180),# SPY-1D AEGIS
    130: (130, 150),# APS-139
    131: (129, 180),# RP-31M Zaslon-M
    134: (134, 150),# SPS-52
    137: (140, 180),# Advanced Mobile Radar
    139: (139, 150),# OPS-24
    141: (141, 180),# ?
    154: (154, 150),# SPS-43A
    157: (157, 160),# SPY-3 DDX
    159: (159, 150),# SPS-49
    160: (160, 65), # Russian AWACS
    174: (174, 180),# ASARS
    179: (179, 180),# APY-2
    188: (188, 180),# Erieye
    190: (190, 180),# Radar Emplacement
    192: (192, 180),# APY-3
    200: (200, 180),# MESA
    206: (206, 180),# MP-RTIP
    225: (225, 180),# Argus S100B

    # --- SONAR TYPES (510-596) ---
    510: (10, 260), # Basic Sonar 10km
    511: (11, 400), # CSU-83
    522: (22, 306), # TSM-2630
    523: (23, 400), # DBQS-40
    526: (26, 380), # Type 2019
    528: (28, 380), # TSM-2633
    530: (30, 362), # Anti-Sub Helo 30km
    532: (32, 358), # AN/SQS-505
    533: (33, 320), # AN/AQS-22 ALFS
    534: (34, 296), # STN Atlas
    535: (35, 296), # Generic
    537: (37, 302), # AN/AQS-18A
    540: (40, 302), # AN/ASQ-81 MAD (Esempio documento: ID 540 -> 40km)
    541: (40, 302), # SQS-23
    542: (42, 318), # UUV
    543: (40, 302), # Russian Mi-14 MAD
    547: (47, 302), # Basic Anti-sub helo
    552: (50, 370), # MGK-400E
    553: (53, 380), # UUV
    556: (55, 410),
    578: (78, 530),
    580: (80, 560), # APS-503
    581: (80, 510),
    596: (96, 260)
}

def get_spotting_data(spot_id: int):
    """(range_km, strength) for any ID. Default (0,0)."""
    return SPOTTING_DB.get(spot_id, (0, 0))