#!/bin/bash
# deploy.sh — run once on a fresh VPS to install and start VERDICT
set -e

echo "=== VERDICT Deploy Script ==="
echo ""

# Install Docker if needed
if ! command -v docker &> /dev/null; then
    echo "→ Installing Docker..."
    curl -fsSL https://get.docker.com | sh
    sudo usermod -aG docker $USER
fi

# Install Docker Compose plugin if needed
if ! docker compose version &> /dev/null; then
    echo "→ Installing Docker Compose..."
    sudo apt-get update -q
    sudo apt-get install -y docker-compose-plugin
fi

# Require API key
if [ -z "$GOOGLE_API_KEY" ]; then
    echo "ERROR: Set GOOGLE_API_KEY env var first:"
    echo "  export GOOGLE_API_KEY=AIza..."
    echo "  Get a free key at: https://aistudio.google.com"
    exit 1
fi

echo "GOOGLE_API_KEY=${GOOGLE_API_KEY}" > .env

echo "→ Pulling & building images..."
docker compose pull --ignore-pull-failures 2>/dev/null || true
docker compose build

echo "→ Starting services..."
docker compose up -d

echo "→ Waiting for services to be healthy..."
sleep 15

echo ""
echo "✓ VERDICT is live at: http://$(curl -s ifconfig.me 2>/dev/null || echo 'YOUR_SERVER_IP')"
echo ""
echo "  Seed the demo case:"
echo "  docker compose exec backend python /app/demo/scripts/seed_demo_case.py"
