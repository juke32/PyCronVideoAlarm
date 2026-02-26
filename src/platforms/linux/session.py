"""Linux session detection for cron job execution.

When cron runs a command, it has NO display session, NO audio server,
and NO DBus connection. This module auto-detects the user's active
session so that alarms can open windows, play VLC, and play audio.
"""

import os
import logging


def ensure_cron_environment():
    """Ensure environment variables are set for headless/cron execution.
    
    Injects DISPLAY and XDG_RUNTIME_DIR if missing, so that GUI apps (VLC, tkinter)
    can launch from a cron job.
    """
    uid = os.getuid()
    
    # 1. XDG_RUNTIME_DIR
    if not os.environ.get('XDG_RUNTIME_DIR'):
        xdg_path = f'/run/user/{uid}'
        if os.path.exists(xdg_path):
            os.environ['XDG_RUNTIME_DIR'] = xdg_path
    
    xdg = os.environ.get('XDG_RUNTIME_DIR', f'/run/user/{uid}')
    
    # 2. WAYLAND_DISPLAY (try to detect)
    if not os.environ.get('WAYLAND_DISPLAY'):
        wayland_sock = os.path.join(xdg, 'wayland-0')
        if os.path.exists(wayland_sock):
            os.environ['WAYLAND_DISPLAY'] = 'wayland-0'
    
    # 3. DISPLAY (Default to :0 if missing)
    if not os.environ.get('DISPLAY'):
        os.environ['DISPLAY'] = ':0'
    
    # 4. DBUS (for notifications/sleep inhibition)
    if not os.environ.get('DBUS_SESSION_BUS_ADDRESS'):
        dbus_path = os.path.join(xdg, 'bus')
        if os.path.exists(dbus_path):
            os.environ['DBUS_SESSION_BUS_ADDRESS'] = f'unix:path={dbus_path}'
            
    # Validation Logging
    logging.info(f"Cron Environment: DISPLAY={os.environ.get('DISPLAY')} XDG_RUNTIME_DIR={os.environ.get('XDG_RUNTIME_DIR')}")
