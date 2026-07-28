# 🧹 Cleaner Pro

> **Premium Windows optimization suite** — clean, fast, and under your control.

![Platform](https://img.shields.io/badge/Platform-Windows%2010%20%2F%2011-0078D6?style=for-the-badge&logo=windows&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.13-3776AB?style=for-the-badge&logo=python&logoColor=white)
![UI](https://img.shields.io/badge/UI-PySide6%20%7C%20Fluent-0A84FF?style=for-the-badge)
![Status](https://img.shields.io/badge/Status-BETA-FF9F0A?style=for-the-badge)

---

### ⚠️ Beta Notice

Cleaner Pro is currently in **public beta**.  
Core features work, but bugs, edge cases, and incomplete polish are expected.  
Use on non-critical systems first. Always create a **System Restore Point** before aggressive cleanups.

---

## ✨ Features

| Module | Description |
|--------|-------------|
| **Dashboard** | Live CPU / RAM charts, disk space, uptime, program & startup counts |
| **Installed Programs** | Real icons, search & sort, uninstall, **Force Remove** with leftover scan |
| **Disk Analyzer** | Largest folders & files per drive, safe delete |
| **Duplicate Finder** | SHA-256 duplicates (Pictures / Videos / Documents / Everything) |
| **Temporary Cleaner** | Temp, Prefetch, Update cache, Thumbnails, Crash dumps, Recycle Bin, DNS… |
| **Browser Cleaner** | Chrome · Edge · Firefox · Opera · Brave |
| **Startup Manager** | Enable / disable / delete startup entries |
| **Process Manager** | Live list, End / Force Kill, open location |
| **Windows Services** | Start · Stop · Restart · change start mode |
| **Registry Cleaner** | Broken path detection + restore point before changes |
| **One-Click Optimize** | Combined cleanup with summary report |
| **SSD / HDD Health** | SMART status, model, serial, firmware |
| **System Info** | OS, CPU, RAM, drives, network |
| **Settings** | Dark / Light / System theme, start with Windows |

### 🛡️ Safety first

- Confirmation before every destructive action  
- Recycle Bin used where possible  
- System Restore Point before Force Remove & Registry clean  
- No silent mass deletion of user files or Windows system folders  

---

## 🚀 Quick start

```bash
cd CleanerPro
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
Build single EXE
Bashpython build.py
Output: dist/CleanerPro.exe (windowed, no console).

📁 Project structure
textCleanerPro/
├── main.py
├── core/          # App shell, theme, logging
├── services/      # Scanners, cleaners, monitor
├── pages/         # All UI pages
├── widgets/       # Reusable components
├── utils/         # Paths, icon loader…
├── assets/icons/  # App icon
├── reports/       # HTML / PDF reports
└── build.py

⚠️ Disclaimer
This software can modify the registry, delete files, and control services.
You are responsible for what you confirm.
The author is not liable for data loss or system issues.
Run as Administrator only when needed. Prefer testing on a VM or secondary PC.

👨‍💻 Author
MRGhesam
Telegram: @MRGhesam

📄 License
Proprietary — original Cleaner Pro implementation.
All rights reserved. Beta builds are for testing and feedback.


  Cleaner Pro — clean smarter, stay in control.

  Beta · Windows 10 / 11 · Made with Python & PySide6
