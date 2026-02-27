import subprocess
import logging
from core.interfaces import PowerManager


class MacOSPowerManager(PowerManager):
    """macOS power manager using caffeinate to inhibit sleep.

    caffeinate ships with macOS — no installation required.

    Flags used:
        -d  Prevent display from sleeping
        -i  Prevent system idle sleep
        -m  Prevent disk from sleeping
        -s  Prevent system sleep (AC power)
    """

    def __init__(self):
        self._caffeinate_proc = None

    def inhibit_sleep(self, reason: str = "Video Alarm Active") -> bool:
        """Start caffeinate as a background process to block sleep."""
        if self._caffeinate_proc and self._caffeinate_proc.poll() is None:
            logging.info("Sleep already inhibited via caffeinate")
            return True
        try:
            self._caffeinate_proc = subprocess.Popen(
                ["caffeinate", "-d", "-i", "-m", "-s"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            logging.info(f"Sleep inhibited via caffeinate (pid {self._caffeinate_proc.pid})")
            return True
        except Exception as e:
            logging.error(f"Failed to start caffeinate: {e}")
            return False

    def uninhibit_sleep(self) -> bool:
        """Terminate caffeinate to allow sleep again."""
        if self._caffeinate_proc:
            try:
                self._caffeinate_proc.terminate()
                self._caffeinate_proc.wait(timeout=5)
                logging.info("Released sleep inhibit (caffeinate terminated)")
            except Exception as e:
                logging.error(f"Failed to terminate caffeinate: {e}")
                try:
                    self._caffeinate_proc.kill()
                except Exception:
                    pass
                return False
            finally:
                self._caffeinate_proc = None
        return True
