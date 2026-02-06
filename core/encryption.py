import os
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

DEFAULT_PASSPHRASE = "RDPManager_NoMasterPassword_DefaultKey"


def _derive_key(master_password: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=480000,
    )
    return base64.urlsafe_b64encode(kdf.derive(master_password.encode()))


def encrypt_password(plain: str, master_password: str, salt: bytes) -> str:
    key = _derive_key(master_password, salt)
    f = Fernet(key)
    return f.encrypt(plain.encode()).decode()


def decrypt_password(encrypted_str: str, master_password: str, salt: bytes) -> str:
    key = _derive_key(master_password, salt)
    f = Fernet(key)
    return f.decrypt(encrypted_str.encode()).decode()


def generate_salt() -> bytes:
    return os.urandom(16)
