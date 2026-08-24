FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

FROM python:3.12-slim-bookworm
RUN useradd --create-home appuser
WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
COPY app/ app/
COPY alembic.ini ./
COPY alembic/ alembic/
RUN mkdir -p /app/data && chown -R appuser:appuser /app/data
USER appuser
ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
