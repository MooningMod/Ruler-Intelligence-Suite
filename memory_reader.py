import pymem
import pymem.process
import struct
import logging
from typing import List, Tuple, Dict, Optional

"""
Supreme Ruler 2030 - Memory Reader v2.1 (PERSISTENT)
- Switched to persistent connection to avoid handle open/close overhead.
- Much faster, prevents skipping days when the game runs at high speed.
"""

PROCESS_NAME = "SupremeRuler2030.exe"

VERSIONS = {
    "FastTrack": {
        "base_ptr": 0x00F14EB8,
        "market_offset": 0x01AF5868,
        "main_pointer_chain": [0x10, 0xA8, 0xA8, 0xC0, 0x88]
    },
    "BasePatch": {
        "base_ptr": 0x01575B28,
        "market_offset": 0x01B1A928,
        "main_pointer_chain": []
    },
}

# Variable offsets mapping
VARIABLES: List[Tuple[str, int, str]] = [
    ("Population", 0x14B48, "float"), ("Domestic Approval", 0x14B04, "float"),
    ("Military Approval", 0x14B08, "float"), ("Credit Rating", 0x14B18, "float"),
    ("Literacy", 0x14B20, "float"), ("Treaty Integrity", 0x14AF4, "float"),
    ("Tourism", 0x14B1C, "float"), ("Subsidy Rate", 0x14B08, "float"),
    ("Treasury", 0x14B88, "double"), ("Bond Debt", 0x14B98, "float"),
    ("GDP/c", 0x14C50, "float"), ("Inflation", 0x14C60, "float"),
    ("Unemployment", 0x14B68, "float"), ("Research Efficiency", 0x14CEC, "float"),
    ("Active Personnel", 0x14B60, "float"), ("Reserve Personnel", 0x14B64, "float"),
    ("Emigration", 0x14B70, "float"), ("Immigration", 0x14B6C, "float"),
    ("Births", 0x14B74, "float"), ("Deaths", 0x14B78, "float"),
    ("Agriculture", 0x14DA4, "float"), ("Rubber", 0x14EF4, "float"),
    ("Timber", 0x15044, "float"), ("Petroleum", 0x15194, "float"),
    ("Coal", 0x152E4, "float"), ("Metal Ore", 0x15434, "float"),
    ("Uranium", 0x15584, "float"), ("Electric Power", 0x156D4, "float"),
    ("Consumer Goods", 0x15824, "float"), ("Industry Goods", 0x15974, "float"),
    ("Military Goods", 0x15AC4, "float"),
    ("Agriculture Production Cost", 0x14DFC, "float"), ("Rubber Production Cost", 0x14F4C, "float"),
    ("Timber Production Cost", 0x1509C, "float"), ("Petroleum Production Cost", 0x151EC, "float"),
    ("Coal Production Cost", 0x1533C, "float"), ("Metal Ore Production Cost", 0x1548C, "float"),
    ("Uranium Production Cost", 0x155DC, "float"), ("Electric Power Production Cost", 0x1572C, "float"),
    ("Consumer Goods Production Cost", 0x1587C, "float"), ("Industry Goods Production Cost", 0x159CC, "float"),
    ("Military Goods Production Cost", 0x15B1C, "float"),
    ("Agriculture Trades", 0x14E00, "float"), ("Rubber Trades", 0x14F50, "float"),
    ("Timber Trades", 0x150A0, "float"), ("Petroleum Trades", 0x151F0, "float"),
    ("Coal Trades", 0x15340, "float"), ("Metal Ore Trades", 0x15490, "float"),
    ("Uranium Trades", 0x155E0, "float"), ("Electric Power Trades", 0x15730, "float"),
    ("Consumer Goods Trades", 0x15880, "float"), ("Industry Goods Trades", 0x159D0, "float"),
    ("Military Goods Trades", 0x15B20, "float"),
]

MARKET_PRICES: List[Tuple[str, int, str]] = [
    ("Agriculture Market Price", 0x074, "float"), ("Rubber Market Price", 0x0F8, "float"),
    ("Timber Market Price", 0x17C, "float"), ("Petroleum Market Price", 0x200, "float"),
    ("Coal Market Price", 0x284, "float"), ("Metal Ore Market Price", 0x308, "float"),
    ("Uranium Market Price", 0x38C, "float"), ("Electric Power Market Price", 0x410, "float"),
    ("Consumer Goods Market Price", 0x494, "float"), ("Industry Goods Market Price", 0x518, "float"),
    ("Military Goods Market Price", 0x59C, "float"),
]

class MemoryReader:
    """
    Persistent memory manager.
    Keeps the process handle open to maximize read speed and minimize CPU overhead.
    """

    def __init__(self, process_name: str = PROCESS_NAME, game_version: str = "FastTrack"):
        self.process_name = process_name
        self.game_version = game_version
        self.pm: Optional[pymem.Pymem] = None
        self.base_address: Optional[int] = None
        self.version_data = None
        self.final_base_ptr: Optional[int] = None

    def attach(self) -> bool:
        """Attempts to attach to the process and resolve base pointers."""
        try:
            self.pm = pymem.Pymem(self.process_name)
            mod = pymem.process.module_from_name(self.pm.process_handle, self.process_name)
            self.base_address = mod.lpBaseOfDll
            
            version_key = "FastTrack" if self.game_version.lower() in ["fasttrack", "fast", "fast track"] else "BasePatch"
            self.version_data = VERSIONS[version_key]
            
            # Pre-resolve the pointer chain. We only do this once (or on retry).
            self._refresh_pointers()
            
            return True
        except Exception:
            self.pm = None
            return False

    def _refresh_pointers(self):
        """Walks the pointer chain to find the actual nation data struct."""
        if not self.pm or not self.base_address:
            return

        try:
            chain_base = self.base_address + self.version_data["base_ptr"]
            addr = self.pm.read_uint(chain_base)
            
            if addr:
                for offset in self.version_data["main_pointer_chain"]:
                    addr = self.pm.read_uint(addr + offset)
                    if not addr:
                        break
                self.final_base_ptr = addr
            else:
                self.final_base_ptr = None
        except:
            self.final_base_ptr = None

    def read_primitive(self, addr: int, t: str) -> Optional[float]:
        """Low-level read wrapper."""
        try:
            if t == "float":
                return self.pm.read_float(addr)
            else:
                return struct.unpack("d", self.pm.read_bytes(addr, 8))[0]
        except:
            return None

    def is_active(self) -> bool:
        return self.pm is not None

    def read_snapshot(self) -> Optional[Dict[str, Optional[float]]]:
        """
        Reads all variables using the open connection.
        This is the hot path - keep it fast.
        """
        if not self.pm:
            if not self.attach():
                return None

        # If we lost the pointer (e.g. main menu reload), try to find it again
        if not self.final_base_ptr:
            self._refresh_pointers()
            if not self.final_base_ptr:
                return None

        results = {}
        
        try:
            # 1. Main variables
            for name, offset, type_ in VARIABLES:
                val = self.read_primitive(self.final_base_ptr + offset, type_)
                results[name] = val

            # 2. Market prices (these live at a different offset)
            try:
                market_base = self.pm.read_uint(self.base_address + self.version_data["market_offset"])
                if market_base:
                    for name, offset, type_ in MARKET_PRICES:
                        val = self.read_primitive(market_base + offset, type_)
                        results[name] = val
            except:
                pass # Market prices are optional/less critical

            # sanity check: if Treasury is None, the read likely failed entirely
            if results.get("Treasury") is None:
                return None
                
            return results

        except Exception:
            # Something broke (process closed?), kill the handle so we reconnect next time
            self.pm = None
            return None

# Legacy wrapper if any other script calls this directly
def read_all_variables(process_name, game_version):
    reader = MemoryReader(process_name, game_version)
    return reader.read_snapshot()