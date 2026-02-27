import subprocess
import logging
import shutil
import os
from core.interfaces import DisplayManager


class MacOSDisplayManager(DisplayManager):
    """macOS display manager.

    Brightness control is attempted via multiple strategies in order:
      1. 'brightness' CLI (Homebrew: brew install brightness)  — Intel + Apple Silicon
      2. swift one-liner via CoreBrightness framework           — requires Xcode CLT
      3. Graceful no-op                                         — logs warning, never crashes

    Display sleep/wake uses pmset (ships with macOS, no install needed).
    No Accessibility permissions required for any of these strategies.
    """

    def _run(self, cmd, **kwargs):
        """Run a command. Returns (success, stdout)."""
        try:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True, **kwargs)
            return True, result.stdout
        except subprocess.CalledProcessError as e:
            logging.debug(f"Command failed {cmd[0]}: {e.stderr.strip()}")
            return False, ""
        except FileNotFoundError:
            logging.debug(f"Command not found: {cmd[0]}")
            return False, ""

    def _find_brightness_bin(self):
        """Locate the 'brightness' CLI in common Homebrew paths."""
        candidates = [
            shutil.which("brightness"),
            "/opt/homebrew/bin/brightness",    # Apple Silicon Homebrew
            "/usr/local/bin/brightness",        # Intel Homebrew
        ]
        for p in candidates:
            if p and os.path.isfile(p) and os.access(p, os.X_OK):
                return p
        return None

    # ------------------------------------------------------------------
    # Display power
    # ------------------------------------------------------------------

    def turn_off(self) -> bool:
        ok, _ = self._run(["pmset", "displaysleepnow"])
        return ok

    def turn_on(self) -> bool:
        ok, _ = self._run(["caffeinate", "-u", "-t", "1"])
        return ok

    # ------------------------------------------------------------------
    # Brightness
    # ------------------------------------------------------------------

    def set_brightness(self, level: int) -> bool:
        """Set screen brightness 0-100 using the best available strategy."""
        level = max(0, min(100, int(level)))
        frac = f"{level / 100.0:.4f}"

        # Strategy 1: 'brightness' CLI (Homebrew)
        bin_path = self._find_brightness_bin()
        if bin_path:
            ok, _ = self._run([bin_path, frac])
            if ok:
                logging.info(f"Brightness → {level}% via 'brightness' CLI")
                return True

        # Strategy 2: swift one-liner via CoreBrightness
        # Requires: xcode-select --install  (no Accessibility perms needed)
        swift_src = (
            "import Foundation\n"
            "import CoreGraphics\n"
            f"CGDisplaySetDisplayBrightness(CGMainDisplayID(), {frac})"
        )
        ok, _ = self._run(["swift", "-"], input=swift_src)
        if ok:
            logging.info(f"Brightness → {level}% via swift/CoreGraphics")
            return True

        # Strategy 3: graceful no-op
        logging.warning(
            f"macOS brightness control unavailable (level={level}). "
            "Install 'brightness': brew install brightness   "
            "  — OR —   install Xcode CLT: xcode-select --install"
        )
        return False

    def get_brightness(self) -> int:
        """Get current brightness (0-100). Returns 100 if unavailable."""
        # Try 'brightness' CLI
        bin_path = self._find_brightness_bin()
        if bin_path:
            ok, out = self._run([bin_path, "-l"])
            if ok:
                for line in out.splitlines():
                    if "brightness" in line:
                        try:
                            val = float(line.strip().split()[-1])
                            return int(val * 100)
                        except (ValueError, IndexError):
                            pass
        return 100  # Safe default
