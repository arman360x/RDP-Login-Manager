import os
import subprocess
import tempfile
import threading
from pathlib import Path

from core.encryption import decrypt_password


def generate_rdp_file(connection: dict) -> str:
    rdp_content = f"""screen mode id:i:{connection.get('screen_mode', 2)}
use multimon:i:0
desktopwidth:i:{connection.get('desktop_width', 1920)}
desktopheight:i:{connection.get('desktop_height', 1080)}
session bpp:i:{connection.get('color_depth', 32)}
full address:s:{connection['hostname']}:{connection.get('port', 3389)}
audiomode:i:0
audiocapturemode:i:0
redirectclipboard:i:{1 if connection.get('redirect_clipboard', True) else 0}
redirectprinters:i:{1 if connection.get('redirect_printers', False) else 0}
redirectdrives:i:{1 if connection.get('redirect_drives', False) else 0}
redirectcomports:i:0
redirectsmartcards:i:0
username:s:{connection.get('username', '')}
authentication level:i:2
prompt for credentials:i:0
negotiate security layer:i:1
"""
    temp_dir = Path(tempfile.gettempdir()) / "rdpmanager"
    temp_dir.mkdir(exist_ok=True)
    rdp_path = temp_dir / f"conn_{connection.get('id', 'temp')}.rdp"
    rdp_path.write_text(rdp_content, encoding="utf-8")
    return str(rdp_path)


def store_credentials(hostname: str, port: int, username: str, password: str):
    target = f"TERMSRV/{hostname}"
    subprocess.run(
        ["cmdkey", f"/generic:{target}", f"/user:{username}", f"/pass:{password}"],
        capture_output=True,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )


def cleanup_credentials(hostname: str):
    target = f"TERMSRV/{hostname}"
    subprocess.run(
        ["cmdkey", f"/delete:{target}"],
        capture_output=True,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )


def cleanup_rdp_file(rdp_path: str):
    try:
        os.remove(rdp_path)
    except OSError:
        pass


def launch_rdp(rdp_file_path: str):
    subprocess.Popen(
        ["mstsc.exe", rdp_file_path],
        creationflags=subprocess.CREATE_NO_WINDOW,
    )


def connect(connection: dict, master_password: str, encryption_salt: bytes):
    password = ""
    if connection.get("encrypted_password"):
        password = decrypt_password(
            connection["encrypted_password"], master_password, encryption_salt
        )

    hostname = connection["hostname"]
    port = connection.get("port", 3389)
    username = connection.get("username", "")

    if username and password:
        store_credentials(hostname, port, username, password)

    rdp_path = generate_rdp_file(connection)
    launch_rdp(rdp_path)

    def _cleanup():
        if username and password:
            cleanup_credentials(hostname)
        cleanup_rdp_file(rdp_path)

    timer = threading.Timer(30.0, _cleanup)
    timer.daemon = True
    timer.start()


def ping_host(hostname: str) -> bool:
    try:
        result = subprocess.run(
            ["ping", "-n", "1", "-w", "1000", hostname],
            capture_output=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
            timeout=5,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False
