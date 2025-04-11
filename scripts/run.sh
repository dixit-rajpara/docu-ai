#!/bin/sh

set -e

uv run alembic upgrade head
uv run python -m mcp_server.main