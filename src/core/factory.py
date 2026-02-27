import sys
import logging
from .interfaces import PowerManager, DisplayManager

def get_platform_managers() -> tuple[PowerManager, DisplayManager]:
    """
    Returns a tuple of (PowerManager, DisplayManager) for the current platform.
    """
    if sys.platform == "win32":
        try:
            from platforms.windows.power import WindowsPowerManager
            from platforms.windows.display import WindowsDisplayManager
            return WindowsPowerManager(), WindowsDisplayManager()
        except ImportError as e:
            logging.error(f"Failed to import Windows managers: {e}")
            raise

    elif sys.platform.startswith("linux"):
        try:
            from platforms.linux.power import LinuxPowerManager
            from platforms.linux.display import LinuxDisplayManager
            return LinuxPowerManager(), LinuxDisplayManager()
        except ImportError as e:
            logging.error(f"Failed to import Linux managers: {e}")
            raise

    elif sys.platform == "darwin":
        try:
            from platforms.macos.power import MacOSPowerManager
            from platforms.macos.display import MacOSDisplayManager
            return MacOSPowerManager(), MacOSDisplayManager()
        except ImportError as e:
            logging.error(f"Failed to import macOS managers: {e}")
            raise

    else:
        raise NotImplementedError(f"Platform {sys.platform} is not supported.")
