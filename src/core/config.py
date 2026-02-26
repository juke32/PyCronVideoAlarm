import json
import os
import sys
import logging

def get_app_data_dir():
    """Return the platform-specific directory for persistent application data."""
    if getattr(sys, 'frozen', False):
        # Running as a PyInstaller bundle (portable mode)
        path = os.path.dirname(sys.executable)
    else:
        # Running as a normal Python script from source
        # config.py is in src/core/, so the root is 3 levels up
        path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
    os.makedirs(path, exist_ok=True)
    return path

SETTINGS_FILE = os.path.join(get_app_data_dir(), "settings.json")

DEFAULT_SETTINGS = {
    "system": {
        "brightness_method": "auto",  # Options: auto, brightnessctl, sysfs, xbacklight, xrandr
        "volume_method": "auto",      # Options: auto, amixer_pulse, amixer_master, pactl, windows_nircmd
        "linux_brightness_device": "", # specific device name for sysfs, e.g. "intel_backlight"
        "windows_nircmd_path": "nircmd.exe" # Path to nircmd for Windows volume/monitor control
    },
    "ui": {
        "theme": "Dark (Default)",
        "start_minimized": False,
        "time_format": "Both"
    },
    "alarms": {
        "sleep_offset_minutes": 15  # Minutes added to fall asleep before sleep cycle starts
    },
    "logging": {
        "file_logging_enabled": False,
        "log_directory": "logs",
        "log_file_format": "video_alarm_{date}.log"
    }
}

class ConfigManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigManager, cls).__new__(cls)
            cls._instance.settings = DEFAULT_SETTINGS.copy()
            cls._instance.load()
        return cls._instance

    def load(self):
        """Load settings from JSON file."""
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, 'r') as f:
                    data = json.load(f)
                    # Recursive update to ensure new keys are present
                    self._update_nested(self.settings, data)
                logging.info(f"Loaded settings from {SETTINGS_FILE}")
            except Exception as e:
                logging.error(f"Failed to load settings: {e}")
        else:
            self.save()

    def save(self):
        """Save current settings to JSON file."""
        try:
            with open(SETTINGS_FILE, 'w') as f:
                json.dump(self.settings, f, indent=4)
            logging.info(f"Saved settings to {SETTINGS_FILE}")
        except Exception as e:
            logging.error(f"Failed to save settings: {e}")

    def get(self, section, key=None):
        """Get a setting value."""
        try:
            if key:
                return self.settings.get(section, {}).get(key)
            return self.settings.get(section)
        except Exception:
            return None
    
    def set(self, section, key, value):
        """Set a setting value."""
        try:
            if section not in self.settings:
                self.settings[section] = {}
            self.settings[section][key] = value
            logging.info(f"Updated setting: {section}.{key} = {value}")
        except Exception as e:
            logging.error(f"Failed to set setting {section}.{key}: {e}")

    def _update_nested(self, d, u):
        for k, v in u.items():
            if isinstance(v, dict) and k != "extensions":
                d[k] = self._update_nested(d.get(k, {}), v)
            else:
                d[k] = v
        return d

# Global instance getter
def get_config():
    return ConfigManager()
