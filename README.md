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

## 📖 Installation Guides

Choose your operating system for detailed installation and setup instructions:

- **[🪟 Windows Setup Guide](./README_Windows.md)**
- **[🐧 Linux Setup Guide](./README_Linux.md)**
- **[🍎 macOS Setup Guide](./README_macOS.md)**

---



## 🤝 Contributing & Support

🍕 **[Support on Ko-fi](https://ko-fi.com/juke32)** — any amount helps!

Issues, feature requests, and pull requests are welcome on the [GitHub Issues](https://github.com/juke32/PyCronVideoAlarm/issues).

---

## 📄 License

[Custom Source-Available License](./LICENSE) — free for personal and non-commercial use with attribution. Commercial use, resale, and public redistribution of modified versions require permission from Juke32.