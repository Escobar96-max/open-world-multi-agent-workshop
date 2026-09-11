# ==============================================================================
# Cloudflare Zero-Trust Tunnel Setup Script (Windows PowerShell)
# ==============================================================================

param (
    [string]$TunnelName = "agentworld-tunnel",
    [string]$Hostname = "gateway.agentworld.io"
)

Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host "🌐 Cloudflare Zero-Trust Tunnel Automated Provisioning" -ForegroundColor Cyan
Write-Host "=================================================================" -ForegroundColor Cyan

# 1. Check if cloudflared is installed
if (-not (Get-Command cloudflared -ErrorAction SilentlyContinue)) {
    Write-Host "❌ cloudflared CLI is not found on PATH." -ForegroundColor Yellow
    Write-Host "👉 Install via: winget install Cloudflare.cloudflared" -ForegroundColor Yellow
    Write-Host "👉 Or download from: https://github.com/cloudflare/cloudflared/releases" -ForegroundColor Yellow
    exit 1
}

Write-Host "✅ cloudflared CLI detected." -ForegroundColor Green

# 2. Login to Cloudflare Account
Write-Host "🔑 Authenticating with Cloudflare Zero Trust..." -ForegroundColor Cyan
cloudflared tunnel login

# 3. Create Named Tunnel
Write-Host "🛠️ Creating named tunnel '$TunnelName'..." -ForegroundColor Cyan
cloudflared tunnel create $TunnelName

# 4. Route DNS hostname to Tunnel
Write-Host "📡 Routing DNS hostname '$Hostname' to tunnel '$TunnelName'..." -ForegroundColor Cyan
cloudflared tunnel route dns $TunnelName $Hostname

Write-Host "`n🚀 Tunnel provisioning complete!" -ForegroundColor Green
Write-Host "To run the tunnel locally or via Docker Compose, execute:"
Write-Host "  docker compose up -d" -ForegroundColor Yellow
