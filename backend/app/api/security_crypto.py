import logging
from cryptography.fernet import Fernet
from app.config import settings

logger = logging.getLogger(__name__)

def _get_fernet() -> Fernet:
    return Fernet(settings.FERNET_KEY)

def encrypt_secret(raw_secret: str | None) -> str | None:
    """
    Encrypts a plain text API key or secret string.
    Returns Fernet token prefix string 'gAAAAA...' or None if input is empty.
    """
    if not raw_secret:
        return None
    if raw_secret.startswith("gAAAAA"):
        # Already encrypted
        return raw_secret
    try:
        f = _get_fernet()
        return f.encrypt(raw_secret.encode("utf-8")).decode("utf-8")
    except Exception as e:
        logger.error(f"Failed to encrypt secret: {e}")
        return raw_secret

def decrypt_secret(encrypted_secret: str | None) -> str | None:
    """
    Decrypts a Fernet token back to plain text.
    If the string is not encrypted (legacy plain text or mock), returns it as-is.
    """
    if not encrypted_secret:
        return None
    if not encrypted_secret.startswith("gAAAAA"):
        # Legacy plain text key or mock key
        return encrypted_secret
    try:
        f = _get_fernet()
        return f.decrypt(encrypted_secret.encode("utf-8")).decode("utf-8")
    except Exception as e:
        logger.error(f"Failed to decrypt secret token: {e}")
        return encrypted_secret
