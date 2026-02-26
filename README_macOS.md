# macOS Setup & Installation Guide

Detailed macOS-specific setup for **PyCron Video Alarm Manager**.

> [!NOTE]
> Pre-built applications are not yet supported for macOS. You must run the application from source.

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

### Running from Source
Currently, macOS relies on running from the Python source:

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

## 🏗️ Building a Native .app Bundle

You can build a native `.app` bundle from your Mac (or trigger GitHub Actions by pushing a commit starting with `build`):

```bash
chmod +x build_macos.sh
./build_macos.sh
```

This will automatically:
1. Compile the icons into an `.icns` file
2. Bundle the application into `dist/PyCronVideoAlarm.app`
3. Inject the necessary macOS Privacy Permissions (`Info.plist`) so the app can request access to your files.
