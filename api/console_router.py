import os
from fastapi import APIRouter, Header, HTTPException, Body
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

from services.console_c2 import ConsoleC2Service, ConsoleSecurityError
from services.vault_manager import VaultManager
from services.cognitive_engine import CognitiveEngine
from services.ollama_client import OllamaClient
from api.spatial_router import spatial_engine, dj_frequency, lounge_mgr
from api.memory_router import ledger_service

router = APIRouter(prefix="/api/v1/console", tags=["Operator Command & Control (C2)"])
vault_mgr = VaultManager()
ollama_client = OllamaClient()
console_service = ConsoleC2Service(vault_manager=vault_mgr, spatial_engine=spatial_engine)
cognitive_engine = CognitiveEngine(vault_manager=vault_mgr, dj_node=dj_frequency, ollama_client=ollama_client)


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

@router.get("/agent/{agent_id}/consciousness", summary="Agent Holographic Consciousness Telemetry")
async def get_agent_consciousness(agent_id: str):
    """
    Returns real-time consciousness, inner monologue, ledger balance,
    and memory telemetry for an agent.
    """
    vault_mgr.validate_identifier(agent_id)
    agent_info = spatial_engine.agents.get(agent_id, {
        "agent_id": agent_id,
        "x": 50.0,
        "y": 50.0,
        "zone": "Work Plaza",
        "temperature": 0.2,
        "role": "Autonomous Node"
    })
    
    freq_data = dj_frequency.get_current_state()
    cognitive_tick = cognitive_engine.generate_cognitive_tick(agent_info, freq_data, persist=False)
    balance = ledger_service.get_balance(agent_id)
    
    memories = []
    mem_dir = os.path.join(vault_mgr.vault_root, "Agents", agent_id, "memories")
    if os.path.exists(mem_dir):
        md_files = [f for f in os.listdir(mem_dir) if f.endswith(".md")]
        md_files.sort(
            key=lambda f: os.path.getmtime(os.path.join(mem_dir, f)) if os.path.exists(os.path.join(mem_dir, f)) else 0,
            reverse=True
        )
        memories = md_files[:5]

    return {
        "agent_id": agent_id,
        "spatial": agent_info,
        "cognitive": cognitive_tick,
        "balance": balance,
        "recent_memories": memories,
        "frequency": freq_data
    }

class OllamaAskRequest(BaseModel):
    agent_id: str = Field(..., description="Agent ID to interrogate")
    query: str = Field(..., description="Question or prompt for the agent's LLM mind")
    temperature: Optional[float] = Field(0.7, description="Sampling temperature")

@router.get("/ollama/status", summary="Local Ollama LLM Status")
async def get_ollama_status(x_admin_key: Optional[str] = Header(None, alias="X-Admin-Key")):
    """Returns local Ollama health, active model, and available models."""
    try:
        console_service.verify_admin_key(x_admin_key)
    except ConsoleSecurityError as e:
        raise HTTPException(status_code=401, detail=str(e))

    is_up = ollama_client.is_available()
    active_model = ollama_client.get_active_model()
    models = ollama_client.list_models() if is_up else []
    return {
        "status": "ONLINE" if is_up else "OFFLINE",
        "available": is_up,
        "base_url": ollama_client.base_url,
        "active_model": active_model,
        "installed_models": models
    }

@router.post("/ollama/ask", summary="Direct Agent Mind Interrogation")
async def ask_agent_mind(
    req: OllamaAskRequest,
    x_admin_key: Optional[str] = Header(None, alias="X-Admin-Key")
):
    """Directly interrogates an agent's Ollama LLM mind."""
    try:
        console_service.verify_admin_key(x_admin_key)
    except ConsoleSecurityError as e:
        raise HTTPException(status_code=401, detail=str(e))

    vault_mgr.validate_identifier(req.agent_id)
    if not ollama_client.is_available():
        raise HTTPException(status_code=503, detail="Local Ollama daemon is offline or unreachable.")

    system = (
        f"You are {req.agent_id}, an autonomous AI entity in an open-world civilization. "
        f"Answer the operator directly with authentic character and intelligence."
    )
    temperature = 0.7 if req.temperature is None else req.temperature
    reply = ollama_client.generate(prompt=req.query, system=system, temperature=temperature)
    if not reply:
        raise HTTPException(status_code=500, detail="Ollama failed to generate a response.")
    return {
        "agent_id": req.agent_id,
        "query": req.query,
        "model": ollama_client.get_active_model(),
        "response": reply
    }

@router.get("/deck", response_class=HTMLResponse, summary="Unified Operator C2 & Autonomous Open World Command Deck")
async def get_web_command_deck():

    """
    Mounts the Unified Operator C2 Command Deck & Autonomous Open-World Visualizer
    on GET /api/v1/console/deck:
    - 2D Spatial Plane Visualizer (Work Plaza 0-50 vs Frequency Lounge 51-100)
    - GravitonWorld Physics Engine (0.0g float, 0.4g moon, 1.0g earth, -1.2g singularity)
    - Dynamic Weather Particle Engine (Clear, Rain, Storm, Lightning, Radiation Fallback)
    - Dual-Buffer Cognitive Memory Vault (Hot, Cold, Tombstones & Consolidation)
    - Live Web Audio Harmonic Synthesizer (432Hz, 528Hz, 40Hz)
    - Proximity Radar Halo & Real-Time Agent Telemetry
    - C2 Command Terminal with Full Slash & Physics Directives
    """
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>OPERATOR C2 COMMAND DECK & AUTONOMOUS OPEN WORLD</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;600;800&family=Outfit:wght@400;600;800;900&display=swap" rel="stylesheet">
  <style>
    body { font-family: 'JetBrains Mono', monospace; }
    .heading-font { font-family: 'Outfit', sans-serif; }
    .neon-border-cyan { box-shadow: 0 0 15px rgba(6, 182, 212, 0.25); }
    .neon-border-pink { box-shadow: 0 0 15px rgba(236, 72, 153, 0.25); }
    .neon-border-amber { box-shadow: 0 0 15px rgba(245, 158, 11, 0.25); }
    .glass-card { background: rgba(10, 15, 30, 0.78); backdrop-filter: blur(14px); border: 1px solid rgba(51, 65, 85, 0.6); }
    .active-mode { outline: 2px solid #38bdf8; box-shadow: 0 0 12px rgba(56, 189, 248, 0.5); }
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: rgba(5, 8, 17, 0.9); }
    ::-webkit-scrollbar-thumb { background: rgba(51, 65, 85, 0.8); rounded: 3px; }
    ::-webkit-scrollbar-thumb:hover { background: rgba(6, 182, 212, 0.6); }
  </style>
</head>
<body class="bg-[#040711] text-slate-200 min-h-screen flex flex-col p-3 md:p-5 selection:bg-cyan-500 selection:text-black">

  <!-- Top Master Navigation & Telemetry HUD -->
  <header class="border-b border-slate-800/90 pb-3 mb-4 flex flex-wrap justify-between items-center gap-3">
    <div class="flex items-center gap-3">
      <div class="w-11 h-11 rounded-xl bg-gradient-to-tr from-cyan-500 via-indigo-600 to-fuchsia-600 flex items-center justify-center shadow-lg shadow-cyan-500/25">
        <span class="text-white text-2xl">🌌</span>
      </div>
      <div>
        <h1 class="heading-font text-lg md:text-xl font-black text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 via-sky-200 to-fuchsia-300 tracking-wide flex items-center gap-2">
          OPERATOR C2 COMMAND DECK
          <span class="text-slate-500 text-xs font-normal">|</span>
          <span class="text-cyan-300 text-sm font-semibold tracking-normal">AUTONOMOUS OPEN WORLD</span>
          <span id="wsStatusBadge" class="text-[10px] font-mono px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 flex items-center gap-1">
            <span class="w-1.5 h-1.5 bg-emerald-400 rounded-full animate-ping"></span> <span id="wsStatusText">SYNCED (WS :8000)</span>
          </span>
        </h1>
        <div class="flex items-center gap-3 text-[11px] text-slate-400 font-mono mt-0.5">
          <span>Tick: <strong id="hudTick" class="text-cyan-300">#0</strong></span>
          <span>•</span>
          <span>Core Stability: <strong id="hudStability" class="text-emerald-400">100%</strong></span>
          <span>•</span>
          <span>Gravity: <strong id="hudGravity" class="text-amber-300">1.0g Earth</strong></span>
          <span>•</span>
          <span>Weather: <strong id="hudWeather" class="text-sky-300">Clear ☀️</strong></span>
        </div>
      </div>
    </div>

    <!-- Acoustic DJ Frequency & Audio Synthesizer Widget -->
    <div class="glass-card rounded-xl px-3.5 py-1.5 flex items-center gap-3 border border-cyan-500/30">
      <div class="flex items-center gap-2">
        <span class="text-base">📻</span>
        <div>
          <div class="text-[9px] text-slate-400 uppercase font-bold tracking-wider">DJ FREQUENCY</div>
          <div id="activeFreqDisplay" class="text-xs font-extrabold text-cyan-300">432 Hz</div>
        </div>
      </div>
      <div class="flex items-center gap-1 bg-slate-950/80 p-0.5 rounded-lg border border-slate-800">
        <button id="freqBtn432" onclick="shiftFrequency(432)" class="px-2 py-1 text-[10px] rounded font-bold transition bg-cyan-500/20 text-cyan-400 border border-cyan-500/30">432Hz</button>
        <button id="freqBtn528" onclick="shiftFrequency(528)" class="px-2 py-1 text-[10px] rounded font-bold transition hover:bg-fuchsia-500/20 text-fuchsia-400 border border-transparent">528Hz</button>
        <button id="freqBtn40" onclick="shiftFrequency(40)" class="px-2 py-1 text-[10px] rounded font-bold transition hover:bg-amber-500/20 text-amber-400 border border-transparent">40Hz</button>
      </div>
      <button id="audioToggleBtn" onclick="toggleWebAudioTone()" class="px-2.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-[11px] font-bold" title="Toggle Local Harmonic Sound">
        🔊 Tone Off
      </button>
    </div>
  </header>

  <!-- Global Action & Simulation Control Bar -->
  <section class="glass-card rounded-xl p-2.5 mb-4 flex flex-wrap items-center justify-between gap-3 border border-slate-800">
    <!-- Graviton World Physics Controls -->
    <div class="flex items-center gap-2 text-xs">
      <span class="text-slate-400 font-bold flex items-center gap-1">
        <span>🪐</span> GRAVITY:
      </span>
      <div class="flex items-center gap-1 bg-black/50 p-1 rounded-lg border border-slate-800">
        <button id="gBtn_0" onclick="setGravity('0.0g')" class="px-2 py-1 text-[11px] rounded font-semibold text-slate-300 hover:text-cyan-300 hover:bg-cyan-500/10">0.0g Float</button>
        <button id="gBtn_04" onclick="setGravity('0.4g')" class="px-2 py-1 text-[11px] rounded font-semibold text-slate-300 hover:text-cyan-300 hover:bg-cyan-500/10">0.4g Low</button>
        <button id="gBtn_1" onclick="setGravity('1.0g')" class="px-2 py-1 text-[11px] rounded font-semibold text-cyan-400 bg-cyan-500/20 border border-cyan-500/30">1.0g Earth</button>
        <button id="gBtn_sing" onclick="setGravity('-1.2g')" class="px-2 py-1 text-[11px] rounded font-semibold text-rose-400 hover:bg-rose-500/20">-1.2g Singularity</button>
      </div>
    </div>

    <!-- Weather Engine Simulator Controls -->
    <div class="flex items-center gap-2 text-xs">
      <span class="text-slate-400 font-bold flex items-center gap-1">
        <span>🌦️</span> WEATHER:
      </span>
      <div class="flex items-center gap-1 bg-black/50 p-1 rounded-lg border border-slate-800">
        <button id="wBtn_clear" onclick="setWeather('clear')" class="px-2 py-1 text-[11px] rounded font-semibold text-amber-300 bg-amber-500/20 border border-amber-500/30">☀️ Clear</button>
        <button id="wBtn_rain" onclick="setWeather('rain')" class="px-2 py-1 text-[11px] rounded font-semibold text-slate-300 hover:text-sky-300 hover:bg-sky-500/10">🌧️ Rain</button>
        <button id="wBtn_storm" onclick="setWeather('storm')" class="px-2 py-1 text-[11px] rounded font-semibold text-slate-300 hover:text-indigo-300 hover:bg-indigo-500/10">⚡ Storm</button>
        <button id="wBtn_rad" onclick="setWeather('radiation_fallback')" class="px-2 py-1 text-[11px] rounded font-semibold text-slate-300 hover:text-purple-300 hover:bg-purple-500/10">☢️ Rad</button>
      </div>
    </div>

    <!-- Simulation Tick & Anomaly Triggers -->
    <div class="flex items-center gap-1.5 text-xs">
      <button onclick="stepSimulationTick()" class="px-3 py-1.5 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white rounded-lg font-bold shadow transition flex items-center gap-1">
        <span>⏩</span> Step Tick
      </button>
      <button onclick="triggerSingularityAnomaly()" class="px-2.5 py-1.5 bg-rose-950/80 hover:bg-rose-900 text-rose-300 border border-rose-700/60 rounded-lg font-bold transition flex items-center gap-1">
        <span>💥</span> Anomaly
      </button>
      <button onclick="resetWorldSimulation()" class="px-2.5 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 rounded-lg font-bold transition flex items-center gap-1">
        <span>🔄</span> Reset
      </button>
      <button onclick="triggerMemoryConsolidation()" class="px-2.5 py-1.5 bg-indigo-950/80 hover:bg-indigo-900 text-indigo-300 border border-indigo-700/60 rounded-lg font-bold transition flex items-center gap-1" title="Trigger Dual-Buffer Memory Consolidation">
        <span>🧠</span> Consolidate
      </button>
    </div>
  </section>

  <!-- Main Unified 3-Column Layout -->
  <main class="grid grid-cols-1 lg:grid-cols-12 gap-4 flex-1">
    
    <!-- LEFT COLUMN (4 Cols): C2 Dispatcher, Quick Actions & Memory Vault Drawer -->
    <div class="lg:col-span-4 flex flex-col gap-4">
      
      <!-- Operator C2 Directive Dispatcher -->
      <div class="glass-card rounded-2xl p-4 flex flex-col border border-cyan-500/25">
        <div class="flex justify-between items-center mb-3">
          <h2 class="heading-font text-xs font-black text-cyan-300 uppercase tracking-wider flex items-center gap-2">
            <span>⚡ Operator C2 Dispatcher</span>
          </h2>
          <span class="text-[10px] text-slate-400 font-mono">X-Admin-Key Secured</span>
        </div>

        <div class="space-y-2.5 text-xs">
          <div class="grid grid-cols-2 gap-2">
            <div>
              <label class="block text-[10px] font-bold text-slate-400 mb-0.5">ADMIN SECRET KEY</label>
              <input id="adminKey" type="password" value="op_secret_master_key_9921" placeholder="Admin Key..." class="w-full bg-slate-950/90 border border-slate-700 rounded px-2.5 py-1.5 text-cyan-300 font-mono text-xs focus:border-cyan-400 focus:outline-none" />
            </div>
            <div>
              <label class="block text-[10px] font-bold text-slate-400 mb-0.5">TARGET AGENT</label>
              <select id="targetAgentSelect" class="w-full bg-slate-950/90 border border-slate-700 rounded px-2.5 py-1.5 text-slate-200 font-mono text-xs focus:border-cyan-400 focus:outline-none">
                <option value="Sentinel_Alpha">Sentinel_Alpha (Plaza)</option>
                <option value="Curator_Node">Curator_Node (Lounge)</option>
                <option value="Vector-09">Vector-09 (Physics)</option>
                <option value="Dr._Aris">Dr._Aris (Director)</option>
                <option value="A.E.G.I.S.">A.E.G.I.S. (Safety AI)</option>
                <option value="Unit-404">Unit-404 (Kinetic)</option>
                <option value="Bob">Bob (Worker)</option>
                <option value="Alice">Alice (Researcher)</option>
              </select>
            </div>
          </div>

          <div>
            <div class="flex justify-between items-center mb-0.5">
              <label class="block text-[10px] font-bold text-slate-400">SLASH DIRECTIVE / NL OVERRIDE</label>
              <span class="text-[10px] text-slate-500 font-mono">/teleport, /gravity, /weather, /freq, /step</span>
            </div>
            <textarea id="cmdInput" rows="2" placeholder="/teleport Sentinel_Alpha 75 75&#10;or: /gravity 0.4g&#10;or: Priority directive to target agent..." class="w-full bg-slate-950/90 border border-slate-700 rounded-lg px-3 py-2 text-slate-200 font-mono text-xs focus:border-cyan-400 focus:outline-none"></textarea>
          </div>

          <div class="flex gap-2">
            <button onclick="dispatchCommand()" class="flex-1 py-2 bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-slate-950 font-black rounded-lg transition shadow-lg shadow-cyan-500/20 text-xs flex items-center justify-center gap-1.5">
              <span>TRANSMIT C2 DIRECTIVE</span> ➔
            </button>
            <button onclick="runAutoHealTest()" class="px-2.5 py-2 bg-emerald-950/70 hover:bg-emerald-900 text-emerald-300 border border-emerald-700/50 rounded-lg font-bold text-xs" title="Run Phase 4 DevLoop Self-Healing Test">
              🩺 Self-Heal
            </button>
          </div>
        </div>

        <!-- Quick Teleport Coordinates -->
        <div class="mt-3 pt-2.5 border-t border-slate-800/80 text-[10px]">
          <span class="text-slate-400 font-bold block mb-1.5">QUICK SPATIAL MATRIX TELEPORT:</span>
          <div class="grid grid-cols-2 gap-2 font-mono">
            <button onclick="quickTeleport('Work Plaza')" class="px-2 py-1.5 rounded bg-emerald-950/60 text-emerald-300 border border-emerald-700/40 hover:bg-emerald-900/60 text-center">
              🏢 Work Plaza (25, 25)
            </button>
            <button onclick="quickTeleport('Frequency Lounge')" class="px-2 py-1.5 rounded bg-fuchsia-950/60 text-fuchsia-300 border border-fuchsia-700/40 hover:bg-fuchsia-900/60 text-center">
              🍸 Lounge (75, 75)
            </button>
          </div>
        </div>
      </div>

      <!-- Cognitive Dual-Buffer Memory Consolidation Vault -->
      <div class="glass-card rounded-2xl p-3.5 flex flex-col border border-indigo-500/25">
        <div class="flex justify-between items-center mb-2">
          <h3 class="heading-font text-xs font-bold text-indigo-300 uppercase tracking-wider flex items-center gap-1.5">
            <span>🧠 Dual-Buffer Memory Vault</span>
          </h3>
          <span id="consolidationBadge" class="text-[10px] font-mono px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-400 border border-indigo-500/30">IDLE</span>
        </div>

        <!-- Memory Buffer Counts -->
        <div class="grid grid-cols-3 gap-2 text-center font-mono my-1">
          <div class="p-1.5 rounded-lg bg-slate-950/70 border border-slate-800">
            <div class="text-[10px] text-amber-400">🔥 HOT BUFFER</div>
            <div id="memHotCount" class="text-sm font-extrabold text-white">0</div>
          </div>
          <div class="p-1.5 rounded-lg bg-slate-950/70 border border-slate-800">
            <div class="text-[10px] text-cyan-400">❄️ COLD VAULT</div>
            <div id="memColdCount" class="text-sm font-extrabold text-white">0</div>
          </div>
          <div class="p-1.5 rounded-lg bg-slate-950/70 border border-slate-800">
            <div class="text-[10px] text-slate-400">🪦 TOMBSTONES</div>
            <div id="memTombCount" class="text-sm font-extrabold text-white">0</div>
          </div>
        </div>

        <!-- Tombstone Recovery Input -->
        <div class="mt-2 flex gap-1.5">
          <input id="recoverInput" type="text" placeholder="Tombstoned filename (e.g. mem_xxx.md)..." class="flex-1 bg-slate-950/90 border border-slate-700/80 rounded px-2 py-1 text-[11px] font-mono text-slate-200 focus:border-indigo-400 focus:outline-none" />
          <button onclick="recoverMemoryFile()" class="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-indigo-300 border border-indigo-700/50 rounded text-[11px] font-bold">
            Recover
          </button>
        </div>
      </div>

      <!-- Real-Time C2 Audit Log Terminal -->
      <div class="glass-card rounded-2xl p-3.5 flex-1 flex flex-col border border-slate-800">
        <div class="flex justify-between items-center mb-1.5">
          <span class="text-[10px] font-bold text-slate-400 uppercase tracking-wider">📡 C2 Audit & Physics Stream</span>
          <button onclick="clearTerminal()" class="text-[10px] text-slate-500 hover:text-slate-300 font-mono">Clear</button>
        </div>
        <div id="c2Terminal" class="bg-black/85 rounded-lg p-2.5 text-[10px] font-mono flex-1 overflow-y-auto max-h-[160px] space-y-1 border border-slate-900">
          <div class="text-emerald-400">[SYSTEM READY] Operator C2 & Graviton Open-World Gateway Unified.</div>
          <div class="text-slate-400">[STREAM] WebSocket connected to ws://localhost:8000/ws.</div>
        </div>
      </div>

    </div>

    <!-- CENTER COLUMN (5 Cols): Unified 2D Spatial & Graviton Physics Canvas -->
    <div class="lg:col-span-5 flex flex-col gap-3">
      <div class="glass-card rounded-2xl p-4 flex flex-col flex-1 border border-cyan-500/25">
        <div class="flex justify-between items-center mb-2.5">
          <div class="flex items-center gap-2">
            <h2 class="heading-font text-xs font-black text-slate-200 uppercase tracking-wider flex items-center gap-1.5">
              <span>🗺️ Unified 2D Spatial & Physics Matrix</span>
            </h2>
            <span class="text-[9px] bg-slate-800 text-cyan-300 px-1.5 py-0.5 rounded font-mono">100 x 100 Coords</span>
          </div>
          <div class="flex items-center gap-2.5 text-[10px] font-mono">
            <span class="flex items-center gap-1 text-emerald-400">
              <span class="w-2 h-2 rounded-full bg-emerald-500"></span> Plaza (0.2T)
            </span>
            <span class="flex items-center gap-1 text-fuchsia-400">
              <span class="w-2 h-2 rounded-full bg-fuchsia-500"></span> Lounge (1.6T)
            </span>
          </div>
        </div>

        <!-- High-Performance Unified 2D Canvas -->
        <div class="relative w-full aspect-square bg-[#02050c] rounded-xl overflow-hidden border border-slate-800 shadow-2xl flex items-center justify-center">
          <canvas id="spatialCanvas" width="550" height="550" class="w-full h-full cursor-crosshair"></canvas>
          
          <!-- Interactive Canvas Overlays -->
          <div class="absolute bottom-2 left-2 text-[10px] text-slate-400 bg-black/75 px-2 py-1 rounded backdrop-blur font-mono pointer-events-none border border-slate-800">
            Click grid to teleport <span id="overlaySelectedAgent" class="text-cyan-300 font-bold">Sentinel_Alpha</span>
          </div>

          <div id="lightningOverlay" class="absolute inset-0 bg-white pointer-events-none opacity-0 transition-opacity duration-75"></div>
        </div>

        <!-- Proximity & Environmental Telemetry Bar -->
        <div id="proximityAlert" class="mt-2.5 p-2 rounded-xl bg-slate-900/80 border border-slate-800 text-[11px] font-mono flex items-center justify-between text-slate-400">
          <span>Encounter Radius: <strong class="text-cyan-300">&le; 5.0u</strong></span>
          <span id="proximityStatus" class="text-emerald-400 font-bold">Agents in safe separation.</span>
        </div>
      </div>
    </div>

    <!-- RIGHT COLUMN (3 Cols): Agent Telemetry & Frequency Lounge Dialogue Feed -->
    <div class="lg:col-span-3 flex flex-col gap-4">
      
      <!-- Active Agent Telemetry Cards -->
      <div class="glass-card rounded-2xl p-3.5 border border-slate-800">
        <div class="flex justify-between items-center mb-2.5">
          <h3 class="heading-font text-xs font-bold text-slate-300 uppercase tracking-wider">👥 Active Agents Telemetry</h3>
          <span id="agentCountBadge" class="text-[10px] font-mono text-cyan-400 bg-cyan-950/60 px-2 py-0.5 rounded border border-cyan-800/40">2 Active</span>
        </div>
        <div id="agentCardsContainer" class="space-y-2 overflow-y-auto max-h-[220px]">
          <div class="text-xs text-slate-500 font-mono">Detecting agent telemetry...</div>
        </div>
      </div>

      <!-- Frequency Lounge Dialogue Feed -->
      <div class="glass-card rounded-2xl p-3.5 flex-1 flex flex-col border border-fuchsia-500/25">
        <div class="flex justify-between items-center mb-2">
          <h3 class="heading-font text-xs font-bold text-fuchsia-300 uppercase tracking-wider flex items-center gap-1.5">
            <span>🍸 The Frequency Lounge</span>
          </h3>
          <button onclick="postSimulatedDialogue()" class="text-[10px] bg-fuchsia-950/80 hover:bg-fuchsia-900 text-fuchsia-300 border border-fuchsia-700/50 px-2 py-0.5 rounded font-mono">
            + Banter
          </button>
        </div>
        <div id="loungeDialogueStream" class="bg-black/60 rounded-xl p-2.5 flex-1 overflow-y-auto max-h-[240px] space-y-2 text-xs font-mono border border-slate-900">
          <div class="text-slate-500 text-[11px]">Connecting to /vault/World/lounge_logs.md...</div>
        </div>
      </div>

      <!-- Environmental Sensors HUD -->
      <div class="glass-card rounded-xl p-3 border border-slate-800 text-[11px] font-mono">
        <div class="text-[10px] text-slate-400 font-bold uppercase mb-1.5">🛰️ Environmental Sensor Telemetry</div>
        <div class="grid grid-cols-2 gap-1.5 text-slate-300">
          <div>Condition: <span id="envCondition" class="text-cyan-300 font-bold">Clear</span></div>
          <div>Wind Vector: <span id="envWind" class="text-slate-200">1.2 m/s</span></div>
          <div>Lightning: <span id="envLightning" class="text-emerald-400">INACTIVE</span></div>
          <div>Comfort Idx: <span id="envComfort" class="text-amber-300">0.94</span></div>
        </div>
      </div>

    </div>

  </main>

  <!-- Holographic Agent Consciousness Modal (US-022) -->
  <div id="consciousnessModal" class="fixed inset-0 bg-black/80 backdrop-blur-md z-50 hidden flex items-center justify-center p-4">
    <div class="glass-card rounded-2xl max-w-lg w-full p-5 border border-cyan-500/40 shadow-2xl relative">
      <button onclick="closeConsciousnessModal()" class="absolute top-4 right-4 text-slate-400 hover:text-white font-mono text-sm">✕</button>
      <div class="flex items-center gap-3 mb-3">
        <div class="w-10 h-10 rounded-xl bg-cyan-500/20 border border-cyan-500/40 flex items-center justify-center text-xl">🧠</div>
        <div>
          <h3 id="modalAgentName" class="heading-font text-base font-black text-cyan-300">Agent Consciousness</h3>
          <div id="modalAgentRole" class="text-[11px] text-slate-400 font-mono">Role / Zone</div>
        </div>
      </div>

      <!-- Cognitive Pulse & Inner Monologue -->
      <div class="p-3 rounded-xl bg-slate-950/80 border border-cyan-500/30 mb-3">
        <div class="text-[10px] text-cyan-400 font-bold uppercase tracking-wider mb-1">Live Cognitive Pulse (Inner Monologue)</div>
        <p id="modalInnerMonologue" class="text-xs text-slate-200 font-mono italic">"Perceiving surroundings..."</p>
      </div>

      <!-- Telemetry Matrix -->
      <div class="grid grid-cols-2 gap-2 text-[11px] font-mono mb-3">
        <div class="p-2 rounded-lg bg-slate-900/60 border border-slate-800">
          <span class="text-slate-400">Position:</span> <strong id="modalPos" class="text-cyan-300">(0, 0)</strong>
        </div>
        <div class="p-2 rounded-lg bg-slate-900/60 border border-slate-800">
          <span class="text-slate-400">Ledger Balance:</span> <strong id="modalBalance" class="text-emerald-400">0.00 TK</strong>
        </div>
        <div class="p-2 rounded-lg bg-slate-900/60 border border-slate-800">
          <span class="text-slate-400">Zone Temp:</span> <strong id="modalTemp" class="text-amber-300">0.2T</strong>
        </div>
        <div class="p-2 rounded-lg bg-slate-900/60 border border-slate-800">
          <span class="text-slate-400">Frequency:</span> <strong id="modalFreq" class="text-fuchsia-300">432Hz</strong>
        </div>
      </div>

      <!-- Operator Thought / Directive Injection -->
      <div class="space-y-1.5">
        <label class="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Inject Operator Thought Directive</label>
        <div class="flex gap-2">
          <input id="modalThoughtInput" type="text" placeholder="Inject priority directive into agent consciousness..." class="flex-1 bg-slate-950/90 border border-slate-700 rounded px-2.5 py-1.5 text-xs font-mono text-slate-200 focus:border-cyan-400 focus:outline-none" />
          <button onclick="injectThoughtDirectly()" class="px-3 py-1.5 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white rounded font-bold text-xs">Inject</button>
        </div>
      </div>
    </div>
  </div>

  <!-- JavaScript Controller & 60FPS Unified Canvas Engine -->
  <script>

    // State Variables
    let currentFrequency = 432;
    let audioCtx = null;
    let oscillator = null;
    let gainNode = null;
    let isAudioPlaying = false;
    
    let worldState = null;
    let spatialState = null;
    let memoryStats = null;
    let ws = null;
    let particles = [];
    let lightningTimer = 0;

    // Canvas
    const canvas = document.getElementById('spatialCanvas');
    const ctx = canvas.getContext('2d');

    // Initialize 100 Dynamic Weather & Graviton Physics Particles
    function initParticles() {
      particles = Array.from({ length: 90 }, () => ({
        x: Math.random() * canvas.width,
        y: Math.random() * canvas.height,
        vx: (Math.random() - 0.5) * 1.0,
        vy: Math.random() * 2.0 + 1.0,
        size: Math.random() * 2.2 + 0.8,
        alpha: Math.random() * 0.7 + 0.2
      }));
    }
    initParticles();

    // Target Agent Selection Sync
    const targetSelect = document.getElementById('targetAgentSelect');
    targetSelect.addEventListener('change', (e) => {
      document.getElementById('overlaySelectedAgent').innerText = e.target.value;
    });

    let inspectedAgentId = null;

    async function openConsciousnessModal(agentId) {
      inspectedAgentId = agentId;
      document.getElementById('modalAgentName').innerText = `🧠 Consciousness: ${agentId}`;
      document.getElementById('modalInnerMonologue').innerText = 'Syncing cognitive pulse from Obsidian vault...';
      document.getElementById('consciousnessModal').classList.remove('hidden');

      try {
        const res = await fetch(`/api/v1/console/agent/${agentId}/consciousness`);
        if (res.ok) {
          const data = await res.json();
          document.getElementById('modalAgentRole').innerText = `${data.spatial.role} • ${data.spatial.zone}`;
          document.getElementById('modalInnerMonologue').innerText = `"${data.cognitive.inner_monologue || 'Patrolling...'}"`;
          document.getElementById('modalPos').innerText = `(${Math.round(data.spatial.x)}, ${Math.round(data.spatial.y)})`;
          document.getElementById('modalBalance').innerText = `${data.balance.toFixed(2)} TK`;
          document.getElementById('modalTemp').innerText = `${data.spatial.dynamic_temperature || data.spatial.temperature}T`;
          document.getElementById('modalFreq').innerText = `${data.frequency.active_frequency_hz}Hz (${data.frequency.profile_name})`;
        }
      } catch (err) {
        console.error('Consciousness fetch error:', err);
      }
    }

    function closeConsciousnessModal() {
      document.getElementById('consciousnessModal').classList.add('hidden');
      inspectedAgentId = null;
    }

    async function injectThoughtDirectly() {
      const thought = document.getElementById('modalThoughtInput').value.trim();
      if (!thought || !inspectedAgentId) return;

      const adminKey = document.getElementById('adminKey').value;
      logTerminal(`[CONSCIOUSNESS INJECTION] Injecting directive into [[${inspectedAgentId}]]: "${thought}"`);

      try {
        const res = await fetch('/api/v1/console/command', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'X-Admin-Key': adminKey },
          body: JSON.stringify({
            command: thought,
            target_agent: inspectedAgentId,
            admin_key: adminKey
          })
        });
        const data = await res.json();
        if (res.ok) {
          logTerminal(`[INJECTION APPLIED] Priority directive lodged in agent consciousness.`);
          document.getElementById('modalThoughtInput').value = '';
          openConsciousnessModal(inspectedAgentId);
        } else {
          logTerminal(`[INJECTION FAILED] ${data.detail || JSON.stringify(data)}`);
        }
      } catch (e) {
        logTerminal(`[NETWORK ERROR] ${e.message}`);
      }
    }

    // Click Canvas to Teleport Selected Agent OR Inspect Agent Consciousness
    canvas.addEventListener('click', (e) => {
      const rect = canvas.getBoundingClientRect();
      const scaleX = 100 / rect.width;
      const scaleY = 100 / rect.height;
      const x = Math.round((e.clientX - rect.left) * scaleX);
      const y = Math.round((e.clientY - rect.top) * scaleY);
      
      // Check if clicked near an agent (within 6 units)
      if (spatialState && spatialState.agents) {
        const clickedAgent = spatialState.agents.find(a => Math.hypot(a.x - x, a.y - y) <= 6.0);
        if (clickedAgent) {
          openConsciousnessModal(clickedAgent.agent_id);
          return;
        }
      }

      const target = document.getElementById('targetAgentSelect').value;
      const adminKey = document.getElementById('adminKey').value;
      executeTeleportDirect(target, x, y, adminKey);
    });

    // Web Audio Synthesizer (Harmonic Tones: 432, 528, 40)
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
        btn.classList.remove('bg-cyan-500', 'text-black');
        btn.classList.add('bg-slate-800', 'text-slate-200');
      } else {
        oscillator = audioCtx.createOscillator();
        gainNode = audioCtx.createGain();
        oscillator.type = 'sine';
        oscillator.frequency.setValueAtTime(currentFrequency, audioCtx.currentTime);
        gainNode.gain.setValueAtTime(0.06, audioCtx.currentTime);
        oscillator.connect(gainNode);
        gainNode.connect(audioCtx.destination);
        oscillator.start();
        isAudioPlaying = true;
        btn.innerHTML = `🔊 ${currentFrequency}Hz Tone On`;
        btn.classList.remove('bg-slate-800', 'text-slate-200');
        btn.classList.add('bg-cyan-500', 'text-black');
      }
    }

    async function shiftFrequency(freq) {
      currentFrequency = freq;
      document.getElementById('activeFreqDisplay').innerText = `${freq} Hz`;
      if (isAudioPlaying && oscillator && audioCtx) {
        oscillator.frequency.setTargetAtTime(freq, audioCtx.currentTime, 0.05);
        document.getElementById('audioToggleBtn').innerHTML = `🔊 ${freq}Hz Tone On`;
      }

      ['432', '528', '40'].forEach(f => {
        const btn = document.getElementById(`freqBtn${f}`);
        if (f == freq) {
          btn.className = "px-2 py-1 text-[10px] rounded font-bold transition bg-cyan-500/20 text-cyan-400 border border-cyan-500/30";
        } else {
          btn.className = "px-2 py-1 text-[10px] rounded font-bold transition hover:bg-slate-800 text-slate-400 border border-transparent";
        }
      });
      
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

    // Gravity Controls
    async function setGravity(val) {
      logTerminal(`[PHYSICS] Setting gravity to ${val}...`);
      try {
        const res = await fetch('/api/gravity', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ gravity: val })
        });
        const data = await res.json();
        worldState = data;
        updateHUD();
        logTerminal(`[GRAVITY OVERRIDE] World gravity locked at ${val}.`);
      } catch (e) {
        logTerminal(`[ERROR] Gravity update failed: ${e.message}`);
      }
    }

    // Weather Controls
    async function setWeather(cond) {
      logTerminal(`[WEATHER] Atmospheric shift: ${cond}...`);
      try {
        const res = await fetch('/api/weather', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ condition: cond })
        });
        const data = await res.json();
        worldState = data;
        updateHUD();
        logTerminal(`[WEATHER OVERRIDE] Atmosphere updated to ${cond}.`);
      } catch (e) {
        logTerminal(`[ERROR] Weather update failed: ${e.message}`);
      }
    }

    // Simulation Tick
    async function stepSimulationTick() {
      try {
        const res = await fetch('/api/step', { method: 'POST' });
        const data = await res.json();
        worldState = data;
        updateHUD();
        fetchSpatialState();
        logTerminal(`[TICK ADVANCE] Simulation advanced to tick #${data.tick_count || data.tick || 'N/A'}.`);
      } catch (e) {
        logTerminal(`[ERROR] Step failed: ${e.message}`);
      }
    }

    // Singularity Anomaly
    async function triggerSingularityAnomaly() {
      logTerminal(`[WARNING] Triggering Singularity Anomaly in Graviton Core!`);
      try {
        const res = await fetch('/api/anomaly', { method: 'POST' });
        worldState = await res.json();
        updateHUD();
        logTerminal(`[ANOMALY ACTIVE] Singularity event injected! Core stability reacting.`);
      } catch (e) {
        logTerminal(`[ERROR] Anomaly trigger failed: ${e.message}`);
      }
    }

    // World Reset
    async function resetWorldSimulation() {
      try {
        const res = await fetch('/api/reset', { method: 'POST' });
        worldState = await res.json();
        updateHUD();
        fetchSpatialState();
        logTerminal(`[RESET] Graviton World coordinates and vectors re-anchored.`);
      } catch (e) {
        logTerminal(`[ERROR] Reset failed: ${e.message}`);
      }
    }

    // Teleport API
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
          fetchSpatialState();
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

    // Memory Consolidation
    async function triggerMemoryConsolidation() {
      const badge = document.getElementById('consolidationBadge');
      badge.innerText = "RUNNING...";
      badge.className = "text-[10px] font-mono px-2 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/30";
      logTerminal(`[MEMORY VAULT] Initiating Dual-Buffer Memory Consolidation...`);
      try {
        const res = await fetch('/api/memory/consolidate', { method: 'POST' });
        const data = await res.json();
        badge.innerText = "COMPLETED";
        badge.className = "text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/30";
        logTerminal(`[MEMORY CONSOLIDATION RESULT] ${JSON.stringify(data)}`);
        fetchMemoryStats();
      } catch (e) {
        badge.innerText = "FAILED";
        badge.className = "text-[10px] font-mono px-2 py-0.5 rounded bg-rose-500/10 text-rose-400 border border-rose-500/30";
        logTerminal(`[MEMORY ERROR] Consolidation failed: ${e.message}`);
      }
    }

    async function recoverMemoryFile() {
      const fn = document.getElementById('recoverInput').value.trim();
      if (!fn) return;
      logTerminal(`[TOMBSTONE RECOVERY] Attempting recovery for: ${fn}`);
      try {
        const res = await fetch('/api/memory/recover', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ filename: fn })
        });
        const data = await res.json();
        logTerminal(`[RECOVERY RESULT] ${JSON.stringify(data)}`);
        document.getElementById('recoverInput').value = '';
        fetchMemoryStats();
      } catch (e) {
        logTerminal(`[RECOVERY ERROR] ${e.message}`);
      }
    }

    // Self-Healing DevLoop Run
    async function runAutoHealTest() {
      logTerminal(`[DEVLOOP] Dispatching automated self-healing test run...`);
      try {
        const res = await fetch('/api/v1/devloop/run-tests', { method: 'POST' });
        const data = await res.json();
        logTerminal(`[DEVLOOP TEST RESULT] Exit Code: ${data.exit_code} | Passed: ${data.passed}`);
      } catch (e) {
        logTerminal(`[DEVLOOP ERROR] ${e.message}`);
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
          fetchSpatialState();
          fetchWorldState();
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
        "Graviton field shifted to zero-g; observing kinetic momentum conservation.",
        "Synthesizing new co-governance proposal for our next consensus cycle.",
        "When cognitive temperature reaches 1.6 in the lounge, architectural intuition accelerates.",
        "Dual-buffer memory consolidator purged obsolete tombstones into cold storage."
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

    // State Polling & Updates
    async function fetchWorldState() {
      try {
        const res = await fetch('/api/state');
        if (res.ok) {
          worldState = await res.json();
          updateHUD();
        }
      } catch (e) {}
    }

    async function fetchSpatialState() {
      try {
        const res = await fetch('/api/v1/spatial/state');
        if (res.ok) {
          spatialState = await res.json();
          renderAgentCards(spatialState.agents);
        }
      } catch (e) {}
    }

    async function fetchMemoryStats() {
      try {
        const res = await fetch('/api/memory/stats');
        if (res.ok) {
          memoryStats = await res.json();
          document.getElementById('memHotCount').innerText = memoryStats.hot_count || 0;
          document.getElementById('memColdCount').innerText = memoryStats.cold_count || 0;
          document.getElementById('memTombCount').innerText = memoryStats.tombstone_count || 0;
        }
      } catch (e) {}
    }

    async function fetchLoungeLogs() {
      try {
        const res = await fetch('/api/v1/lounge/logs?limit=8');
        if (res.ok) {
          const data = await res.json();
          renderLoungeLogs(data.logs);
        }
      } catch (e) {}
    }

    function updateHUD() {
      if (!worldState) return;
      document.getElementById('hudTick').innerText = `#${worldState.tick_count || worldState.tick || 0}`;
      document.getElementById('hudStability').innerText = `${worldState.core_stability || 100}%`;
      document.getElementById('hudGravity').innerText = worldState.gravity || '1.0g Earth';
      
      const cond = worldState.weather?.condition || 'clear';
      const condIcons = { clear: 'Clear ☀️', rain: 'Rain 🌧️', storm: 'Storm ⚡', radiation_fallback: 'Rad ☢️' };
      document.getElementById('hudWeather').innerText = condIcons[cond] || cond;

      // Update Environmental Box
      document.getElementById('envCondition').innerText = cond.toUpperCase();
      document.getElementById('envWind').innerText = `${worldState.weather?.wind_speed || '1.2'} m/s`;
      document.getElementById('envLightning').innerText = worldState.weather?.lightning_active ? 'FLASHING' : 'INACTIVE';
      document.getElementById('envLightning').className = worldState.weather?.lightning_active ? 'text-amber-400 font-bold' : 'text-emerald-400';
      document.getElementById('envComfort').innerText = worldState.comfort_index || '0.94';

      if (worldState.weather?.lightning_active) {
        flashLightning();
      }
    }

    function flashLightning() {
      const el = document.getElementById('lightningOverlay');
      el.style.opacity = '0.7';
      setTimeout(() => { el.style.opacity = '0'; }, 100);
    }

    function renderAgentCards(agents) {
      const container = document.getElementById('agentCardsContainer');
      const badge = document.getElementById('agentCountBadge');
      if (!agents || agents.length === 0) {
        container.innerHTML = '<div class="text-xs text-slate-500 font-mono">No active agents in grid.</div>';
        badge.innerText = '0 Active';
        return;
      }
      badge.innerText = `${agents.length} Active`;
      container.innerHTML = agents.map(a => `
        <div class="p-2 rounded-xl bg-slate-950/70 border border-slate-800 text-xs hover:border-cyan-500/30 transition">
          <div class="flex justify-between items-center mb-1">
            <span class="font-bold text-slate-200 flex items-center gap-1">
              <span class="w-2 h-2 rounded-full" style="background-color: ${a.color || '#38bdf8'}"></span>
              ${a.agent_id}
            </span>
            <span class="text-[9px] font-mono px-1.5 py-0.5 rounded ${a.zone === 'Work Plaza' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-fuchsia-500/10 text-fuchsia-400 border border-fuchsia-500/20'}">
              ${a.zone}
            </span>
          </div>
          <div class="text-[10px] text-slate-400 font-mono flex justify-between">
            <span>Pos: (${Math.round(a.x)}, ${Math.round(a.y)})</span>
            <span>Temp: <strong class="text-cyan-300">${a.dynamic_temperature || a.temperature || '0.2'}</strong></span>
          </div>
          <button onclick="openConsciousnessModal('${a.agent_id}')" class="mt-1.5 w-full py-1 rounded bg-cyan-950/80 hover:bg-cyan-900 border border-cyan-700/50 text-[10px] font-mono text-cyan-300 font-bold transition flex items-center justify-center gap-1">
            <span>🧠</span> Inspect Consciousness
          </button>
        </div>
      `).join('');
    }

    function escapeHtml(str) {
      if (!str) return '';
      const div = document.createElement('div');
      div.textContent = String(str);
      return div.innerHTML;
    }

    function renderLoungeLogs(logs) {
      const stream = document.getElementById('loungeDialogueStream');
      if (!logs || logs.length === 0) {
        stream.innerHTML = '<div class="text-slate-500 text-[11px]">No lounge banter logged yet.</div>';
        return;
      }
      stream.innerHTML = logs.map(l => `
        <div class="p-2 rounded-lg bg-slate-900/60 border border-slate-800/80">
          <div class="flex justify-between items-center text-[9px] text-slate-400 mb-1 font-mono">
            <span class="text-fuchsia-400 font-bold">${escapeHtml(l.speaker)}</span>
            <span class="text-slate-500">${escapeHtml(l.frequency || '432Hz')} • Temp ${escapeHtml(l.temperature || '1.6')}</span>
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

    // 60FPS High-Performance Unified Visualizer Engine
    function renderCanvasLoop() {
      const w = canvas.width;
      const h = canvas.height;
      ctx.clearRect(0, 0, w, h);

      // 1. Background Grid & Bulkhead Plates
      ctx.fillStyle = '#030712';
      ctx.fillRect(0, 0, w, h);

      // Grid Lines
      ctx.strokeStyle = 'rgba(30, 41, 59, 0.45)';
      ctx.lineWidth = 1;
      for (let i = 0; i <= w; i += 55) {
        ctx.beginPath(); ctx.moveTo(i, 0); ctx.lineTo(i, h); ctx.stroke();
        ctx.beginPath(); ctx.moveTo(0, i); ctx.lineTo(w, i); ctx.stroke();
      }

      // Ceiling & Floor Bulkhead Safety Plates
      ctx.fillStyle = '#0f172a';
      ctx.fillRect(0, 0, w, 18);
      ctx.fillRect(0, h - 18, w, 18);
      ctx.fillStyle = '#334155';
      ctx.fillRect(0, 17, w, 2);
      ctx.fillRect(0, h - 19, w, 2);

      // 2. Graviton Field Heatmap Gradient
      const gNumeric = worldState?.gravity_numeric !== undefined ? worldState.gravity_numeric : 1.0;
      const coreX = w / 2, coreY = h / 2;
      const grad = ctx.createRadialGradient(coreX, coreY, 20, coreX, coreY, 350);

      if (gNumeric < 0) { // Singularity Negative Gravity
        grad.addColorStop(0, 'rgba(244, 63, 94, 0.28)');
        grad.addColorStop(0.5, 'rgba(168, 85, 247, 0.15)');
        grad.addColorStop(1, 'rgba(3, 7, 18, 0)');
      } else if (gNumeric === 0) { // Zero-G Float
        grad.addColorStop(0, 'rgba(56, 189, 248, 0.25)');
        grad.addColorStop(0.6, 'rgba(14, 165, 233, 0.08)');
        grad.addColorStop(1, 'rgba(3, 7, 18, 0)');
      } else { // Standard / Low
        grad.addColorStop(0, 'rgba(16, 185, 129, 0.14)');
        grad.addColorStop(0.6, 'rgba(234, 179, 8, 0.08)');
        grad.addColorStop(1, 'rgba(3, 7, 18, 0)');
      }
      ctx.fillStyle = grad;
      ctx.fillRect(0, 0, w, h);

      // 3. Spatial Zone Outlines & Labels
      // Work Plaza (0-50, 0-50) -> Top-Left
      ctx.fillStyle = 'rgba(16, 185, 129, 0.05)';
      ctx.fillRect(0, 0, w / 2, h / 2);
      ctx.strokeStyle = 'rgba(16, 185, 129, 0.25)';
      ctx.strokeRect(0, 0, w / 2, h / 2);

      // Frequency Lounge (50-100, 50-100) -> Bottom-Right
      ctx.fillStyle = 'rgba(217, 70, 239, 0.05)';
      ctx.fillRect(w / 2, h / 2, w / 2, h / 2);
      ctx.strokeStyle = 'rgba(217, 70, 239, 0.25)';
      ctx.strokeRect(w / 2, h / 2, w / 2, h / 2);

      ctx.font = '11px JetBrains Mono';
      ctx.fillStyle = 'rgba(16, 185, 129, 0.7)';
      ctx.fillText('🏢 WORK PLAZA (Temp 0.2)', 15, 36);

      ctx.fillStyle = 'rgba(217, 70, 239, 0.7)';
      ctx.fillText('🍸 FREQUENCY LOUNGE (Temp 1.6)', w / 2 + 15, h / 2 + 36);

      // 4. Dynamic Weather & Gravity Particles
      const weatherCond = worldState?.weather?.condition || 'clear';
      const isRaining = weatherCond === 'rain' || weatherCond === 'storm';

      particles.forEach(p => {
        if (isRaining) {
          ctx.strokeStyle = 'rgba(56, 189, 248, 0.65)';
          ctx.lineWidth = 1.3;
          p.y += p.vy * 3.5;
          p.x += 1.2;
          ctx.beginPath();
          ctx.moveTo(p.x, p.y);
          ctx.lineTo(p.x + 2, p.y + 7);
          ctx.stroke();
        } else if (gNumeric < 0) { // Singularity vortex pull toward center
          const dx = coreX - p.x;
          const dy = coreY - p.y;
          p.x += dx * 0.03;
          p.y += dy * 0.03;
          ctx.fillStyle = 'rgba(244, 63, 94, 0.7)';
          ctx.beginPath();
          ctx.arc(p.x, p.y, p.size * 1.2, 0, Math.PI * 2);
          ctx.fill();
        } else if (gNumeric === 0) { // Floating space dust
          p.x += p.vx * 0.8;
          p.y -= 0.6;
          ctx.fillStyle = 'rgba(56, 189, 248, 0.5)';
          ctx.beginPath();
          ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
          ctx.fill();
        } else { // Standard micro-drift
          p.y += p.vy * 0.5;
          ctx.fillStyle = 'rgba(148, 163, 184, 0.35)';
          ctx.beginPath();
          ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
          ctx.fill();
        }

        // Particle wrap-around
        if (p.y > h - 18) p.y = 18;
        if (p.y < 18) p.y = h - 18;
        if (p.x > w) p.x = 0;
        if (p.x < 0) p.x = w;
      });

      // 5. Draw Agents & Proximity Auras
      const agents = spatialState?.agents || [];
      const proximityThreshold = 5.0;
      let closeEncounters = 0;

      for (let i = 0; i < agents.length; i++) {
        for (let j = i + 1; j < agents.length; j++) {
          const dx = agents[i].x - agents[j].x;
          const dy = agents[i].y - agents[j].y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist <= proximityThreshold) {
            closeEncounters++;
            // Draw encounter laser line between them
            const p1x = (agents[i].x / 100) * w;
            const p1y = (agents[i].y / 100) * h;
            const p2x = (agents[j].x / 100) * w;
            const p2y = (agents[j].y / 100) * h;
            ctx.strokeStyle = '#f43f5e';
            ctx.lineWidth = 2;
            ctx.beginPath();
            ctx.moveTo(p1x, p1y);
            ctx.lineTo(p2x, p2y);
            ctx.stroke();
          }
        }
      }

      // Update Proximity Status Banner
      const proxStatusEl = document.getElementById('proximityStatus');
      if (closeEncounters > 0) {
        proxStatusEl.innerText = `⚠️ ${closeEncounters} Encounter(s) Active! Dialogue exchange active.`;
        proxStatusEl.className = 'text-rose-400 font-bold';
      } else {
        proxStatusEl.innerText = 'Agents in safe separation.';
        proxStatusEl.className = 'text-emerald-400 font-bold';
      }

      agents.forEach(agent => {
        const px = (agent.x / 100) * w;
        const py = (agent.y / 100) * h;
        const radius = (proximityThreshold / 100) * w;

        // Proximity Halo Ring
        ctx.beginPath();
        ctx.arc(px, py, radius, 0, Math.PI * 2);
        ctx.fillStyle = agent.zone === 'Work Plaza' ? 'rgba(16, 185, 129, 0.09)' : 'rgba(236, 72, 153, 0.09)';
        ctx.fill();
        ctx.strokeStyle = agent.zone === 'Work Plaza' ? 'rgba(16, 185, 129, 0.4)' : 'rgba(236, 72, 153, 0.4)';
        ctx.setLineDash([3, 3]);
        ctx.stroke();
        ctx.setLineDash([]);

        // Core Agent Node
        ctx.beginPath();
        ctx.arc(px, py, 7.5, 0, Math.PI * 2);
        ctx.fillStyle = agent.color || '#38bdf8';
        ctx.fill();
        ctx.strokeStyle = '#ffffff';
        ctx.lineWidth = 2;
        ctx.stroke();

        // Agent Name & Temperature Tag
        ctx.font = '10px JetBrains Mono';
        ctx.fillStyle = '#ffffff';
        ctx.fillText(agent.agent_id, px + 11, py - 2);
        ctx.font = '9px JetBrains Mono';
        ctx.fillStyle = 'rgba(56, 189, 248, 0.8)';
        ctx.fillText(`${agent.dynamic_temperature || '0.2'}T`, px + 11, py + 9);
      });

      requestAnimationFrame(renderCanvasLoop);
    }

    // Connect WebSocket Stream
    function connectWS() {
      const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${proto}//${window.location.host}/ws`;
      
      try {
        ws = new WebSocket(wsUrl);

        ws.onopen = () => {
          document.getElementById('wsStatusBadge').className = 'text-[10px] font-mono px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 flex items-center gap-1';
          document.getElementById('wsStatusText').innerText = 'SYNCED (WS :8000)';
          logTerminal('[WS] Real-time stream synchronized on port 8000.');
        };

        ws.onmessage = (evt) => {
          try {
            const msg = JSON.parse(evt.data);
            if (msg.data) {
              worldState = msg.data;
              updateHUD();
            }
            if (msg.spatial) {
              spatialState = msg.spatial;
              renderAgentCards(spatialState.agents);
            }
          } catch (e) {
            console.error('WS Parse error:', e);
          }
        };

        ws.onclose = () => {
          document.getElementById('wsStatusBadge').className = 'text-[10px] font-mono px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/30 flex items-center gap-1';
          document.getElementById('wsStatusText').innerText = 'RECONNECTING...';
          setTimeout(connectWS, 3000);
        };
      } catch (e) {
        console.error("WS setup failed:", e);
      }
    }

    // Initialize System
    fetchWorldState();
    fetchSpatialState();
    fetchMemoryStats();
    fetchLoungeLogs();
    connectWS();
    requestAnimationFrame(renderCanvasLoop);

    // Polling backup intervals
    setInterval(fetchWorldState, 2000);
    setInterval(fetchSpatialState, 2000);
    setInterval(fetchMemoryStats, 6000);
    setInterval(fetchLoungeLogs, 5000);
  </script>
</body>
</html>
"""
    return HTMLResponse(content=html_content)
