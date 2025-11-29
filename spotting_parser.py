import csv
from pathlib import Path

# Global storage for spotting data: {id: (range_km, strength)}
SPOTTING_DB = {}

def get_spotting_data(spot_id: int):
    """
    Returns (range_km, strength) for a given Spotting ID.
    Defaults to (0, 0) if not found.
    """
    return SPOTTING_DB.get(spot_id, (0, 0))

def load_spotting_file(path_str: str):
    """
    Parses Spotting.csv and populates SPOTTING_DB.
    Expected format: ID, Range, Strength, ...
    """
    global SPOTTING_DB
    SPOTTING_DB.clear()

    path = Path(path_str)
    if not path.exists():
        print(f"[Spotting] Error: File not found at {path}")
        return

    try:
        with open(path, "r", encoding="latin-1", errors="replace") as f:
            lines = f.readlines()

        start_index = None
        for i, line in enumerate(lines):
            if line.strip().startswith("&&SPOTTING"):
                start_index = i + 1
                break
        
        if start_index is None:
            # Fallback: try reading from start if &&SPOTTING is missing but file is valid CSV
            start_index = 0

        reader = csv.reader(lines[start_index:], delimiter=",", quotechar='"')

        count = 0
        for row in reader:
            # Skip empty rows or commented lines
            if not row or len(row) < 3:
                continue
            if row[0].strip().startswith("//"):
                continue

            try:
                # Col 0: ID
                raw_id = row[0].strip()
                if not raw_id: continue
                s_id = int(raw_id)

                # Col 1: Range (km)
                raw_rng = row[1].strip()
                s_rng = int(raw_rng) if raw_rng else 0

                # Col 2: Strength
                raw_str = row[2].strip()
                s_str = int(raw_str) if raw_str else 0

                SPOTTING_DB[s_id] = (s_rng, s_str)
                count += 1
            except ValueError:
                continue

        print(f"[Spotting] Loaded {count} spotting entries from {path.name}")

    except Exception as e:
        print(f"[Spotting] Critical error parsing {path}: {e}")