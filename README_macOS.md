# macOS Setup & Installation Guide

Detailed macOS-specific setup for **PyCron Video Alarm Manager**.

---

## 📦 Prerequisites

1. **VLC Media Player** *(required for video/audio playback)*:
   ```bash
   brew install --cask vlc
   ```

2. **Python 3**:
   ```bash
   brew install python
   ```

3. **brightness CLI** *(optional — only needed if your sequences use a `set_brightness` action)*:
   ```bash
   brew install brightness
   ```
   If not installed, the app automatically falls back to a `swift` one-liner using CoreGraphics (requires Xcode Command Line Tools: `xcode-select --install`). Brightness actions are never crash — they log a warning and skip if neither tool is available.

## 🚀 Setting Up the Application

### Using the Pre-built Release
1. Download `PyCronVideoAlarm_macOS.dmg` from the latest release.
2. Double-click the `.dmg` file to mount it.
3. Drag the **PyCronVideoAlarm.app** into your **Applications** folder OR into your custom **Portable Base Folder**.
4. **First launch — bypass Gatekeeper** (the app is not Apple-notarized):
   - **Right-click** the app → **Open** → click **Open** in the dialog.  
   - *Or:* Go to **System Settings → Privacy & Security**, scroll down, and click **Open Anyway** next to the PyCronVideoAlarm entry.
   - You only need to do this once.

> [!TIP]
> **Portable Mode:** On macOS, the app is designed to be portable. It will automatically look for its `audio/`, `video/`, and `sequences/` folders in the same directory where you placed the `.app` bundle.

### Running from Source
If you prefer to run from Python source:

```bash
git clone https://github.com/juke32/PyCronVideoAlarm.git
cd PyCronVideoAlarm
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 src/main.py
```

## ⏰ Scheduling Alarms
On macOS, scheduling uses **launchd** — the native macOS task scheduler — via `~/Library/LaunchAgents/` plist files. No crontab setup, no Full Disk Access permission required.

- Each alarm is stored as a `.plist` file under `~/Library/LaunchAgents/com.juke32.pycronvideoalarm.*.plist`.
- Alarms are managed automatically by the app (add, remove, list).
- One-time alarms automatically delete their plist after firing.
- To inspect your alarms manually:
  ```bash
  ls ~/Library/LaunchAgents/com.juke32.pycronvideoalarm.*.plist
  ```
- To remove all alarms manually (emergency reset):
  ```bash
  for f in ~/Library/LaunchAgents/com.juke32.pycronvideoalarm.*.plist; do
    launchctl unload "$f" && rm "$f"
  done
  ```

## 😴 Sleep and Power Settings
- During alarm playback the app uses `caffeinate` (built-in to macOS) to prevent the system from sleeping.
- If you need the Mac to wake from deep sleep to fire an alarm, enable **System Settings → Displays → Prevent automatic sleeping when the display is off** or use a third-party tool like **Amphetamine**.

---

## 🛠️ Troubleshooting

| Problem | Solution |
|---|---|
| Alarm didn't fire | Ensure the Mac was awake at alarm time. Check `~/Library/LaunchAgents/` for your plist and `launchctl list \| grep pycronvideoalarm`. |
| Brightness does nothing | Install `brew install brightness` OR `xcode-select --install` for the swift fallback. |
| Video won't play | Ensure VLC is installed: `brew install --cask vlc`. |
| Wrong file paths | Ensure `video/`, `audio/`, and `sequences/` folders are in the **same folder as the `.app` bundle**, not inside it. |

Enable **Settings → Logging** and check the logs folder for detailed error output.

---

## 🏗️ Building a Native Executable

The easiest way to build the executable is to let GitHub Actions handle it automatically.

You can trigger a fresh build for macOS, Linux, and Windows simultaneously by pushing a commit whose message **starts with** `build`. Go to the **Actions** tab on your GitHub repository to download the resulting executable artifact!

This workflow automatically:
1. Compiles the icons into a native macOS `.icns` file
2. Bundles the application into `PyCronVideoAlarm.app`
3. Injects the necessary macOS Privacy Permissions (`Info.plist`) so the app can request access to your files (like the Downloads folder).
4. Packages the `.app` into a `.dmg` disk image.
