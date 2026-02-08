import platform
import subprocess
from typing import List


def get_file_systems() -> List[str]:
    """Get available file system roots. Returns drive letters on Windows, ['/'] on Unix."""
    system = get_system_type()

    if system == "windows":
        import string
        from ctypes import windll

        file_systems = []
        bitmask = windll.kernel32.GetLogicalDrives()

        for letter in string.ascii_uppercase:
            if bitmask & 1:
                file_systems.append(letter + ":\\")
            bitmask >>= 1

        return file_systems

    # Linux/macOS: root filesystem
    return ["/"]


def get_system_type() -> str:
    """Determine the current operating system type."""
    system = platform.system().lower()

    if system == "windows":
        return "windows"
    elif system == "linux":
        return "linux"
    elif system == "darwin":
        return "macos"

    return "unknown"


def open_file_explorer(dir_path: str) -> bool:
    """Open the system file explorer to the given directory path."""
    if not dir_path:
        raise ValueError(f"open_file_explorer called with empty dir_path argument ({dir_path})")

    system = get_system_type()

    if system == "windows":
        subprocess.Popen(['explorer', dir_path])
        return True
    elif system == "macos":
        subprocess.Popen(['open', dir_path])
        return True
    elif system == "linux":
        subprocess.Popen(['xdg-open', dir_path])
        return True

    return False
