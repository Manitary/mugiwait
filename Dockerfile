FROM python:3.12-bullseye AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DEFAULT_TIMEOUT=100 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    POETRY_CACHE_DIR="/tmp/poetry_cache" \
    POETRY_HOME="/opt/poetry" \
    POETRY_NO_INTERACTION=1 \
    POETRY_VERSION="1.7.1" \
    POETRY_VIRTUALENVS_CREATE=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    PATH="$PATH:$POETRY_HOME"

RUN apt-get update && apt-get install --no-install-recommends -y \
    build-essential \
    curl

RUN python3 -m venv "$POETRY_HOME"
RUN "$POETRY_HOME"/bin/pip install poetry=="$POETRY_VERSION"

WORKDIR /app

COPY ./poetry.lock ./pyproject.toml ./README.md ./
RUN --mount=type=cache,target="$POETRY_CACHE_DIR" "$POETRY_HOME"/bin/poetry install --no-dev --no-root

FROM python:3.12-slim-bullseye AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    VIRTUAL_ENV="/app/.venv"
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

WORKDIR /app

COPY --from=builder "$VIRTUAL_ENV" "$VIRTUAL_ENV"

COPY ./.env ./
COPY ./src/ ./src/

ENTRYPOINT ["/bin/sh", "-c", "python3 src/mugiwait.py -d && tail logs/mugiwait.log"]
