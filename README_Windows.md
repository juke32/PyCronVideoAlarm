# Windows Setup & Installation Guide

Detailed Windows-specific setup for **PyCron Video Alarm Manager**.

---

## 📦 Prerequisites

1. **VLC Media Player**: Required for reliable media playback on Windows.
   - Install via Winget: `winget install VideoLAN.VLC`
   - Or download from [videolan.org](https://www.videolan.org/vlc/)

## 🚀 Setting Up the Application

### Using the Pre-built Executable
1. Download `PyCronVideoAlarm_Windows.exe` from the latest release.
2. Place the executable in a permanent folder (e.g., `C:\VideoAlarm`). Moving the executable later will break existing scheduled alarms, as the Task Scheduler points to the exact file path.
3. Run the application. On first run, it will automatically create the necessary data folders (`sequences`, `audio`, `video`, `logs`).

### Running from Source
If you prefer not to use the pre-built executable:
```cmd
git clone https://github.com/juke32/PyCronVideoAlarm.git
cd PyCronVideoAlarm
python -m venv .venv
.venv\Scripts\activate.bat
pip install -r requirements.txt
python src/main.py
```

## ⏰ Task Scheduler Integration
Alarms on Windows are registered directly in the **Windows Task Scheduler**.
- You do not need the app running in the background for alarms to trigger.
- Windows can automatically wake from sleep to fire an alarm (this is enabled by default in the app settings, provided your hardware/BIOS supports wake timers).

## 🛠️ Integration & Shortcuts
- To easily access the application, open the app and go to **Settings → Add to Start Menu** to create a shortcut.

---

## 🛠️ Troubleshooting

| Problem | Solution |
|---|---|
| Alarm didn't fire | Check the **Next Alarm** ticker in the Alarms tab. Verify Task Scheduler using a 1-minute test alarm. |
| Video won't play | Ensure VLC is installed (`winget install VideoLAN.VLC`). |

Enable **Settings → Logging** and check the logs folder for detailed error output.

---

## 🏗️ Building from Source

```cmd
build_windows.bat
```

Or push a commit whose message **starts with** `build` to trigger GitHub Actions.
