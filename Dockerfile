FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=never

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl ca-certificates \
    default-libmysqlclient-dev libpq-dev pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Install uv package manager
COPY --from=ghcr.io/astral-sh/uv:0.6.8 /uv /uvx /bin/

WORKDIR /py
COPY ./pyproject.toml ./
COPY ./uv.lock ./

RUN uv sync --frozen --no-dev --no-install-project && \
    apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false \
    build-essential


WORKDIR /app
COPY ./src /app
COPY migrations /app/migrations
COPY alembic.ini /app/alembic.ini

COPY ./scripts /scripts
RUN chmod -R +x /scripts

ENV PATH="/scripts:/py/.venv/bin:$PATH"

# Expose port
EXPOSE 8000

# Run the application
CMD ["run.sh"]