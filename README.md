# PyCron Video Alarm

> A cross-platform video alarm clock that wakes you up with videos, audio, and custom automation sequences — scheduled through your OS natively (cron on Linux, Task Scheduler on Windows).

[![License](https://img.shields.io/badge/License-Custom%20Source--Available-red.svg)](./LICENSE)
[![Platform](https://img.shields.io/badge/platform-Linux%20%7C%20Windows-blue)](https://github.com/juke32/PyCronVideoAlarm/releases)
[![Ko-fi](https://img.shields.io/badge/Support-Ko--fi-FF5E5B?logo=kofi)](https://ko-fi.com/juke32)

---

## ✨ What It Does

- 🎬 **Play videos as alarms** — launch any video file at a scheduled time using MPV
- 🔊 **Play audio** — wake up to music, sounds, or recorded voice clips
- 📋 **Alarm Sequences** — chain actions together (play video → open website → dim screen → etc.)
- 🕐 **Sleep Cycle Calculator** — calculates optimal wake times in 90-minute cycles
- 🔁 **Recurring Alarms** — set alarms for specific days of the week, or one-time only
- 🌙 **Sleep Mode** — dim/black screen overlay with keep-awake to assist sleeping
- 💡 **Brightness Control** — dim the display as part of a sequence (Linux + Windows)
- 🏠 **Native OS Scheduling** — uses `cron` on Linux, `Task Scheduler` on Windows (no background process needed on windows, on linux it will need an application open on the user to run the tasks)
- 🎨 **Themes** — multiple dark/light themes

---

## ⚡ Quick Start

### Option A: Download Pre-built Executable *(Recommended)*

1. Download the latest release from the [Releases page](https://github.com/juke32/PyCronVideoAlarm/releases)
2. Extract the folder anywhere you want the app to live permanently
3. Run the executable:
   - **Windows**: `PyCronVideoAlarm_Windows.exe`
   - **Linux**: `./PyCronVideoAlarm_Linux` (may need: `chmod +x PyCronVideoAlarm_Linux`)
4. On first run, go to **Settings → Add to Applications** to register it in your app launcher

> [!TIP]
> **Keep the folder in one place.** Cron/Task Scheduler entries point to this exact path. Moving the exe after setting alarms will break the schedule links.

### Option B: Run from Source

```bash
git clone https://github.com/juke32/PyCronVideoAlarm.git
cd PyCronVideoAlarm
python3 -m venv .venv
source .venv/bin/activate        # Linux
# .venv\Scripts\activate.bat     # Windows
pip install -r requirements.txt
python src/main.py
```

---

## 📦 Dependencies

### External (install separately)

| Dependency | Purpose | Linux | Windows |
|---|---|---|---|
| **MPV (Linux)** | Video & audio playback | `sudo apt install mpv` | - |
| **VLC (Windows)** | Video & audio playback | - | [videolan.org](https://www.videolan.org/vlc/) or `winget install VideoLAN.VLC` |

### Python (auto-installed via `requirements.txt`)

| Package | Purpose |
|---|---|
| `Pillow` | Image handling / icon display |
| `python-crontab` | Linux cron scheduling *(Linux only)* |
| `jeepney` | DBus / Wayland support *(Linux only)* |
| `pycaw`, `comtypes`, `pywin32` | Windows audio + Task Scheduler *(Windows only)* |
| `pyautogui`, `opencv-python` | Screen automation actions |
| `sounddevice`, `numpy`, `scipy` | Audio recording action |

---

## 📂 Folder Structure

Place the executable (or run from source) with this layout. The app creates missing folders automatically on first run.

```
PyCronVideoAlarm/
│
├── PyCronVideoAlarm_Linux    ← Main executable (Linux)
├── PyCronVideoAlarm_Windows.exe  ← Main executable (Windows)
├── settings.json             ← Auto-generated on first run
│
├── sequences/                ← Alarm sequences (.json files)
│   ├── Morning_Routine.json
│   └── Weekend_Wake.json
│
├── audio/                    ← Audio files for sequences
│   ├── Alarm_Clock.mp3
│   └── 00-100_numbers/       ← Drop the "0-100 Audio" pack here
│
└── video/                    ← Video files for sequences
    ├── FunnyFolder/          ← Drop funny video packs here
    └── MotivationFolder/     ← Drop motivational packs here
```

> [!NOTE]
> Sample sequences, audio, and video packs are available as optional downloads on the [Releases page](https://github.com/juke32/PyCronVideoAlarm/releases). Drop them in the folders above and the included sequences will work immediately.

---

## 🐧 Linux Setup

### Make it executable
```bash
chmod +x PyCronVideoAlarm_Linux
./PyCronVideoAlarm_Linux
```

### Crontab access
The app schedules alarms via cron. Test access with:
```bash
crontab -l
# "no crontab for user" = you have access (just no entries yet)
# "permission denied" = run: echo $USER | sudo tee -a /etc/cron.allow
```

> [!CAUTION]
> Never run the app or set alarms with `sudo`. Cron jobs set as root cannot access your display or audio session.

### Brightness control
Install `brightnessctl` for the most reliable brightness support:
```bash
sudo apt install brightnessctl
```
Or add your user to the `video` group:
```bash
sudo usermod -aG video $USER   # log out and back in after
```

### Session requirement
Your user session must be **logged in** for media to play. The app automatically injects `DISPLAY` and `XDG_RUNTIME_DIR` into cron commands for GUI playback.

For full Linux details (Fedora, udev rules, codecs, sleep inhibition): see [README_Linux.md](./README_Linux.md)

---

## 🪟 Windows Setup

1. Download and run `VideoAlarm_Windows.exe`
2. Install VLC: `winget install VideoLAN.VLC` or from [videolan.org](https://www.videolan.org/vlc/)
3. Alarms are registered in **Windows Task Scheduler** — no background process needed
4. Go to **Settings → Add to Start Menu** to add a shortcut

> [!NOTE]
> Windows can wake from sleep to fire an alarm if configured in Task Scheduler (enabled by default in the app).

---

## 🛠️ Troubleshooting

| Problem | Solution |
|---|---|
| Alarm didn't fire | Check the **Next Alarm** ticker in the Alarms tab. Verify cron/Task Scheduler using a 1-minute test alarm. |
| Video won't play | Ensure MPV (Linux) or VLC (Windows) is installed. |
| No sound | On Linux, check `XDG_RUNTIME_DIR` is set. The app logs this on each alarm run. |
| App won't open on Linux | Run `chmod +x VideoAlarm_Linux` then try again |
| Brightness control fails | Install `brightnessctl` or add user to `video` group (Linux) |

Enable **Settings → Logging** and check the logs folder for detailed error output.

---

## 🏗️ Building from Source

```bash
# Linux
./build_linux.sh

# Windows
build_windows.bat
```

Or push a commit whose message **starts with** `build` to trigger GitHub Actions (builds both platforms automatically).

---

## 🤝 Contributing & Support

🍕 **[Support on Ko-fi](https://ko-fi.com/juke32)** — any amount helps!

Issues, feature requests, and pull requests are welcome on the [GitHub Issues](https://github.com/juke32/PyCronVideoAlarm/issues).

---

## 📄 License

[Custom Source-Available License](./LICENSE) — free for personal and non-commercial use with attribution. Commercial use, resale, and public redistribution of modified versions require permission from Juke32.