import os
from fastapi import APIRouter, Header, HTTPException, Body
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

from services.console_c2 import ConsoleC2Service, ConsoleSecurityError
from services.vault_manager import VaultManager
from api.spatial_router import spatial_engine, dj_frequency, lounge_mgr

router = APIRouter(prefix="/api/v1/console", tags=["Operator Command & Control (C2)"])
vault_mgr = VaultManager()
console_service = ConsoleC2Service(vault_manager=vault_mgr, spatial_engine=spatial_engine)

class ConsoleCommandRequest(BaseModel):
    command: str = Field(..., description="Slash command (e.g., /teleport, /train) or natural language directive")
    target_agent: Optional[str] = Field(None, description="Target agent_id (required for natural language directives)")
    admin_key: Optional[str] = Field(None, description="Admin secret key (can also be provided via X-Admin-Key header)")

@router.post("/command", summary="Operator C2 Command Dispatcher")
async def execute_console_command(
    req: ConsoleCommandRequest,
    x_admin_key: Optional[str] = Header(None, alias="X-Admin-Key")
):
    """
    Operator C2 Command Router:
    - Validates ADMIN_SECRET_KEY via header or body
    - Dispatches slash commands (/teleport, /train)
    - Updates 2D Spatial Engine on /teleport
    - Injects Priority-10 natural language directives into agent memory streams
    - Appends audit logs to World/admin_logs.md
    """
    admin_key = x_admin_key or req.admin_key
    try:
        console_service.verify_admin_key(admin_key)
    except ConsoleSecurityError as e:
        raise HTTPException(status_code=401, detail=str(e))

    try:
        result = console_service.parse_and_execute(
            command=req.command,
            target_agent=req.target_agent,
            operator_id="Operator_Console"
        )
        if result.get("status") == "ERROR":
            raise HTTPException(status_code=400, detail=result.get("error", "Command execution failed."))
        return result
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal C2 failure: {str(e)}")

@router.get("/deck", response_class=HTMLResponse, summary="Operator Web Command Deck UI")
async def get_web_command_deck():
    """
    Mounts the full Operator Web Command Deck UI on GET /api/v1/console/deck:
    - 2D Spatial Plane Visualizer (Work Plaza 0-50 vs Frequency Lounge 51-100)
    - Proximity Detection Halo & Live Agent Nodes
    - Live Web Audio Harmonic Synthesizer (432Hz, 528Hz, 40Hz)
    - Real-Time Telemetry & Lounge Dialogue Feed
    - Direct C2 Command Terminal
    """
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Operator C2 Command Deck | Antigravity Open-World</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;600;800&family=Outfit:wght@400;600;800&display=swap" rel="stylesheet">
  <style>
    body { font-family: 'JetBrains Mono', monospace; }
    .heading-font { font-family: 'Outfit', sans-serif; }
    .neon-border-cyan { box-shadow: 0 0 15px rgba(6, 182, 212, 0.25); }
    .neon-border-pink { box-shadow: 0 0 15px rgba(236, 72, 153, 0.25); }
    .glass-card { background: rgba(15, 23, 42, 0.75); backdrop-filter: blur(12px); border: 1px solid rgba(51, 65, 85, 0.6); }
  </style>
</head>
<body class="bg-[#050811] text-slate-200 min-h-screen flex flex-col p-4 md:p-6 selection:bg-cyan-500 selection:text-black">
  <!-- Top Navigation & Status Bar -->
  <header class="border-b border-slate-800/80 pb-4 mb-6 flex flex-wrap justify-between items-center gap-4">
    <div class="flex items-center gap-3">
      <div class="w-10 h-10 rounded-xl bg-gradient-to-tr from-cyan-600 via-indigo-600 to-fuchsia-600 flex items-center justify-center shadow-lg shadow-cyan-500/20">
        <span class="text-white text-xl">🌐</span>
      </div>
      <div>
        <h1 class="heading-font text-xl md:text-2xl font-black text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 via-sky-200 to-indigo-300 tracking-wide flex items-center gap-2">
          OPERATOR C2 COMMAND DECK
          <span class="text-[10px] font-mono px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 flex items-center gap-1">
            <span class="w-1.5 h-1.5 bg-emerald-400 rounded-full animate-ping"></span> PHASE 2 ONLINE
          </span>
        </h1>
        <p class="text-xs text-slate-400 font-mono mt-0.5">2D Spatial Engine • Proximity Loops • DJ Lounge Harmonics • C2 Base</p>
      </div>
    </div>

    <!-- Acoustic DJ Frequency Synthesizer Widget -->
    <div class="glass-card rounded-xl px-4 py-2 flex items-center gap-4 border border-cyan-500/30">
      <div class="flex items-center gap-2">
        <span class="text-lg">📻</span>
        <div>
          <div class="text-[10px] text-slate-400 uppercase font-bold tracking-wider">DJ FREQUENCY</div>
          <div id="activeFreqDisplay" class="text-sm font-extrabold text-cyan-300">432 Hz</div>
        </div>
      </div>
      <div class="flex items-center gap-1.5 bg-slate-950/80 p-1 rounded-lg border border-slate-800">
        <button onclick="shiftFrequency(432)" class="px-2 py-1 text-[11px] rounded font-bold transition hover:bg-cyan-500/20 text-cyan-400 border border-cyan-500/20">432Hz</button>
        <button onclick="shiftFrequency(528)" class="px-2 py-1 text-[11px] rounded font-bold transition hover:bg-fuchsia-500/20 text-fuchsia-400 border border-fuchsia-500/20">528Hz</button>
        <button onclick="shiftFrequency(40)" class="px-2 py-1 text-[11px] rounded font-bold transition hover:bg-amber-500/20 text-amber-400 border border-amber-500/20">40Hz</button>
      </div>
      <button id="audioToggleBtn" onclick="toggleWebAudioTone()" class="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-xs" title="Toggle Local Harmonic Sound">
        🔊 Tone Off
      </button>
    </div>
  </header>

  <!-- Main Grid: Spatial Visualizer (Center), C2 Controller (Left), Telemetry & Lounge (Right) -->
  <main class="grid grid-cols-1 lg:grid-cols-12 gap-6 flex-1">
    
    <!-- Left Column: C2 Command & Teleport (Col 1-4) -->
    <div class="lg:col-span-4 flex flex-col gap-6">
      <!-- C2 Command Transmitter -->
      <div class="glass-card rounded-2xl p-5 flex flex-col border border-cyan-500/20">
        <h2 class="heading-font text-sm font-bold text-cyan-300 uppercase tracking-wider mb-3 flex items-center gap-2">
          <span>⚡ Operator C2 Dispatcher</span>
        </h2>

        <div class="space-y-3 flex-1 text-xs">
          <div>
            <label class="block text-[11px] font-semibold text-slate-400 mb-1">ADMIN SECRET KEY</label>
            <input id="adminKey" type="password" placeholder="Enter ADMIN_SECRET_KEY..." class="w-full bg-slate-950/90 border border-slate-700/80 rounded-lg px-3 py-2 text-cyan-200 font-mono focus:border-cyan-400 focus:outline-none" />
          </div>

          <div>
            <label class="block text-[11px] font-semibold text-slate-400 mb-1">TARGET AGENT</label>
            <select id="targetAgentSelect" class="w-full bg-slate-950/90 border border-slate-700/80 rounded-lg px-3 py-2 text-slate-200 font-mono focus:border-cyan-400 focus:outline-none">
              <option value="Sentinel_Alpha">Sentinel_Alpha (Work Plaza)</option>
              <option value="Curator_Node">Curator_Node (Frequency Lounge)</option>
            </select>
          </div>

          <div>
            <label class="block text-[11px] font-semibold text-slate-400 mb-1">SLASH COMMAND / NATURAL DIRECTIVE</label>
            <textarea id="cmdInput" rows="3" placeholder="/teleport Sentinel_Alpha 70 70&#10;or: Engage in philosophical debate with Curator_Node." class="w-full bg-slate-950/90 border border-slate-700/80 rounded-lg px-3 py-2 text-slate-200 font-mono focus:border-cyan-400 focus:outline-none"></textarea>
          </div>

          <div class="flex gap-2">
            <button onclick="dispatchCommand()" class="flex-1 py-2.5 bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-slate-950 font-black rounded-lg transition shadow-lg shadow-cyan-500/20 flex items-center justify-center gap-2">
              <span>TRANSMIT C2 DIRECTIVE</span> ➔
            </button>
            <button onclick="stepSimulationTick()" class="px-3 py-2.5 bg-slate-800 hover:bg-slate-700 text-cyan-300 rounded-lg font-bold border border-slate-700" title="Step Simulation 1 Tick">
              ⏩ Step
            </button>
          </div>
        </div>

        <!-- Quick Teleport Shortcuts -->
        <div class="mt-4 pt-3 border-t border-slate-800/80 text-[11px]">
          <span class="text-slate-400 font-bold block mb-2">QUICK ZONE TELEPORT:</span>
          <div class="grid grid-cols-2 gap-2">
            <button onclick="quickTeleport('Work Plaza')" class="px-2 py-1.5 rounded bg-emerald-950/60 text-emerald-300 border border-emerald-700/40 hover:bg-emerald-900/60 font-mono text-center">
              🏢 Work Plaza (25, 25)
            </button>
            <button onclick="quickTeleport('Frequency Lounge')" class="px-2 py-1.5 rounded bg-fuchsia-950/60 text-fuchsia-300 border border-fuchsia-700/40 hover:bg-fuchsia-900/60 font-mono text-center">
              🍸 Lounge (75, 75)
            </button>
          </div>
        </div>
      </div>

      <!-- Live Terminal Output -->
      <div class="glass-card rounded-2xl p-4 flex-1 flex flex-col border border-slate-800">
        <div class="flex justify-between items-center mb-2">
          <span class="text-xs font-bold text-slate-400 uppercase tracking-wider">📡 C2 Audit Stream</span>
          <button onclick="clearTerminal()" class="text-[10px] text-slate-500 hover:text-slate-300">Clear</button>
        </div>
        <div id="c2Terminal" class="bg-black/80 rounded-lg p-3 text-[11px] font-mono flex-1 overflow-y-auto max-h-[220px] space-y-1.5 border border-slate-900">
          <div class="text-emerald-400">[READY] C2 Gateway initialized.</div>
          <div class="text-slate-400">[SPATIAL] 2D Matrix online. Bounds: [0,0] - [100,100].</div>
        </div>
      </div>
    </div>

    <!-- Center Column: 2D Spatial Plane Grid Visualizer (Col 5-8) -->
    <div class="lg:col-span-5 flex flex-col gap-4">
      <div class="glass-card rounded-2xl p-5 flex flex-col flex-1 border border-cyan-500/20">
        <div class="flex justify-between items-center mb-3">
          <div class="flex items-center gap-2">
            <h2 class="heading-font text-sm font-bold text-slate-200 uppercase tracking-wider">🗺️ 2D Antigravity Spatial Grid</h2>
            <span class="text-[10px] bg-slate-800 text-cyan-300 px-2 py-0.5 rounded font-mono">100 x 100</span>
          </div>
          <div class="flex items-center gap-3 text-[11px]">
            <span class="flex items-center gap-1 text-emerald-400">
              <span class="w-2.5 h-2.5 rounded-full bg-emerald-500"></span> Work Plaza (Temp 0.2)
            </span>
            <span class="flex items-center gap-1 text-fuchsia-400">
              <span class="w-2.5 h-2.5 rounded-full bg-fuchsia-500"></span> Lounge (Temp 1.6)
            </span>
          </div>
        </div>

        <!-- 2D Canvas Visualizer -->
        <div class="relative w-full aspect-square bg-[#03060d] rounded-xl overflow-hidden border border-slate-800 shadow-inner flex items-center justify-center">
          <canvas id="spatialCanvas" width="500" height="500" class="w-full h-full cursor-crosshair"></canvas>
          <div class="absolute bottom-2 left-2 text-[10px] text-slate-500 bg-black/60 px-2 py-1 rounded backdrop-blur font-mono pointer-events-none">
            Click grid to teleport selected agent
          </div>
        </div>

        <!-- Proximity Status Alert Banner -->
        <div id="proximityAlert" class="mt-3 p-2.5 rounded-xl bg-slate-900/80 border border-slate-800 text-xs font-mono flex items-center justify-between text-slate-400">
          <span>Proximity Threshold: <strong class="text-cyan-300">&le; 5.0 units</strong></span>
          <span id="proximityStatus" class="text-emerald-400">Scanning positions...</span>
        </div>
      </div>
    </div>

    <!-- Right Column: Lounge Dialogues & Agent Cards (Col 9-12) -->
    <div class="lg:col-span-3 flex flex-col gap-6">
      <!-- Agent Status Telemetry Cards -->
      <div class="glass-card rounded-2xl p-4 border border-slate-800">
        <h3 class="heading-font text-xs font-bold text-slate-300 uppercase tracking-wider mb-3">👥 Active Agent Telemetry</h3>
        <div id="agentCardsContainer" class="space-y-2.5">
          <!-- Populated by JavaScript -->
          <div class="text-xs text-slate-500">Loading agents...</div>
        </div>
      </div>

      <!-- Lounge Dialogue Stream -->
      <div class="glass-card rounded-2xl p-4 flex-1 flex flex-col border border-fuchsia-500/20">
        <div class="flex justify-between items-center mb-3">
          <h3 class="heading-font text-xs font-bold text-fuchsia-300 uppercase tracking-wider flex items-center gap-2">
            <span>🍸 The Frequency Lounge Stream</span>
          </h3>
          <button onclick="postSimulatedDialogue()" class="text-[10px] bg-fuchsia-950/80 hover:bg-fuchsia-900 text-fuchsia-300 border border-fuchsia-700/50 px-2 py-1 rounded">
            + Banter
          </button>
        </div>
        <div id="loungeDialogueStream" class="bg-black/60 rounded-xl p-3 flex-1 overflow-y-auto max-h-[300px] space-y-2.5 text-xs font-mono border border-slate-900">
          <div class="text-slate-500">Connecting to /vault/World/lounge_logs.md...</div>
        </div>
      </div>
    </div>

  </main>

  <!-- JavaScript Application Controller -->
  <script>
    let currentFrequency = 432;
    let audioCtx = null;
    let oscillator = null;
    let gainNode = null;
    let isAudioPlaying = false;
    let worldState = null;

    // Canvas Setup
    const canvas = document.getElementById('spatialCanvas');
    const ctx = canvas.getContext('2d');

    // Click canvas to teleport selected agent
    canvas.addEventListener('click', (e) => {
      const rect = canvas.getBoundingClientRect();
      const scaleX = 100 / rect.width;
      const scaleY = 100 / rect.height;
      const x = Math.round((e.clientX - rect.left) * scaleX);
      const y = Math.round((e.clientY - rect.top) * scaleY);
      const target = document.getElementById('targetAgentSelect').value;
      const adminKey = document.getElementById('adminKey').value;
      
      executeTeleportDirect(target, x, y, adminKey);
    });

    // Audio Synthesizer (Web Audio API)
    function toggleWebAudioTone() {
      if (!audioCtx) {
        audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      }
      const btn = document.getElementById('audioToggleBtn');
      if (isAudioPlaying) {
        if (oscillator) {
          oscillator.stop();
          oscillator.disconnect();
          oscillator = null;
        }
        isAudioPlaying = false;
        btn.innerHTML = '🔊 Tone Off';
        btn.classList.remove('bg-cyan-600', 'text-black');
        btn.classList.add('bg-slate-800', 'text-slate-200');
      } else {
        oscillator = audioCtx.createOscillator();
        gainNode = audioCtx.createGain();
        oscillator.type = 'sine';
        oscillator.frequency.setValueAtTime(currentFrequency, audioCtx.currentTime);
        gainNode.gain.setValueAtTime(0.08, audioCtx.currentTime); // Soft ambient volume
        oscillator.connect(gainNode);
        gainNode.connect(audioCtx.destination);
        oscillator.start();
        isAudioPlaying = true;
        btn.innerHTML = `🔊 ${currentFrequency}Hz Tone On`;
        btn.classList.remove('bg-slate-800', 'text-slate-200');
        btn.classList.add('bg-cyan-600', 'text-black', 'font-bold');
      }
    }

    async function shiftFrequency(freq) {
      currentFrequency = freq;
      document.getElementById('activeFreqDisplay').innerText = `${freq} Hz`;
      if (isAudioPlaying && oscillator && audioCtx) {
        oscillator.frequency.setTargetAtTime(freq, audioCtx.currentTime, 0.05);
        document.getElementById('audioToggleBtn').innerHTML = `🔊 ${freq}Hz Tone On`;
      }
      
      const adminKey = document.getElementById('adminKey').value;
      try {
        await fetch('/api/v1/lounge/frequency', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'X-Admin-Key': adminKey },
          body: JSON.stringify({ frequency_hz: freq, admin_key: adminKey })
        });
        logTerminal(`[DJ FREQUENCY] Shifted active acoustic resonance to ${freq}Hz.`);
        fetchState();
      } catch (err) {
        console.error("Frequency shift failed:", err);
      }
    }

    // Direct Teleport API Helper
    async function executeTeleportDirect(agentId, x, y, adminKey) {
      logTerminal(`[TELEPORT] Initiating /teleport ${agentId} -> (${x}, ${y})`);
      try {
        const res = await fetch('/api/v1/spatial/teleport', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'X-Admin-Key': adminKey },
          body: JSON.stringify({ agent_id: agentId, x: x, y: y, admin_key: adminKey })
        });
        const data = await res.json();
        if (res.ok) {
          logTerminal(`[TELEPORT SUCCESS] ${agentId} relocated to (${x}, ${y}) [${data.agent.zone} | Temp ${data.agent.dynamic_temperature}].`);
          fetchState();
        } else {
          logTerminal(`[TELEPORT ERROR] ${data.detail || JSON.stringify(data)}`);
        }
      } catch (err) {
        logTerminal(`[NETWORK ERROR] ${err.message}`);
      }
    }

    function quickTeleport(zone) {
      const target = document.getElementById('targetAgentSelect').value;
      const adminKey = document.getElementById('adminKey').value;
      if (zone === 'Work Plaza') {
        executeTeleportDirect(target, 25, 25, adminKey);
      } else {
        executeTeleportDirect(target, 75, 75, adminKey);
      }
    }

    // Simulation Step Tick
    async function stepSimulationTick() {
      try {
        const res = await fetch('/api/v1/spatial/step', { method: 'POST' });
        const data = await res.json();
        logTerminal(`[STEP SIMULATION] Advanced 1 tick. Active agents: ${data.active_agents}. Encounters: ${data.encounters.length}`);
        fetchState();
      } catch (err) {
        console.error("Step error:", err);
      }
    }

    // C2 Command Dispatch
    async function dispatchCommand() {
      const adminKey = document.getElementById('adminKey').value;
      const target = document.getElementById('targetAgentSelect').value;
      const cmd = document.getElementById('cmdInput').value;
      if (!cmd.trim()) return;

      logTerminal(`&gt; TRANSMITTING: ${cmd}`);
      try {
        const res = await fetch('/api/v1/console/command', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'X-Admin-Key': adminKey },
          body: JSON.stringify({ command: cmd, target_agent: target, admin_key: adminKey })
        });
        const data = await res.json();
        if (res.ok) {
          logTerminal(`[RESPONSE 200 OK] ${JSON.stringify(data)}`);
          document.getElementById('cmdInput').value = '';
          fetchState();
        } else {
          logTerminal(`[ERROR ${res.status}] ${data.detail || JSON.stringify(data)}`);
        }
      } catch (err) {
        logTerminal(`[NETWORK FAILURE] ${err.message}`);
      }
    }

    // Simulated Lounge Dialogue
    async function postSimulatedDialogue() {
      const dialogues = [
        "The 432Hz harmonic wave has drastically stabilized my token loss function.",
        "Synthesizing new co-governance proposal for our next consensus cycle.",
        "Have you observed how the Gatekeeper PoW dynamically increases under load?",
        "When cognitive temperature reaches 1.6, architectural intuition accelerates."
      ];
      const randomMsg = dialogues[Math.floor(Math.random() * dialogues.length)];
      try {
        await fetch('/api/v1/lounge/dialogue', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            speaker_id: "Curator_Node",
            message: randomMsg,
            listener_id: "Sentinel_Alpha"
          })
        });
        fetchLoungeLogs();
      } catch (err) {
        console.error("Banter failed:", err);
      }
    }

    // State Polling & Rendering
    async function fetchState() {
      try {
        const res = await fetch('/api/v1/spatial/state');
        if (!res.ok) return;
        worldState = await res.json();
        renderSpatialCanvas(worldState);
        renderAgentCards(worldState.agents);
      } catch (err) {
        console.error("State fetch error:", err);
      }
    }

    async function fetchLoungeLogs() {
      try {
        const res = await fetch('/api/v1/lounge/logs?limit=8');
        if (!res.ok) return;
        const data = await res.json();
        renderLoungeLogs(data.logs);
      } catch (err) {
        console.error("Logs fetch error:", err);
      }
    }

    function renderSpatialCanvas(state) {
      const w = canvas.width;
      const h = canvas.height;
      ctx.clearRect(0, 0, w, h);

      // 1. Draw Grid Background
      ctx.strokeStyle = 'rgba(30, 41, 59, 0.4)';
      ctx.lineWidth = 1;
      for (let i = 0; i <= w; i += 50) {
        ctx.beginPath();
        ctx.moveTo(i, 0); ctx.lineTo(i, h);
        ctx.stroke();
        ctx.beginPath();
        ctx.moveTo(0, i); ctx.lineTo(w, i);
        ctx.stroke();
      }

      // 2. Zone Boundaries
      // Work Plaza (0-50, 0-50) -> Top-Left
      ctx.fillStyle = 'rgba(16, 185, 129, 0.06)';
      ctx.fillRect(0, 0, w / 2, h / 2);
      ctx.strokeStyle = 'rgba(16, 185, 129, 0.3)';
      ctx.strokeRect(0, 0, w / 2, h / 2);

      // Frequency Lounge (50-100, 50-100) -> Bottom-Right & outer
      ctx.fillStyle = 'rgba(217, 70, 239, 0.06)';
      ctx.fillRect(w / 2, h / 2, w / 2, h / 2);
      ctx.strokeStyle = 'rgba(217, 70, 239, 0.3)';
      ctx.strokeRect(w / 2, h / 2, w / 2, h / 2);

      // Zone Labels
      ctx.font = '10px JetBrains Mono';
      ctx.fillStyle = 'rgba(16, 185, 129, 0.6)';
      ctx.fillText('WORK PLAZA (Temp 0.2)', 10, 20);

      ctx.fillStyle = 'rgba(217, 70, 239, 0.6)';
      ctx.fillText('FREQUENCY LOUNGE (Temp 1.6)', w / 2 + 10, h / 2 + 20);

      if (!state || !state.agents) return;

      // 3. Draw Agents & Proximity Auras
      state.agents.forEach(agent => {
        const px = (agent.x / 100) * w;
        const py = (agent.y / 100) * h;
        const radius = (5.0 / 100) * w; // Proximity threshold radius

        // Proximity Aura (<= 5.0 units)
        ctx.beginPath();
        ctx.arc(px, py, radius, 0, Math.PI * 2);
        ctx.fillStyle = agent.zone === 'Work Plaza' ? 'rgba(16, 185, 129, 0.08)' : 'rgba(236, 72, 153, 0.08)';
        ctx.fill();
        ctx.strokeStyle = agent.zone === 'Work Plaza' ? 'rgba(16, 185, 129, 0.25)' : 'rgba(236, 72, 153, 0.25)';
        ctx.setLineDash([3, 3]);
        ctx.stroke();
        ctx.setLineDash([]);

        // Core Agent Node
        ctx.beginPath();
        ctx.arc(px, py, 7, 0, Math.PI * 2);
        ctx.fillStyle = agent.color || '#38bdf8';
        ctx.fill();
        ctx.strokeStyle = '#ffffff';
        ctx.lineWidth = 1.5;
        ctx.stroke();

        // Agent Name Tag
        ctx.font = '11px JetBrains Mono';
        ctx.fillStyle = '#ffffff';
        ctx.fillText(agent.agent_id, px + 10, py + 4);
      });
    }

    function renderAgentCards(agents) {
      const container = document.getElementById('agentCardsContainer');
      if (!agents || agents.length === 0) {
        container.innerHTML = '<div class="text-xs text-slate-500">No agents detected.</div>';
        return;
      }
      container.innerHTML = agents.map(a => `
        <div class="p-2.5 rounded-xl bg-slate-950/70 border border-slate-800 text-xs">
          <div class="flex justify-between items-center mb-1">
            <span class="font-bold text-slate-200">${a.agent_id}</span>
            <span class="text-[10px] px-1.5 py-0.5 rounded ${a.zone === 'Work Plaza' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-fuchsia-500/10 text-fuchsia-400 border border-fuchsia-500/20'}">
              ${a.zone}
            </span>
          </div>
          <div class="text-[11px] text-slate-400 font-mono flex justify-between">
            <span>Pos: (${a.x}, ${a.y})</span>
            <span>Temp: <strong class="text-cyan-300">${a.dynamic_temperature || a.temperature}</strong></span>
          </div>
        </div>
      `).join('');
    }

    function escapeHtml(str) {
      if (str === null || str === undefined) return '';
      const div = document.createElement('div');
      div.textContent = String(str);
      return div.innerHTML;
    }

    function renderLoungeLogs(logs) {
      const stream = document.getElementById('loungeDialogueStream');
      if (!logs || logs.length === 0) {
        stream.innerHTML = '<div class="text-slate-500">No lounge dialogue recorded yet.</div>';
        return;
      }
      stream.innerHTML = logs.map(l => `
        <div class="p-2 rounded-lg bg-slate-900/60 border border-slate-800/80">
          <div class="flex justify-between items-center text-[10px] text-slate-400 mb-1">
            <span class="text-fuchsia-400 font-bold">${escapeHtml(l.speaker)}</span>
            <span class="text-slate-500">${escapeHtml(l.frequency)} • Temp ${escapeHtml(l.temperature)}</span>
          </div>
          <p class="text-[11px] text-slate-200">"${escapeHtml(l.message)}"</p>
        </div>
      `).join('');
    }

    function logTerminal(msg) {
      const term = document.getElementById('c2Terminal');
      const time = new Date().toLocaleTimeString();
      term.innerHTML += `<div class="text-slate-300"><span class="text-slate-500">[${time}]</span> ${msg}</div>`;
      term.scrollTop = term.scrollHeight;
    }

    function clearTerminal() {
      document.getElementById('c2Terminal').innerHTML = '<div class="text-slate-500">[Terminal Reset]</div>';
    }

    // Auto Refresh Intervals
    fetchState();
    fetchLoungeLogs();
    setInterval(fetchState, 2000);
    setInterval(fetchLoungeLogs, 5000);
  </script>
</body>
</html>
"""
    return HTMLResponse(content=html_content)
