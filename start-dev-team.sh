#!/usr/bin/env bash
# Antigravity Orchestration Script (Bash)
echo "================================================================="
echo "🚀 STARTING AUTONOMOUS MULTI-AGENT WORKSPACE & SIMULATION"
echo "================================================================="

# 1. Check Python & Node
python3 --version || python --version
node --version

# 2. Check Ollama
if ! pgrep -x "ollama" > /dev/null; then
    echo "[+] Starting Ollama service..."
    ollama serve &
    sleep 3
else
    echo "[✓] Ollama service active."
fi

# 3. Start Secure Reverse Proxy Firewall
echo "[+] Starting Secure Ollama Proxy Firewall on port 11435..."
python3 ollama-secure-proxy.py || python ollama-secure-proxy.py &
sleep 2

# 4. Verify Obsidian directories
mkdir -p ./ObsidianAgentVault/01_Episodic_Logs ./ObsidianAgentVault/02_Semantic_Graph/Agents ./ObsidianAgentVault/02_Semantic_Graph/Locations ./ObsidianAgentVault/05_Learned_Sources

# 5. Start Python Web Server
echo "[+] Starting FastAPI backend on port 8080..."
python3 agent-web-server.py || python agent-web-server.py &

# 6. Start React Visualizer
if [ -d "./agent_obsidian_dashboard" ]; then
    echo "[+] Starting Frontend Visualizer..."
    cd agent_obsidian_dashboard && npm run dev &
    cd ..
fi

# 7. Run Multi-Agent Dev Cycle through Secure Proxy
python3 ollama-developer-team-v2.py || python ollama-developer-team-v2.py
echo "✨ Ecosystem initialized!"
