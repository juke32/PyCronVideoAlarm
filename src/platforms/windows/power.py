import ctypes
import logging
from core.interfaces import PowerManager

class WindowsPowerManager(PowerManager):
    def __init__(self):
        self.kernel32 = ctypes.windll.kernel32
        
    def inhibit_sleep(self, reason: str = "Video Alarm Active") -> bool:
        """
        Prevent system sleep using SetThreadExecutionState.
        ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED
        """
        try:
            ES_CONTINUOUS = 0x80000000
            ES_SYSTEM_REQUIRED = 0x00000001
            ES_DISPLAY_REQUIRED = 0x00000002
            ES_AWAYMODE_REQUIRED = 0x00000040
            
            # Combine flags to prevent sleep and keep display on
            flags = ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED | ES_AWAYMODE_REQUIRED
            
            # Set the execution state
            prev_flags = self.kernel32.SetThreadExecutionState(flags)
            
            if prev_flags == 0:
                logging.error("SetThreadExecutionState failed.")
                return False
                
            logging.info("System sleep inhibited (Windows).")
            return True
            
        except Exception as e:
            logging.error(f"Failed to inhibit sleep on Windows: {e}")
            return False

    def uninhibit_sleep(self) -> bool:
        """
        Restore normal power management.
        """
        try:
            ES_CONTINUOUS = 0x80000000
            
            # Reset to continuous execution only (allowing sleep/display off)
            prev_flags = self.kernel32.SetThreadExecutionState(ES_CONTINUOUS)
            
            if prev_flags == 0:
                logging.error("SetThreadExecutionState restoration failed.")
                return False
                
            logging.info("System sleep uninhibited (Windows).")
            return True
            
        except Exception as e:
            logging.error(f"Failed to uninhibit sleep on Windows: {e}")
            return False
