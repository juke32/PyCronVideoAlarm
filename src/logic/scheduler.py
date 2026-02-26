
import sys
import logging
import os
from datetime import datetime

class AlarmScheduler:
    """Unified scheduler interface"""
    def __init__(self):
        self.platform_scheduler = None
        
        if sys.platform.startswith("linux"):
            try:
                from platforms.linux.scheduler import LinuxScheduler
                self.platform_scheduler = LinuxScheduler()
            except ImportError as e:
                logging.error(f"Failed to load Linux Scheduler: {e}")
        elif sys.platform == "win32":
            try:
                from platforms.windows.scheduler import WindowsScheduler
                self.platform_scheduler = WindowsScheduler()
            except ImportError as e:
                logging.error(f"Failed to load Windows Scheduler: {e}")
        else:
            logging.error(f"Unsupported platform for scheduling: {sys.platform}")

    def add_alarm(self, alarm_time, sequence_name, days=None, one_time=True):
        """Add an alarm. Returns (Success, Message)."""
        if self.platform_scheduler:
            return self.platform_scheduler.add_alarm(alarm_time, sequence_name, days or [], one_time=one_time)
        return False, "No platform scheduler available"

    def list_alarms(self):
        if self.platform_scheduler:
            return self.platform_scheduler.list_alarms()
        return []

    def remove_alarm(self, sequence_name, time_str, days_str=""):
        """Remove an alarm. Returns (Success, Message)."""
        if self.platform_scheduler:
            return self.platform_scheduler.remove_alarm(sequence_name, time_str, days_str=days_str)
        return False, "No platform scheduler available"

    def get_debug_info(self):
        """Get debug info from platform scheduler if available."""
        if self.platform_scheduler and hasattr(self.platform_scheduler, 'get_debug_info'):
            return self.platform_scheduler.get_debug_info()
        return "Debug info not available for this platform."
