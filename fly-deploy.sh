#!/bin/bash
# fly-deploy.sh — deploys VERDICT to Fly.io free tier
# Prerequisites: fly CLI installed (brew install flyctl or curl -L https://fly.io/install.sh | sh)
set -e

echo "=== VERDICT → Fly.io Deploy ==="
echo ""

if [ -z "$GOOGLE_API_KEY" ]; then
  echo "ERROR: export GOOGLE_API_KEY=AIza... first"
  echo "  Get a free key at: https://aistudio.google.com"
  exit 1
fi

# 1. Login
fly auth login

# 2. Provision Postgres (free 3GB)
echo "→ Creating Postgres..."
fly postgres create \
  --name verdict-db \
  --region iad \
  --initial-cluster-size 1 \
  --vm-size shared-cpu-1x \
  --volume-size 1

# 3. Provision Redis via Upstash (free 200MB)
echo "→ Creating Redis..."
fly redis create --name verdict-redis --region iad --plan free

echo ""
echo "⚠  Copy the DATABASE_URL and REDIS_URL from above, then continue."
echo "   Press ENTER when ready..."
read

read -p "DATABASE_URL: " DATABASE_URL
read -p "REDIS_URL: " REDIS_URL

# 4. Deploy MCP server first (backend depends on its URL)
echo "→ Deploying MCP server..."
fly deploy --config fly.mcp.toml --remote-only

# 5. Deploy backend with secrets
echo "→ Deploying backend..."
fly deploy --config fly.backend.toml --remote-only
fly secrets set \
  GOOGLE_API_KEY="$GOOGLE_API_KEY" \
  DATABASE_URL="$DATABASE_URL" \
  REDIS_URL="$REDIS_URL" \
  --config fly.backend.toml

# 6. Deploy frontend to Vercel (free, static)
echo ""
echo "→ Frontend: deploy to Vercel (free for static sites)"
echo "  Run: npx vercel --cwd frontend"
echo "  Set env var: VITE_API_URL=https://verdict-backend.fly.dev"
echo ""
echo "Done! Verify:"
echo "  Backend: https://verdict-backend.fly.dev/api/v1/health"
echo "  MCP:     https://verdict-mcp.fly.dev/health"
