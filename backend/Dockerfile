FROM python:3.12-slim

# No Oracle client libraries: the backend never talks SQL to Oracle (ADR-006).
# Only what psycopg and the geospatial stack need.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq5 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app
COPY pyproject.toml ./
RUN uv pip install --system --no-cache -e .

COPY . .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
