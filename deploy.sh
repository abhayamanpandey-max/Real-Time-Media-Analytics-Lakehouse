#!/usr/bin/env bash
# deploy.sh
# Deployment script for AWS EC2 ingestion host.
# Pulls latest code, builds and launches Docker containers, and validates health.

set -euo pipefail

echo "========================================="
echo "🚀 Starting Real-Time Media Analytics Deployment"
echo "========================================="

# Step 1: Pull latest code from GitHub
echo "📥 Pulling latest changes from git repository..."
git pull origin master

# Step 2: Ensure .env exists (copy from .env.example if missing)
if [ ! -f .env ]; then
  echo "⚠️ .env file not found. Creating from .env.example..."
  cp .env.example .env
fi

# Step 3: Build and bring up Docker Compose stack
echo "📦 Building and starting Docker Compose containers..."
docker compose -f docker/docker-compose.yml up -d --build

# Step 4: Health check loop (Waits for http://localhost:8000/health to return HTTP 200)
echo "🔍 Waiting for Mock API healthcheck (http://localhost:8000/health)..."

MAX_RETRIES=30
RETRY_COUNT=0
HEALTHCHECK_URL="http://localhost:8000/health"

until curl -s -f "$HEALTHCHECK_URL" > /dev/null; do
  RETRY_COUNT=$((RETRY_COUNT + 1))
  if [ "$RETRY_COUNT" -ge "$MAX_RETRIES" ]; then
    echo "❌ Deployment failed: Mock API failed to become healthy within $((MAX_RETRIES * 2)) seconds."
    echo "📋 Container logs:"
    docker compose -f docker/docker-compose.yml logs mock_api --tail=50
    exit 1
  fi
  echo "⏳ Healthcheck pending... retrying in 2 seconds ($RETRY_COUNT/$MAX_RETRIES)"
  sleep 2
done

echo "========================================="
echo "✅ Deployment Successful! Mock API is healthy and operational."
echo "🌐 Health status:"
curl -s "$HEALTHCHECK_URL"
echo ""
echo "========================================="
