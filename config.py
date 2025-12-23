from pydantic import Field, SecretStr, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

BASE_DIR = Path(__file__).parent

class Settings(BaseSettings):
    """
    Класс конфигурации приложения.
    Автоматически загружает переменные из:
    1. Переменных окружения (ENV)
    2. Файла .env (локально)
    3. Значений по умолчанию
    """

    # --- Настройка источника загрузки ---
    model_config = SettingsConfigDict(
        # Искать .env файл в корне проекта
        env_file=BASE_DIR / '.env',
        env_file_encoding='utf-8',
        case_sensitive=True
    )

    # 1. Основные параметры приложения
    APP_NAME: str = "Crypto Registration Service"
    APP_VERSION: str = "1.0.0"
    DEBUG_MODE: bool = Field(default=False, description="Включить режим отладки FastAPI")

    # 2. Параметры безопасности
    SECRET_KEY: SecretStr = Field(
        'hot tea. I gretsya pod blanket',
        description="Ключ для подписи JWT, сессий или cookie",
    )

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 5

    DB_DIALECT: str = "sqlite"
    DB_FILE_NAME: str = Field(
        "database.db",
        description="Имя файла базы данных SQLite"
    )

    @computed_field
    @property
    def DATABASE_URL(self) -> str:
        return f"{self.DB_DIALECT}:///./{self.DB_FILE_NAME}"

    BCRYPT_COST: int = 12
    ROOT_URL: str = 'http://localhost:8000'
    PRIVATE_KEY: str = None
    PUBLIC_KEY: str = None
    ADDRESS: str = None
    ADMIN_PASSWORD: str = None
    MINING_INTERVAL: int = 300
# 💡 Использование в приложении
settings = Settings()