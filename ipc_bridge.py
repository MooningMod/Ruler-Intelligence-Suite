"""
File-Based IPC Bridge - Communication between Overlay and Tech Analyzer.

Uses simple JSON files in temp directory for inter-process communication.
No sockets, no firewall warnings, no antivirus suspicion.

Files used:
- sr2030_analyzer.lock    : PID file indicating analyzer is running
- sr2030_analyzer_cmd.json : Command mailbox (overlay writes, analyzer reads)
"""

import os
import json
import time
import atexit
from pathlib import Path
from typing import Callable, Optional
from datetime import datetime

# =============================================================================
# CONFIGURATION
# =============================================================================

# Use system temp directory
IPC_DIR = Path(os.environ.get('TEMP', os.environ.get('TMP', '/tmp')))
LOCK_FILE = IPC_DIR / "sr2030_analyzer.lock"
COMMAND_FILE = IPC_DIR / "sr2030_analyzer_cmd.json"

# Polling interval for analyzer (ms)
POLL_INTERVAL_MS = 300

# Command timeout (seconds) - ignore stale commands
COMMAND_TIMEOUT = 10.0


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def _read_json_safe(filepath: Path) -> Optional[dict]:
    """Read JSON file safely, return None on any error."""
    try:
        if filepath.exists():
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
    except (json.JSONDecodeError, IOError, PermissionError):
        pass
    return None


def _write_json_safe(filepath: Path, data: dict) -> bool:
    """Write JSON file safely, return True on success."""
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f)
        return True
    except (IOError, PermissionError) as e:
        print(f"[IPC] Failed to write {filepath}: {e}")
        return False


def _delete_safe(filepath: Path):
    """Delete file safely, ignore errors."""
    try:
        if filepath.exists():
            filepath.unlink()
    except (IOError, PermissionError):
        pass


# =============================================================================
# SERVER (Used by Tech Analyzer)
# =============================================================================

class IPCServer:
    """
    File-based IPC server for Tech Analyzer.
    Creates lock file on start, monitors command file for incoming commands.
    """
    
    def __init__(self, 
                 on_navigate: Optional[Callable[[int], None]] = None,
                 on_focus: Optional[Callable[[], None]] = None):
        self.on_navigate = on_navigate
        self.on_focus = on_focus
        self._running = False
    
    def start(self) -> bool:
        """
        Start the IPC server by creating lock file.
        Returns True if started, False if another instance is running.
        """
        # Check if another instance is running
        if self._is_other_instance_running():
            print("[IPC] Another analyzer instance is already running")
            return False
        
        # Create lock file with our PID
        try:
            with open(LOCK_FILE, 'w', encoding='utf-8') as f:
                json.dump({
                    'pid': os.getpid(),
                    'started': datetime.now().isoformat()
                }, f)
            
            # Register cleanup on exit
            atexit.register(self._cleanup)
            
            self._running = True
            print(f"[IPC] Server started (lock: {LOCK_FILE.name})")
            return True
            
        except (IOError, PermissionError) as e:
            print(f"[IPC] Failed to create lock file: {e}")
            return False
    
    def _is_other_instance_running(self) -> bool:
        """Check if another analyzer instance is running."""
        data = _read_json_safe(LOCK_FILE)
        if not data:
            return False
        
        pid = data.get('pid')
        if not pid:
            return False
        
        # Check if process with that PID exists (Windows)
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
            if handle:
                kernel32.CloseHandle(handle)
                return True  # Process exists
            return False
        except:
            # Fallback: assume not running if we can't check
            return False
    
    def check_commands(self):
        """
        Check for incoming commands. Call this periodically from QTimer.
        """
        if not self._running:
            return
        
        data = _read_json_safe(COMMAND_FILE)
        if not data:
            return
        
        # Check if command is fresh (not stale)
        timestamp = data.get('timestamp', 0)
        if time.time() - timestamp > COMMAND_TIMEOUT:
            # Stale command, delete and ignore
            _delete_safe(COMMAND_FILE)
            return
        
        # Process command
        command = data.get('command', '').upper()
        
        # Always handle focus if requested
        if data.get('focus') and self.on_focus:
            self.on_focus()
        
        if command == 'NAVIGATE':
            tech_id = data.get('tech_id')
            if tech_id and self.on_navigate:
                print(f"[IPC] Received NAVIGATE: tech_id={tech_id}")
                self.on_navigate(int(tech_id))
        
        elif command == 'FOCUS':
            if self.on_focus:
                print("[IPC] Received FOCUS")
                self.on_focus()
        
        # Delete command file after processing
        _delete_safe(COMMAND_FILE)
    
    def stop(self):
        """Stop the server and cleanup."""
        self._running = False
        self._cleanup()
        print("[IPC] Server stopped")
    
    def _cleanup(self):
        """Remove lock file on shutdown."""
        _delete_safe(LOCK_FILE)
        _delete_safe(COMMAND_FILE)


# =============================================================================
# CLIENT (Used by Overlay)
# =============================================================================

class IPCClient:
    """
    File-based IPC client for Overlay.
    Writes commands to command file for analyzer to pick up.
    """
    
    @staticmethod
    def is_server_running() -> bool:
        """Check if analyzer is currently running."""
        data = _read_json_safe(LOCK_FILE)
        if not data:
            return False
        
        pid = data.get('pid')
        if not pid:
            return False
        
        # Check if process exists (Windows)
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
            if handle:
                kernel32.CloseHandle(handle)
                return True
            # Process doesn't exist, clean up stale lock
            _delete_safe(LOCK_FILE)
            return False
        except:
            return False
    
    @staticmethod
    def send_navigate(tech_id: int) -> bool:
        """Send navigate command to analyzer."""
        return _write_json_safe(COMMAND_FILE, {
            'command': 'navigate',
            'tech_id': tech_id,
            'focus': True,  # Always bring to front on navigate
            'timestamp': time.time()
        })
    
    @staticmethod
    def send_focus() -> bool:
        """Send focus command to bring analyzer to front."""
        return _write_json_safe(COMMAND_FILE, {
            'command': 'focus',
            'timestamp': time.time()
        })


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def wait_for_server(timeout: float = 5.0, poll_interval: float = 0.3) -> bool:
    """
    Wait for analyzer to become available.
    Useful after launching analyzer process.
    """
    start = time.time()
    while time.time() - start < timeout:
        if IPCClient.is_server_running():
            return True
        time.sleep(poll_interval)
    return False


# =============================================================================
# TEST
# =============================================================================

if __name__ == "__main__":
    print("=== File-Based IPC Test ===")
    print(f"Lock file: {LOCK_FILE}")
    print(f"Command file: {COMMAND_FILE}")
    print()
    
    # Test server
    def on_nav(tid):
        print(f"  -> Navigate callback: tech_id={tid}")
    
    def on_focus():
        print(f"  -> Focus callback triggered")
    
    server = IPCServer(on_navigate=on_nav, on_focus=on_focus)
    
    if server.start():
        print("Server started. Simulating client commands...")
        
        print(f"\nAnalyzer running: {IPCClient.is_server_running()}")
        
        print("\nSending NAVIGATE command...")
        IPCClient.send_navigate(12345)
        time.sleep(0.1)
        server.check_commands()
        
        print("\nSending FOCUS command...")
        IPCClient.send_focus()
        time.sleep(0.1)
        server.check_commands()
        
        print("\nStopping server...")
        server.stop()
    else:
        print("Could not start server (another instance running?)")
        print(f"Analyzer running: {IPCClient.is_server_running()}")
