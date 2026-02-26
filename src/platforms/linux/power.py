import logging
import os
import subprocess
import time
from core.interfaces import PowerManager

class LinuxPowerManager(PowerManager):
    """Linux power manager with multi-strategy sleep inhibition.
    
    Tries multiple methods to maximize compatibility across:
    - X11 (xset)
    - Wayland (DBus)
    - GNOME (SessionManager DBus)
    - KDE (PowerManagement DBus)
    - systemd (systemd-inhibit CLI)
    - Any freedesktop.org-compliant DE
    
    See: COMMON_ISSUES.md for known issues with permissions and environments.
    """
    def __init__(self):
        self.inhibit_proc = None      # For systemd-inhibit subprocess
        self.inhibit_cookie = None    # For DBus inhibit cookie
        self.bus_connection = None    # Keep DBus connection alive
        self._restored_screensaver = False
        self._inhibit_method = None   # Track which method succeeded

    def inhibit_sleep(self, reason: str = "Video Alarm Active") -> bool:
        """
        Inhibits sleep using multiple methods (tries all, uses first success):
        1. systemd-inhibit (CLI) — works on all systemd distros, no GUI needed
        2. xset (X11) — disables DPMS/screensaver on X11
        3. GNOME SessionManager DBus — native GNOME inhibit
        4. KDE PowerManagement DBus — native KDE inhibit
        5. freedesktop ScreenSaver DBus — generic freedesktop fallback
        """
        success = False
        
        # Method 1: systemd-inhibit (CLI) — Most robust, works headless too
        if not success:
            try:
                # systemd-inhibit runs a subprocess and holds the inhibit lock
                # until the subprocess exits. We use 'sleep infinity' to hold it.
                self.inhibit_proc = subprocess.Popen(
                    ['systemd-inhibit', '--what=idle:sleep:handle-lid-switch',
                     f'--why={reason}', '--who=PyCronVideoAlarm',
                     'sleep', 'infinity'],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
                logging.info("Inhibited sleep via systemd-inhibit CLI")
                self._inhibit_method = 'systemd-inhibit'
                success = True
            except FileNotFoundError:
                logging.debug("systemd-inhibit not found")
            except Exception as e:
                logging.debug(f"systemd-inhibit failed: {e}")
        
        # Method 2: xset (Disable DPMS and Screensaver) — X11 only
        if not success or os.environ.get('DISPLAY'):
            try:
                display = os.environ.get('DISPLAY')
                if display:
                    subprocess.run(['xset', '-dpms'], check=False, capture_output=True)
                    subprocess.run(['xset', 's', 'off'], check=False, capture_output=True)
                    logging.info("Disabled DPMS and screensaver via xset")
                    self._restored_screensaver = True
                    success = True
            except FileNotFoundError:
                logging.debug("xset not found (not X11?)")
            except Exception as e:
                logging.warning(f"xset inhibit failed: {e}")

        # Method 3: GNOME SessionManager DBus — Works on GNOME/Wayland
        if not success:
            try:
                from jeepney import DBusAddress, new_method_call
                from jeepney.io.blocking import open_dbus_connection
                
                connection = open_dbus_connection(bus='SESSION')
                
                # GNOME: org.gnome.SessionManager.Inhibit
                # flags: 1=Logout, 2=SwitchUser, 4=Suspend, 8=Idle → 4+8=12
                obj = DBusAddress('/org/gnome/SessionManager',
                                  bus_name='org.gnome.SessionManager',
                                  interface='org.gnome.SessionManager')
                msg = new_method_call(obj, 'Inhibit', 'susu',
                                      ('PyCronVideoAlarm', 0, reason, 12))
                reply = connection.send_and_get_reply(msg)
                self.inhibit_cookie = reply.body[0]
                self.bus_connection = connection
                self._inhibit_method = 'gnome-dbus'
                logging.info("Inhibited sleep via GNOME SessionManager DBus")
                success = True
            except ImportError:
                logging.debug("jeepney not installed, skipping DBus methods")
            except Exception as e:
                logging.debug(f"GNOME DBus inhibit failed: {e}")
        
        # Method 4: KDE PowerManagement DBus
        if not success:
            try:
                from jeepney import DBusAddress, new_method_call
                from jeepney.io.blocking import open_dbus_connection
                
                connection = open_dbus_connection(bus='SESSION')
                
                # KDE: org.freedesktop.PowerManagement.Inhibit
                obj = DBusAddress('/org/freedesktop/PowerManagement/Inhibit',
                                  bus_name='org.kde.Solid.PowerManagement.PolicyAgent',
                                  interface='org.kde.Solid.PowerManagement.PolicyAgent')
                msg = new_method_call(obj, 'AddInhibition', 'uss',
                                      (2, 'PyCronVideoAlarm', reason))  # 2 = ChangeScreenSettings
                reply = connection.send_and_get_reply(msg)
                self.inhibit_cookie = reply.body[0]
                self.bus_connection = connection
                self._inhibit_method = 'kde-dbus'
                logging.info("Inhibited sleep via KDE PowerManagement DBus")
                success = True
            except Exception as e:
                logging.debug(f"KDE DBus inhibit failed: {e}")
        
        # Method 5: freedesktop ScreenSaver DBus — Generic fallback
        if not success:
            try:
                from jeepney import DBusAddress, new_method_call
                from jeepney.io.blocking import open_dbus_connection
                
                connection = open_dbus_connection(bus='SESSION')
                
                obj = DBusAddress('/org/freedesktop/ScreenSaver',
                                  bus_name='org.freedesktop.ScreenSaver',
                                  interface='org.freedesktop.ScreenSaver')
                msg = new_method_call(obj, 'Inhibit', 'ss',
                                      ('PyCronVideoAlarm', reason))
                reply = connection.send_and_get_reply(msg)
                self.inhibit_cookie = reply.body[0]
                self.bus_connection = connection
                self._inhibit_method = 'freedesktop-dbus'
                logging.info("Inhibited sleep via freedesktop ScreenSaver DBus")
                success = True
            except Exception as e:
                logging.debug(f"freedesktop ScreenSaver DBus inhibit failed: {e}")
        
        if not success:
            logging.error("All sleep inhibition methods failed! The system may go to sleep during the alarm.")
        
        return success

    def uninhibit_sleep(self) -> bool:
        """Release all sleep inhibition locks."""
        success = True
        
        # Release systemd-inhibit subprocess
        if self.inhibit_proc:
            try:
                self.inhibit_proc.terminate()
                self.inhibit_proc.wait(timeout=5)
                logging.info("Released systemd-inhibit lock")
            except Exception as e:
                logging.error(f"Failed to release systemd-inhibit: {e}")
                try: self.inhibit_proc.kill()
                except: pass
                success = False
            self.inhibit_proc = None
        
        # Restore xset DPMS/screensaver
        if self._restored_screensaver:
            try:
                subprocess.run(['xset', '+dpms'], check=False, capture_output=True)
                subprocess.run(['xset', 's', 'on'], check=False, capture_output=True)
                logging.info("Re-enabled DPMS and screensaver via xset")
                self._restored_screensaver = False
            except Exception as e:
                logging.error(f"xset restore failed: {e}")
                success = False
        
        # Release DBus inhibit (GNOME/KDE/freedesktop)
        if self.inhibit_cookie is not None and self.bus_connection:
            try:
                from jeepney import DBusAddress, new_method_call
                
                if self._inhibit_method == 'gnome-dbus':
                    obj = DBusAddress('/org/gnome/SessionManager',
                                      bus_name='org.gnome.SessionManager',
                                      interface='org.gnome.SessionManager')
                    msg = new_method_call(obj, 'Uninhibit', 'u', (self.inhibit_cookie,))
                elif self._inhibit_method == 'kde-dbus':
                    obj = DBusAddress('/org/freedesktop/PowerManagement/Inhibit',
                                      bus_name='org.kde.Solid.PowerManagement.PolicyAgent',
                                      interface='org.kde.Solid.PowerManagement.PolicyAgent')
                    msg = new_method_call(obj, 'ReleaseInhibition', 'u', (self.inhibit_cookie,))
                elif self._inhibit_method == 'freedesktop-dbus':
                    obj = DBusAddress('/org/freedesktop/ScreenSaver',
                                      bus_name='org.freedesktop.ScreenSaver',
                                      interface='org.freedesktop.ScreenSaver')
                    msg = new_method_call(obj, 'UnInhibit', 'u', (self.inhibit_cookie,))
                
                self.bus_connection.send_and_get_reply(msg)
                logging.info(f"Released {self._inhibit_method} inhibit lock")
            except Exception as e:
                logging.error(f"Failed to release DBus inhibit: {e}")
                success = False
            
            self.inhibit_cookie = None
            self.bus_connection = None
            self._inhibit_method = None
        
        return success


