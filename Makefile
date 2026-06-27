.DEFAULT_GOAL := help
DC = docker compose

# DOCKER
up: ## Собрать и запустить все сервисы.
	${DC} up --build -d --no-deps $(shell docker compose config --services)

down: ## Остановить и удалить все сервисы.
	${DC} down

restart: ## Перезапустить все сервисы.
	${DC} restart

build: ## Пересобрать все сервисы.
	${DC} build

full-build: ## Пересобрать все сервисы без кэша.
	${DC} build --no-cache

logs: ## Смотреть логи всех сервисов.
	${DC} logs --follow

# ЛОКАЛЬНАЯ РАЗРАБОТКА
DB_URL_LOCAL = postgresql+psycopg://postgres:postgres@localhost:5432/postgres

lint: ## Линт и форматирование всего воркспейса.
	uv run ruff check --fix . && uv run ruff format .

test: ## Запустить все тесты (integration требуют Postgres: make up).
	uv run pytest

test-unit: ## Запустить только тесты без внешних сервисов.
	uv run pytest -m "not integration"

migrate: ## Накатить миграции БД на хосте (нужна инфра: make up).
	cd packages/database && DATABASE_URL=$${DATABASE_URL:-$(DB_URL_LOCAL)} uv run alembic upgrade head

downgrade: ## Откатить миграции (по умолчанию все). Пример: make downgrade rev=-1.
	cd packages/database && DATABASE_URL=$${DATABASE_URL:-$(DB_URL_LOCAL)} uv run alembic downgrade $(or $(rev),base)

makemigration: ## Сгенерировать миграцию: make makemigration name="add something".
	cd packages/database && DATABASE_URL=$${DATABASE_URL:-$(DB_URL_LOCAL)} uv run alembic revision --autogenerate -m "$(name)"

run-gateway: ## Запустить gateway на хосте (нужна инфра: make up).
	uv run --package gateway python -m gateway

run-user: ## Запустить user_service на хосте.
	uv run --package user_service python -m user_service

run-sender: ## Запустить sender на хосте.
	uv run --package sender python -m sender

# СПРАВКА
.PHONY: help
help: ## Показать это сообщение.
	@echo "Usage: make [command]"
	@echo ""
	@echo "Commands:"
	@awk 'BEGIN {FS = ":.*?## "; section=""; prev_section=""} \
		/^[#].*/ { \
			section = substr($$0, 3); \
		} \
		/^[a-zA-Z0-9_-]+:.*?## / { \
			if (section != prev_section) { \
				print ""; \
				print "\033[1;34m" section "\033[0m"; \
				prev_section = section; \
			} \
			gsub(/\\n/, "\n                      \t\t"); \
			printf " \x1b[36;1m%-28s\033[0m%s\n", $$1, $$2; \
		}' $(MAKEFILE_LIST)
