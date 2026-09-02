# Dockerfile for EC2 container deployment (Mock API & Synthetic Generator)
FROM python:3.12-slim

WORKDIR /app

# Install curl for healthchecks
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

# Copy application source
COPY . /app

# Install minimal runtime dependencies directly
RUN pip install --no-cache-dir fastapi uvicorn requests kafka-python pydantic pyyaml numpy python-dotenv mcp httpx

EXPOSE 8000

CMD ["python", "-m", "mock_api.app"]
