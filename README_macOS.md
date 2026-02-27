# macOS Setup & Installation Guide

Detailed macOS-specific setup for **PyCron Video Alarm Manager**.

---

## 📦 Prerequisites

1. **MPV or VLC Media Player**: Required for reliable media playback.
   - Install via Homebrew: 
     ```bash
     brew install mpv
     ```
     or
     ```bash
     brew install --cask vlc
     ```

2. **Python 3**:
   - Install via Homebrew: `brew install python`

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
On macOS, scheduling relies on the underlying `cron` daemon. 

- Alarms are created as standard cron jobs inside your user's crontab.
- Ensure your Terminal (or the IDE/app running Python) has **Full Disk Access** in **System Settings > Privacy & Security > Full Disk Access** so it can modify the crontab without permission errors.
- Test your terminal's crontab access:
  ```bash
  crontab -l
  ```

## 😴 Sleep and Power Settings
- Alarms require the system to be awake to execute properly. You may need to adjust your Energy Saver/Displays settings or use a tool like Amphetamine if you want alarms to trigger without the Mac sleeping fully.

---

## 🛠️ Troubleshooting

| Problem | Solution |
|---|---|
| Alarm didn't fire | Check the **Next Alarm** ticker in the Alarms tab. Verify your terminal has Full Disk Access for crontab. |
| Video won't play | Ensure MPV or VLC is installed via Homebrew. |

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
