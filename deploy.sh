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

# Step 4: Health check loop for Mock API (http://localhost:8000/health)
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
  echo "⏳ Mock API healthcheck pending... retrying in 2 seconds ($RETRY_COUNT/$MAX_RETRIES)"
  sleep 2
done

# Step 5: Health check loop for Supervisor Service (http://localhost:8001/health)
echo "🔍 Waiting for Supervisor healthcheck (http://localhost:8001/health)..."
SUPERVISOR_HEALTH_URL="http://localhost:8001/health"
RETRY_COUNT=0

until curl -s -f "$SUPERVISOR_HEALTH_URL" > /dev/null; do
  RETRY_COUNT=$((RETRY_COUNT + 1))
  if [ "$RETRY_COUNT" -ge "$MAX_RETRIES" ]; then
    echo "❌ Deployment failed: Supervisor service failed to become healthy within $((MAX_RETRIES * 2)) seconds."
    echo "📋 Container logs:"
    docker compose -f docker/docker-compose.yml logs supervisor --tail=50
    exit 1
  fi
  echo "⏳ Supervisor healthcheck pending... retrying in 2 seconds ($RETRY_COUNT/$MAX_RETRIES)"
  sleep 2
done

echo "========================================="
echo "✅ Deployment Successful! All services are healthy and operational."
echo "🌐 Mock API Health:"
curl -s "$HEALTHCHECK_URL"
echo ""
echo "🌐 Supervisor Health:"
curl -s "$SUPERVISOR_HEALTH_URL"
echo ""
echo "========================================="
