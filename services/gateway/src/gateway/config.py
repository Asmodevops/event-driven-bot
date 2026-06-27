from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Настройки gateway.

    Значения читаются из переменных окружения (имена нечувствительны к регистру:
    поле ``bot_token`` берётся из ``BOT_TOKEN``) или из файла ``.env``.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Токен бота от @BotFather.
    bot_token: str
    # Адрес NATS.
    nats_url: str = "nats://localhost:4222"
    # Анти-флуд: не чаще одного апдейта от пользователя за это число секунд.
    throttle_time: float = 0.5


# Единый экземпляр настроек на весь процесс (нужен и в декораторах, и в DI).
settings = Settings()
