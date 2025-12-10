import bcrypt
import os
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