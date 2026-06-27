from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Настройки user_service. Читаются из переменных окружения или файла ``.env``."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Адрес NATS.
    nats_url: str = "nats://localhost:4222"
    # Строка подключения к Postgres (async-драйвер psycopg).
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/postgres"
    # Пул соединений к БД (см. database.create_engine).
    db_pool_size: int = 20
    db_max_overflow: int = 10


# Единый экземпляр настроек на весь процесс.
settings = Settings()
