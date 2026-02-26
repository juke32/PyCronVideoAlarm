# Linux Setup & Permissions Guide

Detailed Linux-specific setup for **PyCron Video Alarm Manager**. Most users only need to install MPV and check crontab access — the rest here is for edge cases and advanced setups.

---

## 📦 Prerequisites

### System packages

```bash
sudo apt install mpv python3-tk
```

| Package | Purpose |
|---|---|
| `mpv` | Video & audio playback (required) |
| `python3-tk` | GUI framework — source installs only |
| `ffmpeg` | Optional: used for duration checks |

### Source install only

```bash
sudo apt install python3 python3-pip python3-venv
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

> [!IMPORTANT]
> Install **`python-crontab`** (not `crontab` — they are different packages).
> Verify: `python3 -c "from crontab import CronTab; print('OK')"`

---

## ⏰ Crontab Access

```bash
crontab -l
```

- `"no crontab for user"` → ✅ You have access, no entries yet
- `"permission denied"` → Run:
  ```bash
  echo $USER | sudo tee -a /etc/cron.allow
  ```

> [!CAUTION]
> **Never use `sudo` to run the app or set alarms.** Root cron jobs cannot access your display or audio session.

---

## 💡 Brightness Control

| Method | Setup |
|---|---|
| **brightnessctl** *(recommended)* | `sudo apt install brightnessctl` |
| **Video group** | `sudo usermod -aG video $USER` (log out/in after) |
| **xrandr** | No setup — software-only fallback |
| **Udev rule** *(most robust)* | See below |

### Udev rule (set once, survives reboots)
```bash
echo 'SUBSYSTEM=="backlight", ACTION=="add", RUN+="/bin/chgrp video /sys/class/backlight/%k/brightness", RUN+="/bin/chmod g+w /sys/class/backlight/%k/brightness"' \
  | sudo tee /etc/udev/rules.d/90-backlight.rules
sudo udevadm control --reload-rules
```

---

## 😴 Sleep Inhibition

The app prevents sleep using these methods in order:

1. `systemd-inhibit` — works on most modern distros
2. `xset s off` — X11 sessions (`sudo apt install x11-xserver-utils`)
3. `jeepney` DBus calls — GNOME/KDE/Wayland (included in requirements)

---

## 🎬 Codecs

If video playback fails, install codecs:

```bash
# Ubuntu/Debian
sudo apt install ubuntu-restricted-extras

# Fedora
sudo dnf install gstreamer1-plugin-openh264 mozilla-openh264
```

### Fedora: cron alternative

If cron isn't available, use the `at` service:
```bash
sudo dnf install at && sudo systemctl enable --now atd
```

---

## ⚠️ Important Notes

1. **Session must be active** — your desktop session must be logged in for media and GUI to work from cron.
2. **Keep Awake** — the app window must be open to actively block system sleep.
3. **Display injection** — the app automatically sets `DISPLAY` and `XDG_RUNTIME_DIR` in cron commands so playback works from background triggers.
4. **Moving the executable** — if you move the exe after setting alarms, update the crontab entries or re-set the alarms from the app.
