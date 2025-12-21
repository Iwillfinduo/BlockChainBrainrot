import hashlib
from typing import Tuple

import bcrypt
from ecdsa import SigningKey, SECP256k1

from config import settings

BCRYPT_COST = settings.BCRYPT_COST


def hash_password(password: str) -> bytes:
    """
    Хеширует чистый пароль.

    Возвращает хеш в виде байтов (bytes).
    """
    salt = bcrypt.gensalt(rounds=int(BCRYPT_COST))

    password_bytes = password.encode('utf-8')

    hashed_password = bcrypt.hashpw(password_bytes, salt)

    return hashed_password


def verify_password(password: str, hashed_password: bytes) -> bool:
    """
    Проверяет, соответствует ли чистый пароль данному хешу.

    Args:
        password: Чистый пароль, введенный пользователем.
        hashed_password: Хеш пароля, извлеченный из базы данных.

    Returns:
        True, если пароли совпадают, иначе False.
    """
    password_bytes = password.encode('utf-8')

    return bcrypt.checkpw(password_bytes, hashed_password)


def generate_keys() -> Tuple[str, str]:
    """
    Генерирует пару ключей (приватный, публичный).
    Возвращает в hex формате.
    """
    private_key = SigningKey.generate(curve=SECP256k1)
    public_key = private_key.get_verifying_key()

    return (
        private_key.to_string().hex(),
        public_key.to_string().hex()
    )


def get_address_from_public_key(public_key_hex: str) -> str:
    """
    Генерирует адрес из публичного ключа.
    Адрес = первые 40 символов от SHA256(public_key).
    """
    return hashlib.sha256(bytes.fromhex(public_key_hex)).hexdigest()[:40]
