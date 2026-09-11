#!/usr/bin/env bash
# ==============================================================================
# Cloudflare Zero-Trust Tunnel Setup Script (Linux / macOS / WSL)
# ==============================================================================

set -euo pipefail

TUNNEL_NAME="${1:-agentworld-tunnel}"
HOSTNAME="${2:-gateway.agentworld.io}"

echo "================================================================="
echo "🌐 Cloudflare Zero-Trust Tunnel Automated Provisioning"
echo "================================================================="

if ! command -v cloudflared &> /dev/null; then
    echo "❌ cloudflared CLI not found on PATH."
    echo "👉 Install: curl -fsSL https://pkg.cloudflare.com/cloudflared-ascii.repo | sudo tee /etc/yum.repos.d/cloudflared.repo"
    echo "👉 Or brew install cloudflared"
    exit 1
fi

echo "✅ cloudflared CLI detected."

echo "🔑 Authenticating with Cloudflare Zero Trust..."
cloudflared tunnel login

echo "🛠️ Creating named tunnel '${TUNNEL_NAME}'..."
cloudflared tunnel create "${TUNNEL_NAME}"

echo "📡 Routing DNS hostname '${HOSTNAME}' to tunnel '${TUNNEL_NAME}'..."
cloudflared tunnel route dns "${TUNNEL_NAME}" "${HOSTNAME}"

echo ""
echo "🚀 Tunnel provisioning complete!"
echo "Run via Docker Compose:"
echo "  docker compose up -d"
