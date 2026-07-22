import os

from cryptography.fernet import Fernet, InvalidToken


class TokenEncryptionError(RuntimeError):
    """Raised when credentials cannot be encrypted or decrypted."""


def _get_fernet() -> Fernet:
    key = os.getenv("TOKEN_ENCRYPTION_KEY")

    if not key:
        raise RuntimeError(
            "TOKEN_ENCRYPTION_KEY is not configured."
        )

    try:
        return Fernet(key.encode("utf-8"))
    except (TypeError, ValueError) as exc:
        raise RuntimeError(
            "TOKEN_ENCRYPTION_KEY is invalid."
        ) from exc


def encrypt_token(plain_token: str) -> str:
    if not plain_token or not plain_token.strip():
        raise ValueError("Credential cannot be empty.")

    encrypted = _get_fernet().encrypt(
        plain_token.encode("utf-8")
    )

    return encrypted.decode("utf-8")


def decrypt_token(encrypted_token: str) -> str:
    if not encrypted_token:
        raise TokenEncryptionError(
            "Encrypted credential is empty."
        )

    try:
        decrypted = _get_fernet().decrypt(
            encrypted_token.encode("utf-8")
        )
    except InvalidToken as exc:
        raise TokenEncryptionError(
            "Stored credential could not be decrypted."
        ) from exc

    return decrypted.decode("utf-8")
