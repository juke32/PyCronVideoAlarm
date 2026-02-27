import subprocess
import logging
from core.interfaces import DisplayManager


class MacOSDisplayManager(DisplayManager):
    """macOS display manager.

    Brightness control requires the 'brightness' CLI tool:
        brew install brightness

    If it is not installed, brightness calls log a warning and return False
    silently — no crash, no error dialog.

    Display sleep / wake uses pmset which ships with macOS.
    """

    def _run(self, cmd):
        """Run a command. Returns True on success."""
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            return True
        except subprocess.CalledProcessError as e:
            logging.debug(f"Command failed: {' '.join(cmd)} — {e}")
            return False
        except FileNotFoundError:
            logging.debug(f"Command not found: {cmd[0]}")
            return False

    # ------------------------------------------------------------------
    # Display power
    # ------------------------------------------------------------------

    def turn_off(self) -> bool:
        """Put the display to sleep immediately."""
        return self._run(["pmset", "displaysleepnow"])

    def turn_on(self) -> bool:
        """Wake the display (brief caffeinate wakeup assertion)."""
        return self._run(["caffeinate", "-u", "-t", "1"])

    # ------------------------------------------------------------------
    # Brightness
    # ------------------------------------------------------------------

    def set_brightness(self, level: int) -> bool:
        """Set screen brightness (0-100) via the 'brightness' Homebrew CLI.

        If 'brightness' is not installed the call returns False and logs a
        warning — it does NOT raise an exception or show an error dialog.

        Install with: brew install brightness
        """
        level = max(0, min(100, int(level)))
        brightness_val = f"{level / 100.0:.2f}"

        if self._run(["brightness", brightness_val]):
            logging.info(f"Brightness set to {level}% via 'brightness' CLI")
            return True

        logging.warning(
            "macOS brightness control unavailable. "
            "Install with: brew install brightness"
        )
        return False

    def get_brightness(self) -> int:
        """Get current brightness (0-100) via the 'brightness' CLI."""
        try:
            result = subprocess.run(
                ["brightness", "-l"],
                capture_output=True,
                text=True
            )
            # Output contains lines like: "display 0: brightness 0.7500"
            for line in result.stdout.splitlines():
                if "brightness" in line:
                    parts = line.strip().split()
                    val = float(parts[-1])
                    return int(val * 100)
        except Exception:
            pass
        return 100  # Safe default
