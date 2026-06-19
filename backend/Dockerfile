# Backend image: FastAPI + garminconnect, served by uvicorn.
# Uses uv for fast, reproducible installs from uv.lock.
FROM python:3.12-slim

# Copy the uv binary from its official image (no network install needed).
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Install dependencies first (cached layer) using the lockfile.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

# Then the application code.
COPY garmin_dash ./garmin_dash
RUN uv sync --frozen --no-dev

ENV PATH="/app/.venv/bin:$PATH"

# Cache + token store live on a mounted volume so they survive restarts.
ENV GARMIN_DB=/data/garmin.db \
    GARMINTOKENS=/data/tokens

EXPOSE 8000

CMD ["uvicorn", "garmin_dash.app:app", "--host", "0.0.0.0", "--port", "8000"]
