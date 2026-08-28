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

# 3. Verify Obsidian directories
mkdir -p ./ObsidianAgentVault/01_Episodic_Logs ./ObsidianAgentVault/02_Semantic_Graph/Agents ./ObsidianAgentVault/02_Semantic_Graph/Locations ./ObsidianAgentVault/05_Learned_Sources

# 4. Start Python Web Server
echo "[+] Starting FastAPI backend on port 8080..."
python3 agent-web-server.py || python agent-web-server.py &

# 5. Start React Visualizer
if [ -d "./agent_obsidian_dashboard" ]; then
    echo "[+] Starting Frontend Visualizer..."
    cd agent_obsidian_dashboard && npm run dev &
    cd ..
fi

# 6. Run Multi-Agent Dev Cycle
python3 ollama-developer-team-v2.py || python ollama-developer-team-v2.py
echo "✨ Ecosystem initialized!"
