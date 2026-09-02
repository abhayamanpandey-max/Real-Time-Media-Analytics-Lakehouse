# Dockerfile for Multi-Agent Supervisor Service
FROM python:3.12-slim

WORKDIR /app

# Install curl for docker healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

# Copy project source
COPY . /app

# Install project and dependencies
RUN pip install --no-cache-dir .

EXPOSE 8001

CMD ["python", "-m", "uvicorn", "supervisor.app:app", "--host", "0.0.0.0", "--port", "8001"]
