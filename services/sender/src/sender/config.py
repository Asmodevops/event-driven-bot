from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Настройки sender. Читаются из переменных окружения или файла ``.env``."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Токен бота (нужен для отправки сообщений в Telegram).
    bot_token: str
    # Адрес NATS.
    nats_url: str = "nats://localhost:4222"

    # Глобальный лимит Telegram: sender_rate сообщений за sender_per секунд.
    sender_rate: float = 25
    sender_per: float = 1.1

    # Pull из JetStream: тянуть до N сообщений, ожидая не дольше T секунд.
    sender_batch_size: int = 25
    sender_batch_timeout: float = 1.1

    # Повторы при временных сбоях: сколько всего попыток доставки, затем — DLQ.
    sender_max_attempts: int = 5
    # Экспоненциальный backoff: задержка = base * 2^(попытка-1), но не больше cap.
    sender_backoff_base: float = 2.0
    sender_backoff_cap: float = 60.0

    def backoff_delay(self, attempt: int) -> float:
        """Задержка перед попыткой ``attempt`` (1 — первый повтор)."""
        return min(
            self.sender_backoff_base * 2 ** (attempt - 1), self.sender_backoff_cap
        )


# Единый экземпляр настроек на весь процесс.
settings = Settings()
