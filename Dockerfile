# Dockerfile for EC2 container deployment (Mock API & Synthetic Generator)
FROM python:3.12-slim

WORKDIR /app

# Install curl for healthchecks
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

# Install uv and dependencies
COPY pyproject.toml /app/
RUN pip install --no-cache-dir uv && uv pip install --system .

# Copy application source
COPY . /app

# Default port exposure
EXPOSE 8000

CMD ["python", "-m", "mock_api.app"]
