# RDP Login Manager

A Windows desktop application for managing and launching Remote Desktop (RDP) connections. Built with Python and CustomTkinter.

![Python](https://img.shields.io/badge/Python-3.10+-blue) ![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey) ![License](https://img.shields.io/badge/License-MIT-green)

## Features

- **Connection Management** - Store, edit, duplicate, and organize RDP connections
- **Encrypted Credentials** - Passwords are encrypted using Fernet (PBKDF2 + AES) and never stored in plain text
- **Categories** - Group connections into custom categories with collapsible sidebar sections
- **Search & Filter** - Quickly find connections by name, hostname, or username
- **Live Status** - Automatic ping check shows green/red indicators for each host
- **RDP Settings** - Configure screen mode, resolution, color depth, clipboard/printer/drive redirection per connection
- **Import / Export** - Backup and restore connections as JSON files
- **System Tray** - Minimizes to tray with quick-access menu
- **Keyboard Shortcuts** - `Ctrl+N` new connection, `Enter` connect, `Delete` remove
- **Installer Builder** - Included build script to create a standalone `.exe` with PyInstaller

## Installation

```bash
git clone https://github.com/arman360x/RDP-Login-Manager.git
cd RDP-Login-Manager
pip install -r requirements.txt
python main.py
```

## Requirements

- Windows 10/11
- Python 3.10+
- Dependencies: `customtkinter`, `cryptography`, `pillow`, `pystray`

## Building a Standalone Executable

```bash
pip install pyinstaller
python build_installer.py
```

This creates a distributable package in `dist/` with an installer script.

## Project Structure

```
├── main.py                 # Entry point
├── config.json             # Default settings
├── requirements.txt        # Python dependencies
├── build_installer.py      # PyInstaller build script
├── assets/                 # Icons and images
├── core/
│   ├── database.py         # SQLite storage layer
│   ├── encryption.py       # Fernet encryption (PBKDF2-SHA256)
│   └── rdp.py              # RDP file generation and mstsc.exe launcher
└── ui/
    ├── app.py              # Main application window
    ├── sidebar.py          # Connection list with categories
    ├── details.py          # Connection detail panel
    └── dialogs.py          # Add/Edit/Import/Export dialogs
```

## Data Storage

Connection data is stored locally at `~/.rdpmanager/connections.db` (SQLite). Passwords are encrypted with PBKDF2-SHA256 key derivation (480,000 iterations) + Fernet (AES-128-CBC). Credentials passed to `mstsc.exe` via `cmdkey` are automatically cleaned up after 30 seconds.
