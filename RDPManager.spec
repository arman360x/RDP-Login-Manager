# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['E:\\Desktop\\Personal Project\\RDPManager\\main.py'],
    pathex=[],
    binaries=[],
    datas=[('C:\\Users\\user\\AppData\\Roaming\\Python\\Python313\\site-packages\\customtkinter', 'customtkinter'), ('E:\\Desktop\\Personal Project\\RDPManager\\assets', 'assets'), ('E:\\Desktop\\Personal Project\\RDPManager\\config.json', '.')],
    hiddenimports=['pystray._win32', 'PIL._tkinter_finder'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='RDPManager',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['E:\\Desktop\\Personal Project\\RDPManager\\assets\\logo.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='RDPManager',
)
