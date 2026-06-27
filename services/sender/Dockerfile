# Контекст сборки — корень репозитория (см. docker-compose.yml).
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS builder
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

COPY pyproject.toml uv.lock ./
COPY packages/contracts/pyproject.toml packages/contracts/pyproject.toml
COPY packages/database/pyproject.toml packages/database/pyproject.toml
COPY packages/adapters/pyproject.toml packages/adapters/pyproject.toml
COPY packages/domain/pyproject.toml packages/domain/pyproject.toml
COPY services/gateway/pyproject.toml services/gateway/pyproject.toml
COPY services/user_service/pyproject.toml services/user_service/pyproject.toml
COPY services/sender/pyproject.toml services/sender/pyproject.toml
RUN uv sync --frozen --no-install-workspace --package sender

COPY packages/contracts/src packages/contracts/src
COPY packages/adapters/src packages/adapters/src
COPY services/sender/src services/sender/src
RUN uv sync --frozen --package sender

FROM python:3.13-slim
WORKDIR /app
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/packages /app/packages
COPY --from=builder /app/services/sender /app/services/sender
CMD ["python", "-m", "sender"]
