# Antigravity Orchestration Script (PowerShell)
# One-click setup and launch for Autonomous Multi-Agent Workspace

Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host "🚀 STARTING AUTONOMOUS MULTI-AGENT WORKSPACE & SIMULATION" -ForegroundColor Green
Write-Host "=================================================================" -ForegroundColor Cyan

# 1. Check Python & Node
python --version
node --version

# 2. Check Ollama
$ollamaProc = Get-Process -Name ollama -ErrorAction SilentlyContinue
if (-not $ollamaProc) {
    Write-Host "[+] Booting Ollama background service..." -ForegroundColor Yellow
    Start-Process "ollama.exe"
    Start-Sleep -Seconds 3
} else {
    Write-Host "[✓] Ollama is already active (PID: $($ollamaProc.Id))." -ForegroundColor Green
}

# 3. Verify Obsidian Vault Structure
$vaultDir = Join-Path $PSScriptRoot "ObsidianAgentVault"
New-Item -ItemType Directory -Path "$vaultDir\01_Episodic_Logs", "$vaultDir\02_Semantic_Graph\Agents", "$vaultDir\02_Semantic_Graph\Locations", "$vaultDir\05_Learned_Sources" -Force | Out-Null
Write-Host "[✓] Obsidian directories confirmed at: $vaultDir" -ForegroundColor Green

# 4. Launch FastAPI Web Server in Background
Write-Host "[+] Launching FastAPI WebSocket server (localhost:8080)..." -ForegroundColor Yellow
Start-Process python -ArgumentList "agent-web-server.py" -WorkingDirectory $PSScriptRoot

# 5. Launch React Visualizer (Vite)
$dashDir = Join-Path $PSScriptRoot "agent_obsidian_dashboard"
if (Test-Path $dashDir) {
    Write-Host "[+] Launching React Visualizer (localhost:5173)..." -ForegroundColor Yellow
    Start-Process npm -ArgumentList "run dev" -WorkingDirectory $dashDir
}

# 6. Execute Local Multi-Agent Dev Team
Write-Host "[+] Running Multi-Agent Development Cycle (ollama-developer-team-v2.py)..." -ForegroundColor Cyan
python "ollama-developer-team-v2.py"

Write-Host "`n=================================================================" -ForegroundColor Green
Write-Host "✨ ALL AGENT ECOSYSTEM SERVICES INITIALIZED SUCCESSFULLY!" -ForegroundColor Green
Write-Host "=================================================================" -ForegroundColor Green
