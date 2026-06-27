# q_bot

Телеграм-бот, собранный из нескольких маленьких независимых сервисов, которые
общаются друг с другом через очередь сообщений (NATS). Такой подход позволяет
выдерживать нагрузку, не терять сообщения и спокойно добавлять новые функции.

## Из чего состоит

Бот разбит на три части. Каждая занимается своим делом и запускается отдельно:

1. **gateway** — «приёмная». Слушает Telegram, разбирает входящие сообщения и
   кладёт их в очередь. Сам ничего не решает по существу — только передаёт дальше.
2. **user_service** — «логика». Забирает сообщения из очереди, сохраняет
   пользователя в базу данных и кладёт в очередь ответ, который нужно отправить.
3. **sender** — «почтальон». Единственный, кто шлёт ответы в Telegram, и делает
   это аккуратно, не превышая лимиты Telegram (примерно 30 сообщений в секунду).

Между ними — очередь NATS, а данные о пользователях лежат в базе PostgreSQL.

```
Telegram ──polling──> [API Gateway] ──NATS──> [User Service] ──NATS──> [Sender] ──> Telegram
                                                      │
                                                      └──> Postgres
```

Почему так, а не одним куском: если «почтальон» перегружен или временно упал,
сообщения подождут в очереди и не потеряются; части можно обновлять и
масштабировать независимо.

## Как устроен код

- `services/` — три сервиса (`gateway`, `user_service`, `sender`).
- `packages/contracts` — общие «формы» сообщений, которыми обмениваются сервисы.
- `packages/database` — модели базы данных, репозитории и миграции (Alembic).
- `tests/` — тесты.
- `docs/wiki/` — подробная документация по архитектуре и принятым решениям.

Каждый сервис устроен одинаково: `config.py` (настройки), `ioc.py` (сборка
зависимостей), `handlers.py` (обработчики), `__main__.py` (запуск).

## Как запустить

Нужен установленный Docker.

```bash
cp env.example .env        # скопировать настройки и вписать BOT_TOKEN
make up                    # поднять всё (база, очередь, сервисы); миграции накатятся сами
make logs                  # смотреть логи
make down                  # остановить
```

Запустить отдельный сервис локально (поверх поднятой инфраструктуры):

```bash
make run-gateway   # или run-user / run-sender
```

## Команды для разработки

```bash
make test          # все тесты (часть требует поднятого Postgres)
make test-unit     # быстрые тесты без внешних сервисов
make lint          # проверка и автоформатирование кода
make migrate       # накатить миграции базы на хосте
```

Подробности об архитектуре — в [docs/wiki/implementation-plan.md](docs/wiki/implementation-plan.md).

## Сервисы

### 1. API Gateway
- Принимает **всё** от пользователя: messages, callbacks, любые апдейты.
- Старт на **polling**, позже — webhooks для продакшена.
- Лёгкий парсинг апдейта + маршрутизация: публикует распарсенное сообщение в нужный NATS subject по интенту.
- На старте — один потребитель (User Service), один кейс: `/start`.
- **НЕ ходит в БД.**

### 2. User Service (тестовый)
- Принимает запрос из очереди (напр. `/start`).
- Сохраняет пользователя в Postgres (единственный писатель в свои таблицы).
- Публикует ответное сообщение в очередь Sender через NATS + FastStream.

### 3. Sender
- **Единственный экземпляр** — глобальный страж rate-limit Telegram.
- Разгребает сообщения батчами, отправляет пользователям.
- Соблюдает лимиты: ~30 msg/s глобально, 1 msg/s на чат, ~20/min в группу.
- Stateless относительно БД.

## Архитектурные решения (по итогам обсуждения)

| # | Вопрос | Рекомендация | Статус |
|---|--------|--------------|--------|
| 0 | Layout монорепо | **uv workspace**: `packages/contracts` + `services/{gateway,user_service,sender}`, общий `uv.lock`, per-service Dockerfile | **реализовано** |
| 1 | Транспорт | **JetStream**: стримы `commands` ← `tg.cmd.>`, `outgoing` ← `tg.send.>`, `dlq` ← `tg.dlq.>`; durable pull-консьюмеры. Стримы декларируются и подписчиком, и publisher'ом — порядок старта не важен | **реализовано** |
| 2 | Идемпотентность | Дедуп по `update_id` через `Nats-Msg-Id` + окно дедупа JetStream | предложено |
| 3 | Толстый/тонкий gateway | Роутинг по subject (intent), а payload — **универсальный** распарсенный `IncomingMessage` (не тип на команду) | **реализовано** |
| 4 | 429 RetryAfter | `nack(delay=retry_after)` — переотправка с задержкой без блокирующего `sleep` | **реализовано** |
| 5 | FastStream vs Taskiq | FastStream = шина между сервисами; Taskiq = отложенные/периодические задачи | **нужно решить** |
| 6 | Контракты сообщений | Универсальные `IncomingMessage` / `IncomingCallback` (вложенные `TelegramUser`/`TelegramChat`, `update_id`, дата, текст) + `OutgoingMessage`. `contracts` без aiogram, парсинг aiogram→контракт — в gateway | **реализовано** |
| 7 | Масштабирование | Gateway-polling строго 1 инстанс; сервисы — queue group; Sender — 1 инстанс или распределённый token-bucket в Redis | предложено |
| 8 | Конфиги и DI | **pydantic-settings** (`Settings(BaseSettings)`, читает env/`.env`) + **dishka** IoC: зависимости (брокер, бот, publisher, сессия, репозиторий) собираются в `ioc.py` и внедряются «снаружи» через `FromDishka`. Интеграции: `dishka.integrations.aiogram` (gateway), `dishka_faststream` (faststream-сервисы) | **реализовано** |
| 9 | Доменный слой | Сервисы работают с **доменными сущностями** (`packages/domain`, чистые dataclass'ы), а не с моделями БД. Репозиторий в `database` мапит модель↔домен (`_to_domain`/`_to_model`) и наружу отдаёт `domain.User`. Зависимости слоёв: `domain` ← `database` ← сервис | **реализовано** |
| 10 | Транзакции (UoW) | `domain.UoW` — Protocol (`commit/flush/rollback`). Репозиторий только готовит изменения (`add`), а транзакцию фиксирует хэндлер через `uow.commit()`. Реализация UoW — сам `AsyncSession`: в DI отдаётся как `AnyOf[AsyncSession, UoW]` (один объект под двумя типами) | **реализовано** |
| 11 | Пул БД | `create_engine` с `pool_size`/`max_overflow`/`pool_pre_ping` (дефолт 20+10, из env) — дефолтные 5 малы под нагрузку | **реализовано** |
| 12 | Gateway-middleware | **Throttling** (in-memory `TTLCache`, молчаливый дроп флуда до очередей) + **SafeCallbackAnswer** (автоответ на колбэки). `UserSaver` — осознанно отложен, см. [[user-saver-idea]] | **реализовано** |
| 13 | Слой application | В каждом сервисе папка `application/` с **интеракторами** — по одному сценарию (`RegisterUser`, `AnswerCallback`, `ProcessMessage`/`ProcessCallback`, `DeliverMessage`). Зависимости приходят в `__init__` (их собирает dishka через `provide(Класс, scope=...)`), сам сценарий — `async def __call__`. Хэндлер стал тонким: транспорт (NATS/aiogram) + `set_trace_id` → зовёт интерактор. Логику можно тестировать без брокера. См. [[application-layer]] | **реализовано** |
| 14 | Лексикон и клавиатуры | Тексты для пользователя — в `lexicon.py` сервиса, inline-кнопки (подпись + `callback_data`) — в `keyboards.py`; `callback_data` вынесен в одну константу, общую для «рисую кнопку» и «обрабатываю нажатие». Клавиатуры собираются строителем `contracts.KeyboardBuilder` (chained `.button()`, раскладка `width`/`adjust`, `combine_keyboards`), который возвращает `list[list[Button]]` (без aiogram, без DI). Пока есть только у `user_service`. Реальную клавиатуру из контракта собирает sender. См. [[lexicon-keyboards]] | **реализовано** |

## Дизайн NATS (черновик)

**Subjects:**
- `tg.cmd.start` — команда /start
- `tg.msg.text` — текстовые сообщения
- `tg.callback` — callback-кнопки
- `tg.send.out` — исходящие сообщения для Sender

**Streams:** по доменам, дедуп-окно для входящих по `update_id`.

**Надёжность:** ack/nak, `max_deliver` + DLQ subject для poison-сообщений.

## Rate limiting (Sender)

- Глобальный token-bucket: 30 msg/s.
- Per-chat throttle: 1 msg/s, ключ = `chat_id`.
- Батчинг: вытянуть N, отправить с соблюдением лимитов.
- На `429` читать `retry_after`, откладывать доставку.
- При масштабировании Sender — token-bucket в Redis (распределённый).

## Контракт исходящего сообщения

`OutgoingMessage` зеркалит параметры Telegram `sendMessage`:
`chat_id`, `text`, `parse_mode`, `reply_markup`, `disable_notification`, ...
Плюс сквозной `trace_id` для наблюдаемости через все сервисы.

## Наблюдаемость

- **Сквозной `trace_id`** — *реализовано*. Рождается в gateway при приёме
  апдейта, едет в полях контрактов (`IncomingMessage`/`IncomingCallback`/
  `OutgoingMessage`/`DeadLetter`) через NATS во все сервисы. Так одно действие
  пользователя прослеживается сквозь gateway → user_service → sender.
- **Структурные логи** — *реализовано*. Общий модуль `adapters.logging`:
  `configure_logging(service)` на старте + `set_trace_id(...)` в начале обработки.
  JSON-логи (по строке на событие), `trace_id` автоматически в каждой строке
  через `ContextVar`. Формат/уровень — из окружения `LOG_JSON`/`LOG_LEVEL`
  (`LOG_JSON=0` — человекочитаемый формат для локалки). См. [[logging-tracing]].
- *Ещё не сделано:* метрики (глубина очередей, лаг консьюмеров) — по факту нужды.

## Реализовано (MVP scaffold)

```
q_bot/
├── pyproject.toml            # uv workspace (virtual root) + ruff
├── uv.lock                   # один общий lock
├── docker-compose.yml        # infra (postgres, nats, redis, pgadmin, nui) + 3 сервиса
├── env.example               # глобальный конфиг
├── nats/server.conf
├── packages/
│   ├── contracts/           # IncomingMessage/Callback, OutgoingMessage, DeadLetter, Subjects, Streams, KeyboardBuilder
│   ├── domain/              # доменные сущности (User) + UoW-протокол — без БД/фреймворков
│   ├── adapters/            # инфраструктурные хелперы (IDGenerator → uuid7)
│   └── database/            # модели, движок, репозитории (маппинг модель↔домен) + Alembic
│       ├── Dockerfile       # сервис migrations: alembic upgrade head
│       ├── alembic.ini
│       └── src/database/
│           ├── models/, base.py, engine.py
│           ├── repositories/   # UserRepository: отдаёт/принимает domain.User
│           └── migrations/     # env.py (async) + versions/
└── services/
    └── <service>/            # каждый сервис устроен одинаково:
        ├── config.py         #   Settings(BaseSettings) — настройки из env/.env
        ├── ioc.py            #   dishka-провайдеры + create_container()
        ├── handlers.py       #   роутер + тонкие хэндлеры: транспорт → интерактор
        ├── application/      #   интеракторы (сценарии бизнес-логики), без транспорта
        ├── lexicon.py        #   тексты для пользователя (где есть — пока user_service)
        ├── keyboards.py      #   inline-кнопки: подпись + callback_data (user_service)
        ├── publisher.py      #   класс-обёртка publisher'а (gateway, user_service)
        └── __main__.py       #   точка входа: собрать контейнер, включить роутер, старт
```

Сервисы: **gateway** (aiogram polling + middleware throttling/callback-answer →
стрим `commands`), **user_service** (pull `commands` → сохранить юзера → стрим
`outgoing`), **sender** (pull `outgoing` батчем → отправка с лимитом + ретрай на 429).

**Конфиги и DI:** настройки — `pydantic-settings` (поля читаются из env/`.env`,
имена нечувствительны к регистру). Зависимости собираются в `ioc.py` (dishka) и
внедряются в хэндлеры через `FromDishka` — сервис их не создаёт сам. Брокер, бот,
publisher'ы и сессия БД (scope REQUEST — на каждое сообщение) приходят из контейнера.
`Settings` передаётся в контейнер через `context`. Интеграции: `dishka.integrations.aiogram`
(gateway), `dishka_faststream` (user_service, sender).

**Поток (на JetStream):** `/start` → gateway парсит апдейт в `IncomingMessage` и публикует
в стрим `commands` → user_service (durable pull-консьюмер) достаёт `from_user`/`chat`,
сохраняет юзера через `UserRepository` и публикует `OutgoingMessage` в стрим `outgoing`
→ sender (durable pull, батч) отправляет с соблюдением лимита. При ошибке хендлера сообщение **передоставляется**
(`AckPolicy.NACK_ON_ERROR`), а не теряется.

**Транспорт:** стримы `commands` (`tg.cmd.>`), `outgoing` (`tg.send.>`) и `dlq`
(`tg.dlq.>`); имена — в `contracts.Streams`. Каждый стрим декларируется и там, где
его читают (subscriber), и там, где в него пишут (publisher) — декларация
идемпотентна, поэтому порядок старта сервисов не важен. Жизненный цикл брокера —
`start()` / `stop()`.

**Надёжность доставки (sender):** подтверждение вручную (`AckPolicy.MANUAL`),
число попыток ограничено `ConsumerConfig(max_deliver=...)`. Решение «ack или
nack(delay)» — в интеракторе `DeliverMessage` (`application/`, тестируется без
NATS), хэндлер лишь читает `num_delivered` и применяет результат. Три ветки:
- *неустранимое* (`chat not found`, бот заблокирован) → `ack`, в DLQ не кладём;
- *лимит 429* → `nack(delay=retry_after)` (без блокирующего `sleep`);
- *временное/неизвестное* → `nack` с экспоненциальным backoff
  (`base·2^(n-1)`, не больше `cap`); после `max_attempts` попыток → публикуем
  `DeadLetter` в стрим `dlq` и `ack`. Так нет hot-loop, а «мёртвые» сообщения
  сохраняются (payload + ошибка + число попыток) для ручного разбора.

**БД:** общий пакет `packages/database` (модели + репозитории + Alembic). Схема —
источник правды Alembic; в Docker сервис `migrations` гоняет `alembic upgrade head`
до старта user_service (`service_completed_successfully`). Локально — `make migrate`
/ `make makemigration name="..."`. Пока пишет только user_service (single-writer —
держим дисциплиной, пакет лишь даёт инструменты).

**Конфиг:** глобальный `.env`, каждый сервис читает свои переменные через `os.environ`.
**Запуск:** `make up` (всё в Docker) или `make run-gateway|run-user|run-sender` (локально поверх инфры).

Сознательно отложено (по принципу «не строим наперёд»): dishka (DI), taskiq,
dedup по `update_id`, per-chat throttle, DLQ + backoff.

## Тесты

`tests/` в корне (один пакет на весь воркспейс). Стек: `pytest` + `pytest-asyncio`
(`asyncio_mode=auto`). Конвенции — из заметок (Groosha): `conftest.py` с фикстурами,
`MockedBot`/`MockedSession` (`tests/mocked_aiogram.py`) вместо реального Telegram API.

- **contracts** — round-trip pydantic-моделей.
- **RateLimiter** — тайминг (burst до ёмкости, троттлинг сверх неё).
- **gateway** — `dp.feed_update(/start)` + `MockedBot`; через `TestNatsBroker`
  проверяем, что опубликован `StartCommand` (`publisher.mock`). Хэндлер вынесен в
  `gateway/handlers.py:build_router(publisher)` ради тестируемости.
- **user_service** (`@pytest.mark.integration`, нужен Postgres) — `TestNatsBroker`
  публикует `StartCommand`; проверяем запись в тестовой БД (`q_bot_test`,
  `create_all` + truncate на каждый тест, `session_factory` сервиса
  monkeypatch'им на тестовый движок) и публикацию `OutgoingMessage`. Плюс тест
  идемпотентности.
- **sender** — тестируем чистую `decide_delivery` напрямую (без NATS): успех→ack,
  неустранимая ошибка→ack без DLQ, 429→nack(retry_after), временная→nack(backoff),
  исчерпание попыток→DeadLetter в DLQ. Номер попытки передаём аргументом, т.к.
  `TestNatsBroker` не симулирует JetStream-метаданные (`num_delivered`).

Ключевой нюанс: `TestNatsBroker` сбрасывает `*.mock` на выходе из контекста —
ассерты по мокам держим **внутри** `async with TestNatsBroker(...)`. Полный
backoff→DLQ-поток (через реальный `num_delivered`) проверен живым прогоном на NATS.

Запуск: `make test` (всё) / `make test-unit` (без Postgres).
