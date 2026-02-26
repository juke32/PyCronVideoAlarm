import subprocess
import logging
import os
from core.interfaces import DisplayManager

class LinuxDisplayManager(DisplayManager):
    """Linux display manager with multi-strategy brightness control.
    
    Supports X11 and Wayland through multiple fallback strategies.
    See: COMMON_ISSUES.md #2 for brightness permission issues.
    """
    
    def _run_cmd(self, cmd, env=None):
        """Run a command, return True if successful."""
        try:
            run_env = os.environ.copy()
            if env:
                run_env.update(env)
            if "DISPLAY" not in run_env:
                run_env["DISPLAY"] = ":0"
            subprocess.run(cmd, check=True, capture_output=True, env=run_env)
            return True
        except subprocess.CalledProcessError as e:
            logging.debug(f"Command failed: {' '.join(cmd)} - {e}")
            return False
        except FileNotFoundError:
            logging.debug(f"Command not found: {cmd[0]}")
            return False

    def turn_off(self) -> bool:
        """Turn off display using DPMS force off."""
        return self._run_cmd(["xset", "dpms", "force", "off"])

    def turn_on(self) -> bool:
        """Turn on display by forcing DPMS on and resetting screensaver."""
        success = self._run_cmd(["xset", "dpms", "force", "on"])
        if success:
            self._run_cmd(["xset", "s", "reset"])
        return success

    def set_brightness(self, level: int) -> bool:
        """
        Set screen brightness using multiple strategies for maximum compatibility.
        
        Order of strategies:
        1. brightnessctl — Best: handles permissions via polkit/SUID, works X11+Wayland
        2. /sys/class/backlight — Direct kernel: needs 'video' group or udev rules
        3. xbacklight — Legacy X11 backlight control
        4. xrandr — Software gamma fallback: no permissions needed, X11 only
        
        Args:
            level: Brightness percentage 0-100 (clamped to 5-100 to prevent black screen)
        
        Returns:
            True if any strategy succeeded
        """
        level = max(1, min(100, int(level)))  # Clamp 1-100 (1 min prevents black screen)
        
        # Strategy 1: brightnessctl (Hardware + polkit permissions)
        if self._run_cmd(["brightnessctl", "s", f"{level}%"]):
            logging.info(f"Brightness set to {level}% via brightnessctl")
            return True
            
        # Strategy 2: /sys/class/backlight (Direct kernel interface)
        try:
            bl_dir = "/sys/class/backlight"
            if os.path.exists(bl_dir):
                devices = os.listdir(bl_dir)
                if devices:
                    dev = devices[0]
                    max_path = os.path.join(bl_dir, dev, "max_brightness")
                    curr_path = os.path.join(bl_dir, dev, "brightness")
                    
                    if os.path.exists(max_path) and os.path.exists(curr_path):
                        with open(max_path, 'r') as f:
                            max_val = int(f.read().strip())
                        val = int(max_val * (level / 100.0))
                        with open(curr_path, 'w') as f:
                            f.write(str(val))
                        logging.info(f"Brightness set to {level}% via sysfs ({dev})")
                        return True
        except PermissionError:
            logging.warning("Permission denied for /sys/class/backlight. "
                          "Fix: sudo usermod -aG video $USER (then re-login) "
                          "or install brightnessctl")
        except Exception as e:
            logging.debug(f"sysfs brightness failed: {e}")

        # Strategy 3: xbacklight (Legacy X11)
        if self._run_cmd(["xbacklight", "-set", str(level)]):
            logging.info(f"Brightness set to {level}% via xbacklight")
            return True

        # Strategy 4: xrandr (Software gamma fallback — works without root)
        try:
            out = subprocess.check_output(["xrandr"], capture_output=False, 
                                         stderr=subprocess.DEVNULL).decode()
            import re
            # Find connected display (prefer primary)
            match = re.search(r'^(\S+) connected primary', out, re.MULTILINE)
            if not match:
                match = re.search(r'^(\S+) connected', out, re.MULTILINE)
            
            if match:
                display_name = match.group(1)
                brightness_val = max(0.1, level / 100.0)
                if self._run_cmd(["xrandr", "--output", display_name, 
                                 "--brightness", str(brightness_val)]):
                    logging.info(f"Brightness set to {level}% via xrandr (software gamma)")
                    return True
        except Exception as e:
            logging.debug(f"xrandr brightness failed: {e}")

        # Strategy 5: ddcutil (External Monitors via I2C) — Needs i2c-dev/permissions
        try:
            # Check if ddcutil is available first to avoid slow timeout
            if self._run_cmd(["which", "ddcutil"]):
                # setvcp 10 = Brightness Control
                if self._run_cmd(["ddcutil", "setvcp", "10", str(level)]):
                    logging.info(f"Brightness set to {level}% via ddcutil (DDC/CI)")
                    return True
        except Exception:
            pass # ddcutil can be slow/fail silently, ignore


        logging.error("All brightness control strategies failed. "
                     "Install brightnessctl or add user to 'video' group.")
        return False

    def get_brightness(self) -> int:
        """Get current brightness level.
        
        Tries brightnessctl first, falls back to sysfs.
        Returns 100 if unable to determine.
        """
        # Try brightnessctl
        try:
            result = subprocess.run(["brightnessctl", "g"], capture_output=True, text=True)
            max_result = subprocess.run(["brightnessctl", "m"], capture_output=True, text=True)
            if result.returncode == 0 and max_result.returncode == 0:
                current = int(result.stdout.strip())
                maximum = int(max_result.stdout.strip())
                if maximum > 0:
                    return int((current / maximum) * 100)
        except Exception:
            pass
        
        # Try sysfs
        try:
            bl_dir = "/sys/class/backlight"
            if os.path.exists(bl_dir):
                devices = os.listdir(bl_dir)
                if devices:
                    dev = devices[0]
                    with open(os.path.join(bl_dir, dev, "brightness"), 'r') as f:
                        current = int(f.read().strip())
                    with open(os.path.join(bl_dir, dev, "max_brightness"), 'r') as f:
                        maximum = int(f.read().strip())
                    if maximum > 0:
                        return int((current / maximum) * 100)
        except Exception:
            pass
        
        return 100  # Default fallback
