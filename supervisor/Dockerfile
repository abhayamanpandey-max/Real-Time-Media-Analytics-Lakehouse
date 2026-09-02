# Robust Dockerfile for Multi-Agent Supervisor Service
FROM python:3.12-slim

WORKDIR /app

# Ensure /tmp has standard permissions for pip temporary files
RUN mkdir -p /tmp && chmod 1777 /tmp && apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

# Install runtime dependencies first (cached by Docker)
RUN pip install --no-cache-dir fastapi uvicorn requests mcp httpx python-dotenv

# Copy application source code
COPY supervisor/ /app/supervisor/
COPY config/ /app/config/

EXPOSE 8001

CMD ["python", "-m", "uvicorn", "supervisor.app:app", "--host", "0.0.0.0", "--port", "8001"]
