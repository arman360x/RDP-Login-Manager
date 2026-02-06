"""
Build script for RDP Manager installer.
Creates a standalone .exe using PyInstaller, then packages it into
a self-extracting installer.

Usage: python build_installer.py
"""

import subprocess
import shutil
import sys
import os
from pathlib import Path

ROOT = Path(__file__).parent
DIST = ROOT / "dist"
BUILD = ROOT / "build"
APP_NAME = "RDPManager"
VERSION = "1.0.0"


def clean():
    print("Cleaning previous builds...")
    for d in [DIST, BUILD]:
        if d.exists():
            shutil.rmtree(d)
    spec = ROOT / f"{APP_NAME}.spec"
    if spec.exists():
        spec.unlink()


def build_exe():
    print("Building executable with PyInstaller...")

    # Find customtkinter package path for data inclusion
    import customtkinter
    ctk_path = Path(customtkinter.__file__).parent

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name", APP_NAME,
        "--onedir",
        "--windowed",
        "--noconfirm",
        "--icon", str(ROOT / "assets" / "logo.ico"),
        # Include customtkinter themes/assets
        "--add-data", f"{ctk_path};customtkinter",
        # Include our assets
        "--add-data", f"{ROOT / 'assets'};assets",
        # Include config
        "--add-data", f"{ROOT / 'config.json'};.",
        # Hidden imports
        "--hidden-import", "pystray._win32",
        "--hidden-import", "PIL._tkinter_finder",
        str(ROOT / "main.py"),
    ]

    result = subprocess.run(cmd, cwd=str(ROOT))
    if result.returncode != 0:
        print("PyInstaller build failed!")
        sys.exit(1)

    print(f"Build complete: {DIST / APP_NAME}")


def create_installer_script():
    """Create a PowerShell-based installer that copies files and creates shortcuts."""
    installer_ps1 = DIST / "Install_RDPManager.ps1"
    installer_ps1.write_text(f'''# RDP Manager Installer v{VERSION}
# Run as: powershell -ExecutionPolicy Bypass -File Install_RDPManager.ps1

$AppName = "{APP_NAME}"
$Version = "{VERSION}"
$InstallDir = "$env:LOCALAPPDATA\\$AppName"
$SourceDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$AppDir = Join-Path $SourceDir "$AppName"

Write-Host ""
Write-Host "=================================" -ForegroundColor Cyan
Write-Host "  RDP Manager v$Version Installer" -ForegroundColor Cyan
Write-Host "=================================" -ForegroundColor Cyan
Write-Host ""

# Check source exists
if (-not (Test-Path (Join-Path $AppDir "$AppName.exe"))) {{
    Write-Host "ERROR: $AppName.exe not found in $AppDir" -ForegroundColor Red
    Write-Host "Make sure you run this from the dist folder." -ForegroundColor Red
    pause
    exit 1
}}

Write-Host "Install location: $InstallDir"
Write-Host ""

# Kill running instance before upgrading
$running = Get-Process -Name "$AppName" -ErrorAction SilentlyContinue
if ($running) {{
    Write-Host "Closing running RDP Manager..." -ForegroundColor Yellow
    $running | Stop-Process -Force
    Start-Sleep -Seconds 2
}}

# Create install directory
if (Test-Path $InstallDir) {{
    Write-Host "Removing previous installation..." -ForegroundColor Yellow
    Remove-Item -Path $InstallDir -Recurse -Force -ErrorAction SilentlyContinue
}}

Write-Host "Copying files..."
Copy-Item -Path $AppDir -Destination $InstallDir -Recurse -Force
Write-Host "  Copied to $InstallDir" -ForegroundColor Green

# Create Start Menu shortcut
$StartMenu = "$env:APPDATA\\Microsoft\\Windows\\Start Menu\\Programs"
$ShortcutPath = Join-Path $StartMenu "$AppName.lnk"
$WScriptShell = New-Object -ComObject WScript.Shell
$Shortcut = $WScriptShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = Join-Path $InstallDir "$AppName.exe"
$Shortcut.WorkingDirectory = $InstallDir
$Shortcut.IconLocation = Join-Path $InstallDir "$AppName.exe"
$Shortcut.Description = "RDP Connection Manager"
$Shortcut.Save()
Write-Host "  Start Menu shortcut created" -ForegroundColor Green

# Create Desktop shortcut
$DesktopPath = [Environment]::GetFolderPath("Desktop")
$DesktopShortcut = Join-Path $DesktopPath "$AppName.lnk"
$Shortcut2 = $WScriptShell.CreateShortcut($DesktopShortcut)
$Shortcut2.TargetPath = Join-Path $InstallDir "$AppName.exe"
$Shortcut2.WorkingDirectory = $InstallDir
$Shortcut2.IconLocation = Join-Path $InstallDir "$AppName.exe"
$Shortcut2.Description = "RDP Connection Manager"
$Shortcut2.Save()
Write-Host "  Desktop shortcut created" -ForegroundColor Green

# Create uninstaller
$UninstallScript = Join-Path $InstallDir "Uninstall.ps1"
@"
# RDP Manager Uninstaller
`$AppName = "$AppName"
`$InstallDir = "$env:LOCALAPPDATA\\`$AppName"

Write-Host "Uninstalling `$AppName..." -ForegroundColor Yellow

# Remove Start Menu shortcut
`$StartMenuShortcut = "`$env:APPDATA\\Microsoft\\Windows\\Start Menu\\Programs\\`$AppName.lnk"
if (Test-Path `$StartMenuShortcut) {{ Remove-Item `$StartMenuShortcut -Force }}

# Remove Desktop shortcut
`$DesktopShortcut = Join-Path ([Environment]::GetFolderPath("Desktop")) "`$AppName.lnk"
if (Test-Path `$DesktopShortcut) {{ Remove-Item `$DesktopShortcut -Force }}

# Remove install directory
if (Test-Path `$InstallDir) {{ Remove-Item `$InstallDir -Recurse -Force }}

Write-Host "`$AppName has been uninstalled." -ForegroundColor Green
Write-Host "Note: Your connection database at ~/.rdpmanager/ was preserved." -ForegroundColor Cyan
pause
"@ | Out-File -FilePath $UninstallScript -Encoding UTF8

Write-Host "  Uninstaller created" -ForegroundColor Green

# Add to Windows Apps & Features (registry)
$RegPath = "HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\$AppName"
New-Item -Path $RegPath -Force | Out-Null
Set-ItemProperty -Path $RegPath -Name "DisplayName" -Value "$AppName"
Set-ItemProperty -Path $RegPath -Name "DisplayVersion" -Value "$Version"
Set-ItemProperty -Path $RegPath -Name "Publisher" -Value "RDP Manager"
Set-ItemProperty -Path $RegPath -Name "InstallLocation" -Value "$InstallDir"
Set-ItemProperty -Path $RegPath -Name "UninstallString" -Value "powershell -ExecutionPolicy Bypass -File `"$UninstallScript`""
Set-ItemProperty -Path $RegPath -Name "DisplayIcon" -Value (Join-Path $InstallDir "$AppName.exe")
Set-ItemProperty -Path $RegPath -Name "NoModify" -Value 1 -Type DWord
Set-ItemProperty -Path $RegPath -Name "NoRepair" -Value 1 -Type DWord
Write-Host "  Added to Apps & Features" -ForegroundColor Green

Write-Host ""
Write-Host "=================================" -ForegroundColor Green
Write-Host "  Installation complete!" -ForegroundColor Green
Write-Host "=================================" -ForegroundColor Green
Write-Host ""
Write-Host "You can launch RDP Manager from:"
Write-Host "  - Desktop shortcut"
Write-Host "  - Start Menu"
Write-Host "  - $InstallDir\\$AppName.exe"
Write-Host ""
pause
''', encoding='utf-8')
    print(f"Installer script created: {installer_ps1}")

    # Also create a .bat launcher for the installer (easier to double-click)
    bat = DIST / "Install_RDPManager.bat"
    bat.write_text(
        f'@echo off\r\n'
        f'powershell -ExecutionPolicy Bypass -File "%~dp0Install_RDPManager.ps1"\r\n',
        encoding='utf-8'
    )
    print(f"Installer batch file created: {bat}")


def main():
    print(f"=== Building {APP_NAME} v{VERSION} ===\n")
    clean()
    build_exe()
    create_installer_script()
    print(f"\n=== Done! ===")
    print(f"Output: {DIST}")
    print(f"To install: double-click dist\\Install_RDPManager.bat")


if __name__ == "__main__":
    main()
