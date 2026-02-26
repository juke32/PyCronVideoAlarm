import ctypes
import logging
from core.interfaces import DisplayManager

class WindowsDisplayManager(DisplayManager):
    def __init__(self):
        self.user32 = ctypes.windll.user32
        self.HWND_BROADCAST = 0xFFFF
        self.WM_SYSCOMMAND = 0x0112
        self.SC_MONITORPOWER = 0xF170
        
    def turn_off(self) -> bool:
        """
        Turn off monitor using SendMessage.
        lParam: 2 (power off), 1 (low power), -1 (on)
        """
        try:
            self.user32.SendMessageW(
                self.HWND_BROADCAST, 
                self.WM_SYSCOMMAND, 
                self.SC_MONITORPOWER, 
                2
            )
            return True
        except Exception as e:
            logging.error(f"Failed to turn off display on Windows: {e}")
            return False

    def turn_on(self) -> bool:
        """Turn on monitor."""
        try:
            self.user32.SendMessageW(
                self.HWND_BROADCAST, 
                self.WM_SYSCOMMAND, 
                self.SC_MONITORPOWER, 
                -1
            )
            return True
        except Exception as e:
            logging.error(f"Failed to turn on display on Windows: {e}")
            return False

    def set_brightness(self, level: int) -> bool:
        """
        Set brightness using PowerShell WMI (WmiMonitorBrightnessMethods).
        Level should be 0-100.
        """
        level = max(0, min(100, int(level)))
        try:
            # PowerShell command to set brightness via WMI
            # (Get-WmiObject -Namespace root/wmi -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1, level)
            cmd = [
                "powershell", 
                "-Command", 
                f"(Get-WmiObject -Namespace root/wmi -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1, {level})"
            ]
            
            # Using subprocess to call powershell
            # creationflags=0x08000000 (CREATE_NO_WINDOW) to avoid popping up a console window
            import subprocess
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
            subprocess.run(cmd, check=True, startupinfo=startupinfo, capture_output=True)
            logging.info(f"Windows brightness set to {level}% via PowerShell")
            return True
            
        except subprocess.CalledProcessError as e:
            logging.error(f"PowerShell WMI brightness failed: {e}")
        except Exception as e:
            # Fallback or just log
            logging.error(f"Windows set_brightness failed: {e}")
            
        return False

    def get_brightness(self) -> int:
        return 100 # Placeholder
