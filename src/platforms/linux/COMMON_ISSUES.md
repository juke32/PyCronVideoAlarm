# Common Coding Issues - Linux Platform

A running list of bugs encountered and lessons learned during development.

---

## 1. Crontab Requires User Permissions (Not sudo)

**Severity:** High (alarms silently fail to schedule)  
**File:** `src/platforms/linux/scheduler.py`

### What Happened
Can't post to cron on Linux unless using `sudo crontab`, but that creates entries under root's crontab — not the user's. This means the alarm runs as root with a different environment (no `DISPLAY`, no audio devices, no user session), so even if it fires, it can't play video or audio.

### Root Cause
`CronTab(user=True)` accesses the **current user's** crontab. On some systems, the user might not have permission to edit their own crontab (check `/etc/cron.allow` and `/etc/cron.deny`).

If you use `sudo`, the crontab entry goes into root's tab, and when it fires:
- No `$DISPLAY` → can't open windows or play video  
- No PulseAudio/PipeWire session → no audio  
- Wrong working directory and paths  

### Workarounds
1. **Ensure user is in cron.allow**: `echo $USER | sudo tee -a /etc/cron.allow`
2. **Use systemd timers instead** as an alternative (future enhancement)
3. **Never use `sudo crontab -e`** for user-facing alarms

### Prevention Rules
1. Always use `CronTab(user=True)` — never `CronTab(user='root')`
2. Check `self.cron_accessible` before attempting writes
3. Show a clear error to the user if crontab access fails

---

## 2. Brightness Control Requires Elevated Permissions

**Severity:** Medium (feature doesn't work without setup)  
**File:** `src/platforms/linux/display.py`

### What Happened
Can't change brightness unless running as sudo. The `/sys/class/backlight/*/brightness` file requires write permissions that normal users don't have.

### Root Cause
The kernel backlight interface (`/sys/class/backlight`) is owned by root. Writing to it needs either:
- Root permissions (bad for a user app)
- Membership in the `video` group
- A udev rule granting access

### Workarounds
1. **Add user to video group**: `sudo usermod -aG video $USER` (then log out/in)
2. **Install brightnessctl**: `sudo apt install brightnessctl` — it has its own suid/polkit setup
3. **Create a udev rule** (most robust):
   ```
   # /etc/udev/rules.d/90-backlight.rules
   SUBSYSTEM=="backlight", ACTION=="add", RUN+="/bin/chgrp video /sys/class/backlight/%k/brightness", RUN+="/bin/chmod g+w /sys/class/backlight/%k/brightness"
   ```
4. **xrandr software fallback** works without permissions but only adjusts gamma, not actual backlight

### Prevention Rules
1. Always try `brightnessctl` first (it handles permissions internally)
2. Catch `PermissionError` specifically and show a helpful message
3. Fall through all 4 strategies before reporting failure
4. The code already does this — see the strategy chain in `set_brightness()`

---

## 3. Wrong `crontab` Package Installed

**Severity:** High (app won't schedule at all)  
**File:** `src/platforms/linux/scheduler.py`

### What Happened
`import crontab` succeeds but `from crontab import CronTab` fails. The scheduler thinks crontab isn't available.

### Root Cause
PyPI has TWO packages named similarly:
- **`crontab`** — a minimal cron expression parser (WRONG)
- **`python-crontab`** — the full CronTab management library (CORRECT)

If someone runs `pip install crontab` instead of `pip install python-crontab`, the import partially succeeds but `CronTab` class doesn't exist.

### The Fix
The code already detects this (lines 18-23 in scheduler.py):
```python
try:
    import crontab
    logging.warning(f"'crontab' module found at {crontab.__file__} but 'CronTab' class is missing...")
except ImportError:
    pass
```

### Prevention Rules
1. Always use `pip install python-crontab` (it's in `requirements.txt`)
2. The startup log will warn if the wrong package is installed
3. If alarms aren't working, check: `python -c "from crontab import CronTab; print('OK')"`

---

## 4. `DISPLAY` Environment Variable Missing

**Severity:** High (all X11 features break)  
**Files:** `display.py`, `power.py`

### What Happened
`xset`, `xrandr`, and `xbacklight` commands all fail when `$DISPLAY` is not set. This happens when:
- Running from a cron job (cron has NO desktop environment)
- Running via SSH without X forwarding
- Running on Wayland (no X11 display)

### Root Cause
X11 utilities need to know which display server to connect to. Cron jobs run in a minimal environment with no `$DISPLAY`.

### Workarounds
1. **In cron commands**, prefix with `DISPLAY=:0`:
   ```
   DISPLAY=:0 /path/to/app --execute-sequence "Morning"
   ```
2. **In code**, check for `$DISPLAY` before calling X11 tools (already done in `power.py`)
3. **For Wayland**, use DBus methods instead of xset

### Prevention Rules
1. Always check `os.environ.get('DISPLAY')` before running X11 commands
2. Have fallback methods that don't depend on X11 (DBus, brightnessctl)
3. When scheduling cron jobs, consider injecting `DISPLAY=:0` into the command

---

## 5. Audio Playback from Cron

**Severity:** Medium (audio won't play from scheduled alarms)

### What Happened
Alarms scheduled via cron can play video (if DISPLAY is set) but audio doesn't work.

### Root Cause
PulseAudio/PipeWire runs per-user-session. Cron jobs don't have access to the audio server because they lack:
- `$XDG_RUNTIME_DIR`
- `$PULSE_SERVER` or PipeWire socket access

### Workarounds
1. **Export audio vars in cron**:
   ```
   XDG_RUNTIME_DIR=/run/user/$(id -u) /path/to/app --execute-sequence "Alarm"
   ```
2. **Use systemd user timers** instead of cron (they inherit the user session)
3. **Use `pactl`** to check if audio is available before attempting playback

---

## General Linux Platform Tips

- **X11 vs Wayland**: Always have fallbacks. `xset`/`xrandr` won't work on Wayland. Use DBus or `brightnessctl` as alternatives
- **File permissions**: Linux is strict. `/sys/class/backlight`, crontab, and audio devices all have permission boundaries
- **Environment inheritance**: Cron jobs get a **minimal** environment. Never assume `DISPLAY`, `HOME`, `XDG_RUNTIME_DIR`, or audio server variables are set
- **Package naming**: `python-crontab` ≠ `crontab` on PyPI. Always double-check
- **Testing cron jobs**: Run your command manually with `env -i /bin/bash -c "your_command"` to simulate cron's empty environment
- **SELinux/AppArmor**: On hardened distros, these can block file access, subprocess calls, and DBus connections silently
