FROM python:3.13.4-alpine3.21 AS base

ENV PYTHONFAULTHANDLER=1 \
    PYTHONHASHSEED=random \
    PYTHONUNBUFFERED=1

WORKDIR /app

FROM base AS builder

ENV PIP_DEFAULT_TIMEOUT=100 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    POETRY_VERSION=2.1.1

RUN apk add --no-cache git \
  bluez \
  dbus
RUN pip install "poetry==$POETRY_VERSION"
RUN python -m venv /venv

COPY pyproject.toml poetry.lock ./
RUN poetry export -f requirements.txt | /venv/bin/pip install -r /dev/stdin

COPY . .
RUN poetry build && /venv/bin/pip install dist/*.whl

FROM base AS final

RUN apk add --no-cache libffi \
  libpq \
  bluez \
  dbus \
  bash
COPY --from=builder /venv /venv
COPY docker-entrypoint.sh ./
CMD ["./docker-entrypoint.sh"]
