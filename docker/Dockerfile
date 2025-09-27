# Build with a context of the project root

# Install uv
FROM ghcr.io/astral-sh/uv:python3.13-alpine
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Install runtime dependencies
RUN apk add --no-cache \
  bluez # Linux Bluetooth stack \
  dbus \
  git # for pyproject.toml Git dependency \
  libffi

# Change the working directory to the `app` directory
WORKDIR /app

# Install dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project

# Copy the project into the image
ADD . /app

# Sync the project
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked

COPY docker/docker-entrypoint.sh ./
CMD ["./docker-entrypoint.sh"]
