import React, { useState, useEffect, useRef, useMemo } from 'react';
import {
  Activity, Play, Pause, RotateCcw,
  Sparkles, RefreshCw, Zap, Compass, FileText, ChevronRight,
  Database, UserCheck, Flame, CloudRain, Wind, Layers, Eye,
  AlertTriangle, Radio, Navigation, Maximize2,
  CloudLightning, Sun, ShieldAlert, Cpu
} from 'lucide-react';

interface AgentState {
  id?: string;
  name?: string;
  x: number;
  y: number;
  vx?: number;
  vy?: number;
  anchored?: boolean;
  tethered_to?: string | null;
  thruster_fuel?: number;
  status?: string;
  last_action?: string;
  role?: string;
  archetype?: string;
  temperature?: number;
}

interface WorldState {
  tick?: number;
  tick_count?: number;
  location?: string;
  local_gravity?: string;
  gravity?: string;
  gravity_numeric?: number;
  core_stability?: number;
  anomaly_active?: boolean;
  weather?: {
    condition: string;
    lightning_active?: boolean;
    wind_speed?: number;
    solar_flux?: number;
  };
  objects?: Array<{ id?: string; name?: string; x: number; y: number; radius?: number; mass?: number }> | Record<string, any>;
  agents?: Record<string, AgentState> | AgentState[];
  events?: Array<{ timestamp: string; message: string; severity?: string }>;
}

export const OpenWorldVisualizer: React.FC = () => {
  const [worldState, setWorldState] = useState<WorldState | null>(null);
  const [selectedAgentId, setSelectedAgentId] = useState<string>('Bob');
  const [sidebarTab, setSidebarTab] = useState<'telemetry' | 'memory' | 'console'>('telemetry');
  const [memoryStats, setMemoryStats] = useState<any>(null);
  const [consoleInput, setConsoleInput] = useState<string>('');
  const [consoleLogs, setConsoleLogs] = useState<Array<{ text: string; type: 'info' | 'success' | 'error' }>>([
    { text: '✨ Autonomous Open World C2 Terminal Online.', type: 'info' },
    { text: '🧠 Parallel RLCD & Soup Zero RLVR Sanctum Synchronized.', type: 'success' }
  ]);
  const [rlcdTelemetry, setRlcdTelemetry] = useState<{ active?: boolean; total_distillations?: number } | null>(null);
  const [isDistilling, setIsDistilling] = useState<boolean>(false);

  // Controls & Toggles
  const [autoPlay, setAutoPlay] = useState<boolean>(true);
  const [wsConnected, setWsConnected] = useState<boolean>(false);
  const [showInfluenceOverlay, setShowInfluenceOverlay] = useState<boolean>(true);
  const [showParticleVectors, setShowParticleVectors] = useState<boolean>(true);
  const [statusMessage, setStatusMessage] = useState<string>('Connecting to WebSocket Stream...');

  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const particlesRef = useRef<Array<{ x: number; y: number; vx: number; vy: number; size: number; alpha: number }>>([]);
  const lightningFlashRef = useRef<number>(0);

  // Normalize Agents Map/List
  const normalizedAgents = useMemo(() => {
    if (!worldState || !worldState.agents) return [];
    if (Array.isArray(worldState.agents)) {
      return worldState.agents;
    }
    return Object.entries(worldState.agents).map(([id, ag]) => ({
      ...ag,
      id: ag.id || id,
      name: ag.name || id
    }));
  }, [worldState]);

  const selectedAgent = useMemo(() => {
    return normalizedAgents.find(a => (a.id || a.name) === selectedAgentId) || normalizedAgents[0] || null;
  }, [normalizedAgents, selectedAgentId]);

  // Fetch memory stats
  const fetchMemoryStats = async () => {
    try {
      const res = await fetch('/api/memory/stats');
      if (res.ok) {
        setMemoryStats(await res.json());
      }
    } catch (e) {
      // fallback
    }
  };

  useEffect(() => {
    fetchMemoryStats();
    const timer = setInterval(fetchMemoryStats, 10000);
    return () => clearInterval(timer);
  }, []);

  // WebSocket Connection Handler
  useEffect(() => {
    let ws: WebSocket | null = null;
    let reconnectTimer: any = null;
    let isDisposed = false;

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host || '127.0.0.1:8000';
    const wsUrl = `${protocol}//${host}/ws`;

    const connect = () => {
      if (isDisposed) return;
      try {
        ws = new WebSocket(wsUrl);
        wsRef.current = ws;

        ws.onopen = () => {
          if (isDisposed) return;
          setWsConnected(true);
          setStatusMessage(`⚡ Realtime WebSocket Live (${wsUrl})`);
        };

        ws.onmessage = (event) => {
          if (isDisposed) return;
          try {
            const msg = JSON.parse(event.data);
            if (msg.data) {
              setWorldState(msg.data);
              if (msg.data.weather?.lightning_active) {
                lightningFlashRef.current = 1.0;
              }
            }
            if (msg.rlcd) {
              setRlcdTelemetry(msg.rlcd);
            }
          } catch (e) {
            console.error('Error parsing WS message:', e);
          }
        };

        ws.onerror = () => {
          if (isDisposed) return;
          setWsConnected(false);
        };

        ws.onclose = () => {
          if (isDisposed) return;
          setWsConnected(false);
          setStatusMessage('WebSocket disconnected. Reconnecting in 2s...');
          reconnectTimer = setTimeout(connect, 2000);
        };
      } catch (e) {
        if (!isDisposed) {
          console.error('WebSocket connection failure:', e);
        }
      }
    };

    connect();

    // Initial fallback HTTP poll
    fetch('/api/sim/state')
      .then(res => res.json())
      .then(data => {
        if (!isDisposed && !data.error) setWorldState(data);
      })
      .catch(() => {});

    return () => {
      isDisposed = true;
      if (reconnectTimer) clearTimeout(reconnectTimer);
      if (ws) {
        ws.onopen = null;
        ws.onmessage = null;
        ws.onerror = null;
        ws.onclose = null;
        ws.close();
      }
      wsRef.current = null;
    };
  }, []);

  // Send Simulation Control Action
  const sendWsAction = async (payload: Record<string, any>) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(payload));
    } else {
      try {
        if (payload.action === 'gravity') {
          const res = await fetch('/api/gravity', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ gravity: payload.gravity || payload.value })
          });
          setWorldState(await res.json());
        } else if (payload.action === 'weather') {
          const res = await fetch('/api/weather', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ condition: payload.condition || payload.value })
          });
          setWorldState(await res.json());
        } else if (payload.action === 'anomaly') {
          const res = await fetch('/api/anomaly', { method: 'POST' });
          setWorldState(await res.json());
        } else if (payload.action === 'reset') {
          const res = await fetch('/api/reset', { method: 'POST' });
          setWorldState(await res.json());
        }
      } catch (e) {
        console.error('HTTP action fallback error:', e);
      }
    }
  };

  const handleSetGravity = (gravity: string) => sendWsAction({ action: 'gravity', gravity, value: gravity });
  const handleSetWeather = (condition: string) => sendWsAction({ action: 'weather', condition, value: condition });
  const handleTriggerAnomaly = () => sendWsAction({ action: 'anomaly' });
  const handleReset = () => sendWsAction({ action: 'reset' });

  // Execute Console Command
  const handleExecuteCommand = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!consoleInput.trim()) return;

    const cmd = consoleInput.trim();
    setConsoleLogs(prev => [...prev, { text: `> ${cmd}`, type: 'info' }]);
    setConsoleInput('');

    try {
      const res = await fetch('/api/v1/console/operator-command', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ command: cmd })
      });
      const data = await res.json();
      if (res.ok && data.status !== 'ERROR') {
        setConsoleLogs(prev => [...prev, { text: `✓ ${JSON.stringify(data)}`, type: 'success' }]);
      } else {
        setConsoleLogs(prev => [...prev, { text: `✕ ${data.error || 'Execution failed'}`, type: 'error' }]);
      }
    } catch (err: any) {
      setConsoleLogs(prev => [...prev, { text: `✕ Connection error: ${err.message}`, type: 'error' }]);
    }
  };

  // Particle System init
  useEffect(() => {
    const numParticles = 75;
    particlesRef.current = Array.from({ length: numParticles }, () => ({
      x: Math.random() * 800,
      y: Math.random() * 480,
      vx: (Math.random() - 0.5) * 0.8,
      vy: Math.random() * 1.5 + 0.5,
      size: Math.random() * 2 + 1,
      alpha: Math.random() * 0.6 + 0.2
    }));
  }, []);

  // 60FPS High Performance Open-World Canvas Renderer
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animId: number;

    const render = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      const gNumeric = worldState?.gravity_numeric !== undefined ? worldState.gravity_numeric : 1.0;
      const weather = worldState?.weather || { condition: 'clear', lightning_active: false };

      // 1. Background Grid
      ctx.fillStyle = '#050811';
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      ctx.strokeStyle = 'rgba(30, 41, 59, 0.45)';
      ctx.lineWidth = 1;
      const step = 40;
      for (let x = 0; x <= canvas.width; x += step) {
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, canvas.height);
        ctx.stroke();
      }
      for (let y = 0; y <= canvas.height; y += step) {
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(canvas.width, y);
        ctx.stroke();
      }

      // Bulkheads (Top & Bottom safety rails)
      ctx.fillStyle = '#0f172a';
      ctx.fillRect(0, 0, canvas.width, 22);
      ctx.fillRect(0, canvas.height - 22, canvas.width, 22);
      ctx.fillStyle = '#334155';
      ctx.fillRect(0, 21, canvas.width, 1);
      ctx.fillRect(0, canvas.height - 23, canvas.width, 1);

      // 2. Heatmap & Influence Overlay
      if (showInfluenceOverlay) {
        const coreX = canvas.width / 2;
        const coreY = canvas.height / 2;
        const grad = ctx.createRadialGradient(coreX, coreY, 20, coreX, coreY, 340);

        if (gNumeric < 0) {
          grad.addColorStop(0, 'rgba(239, 68, 68, 0.25)');
          grad.addColorStop(0.6, 'rgba(168, 85, 247, 0.1)');
          grad.addColorStop(1, 'rgba(5, 8, 17, 0)');
        } else if (gNumeric === 0) {
          grad.addColorStop(0, 'rgba(56, 189, 248, 0.22)');
          grad.addColorStop(0.6, 'rgba(14, 165, 233, 0.08)');
          grad.addColorStop(1, 'rgba(5, 8, 17, 0)');
        } else {
          grad.addColorStop(0, 'rgba(234, 179, 8, 0.18)');
          grad.addColorStop(0.6, 'rgba(16, 185, 129, 0.08)');
          grad.addColorStop(1, 'rgba(5, 8, 17, 0)');
        }
        ctx.fillStyle = grad;
        ctx.fillRect(0, 0, canvas.width, canvas.height);
      }

      // 3. Dynamic Rain & Kinetic Particle Vectors
      if (showParticleVectors) {
        const isRaining = weather.condition === 'rain' || weather.condition === 'storm' || weather.condition === 'lightning';
        particlesRef.current.forEach(p => {
          if (isRaining) {
            ctx.strokeStyle = 'rgba(56, 189, 248, 0.65)';
            ctx.lineWidth = 1.2;
            p.y += (p.vy * 5.0);
            p.x += 1.5;
            if (p.y > canvas.height - 24) {
              p.y = 24;
              p.x = Math.random() * canvas.width;
            }
            ctx.beginPath();
            ctx.moveTo(p.x, p.y);
            ctx.lineTo(p.x - 3, p.y - 10);
            ctx.stroke();
          } else {
            ctx.fillStyle = gNumeric < 0 ? '#f43f5e' : (gNumeric === 0 ? '#38bdf8' : '#e2e8f0');
            if (gNumeric < 0) {
              p.y -= (p.vy * 2.2 * Math.abs(gNumeric));
              if (p.y < 24) p.y = canvas.height - 30;
            } else if (gNumeric === 0) {
              p.x += p.vx * 0.8;
              p.y += (Math.sin(Date.now() * 0.002 + p.x) * 0.5);
              if (p.x < 0) p.x = canvas.width;
              if (p.x > canvas.width) p.x = 0;
              if (p.y < 30) p.y = canvas.height - 30;
            } else {
              p.y += (p.vy * 1.5 * gNumeric);
              if (p.y > canvas.height - 26) p.y = 30;
            }
            ctx.beginPath();
            ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
            ctx.fill();
          }
        });
      }

      // 4. Lightning Flash
      if (lightningFlashRef.current > 0) {
        ctx.fillStyle = `rgba(255, 255, 255, ${lightningFlashRef.current * 0.4})`;
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        ctx.strokeStyle = '#38bdf8';
        ctx.lineWidth = 3;
        ctx.beginPath();
        let lx = 200 + Math.random() * 400;
        let ly = 24;
        ctx.moveTo(lx, ly);
        while (ly < canvas.height - 30) {
          lx += (Math.random() - 0.5) * 50;
          ly += 30 + Math.random() * 30;
          ctx.lineTo(lx, ly);
        }
        ctx.stroke();
        lightningFlashRef.current = Math.max(0, lightningFlashRef.current - 0.08);
      }

      // 5. Graviton Core Singularity
      const coreX = canvas.width / 2;
      const coreY = canvas.height / 2;
      const pulseTime = Date.now() * 0.003;
      const pulseRadius = 32 + Math.sin(pulseTime) * 4;

      const coreAura = ctx.createRadialGradient(coreX, coreY, 10, coreX, coreY, pulseRadius + 25);
      coreAura.addColorStop(0, gNumeric < 0 ? 'rgba(244, 63, 94, 0.85)' : 'rgba(56, 189, 248, 0.85)');
      coreAura.addColorStop(0.6, gNumeric < 0 ? 'rgba(168, 85, 247, 0.3)' : 'rgba(14, 165, 233, 0.3)');
      coreAura.addColorStop(1, 'rgba(0, 0, 0, 0)');
      ctx.fillStyle = coreAura;
      ctx.beginPath();
      ctx.arc(coreX, coreY, pulseRadius + 25, 0, Math.PI * 2);
      ctx.fill();

      ctx.fillStyle = gNumeric < 0 ? '#f43f5e' : '#0284c7';
      ctx.beginPath();
      ctx.arc(coreX, coreY, pulseRadius, 0, Math.PI * 2);
      ctx.fill();

      // Core Label
      ctx.fillStyle = '#ffffff';
      ctx.font = 'bold 9px monospace';
      ctx.textAlign = 'center';
      ctx.fillText('GRAVITON CORE', coreX, coreY - 4);
      ctx.font = '8px monospace';
      ctx.fillStyle = '#bae6fd';
      ctx.fillText(`${worldState?.local_gravity || '1.0g'}`, coreX, coreY + 8);

      // 6. Render Floating Physical Objects
      if (worldState?.objects) {
        const objectList = Array.isArray(worldState.objects)
          ? worldState.objects
          : Object.entries(worldState.objects).map(([name, obj]) => ({
              ...(typeof obj === 'object' ? obj : {}),
              id: (obj as any)?.id || name,
              name: (obj as any)?.name || name
            }));

        objectList.forEach(obj => {
          if (obj.name === 'Graviton_Core') return;
          const rad = obj.radius || 12;
          ctx.fillStyle = '#475569';
          ctx.beginPath();
          ctx.arc(obj.x, obj.y, rad, 0, Math.PI * 2);
          ctx.fill();
          ctx.strokeStyle = '#94a3b8';
          ctx.lineWidth = 1;
          ctx.stroke();

          ctx.fillStyle = '#cbd5e1';
          ctx.font = '9px monospace';
          ctx.fillText(obj.name || 'Object', obj.x, obj.y + rad + 10);
        });
      }

      // 7. Render Autonomous Multi-Agents
      normalizedAgents.forEach(ag => {
        const isSelected = (ag.id || ag.name) === selectedAgentId;
        const agX = ag.x;
        const agY = ag.y;

        // Selection ring
        if (isSelected) {
          ctx.strokeStyle = '#38bdf8';
          ctx.lineWidth = 2;
          ctx.beginPath();
          ctx.arc(agX, agY, 22, 0, Math.PI * 2);
          ctx.stroke();
        }

        // Thruster exhaust
        if (!ag.anchored && (ag.vx || ag.vy)) {
          ctx.fillStyle = '#f59e0b';
          ctx.beginPath();
          ctx.arc(agX - (ag.vx || 0) * 3, agY - (ag.vy || 0) * 3, 5, 0, Math.PI * 2);
          ctx.fill();
        }

        // Agent body
        const agentGradient = ctx.createRadialGradient(agX - 3, agY - 3, 2, agX, agY, 14);
        if (ag.name?.includes('Orion') || ag.id?.includes('Orion')) {
          agentGradient.addColorStop(0, '#fef08a');
          agentGradient.addColorStop(1, '#ca8a04');
        } else if (ag.name?.includes('Nova') || ag.id?.includes('Nova')) {
          agentGradient.addColorStop(0, '#fbcfe8');
          agentGradient.addColorStop(1, '#db2777');
        } else if (ag.name?.includes('Architect') || ag.id?.includes('Architect')) {
          agentGradient.addColorStop(0, '#99f6e4');
          agentGradient.addColorStop(1, '#0d9488');
        } else if (ag.name?.includes('Sentinel') || ag.id?.includes('Sentinel')) {
          agentGradient.addColorStop(0, '#fecdd3');
          agentGradient.addColorStop(1, '#e11d48');
        } else {
          agentGradient.addColorStop(0, '#c7d2fe');
          agentGradient.addColorStop(1, '#4f46e5');
        }

        ctx.fillStyle = agentGradient;
        ctx.beginPath();
        ctx.arc(agX, agY, 14, 0, Math.PI * 2);
        ctx.fill();
        ctx.strokeStyle = '#ffffff';
        ctx.lineWidth = 1.5;
        ctx.stroke();

        // Agent Name
        ctx.fillStyle = '#f8fafc';
        ctx.font = 'bold 10px sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText(ag.name || ag.id || 'Agent', agX, agY - 18);

        // Fuel Bar
        const fuel = ag.thruster_fuel !== undefined ? ag.thruster_fuel : 100;
        ctx.fillStyle = '#1e293b';
        ctx.fillRect(agX - 14, agY + 16, 28, 4);
        ctx.fillStyle = fuel > 40 ? '#10b981' : '#f43f5e';
        ctx.fillRect(agX - 14, agY + 16, (28 * fuel) / 100, 4);
      });

      animId = requestAnimationFrame(render);
    };

    render();

    return () => {
      cancelAnimationFrame(animId);
    };
  }, [worldState, selectedAgentId, showInfluenceOverlay, showParticleVectors, normalizedAgents]);

  // Click on canvas to select agent
  const handleCanvasClick = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const scaleX = canvas.width / (rect.width || 1);
    const scaleY = canvas.height / (rect.height || 1);
    const clickX = (e.clientX - rect.left) * scaleX;
    const clickY = (e.clientY - rect.top) * scaleY;

    // Check if clicked near any agent
    for (const ag of normalizedAgents) {
      const dist = Math.sqrt((ag.x - clickX) ** 2 + (ag.y - clickY) ** 2);
      if (dist <= 26) {
        setSelectedAgentId(ag.id || ag.name || '');
        return;
      }
    }
  };

  return (
    <div className="flex flex-col xl:flex-row h-full w-full gap-3 overflow-hidden text-slate-200">
      {/* LEFT: 2D Canvas View & Physical Control HUD */}
      <div className="flex-1 flex flex-col bg-slate-900/70 rounded-xl border border-slate-800 p-3 shadow-xl overflow-hidden backdrop-blur-md">
        {/* Top Simulation HUD Bar */}
        <div className="flex items-center justify-between pb-2.5 border-b border-slate-800/80 mb-2">
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2">
              <span className={`h-2.5 w-2.5 rounded-full ${wsConnected ? 'bg-emerald-400 animate-pulse' : 'bg-rose-500'}`}></span>
              <span className="text-xs font-mono text-slate-300">
                Tick: <strong className="text-amber-400">#{worldState?.tick || worldState?.tick_count || 0}</strong>
              </span>
            </div>
            <span className="text-slate-600">|</span>
            <div className="text-xs text-slate-400 font-mono">
              Bay: <span className="text-cyan-300">{worldState?.location || 'Chamber 04 - Core Resonance Bay'}</span>
            </div>
            <span className="text-slate-600 hidden md:inline">|</span>
            <div className="hidden md:flex items-center gap-1.5 px-2 py-0.5 rounded bg-purple-950/50 border border-purple-800/60 text-[10px] font-mono text-purple-300">
              <Sparkles className="h-3 w-3 text-purple-400" />
              <span>RLCD: <strong className="text-purple-200">{rlcdTelemetry?.total_distillations || 0} traces</strong></span>
            </div>
            <div className="hidden lg:flex items-center gap-1.5 px-2 py-0.5 rounded bg-emerald-950/50 border border-emerald-800/60 text-[10px] font-mono text-emerald-300">
              <Zap className="h-3 w-3 text-emerald-400" />
              <span>Sanctum: [51-100] 432Hz</span>
            </div>
          </div>

          {/* Quick HUD Toggles */}
          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowInfluenceOverlay(!showInfluenceOverlay)}
              className={`px-2.5 py-1 rounded text-[11px] font-mono border transition-all flex items-center gap-1 ${
                showInfluenceOverlay ? 'bg-indigo-950/80 border-indigo-500/50 text-indigo-300' : 'bg-slate-950 border-slate-800 text-slate-400'
              }`}
            >
              <Layers className="h-3 w-3" /> Influence Map
            </button>
            <button
              onClick={() => setShowParticleVectors(!showParticleVectors)}
              className={`px-2.5 py-1 rounded text-[11px] font-mono border transition-all flex items-center gap-1 ${
                showParticleVectors ? 'bg-cyan-950/80 border-cyan-500/50 text-cyan-300' : 'bg-slate-950 border-slate-800 text-slate-400'
              }`}
            >
              <Wind className="h-3 w-3" /> Kinetic Vectors
            </button>
          </div>
        </div>

        {/* 2D Canvas Container */}
        <div className="flex-1 relative rounded-lg border border-slate-800 bg-slate-950 overflow-hidden flex items-center justify-center">
          <canvas
            ref={canvasRef}
            width={820}
            height={480}
            onClick={handleCanvasClick}
            className="w-full h-full object-contain cursor-crosshair"
          />

          {/* Floating Live Anomaly / Weather Banner */}
          {worldState?.anomaly_active && (
            <div className="absolute top-4 left-4 bg-rose-950/90 border border-rose-600/80 text-rose-200 text-xs px-3 py-1.5 rounded-md flex items-center gap-2 backdrop-blur shadow-lg animate-pulse font-mono">
              <AlertTriangle className="h-4 w-4 text-rose-400" />
              <span>SINGULARITY ANOMALY DETECTED IN GRAVITON CORE</span>
            </div>
          )}
        </div>

        {/* Bottom Simulation Control Rail */}
        <div className="pt-3 flex flex-wrap items-center justify-between gap-2 border-t border-slate-800/80 mt-2">
          {/* Gravity Control */}
          <div className="flex items-center gap-1.5 bg-slate-950 p-1 rounded-lg border border-slate-800">
            <span className="text-[10px] uppercase font-mono px-2 text-slate-400">Gravity:</span>
            {['0.0g', '0.5g', '1.0g', '2.5g'].map(g => (
              <button
                key={g}
                onClick={() => handleSetGravity(g)}
                className={`px-2 py-0.5 rounded text-xs font-mono transition-all ${
                  (worldState?.local_gravity || worldState?.gravity) === g
                    ? 'bg-amber-500 text-slate-950 font-bold shadow'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                {g}
              </button>
            ))}
          </div>

          {/* Weather Control */}
          <div className="flex items-center gap-1.5 bg-slate-950 p-1 rounded-lg border border-slate-800">
            <span className="text-[10px] uppercase font-mono px-2 text-slate-400">Weather:</span>
            {[
              { id: 'clear', icon: Sun, label: 'Clear' },
              { id: 'rain', icon: CloudRain, label: 'Rain' },
              { id: 'storm', icon: CloudLightning, label: 'Storm' },
              { id: 'solar_flare', icon: Flame, label: 'Solar' }
            ].map(w => (
              <button
                key={w.id}
                onClick={() => handleSetWeather(w.id)}
                className={`px-2 py-0.5 rounded text-xs font-mono flex items-center gap-1 transition-all ${
                  worldState?.weather?.condition === w.id
                    ? 'bg-cyan-500 text-slate-950 font-bold shadow'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                <w.icon className="h-3 w-3" />
                <span>{w.label}</span>
              </button>
            ))}
          </div>

          {/* Core Anomaly & Reset Controls */}
          <div className="flex items-center gap-2">
            <button
              onClick={handleTriggerAnomaly}
              className="px-3 py-1 bg-rose-950/70 hover:bg-rose-900 border border-rose-700/60 text-rose-300 rounded text-xs font-mono font-medium transition-all flex items-center gap-1.5 shadow"
            >
              <Zap className="h-3.5 w-3.5" /> Anomaly Pulse
            </button>
            <button
              onClick={handleReset}
              className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-300 rounded text-xs font-mono transition-all flex items-center gap-1 shadow"
            >
              <RotateCcw className="h-3.5 w-3.5" /> Reset
            </button>
          </div>
        </div>
      </div>

      {/* RIGHT: Agent Fleet Telemetry & C2 Terminal Drawer */}
      <div className="w-full xl:w-96 flex flex-col bg-slate-900/70 rounded-xl border border-slate-800 p-3 shadow-xl backdrop-blur-md overflow-hidden">
        {/* Tab Header */}
        <div className="flex items-center justify-between pb-2 border-b border-slate-800 mb-2.5">
          <div className="flex items-center gap-1 bg-slate-950 p-0.5 rounded-lg border border-slate-800 text-xs">
            <button
              onClick={() => setSidebarTab('telemetry')}
              className={`px-2.5 py-1 rounded-md font-medium transition-all ${
                sidebarTab === 'telemetry' ? 'bg-slate-800 text-amber-300' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Telemetry
            </button>
            <button
              onClick={() => setSidebarTab('console')}
              className={`px-2.5 py-1 rounded-md font-medium transition-all ${
                sidebarTab === 'console' ? 'bg-slate-800 text-cyan-300' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Console C2
            </button>
            <button
              onClick={() => setSidebarTab('memory')}
              className={`px-2.5 py-1 rounded-md font-medium transition-all ${
                sidebarTab === 'memory' ? 'bg-slate-800 text-emerald-300' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Memory Vault
            </button>
          </div>

          <div className="text-[11px] font-mono text-slate-400">
            {normalizedAgents.length} Agents
          </div>
        </div>

        {/* Tab Body */}
        <div className="flex-1 overflow-y-auto space-y-3 pr-1">
          {sidebarTab === 'telemetry' && (
            <>
              {/* Agent Picker Pill Rail */}
              <div>
                <div className="text-[10px] font-mono uppercase text-slate-400 mb-1.5">Select Agent:</div>
                <div className="flex flex-wrap gap-1.5">
                  {normalizedAgents.map(ag => {
                    const id = ag.id || ag.name || '';
                    const isSelected = id === selectedAgentId;
                    return (
                      <button
                        key={id}
                        onClick={() => setSelectedAgentId(id)}
                        className={`px-2 py-0.5 rounded text-xs font-mono transition-all border ${
                          isSelected
                            ? 'bg-amber-500/20 border-amber-400 text-amber-300 font-bold'
                            : 'bg-slate-950 border-slate-800 text-slate-400 hover:text-slate-200'
                        }`}
                      >
                        {ag.name || id}
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Selected Agent Telemetry Card */}
              {selectedAgent ? (
                <div className="bg-slate-950/80 rounded-lg p-3 border border-slate-800 space-y-2.5">
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="text-sm font-bold text-slate-100 flex items-center gap-1.5">
                        <Activity className="h-4 w-4 text-cyan-400" />
                        <span>{selectedAgent.name || selectedAgent.id}</span>
                      </div>
                      <div className="text-[11px] text-slate-400">
                        {selectedAgent.role || 'Autonomous Field Operative'}
                      </div>
                    </div>
                    <span className="px-2 py-0.5 rounded bg-slate-900 border border-slate-800 text-[10px] font-mono text-emerald-300">
                      {selectedAgent.status || 'active'}
                    </span>
                  </div>

                  {/* Telemetry Grid */}
                  <div className="grid grid-cols-2 gap-2 text-xs font-mono pt-1">
                    <div className="bg-slate-900/60 p-2 rounded border border-slate-800/80">
                      <div className="text-[10px] text-slate-500">COORDINATES</div>
                      <div className="text-slate-200">
                        ({selectedAgent.x?.toFixed(1) || 0}, {selectedAgent.y?.toFixed(1) || 0})
                      </div>
                    </div>
                    <div className="bg-slate-900/60 p-2 rounded border border-slate-800/80">
                      <div className="text-[10px] text-slate-500">THRUSTER FUEL</div>
                      <div className="text-amber-400 font-bold">
                        {selectedAgent.thruster_fuel !== undefined ? selectedAgent.thruster_fuel : 100}%
                      </div>
                    </div>
                    <div className="bg-slate-900/60 p-2 rounded border border-slate-800/80">
                      <div className="text-[10px] text-slate-500">VELOCITY</div>
                      <div className="text-slate-200">
                        vx: {selectedAgent.vx?.toFixed(2) || '0.00'}, vy: {selectedAgent.vy?.toFixed(2) || '0.00'}
                      </div>
                    </div>
                    <div className="bg-slate-900/60 p-2 rounded border border-slate-800/80">
                      <div className="text-[10px] text-slate-500">BEHAVIORAL TYPE</div>
                      <div className="text-indigo-300 truncate">
                        {selectedAgent.archetype || 'EQUILIBRIST'}
                      </div>
                    </div>
                  </div>

                  {/* Last Action / Thought */}
                  <div className="bg-slate-900/40 p-2.5 rounded border border-slate-800 text-xs">
                    <div className="text-[10px] font-mono text-slate-500 uppercase mb-1">Current Action / Directive:</div>
                    <div className="text-slate-300 font-sans italic">
                      "{selectedAgent.last_action || 'Executing spatial recon and acoustic entrainment alignment.'}"
                    </div>
                  </div>
                </div>
              ) : (
                <div className="text-center py-6 text-slate-500 text-xs font-mono">
                  No agent selected. Click an agent avatar on canvas.
                </div>
              )}
            </>
          )}

          {sidebarTab === 'console' && (
            <div className="flex flex-col h-full space-y-2">
              <div className="text-[11px] text-slate-400 font-mono">
                Operator Slash Commands: <code className="text-amber-300">/teleport &lt;agent&gt; &lt;x&gt; &lt;y&gt;</code>, <code className="text-cyan-300">/gravity &lt;val&gt;</code>
              </div>

              {/* RLCD & RLVR Quick Action Triggers */}
              <div className="flex items-center gap-2 pt-0.5">
                <button
                  onClick={async () => {
                    setIsDistilling(true);
                    setConsoleLogs(prev => [...prev, { text: '⚖️ Initiating Parallel RLCD Constitutional Distillation Cycle...', type: 'info' }]);
                    try {
                      const res = await fetch('/api/v1/c2/rlcd/distill', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ query: 'Explain the active Open World state with 100% truthfulness and sweet companion charm', agent_name: 'Nova' })
                      });
                      if (res.ok) {
                        const data = await res.json();
                        setConsoleLogs(prev => [
                          ...prev,
                          { text: `🏆 RLCD Distilled! Winner: Branch [${data.winner}] (Δ=${data.score_delta}). Critique: ${data.reason}`, type: 'success' }
                        ]);
                        setRlcdTelemetry(prev => ({ ...prev, total_distillations: (prev?.total_distillations || 0) + 1 }));
                      } else {
                        setConsoleLogs(prev => [...prev, { text: '❌ RLCD Distillation request failed.', type: 'error' }]);
                      }
                    } catch (e: any) {
                      setConsoleLogs(prev => [...prev, { text: `❌ RLCD Error: ${e.message}`, type: 'error' }]);
                    } finally {
                      setIsDistilling(false);
                    }
                  }}
                  disabled={isDistilling}
                  className="px-2.5 py-1 rounded bg-purple-900/60 hover:bg-purple-800 border border-purple-700/60 text-purple-200 text-xs font-mono transition-all flex items-center gap-1 disabled:opacity-50"
                >
                  <Sparkles className={`h-3 w-3 text-purple-400 ${isDistilling ? 'animate-spin' : ''}`} />
                  {isDistilling ? 'Distilling...' : '⚖️ Trigger RLCD'}
                </button>
                <button
                  onClick={async () => {
                    const agentId = selectedAgent?.id || 'Architect_Prime';
                    setConsoleLogs(prev => [...prev, { text: `🥣 Entering Soup Zero Synthesis Sanctum for [[${agentId}]]...`, type: 'info' }]);
                    try {
                      const res = await fetch('/api/v1/sanctum/enter', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ agent_id: agentId, desired_skill_domain: 'AST_Optimization' })
                      });
                      if (res.ok) {
                        const data = await res.json();
                        setConsoleLogs(prev => [
                          ...prev,
                          { text: `✨ [[${agentId}]] entered Sanctum! Grid: ${data.spatial_grid} | 432Hz Soundscape active.`, type: 'success' }
                        ]);
                      } else {
                        setConsoleLogs(prev => [...prev, { text: '❌ Sanctum entry failed.', type: 'error' }]);
                      }
                    } catch (e: any) {
                      setConsoleLogs(prev => [...prev, { text: `❌ Sanctum Error: ${e.message}`, type: 'error' }]);
                    }
                  }}
                  className="px-2.5 py-1 rounded bg-emerald-900/60 hover:bg-emerald-800 border border-emerald-700/60 text-emerald-200 text-xs font-mono transition-all flex items-center gap-1"
                >
                  <Cpu className="h-3 w-3 text-emerald-400" />
                  🥣 Enter Sanctum
                </button>
              </div>

              {/* Console Output Log */}
              <div className="flex-1 bg-slate-950 p-2.5 rounded-lg border border-slate-800 font-mono text-xs overflow-y-auto space-y-1 h-56">
                {consoleLogs.map((lg, i) => (
                  <div
                    key={i}
                    className={`leading-relaxed break-all ${
                      lg.type === 'success' ? 'text-emerald-400' : (lg.type === 'error' ? 'text-rose-400' : 'text-slate-300')
                    }`}
                  >
                    {lg.text}
                  </div>
                ))}
              </div>

              {/* Command Form */}
              <form onSubmit={handleExecuteCommand} className="flex items-center gap-1.5 pt-1">
                <input
                  type="text"
                  value={consoleInput}
                  onChange={(e) => setConsoleInput(e.target.value)}
                  placeholder="/teleport Bob 25 25"
                  className="flex-1 bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-xs font-mono text-slate-100 focus:outline-none focus:border-amber-400"
                />
                <button
                  type="submit"
                  className="px-3 py-1.5 bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold rounded text-xs transition-all"
                >
                  Send
                </button>
              </form>
            </div>
          )}

          {sidebarTab === 'memory' && (
            <div className="space-y-3">
              <div className="bg-slate-950 p-3 rounded-lg border border-slate-800 space-y-2 text-xs font-mono">
                <div className="text-slate-400 uppercase text-[10px]">Vault Telemetry:</div>
                <div className="flex justify-between border-b border-slate-900 pb-1">
                  <span className="text-slate-500">Vault Path:</span>
                  <span className="text-slate-300 truncate max-w-[180px]">{memoryStats?.vault_path || './vault/'}</span>
                </div>
                <div className="flex justify-between border-b border-slate-900 pb-1">
                  <span className="text-slate-500">Episodic Daily Logs:</span>
                  <span className="text-amber-400">{memoryStats?.episodic_count || 14}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Active Agents Indexed:</span>
                  <span className="text-emerald-400">{memoryStats?.agents_indexed || normalizedAgents.length}</span>
                </div>
              </div>

              <div className="bg-slate-950/60 p-3 rounded-lg border border-slate-800 text-xs">
                <div className="text-amber-300 font-bold mb-1 flex items-center gap-1">
                  <Database className="h-3.5 w-3.5" /> Obsidian Vault Integration
                </div>
                <p className="text-slate-400 text-[11px] leading-relaxed">
                  All autonomous agent observations, encounters, and spatial transitions are continuously written to Obsidian markdown notes with YAML frontmatter.
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
