import React, { useState, useEffect, useRef } from 'react';
import {
  Brain, ShieldAlert, Cpu, Activity, Play, Pause, RotateCcw,
  Sparkles, RefreshCw, Zap, Compass, FileText, ChevronRight,
  Database, UserCheck, Flame, CloudRain, Wind, Layers, Eye,
  Lock, CheckCircle2, AlertTriangle, Radio, Navigation, Maximize2,
  CloudLightning, Sun
} from 'lucide-react';

const HTTP_API_BASE = 'http://localhost:8080';
const WS_URL = 'ws://localhost:8080/ws';

export default function OpenWorldVisualizer({ onOpenFullVault }) {
  // Python Physics World State
  const [worldState, setWorldState] = useState(null);
  const [vaultFiles, setVaultFiles] = useState([]);
  const [selectedAgent, setSelectedAgent] = useState('Bob');
  const [activeDiaryNote, setActiveDiaryNote] = useState(null);
  
  // Memory Vault State
  const [sidebarTab, setSidebarTab] = useState('telemetry'); // 'telemetry' | 'memory'
  const [memoryStats, setMemoryStats] = useState(null);
  const [isConsolidating, setIsConsolidating] = useState(false);
  const [recoverInput, setRecoverInput] = useState('');
  const [consolidationResult, setConsolidationResult] = useState(null);
  
  // Controls & Toggles
  const [autoPlay, setAutoPlay] = useState(true);
  const [wsConnected, setWsConnected] = useState(false);
  const [showInfluenceOverlay, setShowInfluenceOverlay] = useState(true);
  const [showParticleVectors, setShowParticleVectors] = useState(true);
  const [statusMessage, setStatusMessage] = useState('Connecting to WebSocket Stream (ws://localhost:8080/ws)...');

  const canvasRef = useRef(null);
  const wsRef = useRef(null);
  const particlesRef = useRef([]);
  const lightningFlashRef = useRef(0);

  const fetchMemoryStats = async () => {
    try {
      const res = await fetch(`${HTTP_API_BASE}/api/memory/stats`);
      if (res.ok) {
        const data = await res.json();
        setMemoryStats(data);
      }
    } catch (e) {
      console.error('Error fetching memory stats:', e);
    }
  };

  const triggerConsolidation = async () => {
    setIsConsolidating(true);
    try {
      const res = await fetch(`${HTTP_API_BASE}/api/memory/consolidate`, { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        setConsolidationResult(data);
        await fetchMemoryStats();
      }
    } catch (e) {
      console.error('Error running consolidation:', e);
    } finally {
      setIsConsolidating(false);
    }
  };

  const handleRecover = async () => {
    if (!recoverInput) return;
    try {
      const res = await fetch(`${HTTP_API_BASE}/api/memory/recover`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filename: recoverInput })
      });
      if (res.ok) {
        setRecoverInput('');
        await fetchMemoryStats();
      }
    } catch (e) {
      console.error('Error recovering memory:', e);
    }
  };

  useEffect(() => {
    fetchMemoryStats();
    const timer = setInterval(fetchMemoryStats, 8000);
    return () => clearInterval(timer);
  }, []);

  // Connect to WebSocket Server (port 8080 /ws)
  useEffect(() => {
    let ws;
    let reconnectTimer;

    const connectWebSocket = () => {
      try {
        ws = new WebSocket(WS_URL);
        wsRef.current = ws;

        ws.onopen = () => {
          setWsConnected(true);
          setStatusMessage('⚡ Connected to FastAPI WebSocket Stream (ws://localhost:8080/ws)');
        };

        ws.onmessage = (event) => {
          try {
            const msg = JSON.parse(event.data);
            if (msg.data) {
              setWorldState(msg.data);
              if (msg.data.weather?.lightning_active) {
                lightningFlashRef.current = 1.0;
              }
            }
          } catch (e) {
            console.error('Error parsing WebSocket message:', e);
          }
        };

        ws.onerror = (err) => {
          console.warn('WebSocket error, attempting HTTP polling fallback...', err);
          setWsConnected(false);
        };

        ws.onclose = () => {
          setWsConnected(false);
          setStatusMessage('WebSocket disconnected. Reconnecting...');
          reconnectTimer = setTimeout(connectWebSocket, 2000);
        };
      } catch (e) {
        console.error('WebSocket connection error:', e);
      }
    };

    connectWebSocket();

    // Fallback initial HTTP fetch
    fetch(`${HTTP_API_BASE}/api/state`)
      .then(res => res.json())
      .then(data => setWorldState(data))
      .catch(() => {});

    return () => {
      if (reconnectTimer) clearTimeout(reconnectTimer);
      if (ws) ws.close();
    };
  }, []);

  // Send Action over WebSocket or HTTP Fallback
  const sendWsAction = async (payload) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(payload));
    } else {
      // HTTP fallback
      try {
        if (payload.action === 'step') {
          const res = await fetch(`${HTTP_API_BASE}/api/step`, { method: 'POST' });
          setWorldState(await res.json());
        } else if (payload.action === 'gravity') {
          const res = await fetch(`${HTTP_API_BASE}/api/gravity`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ gravity: payload.gravity })
          });
          setWorldState(await res.json());
        } else if (payload.action === 'weather') {
          const res = await fetch(`${HTTP_API_BASE}/api/weather`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ condition: payload.condition })
          });
          setWorldState(await res.json());
        } else if (payload.action === 'anomaly') {
          const res = await fetch(`${HTTP_API_BASE}/api/anomaly`, { method: 'POST' });
          setWorldState(await res.json());
        } else if (payload.action === 'reset') {
          const res = await fetch(`${HTTP_API_BASE}/api/reset`, { method: 'POST' });
          setWorldState(await res.json());
        }
      } catch (e) {
        console.error('HTTP action error:', e);
      }
    }
  };

  const stepSimulation = () => sendWsAction({ action: 'step' });
  const setGravity = (gravity) => sendWsAction({ action: 'gravity', gravity });
  const setWeather = (condition) => sendWsAction({ action: 'weather', condition });
  const triggerAnomaly = () => sendWsAction({ action: 'anomaly' });
  const resetWorld = () => sendWsAction({ action: 'reset' });

  // Auto-play interval if WebSocket is not streaming ticks automatically
  useEffect(() => {
    let timer;
    if (autoPlay && !wsConnected) {
      timer = setInterval(stepSimulation, 1000);
    }
    return () => {
      if (timer) clearInterval(timer);
    };
  }, [autoPlay, wsConnected]);

  // Particle System initialization
  useEffect(() => {
    const numParticles = 80;
    particlesRef.current = Array.from({ length: numParticles }, () => ({
      x: Math.random() * 800,
      y: Math.random() * 450,
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

    let animId;
    const render = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      const gNumeric = worldState?.gravity_numeric !== undefined ? worldState.gravity_numeric : 1.0;
      const weather = worldState?.weather || { condition: 'clear', lightning_active: false };

      // 1. Render Background Subfloor & Bulkhead Grid
      ctx.fillStyle = '#060911';
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      // Grid Pattern
      ctx.strokeStyle = 'rgba(30, 41, 59, 0.4)';
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

      // Ceiling & Floor Bulkhead Safety Plates
      ctx.fillStyle = '#0f172a';
      ctx.fillRect(0, 0, canvas.width, 24); // Ceiling
      ctx.fillRect(0, canvas.height - 24, canvas.width, 24); // Floor
      ctx.fillStyle = '#334155';
      ctx.fillRect(0, 23, canvas.width, 2);
      ctx.fillRect(0, canvas.height - 25, canvas.width, 2);

      // 2. Comfort Heatmap Overlay
      if (showInfluenceOverlay) {
        const coreX = 400, coreY = 225;
        const grad = ctx.createRadialGradient(coreX, coreY, 20, coreX, coreY, 320);
        
        if (gNumeric < 0) {
          grad.addColorStop(0, 'rgba(239, 68, 68, 0.25)');
          grad.addColorStop(0.5, 'rgba(168, 85, 247, 0.12)');
          grad.addColorStop(1, 'rgba(6, 9, 17, 0)');
        } else if (gNumeric === 0) {
          grad.addColorStop(0, 'rgba(56, 189, 248, 0.22)');
          grad.addColorStop(0.6, 'rgba(14, 165, 233, 0.08)');
          grad.addColorStop(1, 'rgba(6, 9, 17, 0)');
        } else {
          grad.addColorStop(0, 'rgba(234, 179, 8, 0.18)');
          grad.addColorStop(0.6, 'rgba(16, 185, 129, 0.08)');
          grad.addColorStop(1, 'rgba(6, 9, 17, 0)');
        }
        ctx.fillStyle = grad;
        ctx.fillRect(0, 0, canvas.width, canvas.height);
      }

      // 3. Dynamic Rain & Gravity Particle Vectors
      if (showParticleVectors) {
        const isRaining = weather.condition === 'rain' || weather.condition === 'lightning';
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

      // 4. Dynamic Lightning Flash
      if (lightningFlashRef.current > 0) {
        ctx.fillStyle = `rgba(255, 255, 255, ${lightningFlashRef.current * 0.4})`;
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        
        // Draw lightning bolt
        ctx.strokeStyle = '#38bdf8';
        ctx.lineWidth = 3;
        ctx.beginPath();
        let lx = 200 + Math.random() * 400;
        let ly = 24;
        ctx.moveTo(lx, ly);
        while (ly < 380) {
          lx += (Math.random() - 0.5) * 50;
          ly += 30 + Math.random() * 30;
          ctx.lineTo(lx, ly);
        }
        ctx.stroke();
        lightningFlashRef.current = Math.max(0, lightningFlashRef.current - 0.08);
      }

      // 5. Render Graviton Core Singularity
      const coreX = 400, coreY = 225;
      const pulseTime = Date.now() * 0.003;
      const pulseRadius = 36 + Math.sin(pulseTime) * 4;

      const coreAura = ctx.createRadialGradient(coreX, coreY, 10, coreX, coreY, pulseRadius + 28);
      coreAura.addColorStop(0, gNumeric < 0 ? 'rgba(244, 63, 94, 0.8)' : 'rgba(56, 189, 248, 0.8)');
      coreAura.addColorStop(0.6, gNumeric < 0 ? 'rgba(168, 85, 247, 0.3)' : 'rgba(14, 165, 233, 0.3)');
      coreAura.addColorStop(1, 'rgba(0, 0, 0, 0)');
      ctx.fillStyle = coreAura;
      ctx.beginPath();
      ctx.arc(coreX, coreY, pulseRadius + 28, 0, Math.PI * 2);
      ctx.fill();

      ctx.fillStyle = gNumeric < 0 ? '#f43f5e' : '#0284c7';
      ctx.beginPath();
      ctx.arc(coreX, coreY, pulseRadius, 0, Math.PI * 2);
      ctx.fill();

      ctx.strokeStyle = '#ffffff';
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.ellipse(coreX, coreY, pulseRadius + 14, 12, pulseTime, 0, Math.PI * 2);
      ctx.stroke();

      ctx.fillStyle = '#ffffff';
      ctx.font = 'bold 10px monospace';
      ctx.textAlign = 'center';
      ctx.fillText(`GRAVITON CORE [${worldState?.core_stability || 98.5}%]`, coreX, coreY + 55);

      // 6. Render Autonomous Agents & Spatial Cards (Bob, Alice, Charlie, Vector-09, Dr. Aris, AEGIS, Unit-404)
      if (worldState?.agents) {
        Object.entries(worldState.agents).forEach(([name, agent]) => {
          const isSelected = selectedAgent === name;
          
          let color = '#38bdf8';
          let icon = '🤖';
          if (name === 'Bob') { color = '#6366f1'; icon = '👨‍💻'; }
          else if (name === 'Alice') { color = '#ec4899'; icon = '👩‍🎨'; }
          else if (name === 'Charlie') { color = '#14b8a6'; icon = '🧑‍🔧'; }
          else if (name === 'Vector-09') { color = '#38bdf8'; icon = '🔬'; }
          else if (name === 'Dr._Aris') { color = '#f43f5e'; icon = '👩‍🔬'; }
          else if (name === 'A.E.G.I.S.') { color = '#eab308'; icon = '🛡️'; }
          else if (name === 'Unit-404') { color = '#10b981'; icon = '🤖'; }

          // Selection Ring
          if (isSelected) {
            ctx.strokeStyle = '#ffffff';
            ctx.lineWidth = 2;
            ctx.setLineDash([4, 4]);
            ctx.beginPath();
            ctx.arc(agent.x, agent.y, 28, 0, Math.PI * 2);
            ctx.stroke();
            ctx.setLineDash([]);
          }

          // Agent Avatar Body
          ctx.fillStyle = '#0f172a';
          ctx.strokeStyle = color;
          ctx.lineWidth = 2.5;
          ctx.beginPath();
          ctx.arc(agent.x, agent.y, 20, 0, Math.PI * 2);
          ctx.fill();
          ctx.stroke();

          // Agent Icon / Emoji
          ctx.fillStyle = '#ffffff';
          ctx.font = '15px sans-serif';
          ctx.textAlign = 'center';
          ctx.fillText(icon, agent.x, agent.y + 5);

          // Agent Name Label
          ctx.fillStyle = color;
          ctx.font = 'bold 11px monospace';
          ctx.fillText(name.replace('_', ' '), agent.x, agent.y - 25);

          // Real-time Status Badge
          ctx.fillStyle = '#0b0f19';
          ctx.fillRect(agent.x - 28, agent.y + 24, 56, 14);
          ctx.strokeStyle = color;
          ctx.strokeRect(agent.x - 28, agent.y + 24, 56, 14);

          ctx.fillStyle = '#f1f5f9';
          ctx.font = 'bold 8px monospace';
          ctx.fillText(agent.status || 'Active', agent.x, agent.y + 34);
        });
      }

      animId = requestAnimationFrame(render);
    };

    render();
    return () => cancelAnimationFrame(animId);
  }, [worldState, selectedAgent, showInfluenceOverlay, showParticleVectors]);

  const handleCanvasClick = (e) => {
    if (!canvasRef.current || !worldState?.agents) return;
    const rect = canvasRef.current.getBoundingClientRect();
    const clickX = (e.clientX - rect.left) * (800 / rect.width);
    const clickY = (e.clientY - rect.top) * (450 / rect.height);

    let clickedAgent = null;
    Object.entries(worldState.agents).forEach(([name, agent]) => {
      const dist = Math.hypot(clickX - agent.x, clickY - agent.y);
      if (dist <= 30) {
        clickedAgent = name;
      }
    });

    if (clickedAgent) {
      setSelectedAgent(clickedAgent);
    }
  };

  const currentAgentData = worldState?.agents?.[selectedAgent];

  return (
    <div className="flex flex-col h-screen w-full bg-[#070b14] text-slate-100 font-sans overflow-hidden">
      
      {/* TOP HEADER */}
      <header className="h-14 border-b border-slate-800/80 bg-[#0a0f1d] px-6 flex items-center justify-between shrink-0 shadow-md">
        <div className="flex items-center space-x-3">
          <div className="p-2 bg-cyan-950 text-cyan-400 border border-cyan-700/60 rounded-xl flex items-center justify-center shadow-sm">
            <Compass className="w-5 h-5 animate-spin" style={{ animationDuration: '12s' }} />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="font-bold text-sm tracking-wide text-white">AUTONOMOUS MULTI-AGENT OPEN WORLD</h1>
              <span className={`text-[10px] px-2 py-0.5 rounded font-mono flex items-center space-x-1 ${wsConnected ? 'bg-emerald-950 text-emerald-300 border border-emerald-700' : 'bg-amber-950 text-amber-300 border border-amber-700'}`}>
                <span className={`w-1.5 h-1.5 rounded-full animate-ping ${wsConnected ? 'bg-emerald-400' : 'bg-amber-400'}`}></span>
                <span>{wsConnected ? 'WEBSOCKET STREAM ACTIVE' : 'HTTP POLLING'}</span>
              </span>
            </div>
            <p className="text-[11px] text-slate-400 font-mono truncate max-w-md">
              {statusMessage}
            </p>
          </div>
        </div>

        {/* Global Telemetry Chips */}
        <div className="flex items-center space-x-4 text-xs font-mono">
          <div className="flex items-center space-x-1.5 bg-slate-900 border border-slate-800 px-2.5 py-1 rounded-lg">
            <Activity className="w-3.5 h-3.5 text-cyan-400" />
            <span className="text-slate-400">Tick:</span>
            <span className="font-bold text-white">{worldState?.tick || 0}</span>
          </div>

          <div className="flex items-center space-x-1.5 bg-slate-900 border border-slate-800 px-2.5 py-1 rounded-lg">
            <Radio className="w-3.5 h-3.5 text-emerald-400" />
            <span className="text-slate-400">Gravity:</span>
            <span className="font-bold text-emerald-300">{worldState?.local_gravity || '1.0g'}</span>
          </div>

          <div className="flex items-center space-x-1.5 bg-slate-900 border border-slate-800 px-2.5 py-1 rounded-lg">
            <CloudLightning className="w-3.5 h-3.5 text-yellow-400" />
            <span className="text-slate-400">Weather:</span>
            <span className="font-bold text-yellow-300 uppercase">{worldState?.weather?.condition || 'clear'}</span>
          </div>

          {onOpenFullVault && (
            <button
              onClick={onOpenFullVault}
              className="flex items-center space-x-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-cyan-300 text-xs font-semibold rounded-lg border border-slate-700 transition"
            >
              <Database className="w-3.5 h-3.5" />
              <span>Full Obsidian Vault</span>
            </button>
          )}
        </div>
      </header>

      {/* 2-COLUMN MAIN WORKSPACE */}
      <div className="flex-1 flex overflow-hidden">
        
        {/* LEFT COLUMN: 2.5D OPEN-WORLD VISUALIZER */}
        <main className="flex-1 flex flex-col p-4 space-y-4 overflow-y-auto">
          
          <div className="bg-slate-950 border border-slate-800/90 rounded-2xl overflow-hidden shadow-2xl relative flex flex-col">
            
            <div className="bg-slate-900/90 px-4 py-2 border-b border-slate-800 flex justify-between items-center text-xs">
              <div className="flex items-center space-x-3">
                <span className="font-bold text-slate-200 flex items-center space-x-1.5">
                  <Navigation className="w-4 h-4 text-cyan-400" />
                  <span>{worldState?.location || 'Dev Citadel & Graviton Bay'}</span>
                </span>
                <span className="text-[10px] bg-slate-800 text-slate-400 px-2 py-0.5 rounded font-mono">
                  800x450 Matrix
                </span>
              </div>

              <div className="flex items-center space-x-2">
                <button
                  onClick={() => setShowInfluenceOverlay(!showInfluenceOverlay)}
                  className={`text-[10px] px-2 py-0.5 rounded border font-mono transition ${showInfluenceOverlay ? 'bg-cyan-950 text-cyan-300 border-cyan-700' : 'bg-slate-800 text-slate-500 border-slate-700'}`}
                >
                  Comfort Heatmap
                </button>
                <button
                  onClick={() => setShowParticleVectors(!showParticleVectors)}
                  className={`text-[10px] px-2 py-0.5 rounded border font-mono transition ${showParticleVectors ? 'bg-emerald-950 text-emerald-300 border-emerald-700' : 'bg-slate-800 text-slate-500 border-slate-700'}`}
                >
                  Vector Field
                </button>
              </div>
            </div>

            <canvas
              ref={canvasRef}
              width={800}
              height={450}
              onClick={handleCanvasClick}
              className="w-full h-[450px] bg-[#060911] block cursor-crosshair"
              title="Click any agent avatar to inspect live telemetry and Obsidian memory"
            />

            <div className="absolute bottom-3 left-3 bg-slate-950/85 backdrop-blur border border-slate-800 px-3 py-1.5 rounded-xl text-[11px] text-slate-300 font-mono flex items-center space-x-4">
              <span>Selected: <strong className="text-cyan-400">{selectedAgent}</strong></span>
              <span>Coords: <strong className="text-white">({currentAgentData?.x || 0}, {currentAgentData?.y || 0})</strong></span>
              <span>Status: <strong className="text-emerald-400">{currentAgentData?.status || 'Active'}</strong></span>
            </div>
          </div>

          {/* MISSION CONTROL ACTION TOOLBAR */}
          <div className="bg-slate-900/90 p-4 rounded-xl border border-slate-800 flex flex-wrap items-center justify-between gap-4 shadow-md">
            
            {/* Playback Controls */}
            <div className="flex items-center space-x-2">
              <button
                onClick={() => setAutoPlay(!autoPlay)}
                className={`px-4 py-2 rounded-lg font-bold text-xs flex items-center space-x-1.5 transition ${autoPlay ? 'bg-amber-500 hover:bg-amber-400 text-slate-950' : 'bg-emerald-500 hover:bg-emerald-400 text-slate-950'}`}
              >
                {autoPlay ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
                <span>{autoPlay ? 'Pause Loop' : 'Live Loop'}</span>
              </button>

              <button
                onClick={stepSimulation}
                className="px-3.5 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold rounded-lg border border-slate-700 transition"
              >
                Step Tick
              </button>

              <button
                onClick={resetWorld}
                className="p-2 bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white text-xs rounded-lg border border-slate-700 transition"
                title="Reset World"
              >
                <RotateCcw className="w-4 h-4" />
              </button>
            </div>

            {/* Dynamic Weather Overrides */}
            <div className="flex items-center space-x-1.5 text-xs">
              <span className="text-slate-400 text-[10px] uppercase font-bold mr-1">Weather:</span>
              <button onClick={() => setWeather('clear')} className="px-2.5 py-1.5 bg-slate-800 hover:bg-slate-700 rounded text-xs font-mono border border-slate-700 transition flex items-center space-x-1">
                <Sun className="w-3 h-3 text-amber-400" />
                <span>Clear</span>
              </button>
              <button onClick={() => setWeather('rain')} className="px-2.5 py-1.5 bg-slate-800 hover:bg-slate-700 rounded text-xs font-mono border border-slate-700 transition flex items-center space-x-1">
                <CloudRain className="w-3 h-3 text-cyan-400" />
                <span>Rain</span>
              </button>
              <button onClick={() => setWeather('lightning')} className="px-2.5 py-1.5 bg-yellow-950 hover:bg-yellow-900 text-yellow-300 rounded text-xs font-mono border border-yellow-700 transition flex items-center space-x-1">
                <CloudLightning className="w-3 h-3 text-yellow-400" />
                <span>Lightning</span>
              </button>
            </div>

            {/* Gravity Field Overrides */}
            <div className="flex items-center space-x-1.5 text-xs">
              <span className="text-slate-400 text-[10px] uppercase font-bold mr-1">Gravity:</span>
              <button onClick={() => setGravity('1.0g')} className="px-2 py-1 rounded text-xs font-mono bg-slate-800 border border-slate-700 hover:bg-slate-700">1.0g</button>
              <button onClick={() => setGravity('0.0g')} className="px-2 py-1 rounded text-xs font-mono bg-slate-800 border border-slate-700 hover:bg-slate-700">0.0g</button>
              <button onClick={() => setGravity('-1.2g')} className="px-2 py-1 rounded text-xs font-mono bg-rose-950 border border-rose-700 text-rose-300 hover:bg-rose-900">-1.2g</button>
            </div>

            {/* Anomaly Trigger */}
            <button
              onClick={triggerAnomaly}
              className="px-3.5 py-2 bg-rose-600 hover:bg-rose-500 text-white font-bold text-xs rounded-lg transition flex items-center space-x-1.5 shadow-md active:scale-95"
            >
              <Zap className="w-3.5 h-3.5" />
              <span>Anomaly</span>
            </button>

          </div>

          {/* AGENT FLEET CARDS (Bob, Alice, Charlie, Vector-09, etc.) */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {worldState?.agents && Object.entries(worldState.agents).map(([name, agent]) => {
              const isSelected = selectedAgent === name;
              let borderClass = 'border-slate-800';
              if (name === 'Bob') borderClass = 'border-indigo-500/60 bg-indigo-950/20';
              else if (name === 'Alice') borderClass = 'border-pink-500/60 bg-pink-950/20';
              else if (name === 'Charlie') borderClass = 'border-teal-500/60 bg-teal-950/20';
              else if (name === 'Vector-09') borderClass = 'border-cyan-500/60 bg-cyan-950/20';

              return (
                <div
                  key={name}
                  onClick={() => setSelectedAgent(name)}
                  className={`p-3 rounded-xl border cursor-pointer transition ${isSelected ? `${borderClass} shadow-lg ring-1 ring-white/30` : 'bg-slate-900/60 border-slate-800 hover:bg-slate-800/80'}`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-bold text-xs text-white">{name.replace('_', ' ')}</span>
                    <span className="text-[10px] font-mono text-slate-400">({agent.x}, {agent.y})</span>
                  </div>
                  <div className="text-[10px] text-slate-400 truncate mb-2">{agent.last_action}</div>
                  <div className="flex justify-between items-center text-[10px] font-mono pt-2 border-t border-slate-800">
                    <span className="text-slate-500">Status:</span>
                    <span className="font-bold text-emerald-400">{agent.status || 'Active'}</span>
                  </div>
                </div>
              );
            })}
          </div>

        </main>

        {/* RIGHT COLUMN: REASONING & TELEMETRY / MEMORY VAULT */}
        <aside className="w-96 border-l border-slate-800/80 bg-[#0a0f1c] flex flex-col shrink-0 overflow-hidden shadow-2xl">
          {/* Dual-Tab Header */}
          <div className="h-12 border-b border-slate-800 px-2 flex items-center justify-between shrink-0 bg-[#0d1424]">
            <div className="flex space-x-1 w-full">
              <button
                onClick={() => setSidebarTab('telemetry')}
                className={`flex-1 py-1.5 px-2 rounded-lg text-xs font-bold flex items-center justify-center space-x-1.5 transition ${sidebarTab === 'telemetry' ? 'bg-slate-800 text-cyan-400 shadow' : 'text-slate-400 hover:text-slate-200'}`}
              >
                <FileText className="w-3.5 h-3.5" />
                <span>Telemetry</span>
              </button>
              <button
                onClick={() => setSidebarTab('memory')}
                className={`flex-1 py-1.5 px-2 rounded-lg text-xs font-bold flex items-center justify-center space-x-1.5 transition ${sidebarTab === 'memory' ? 'bg-indigo-950 text-indigo-300 border border-indigo-700/60 shadow' : 'text-slate-400 hover:text-slate-200'}`}
              >
                <Brain className="w-3.5 h-3.5 text-indigo-400" />
                <span>Memory Vault</span>
              </button>
            </div>
          </div>

          {sidebarTab === 'telemetry' ? (
            <>
              {currentAgentData && (
                <div className="p-4 border-b border-slate-800 bg-slate-900/40 space-y-2">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-bold text-white flex items-center space-x-1.5">
                      <UserCheck className="w-3.5 h-3.5 text-cyan-400" />
                      <span>{selectedAgent.replace('_', ' ')} Active Profile</span>
                    </span>
                    <span className="text-[10px] bg-emerald-950 text-emerald-300 border border-emerald-800 px-1.5 py-0.5 rounded font-mono">
                      {currentAgentData.status || 'Active'}
                    </span>
                  </div>

                  <div className="text-xs text-slate-300 bg-slate-950/70 p-2.5 rounded-lg border border-slate-800/80 font-mono text-[11px] leading-relaxed">
                    <div className="text-slate-500 text-[10px] mb-1 uppercase font-bold">Latest Action:</div>
                    "{currentAgentData.last_action}"
                    <div className="text-slate-500 text-[10px] mt-2 mb-1 uppercase font-bold">Internal Reasoning:</div>
                    "{currentAgentData.last_reasoning}"
                  </div>
                </div>
              )}

              {/* Recent Events Log */}
              <div className="flex-1 overflow-y-auto p-4 space-y-3 font-mono text-xs">
                <div className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">Live Stream Events:</div>
                {worldState?.events?.slice(-8).map((evt, idx) => (
                  <div key={idx} className="p-2 bg-slate-900/70 border border-slate-800 rounded-lg text-[11px]">
                    <div className="flex justify-between text-slate-500 text-[10px] mb-1">
                      <span>Tick {evt.tick}</span>
                      <span className="uppercase text-cyan-400">{evt.type}</span>
                    </div>
                    <div className="text-slate-300">{evt.text}</div>
                  </div>
                ))}
              </div>
            </>
          ) : (
            /* MEMORY VAULT CONSOLIDATION TAB */
            <div className="flex-1 overflow-y-auto p-4 space-y-4 font-mono text-xs">
              <div className="bg-indigo-950/30 border border-indigo-800/50 p-3 rounded-xl space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-indigo-300 uppercase tracking-wider flex items-center space-x-1.5">
                    <Brain className="w-4 h-4 text-indigo-400" />
                    <span>Dual-Buffer Consolidation</span>
                  </span>
                  <span className="text-[10px] bg-indigo-900 text-indigo-200 px-2 py-0.5 rounded-full font-bold">
                    {memoryStats?.compression_ratio || 65.0}% Savings
                  </span>
                </div>
                <div className="text-[11px] text-slate-400 leading-relaxed font-sans">
                  Hippocampal short-term diaries periodically distilled into hardened neocortical semantic facts.
                </div>
              </div>

              {/* Memory Buffers Grid */}
              <div className="grid grid-cols-3 gap-2">
                <div className="bg-slate-900/90 border border-amber-500/30 p-2.5 rounded-lg text-center">
                  <div className="text-[10px] text-amber-400 font-bold uppercase mb-0.5">Hot Buffer</div>
                  <div className="text-lg font-bold text-white">{memoryStats?.hot_count || 0}</div>
                  <div className="text-[9px] text-slate-500">Episodic Diaries</div>
                </div>

                <div className="bg-slate-900/90 border border-cyan-500/30 p-2.5 rounded-lg text-center">
                  <div className="text-[10px] text-cyan-400 font-bold uppercase mb-0.5">Cold Memory</div>
                  <div className="text-lg font-bold text-white">{memoryStats?.cold_count || 0}</div>
                  <div className="text-[9px] text-slate-500">LATCH Facts</div>
                </div>

                <div className="bg-slate-900/90 border border-rose-500/30 p-2.5 rounded-lg text-center">
                  <div className="text-[10px] text-rose-400 font-bold uppercase mb-0.5">Tombstone</div>
                  <div className="text-lg font-bold text-white">{memoryStats?.tombstone_count || 0}</div>
                  <div className="text-[9px] text-slate-500">Recycle Bin</div>
                </div>
              </div>

              {/* Token Compression Progress */}
              <div className="bg-slate-900/80 border border-slate-800 p-3 rounded-xl space-y-2">
                <div className="flex justify-between text-[11px]">
                  <span className="text-slate-400">Context Window Optimization</span>
                  <span className="text-emerald-400 font-bold">{memoryStats?.compression_ratio || 65.0}% Reduction</span>
                </div>
                <div className="w-full bg-slate-950 h-2 rounded-full overflow-hidden border border-slate-800">
                  <div 
                    className="bg-gradient-to-r from-indigo-500 via-cyan-400 to-emerald-400 h-full transition-all duration-500" 
                    style={{ width: `${memoryStats?.compression_ratio || 65.0}%` }}
                  />
                </div>
                <div className="flex justify-between text-[10px] text-slate-500">
                  <span>Raw: ~{memoryStats?.estimated_raw_tokens || 22200} tokens</span>
                  <span>Distilled: ~{memoryStats?.optimized_tokens || 17550} tokens</span>
                </div>
              </div>

              {/* Actions & Consolidation Trigger */}
              <div className="space-y-2 pt-2 border-t border-slate-800">
                <button
                  onClick={triggerConsolidation}
                  disabled={isConsolidating}
                  className={`w-full py-2.5 px-4 rounded-xl font-bold text-xs flex items-center justify-center space-x-2 transition ${isConsolidating ? 'bg-indigo-900 text-indigo-300 cursor-wait' : 'bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg hover:shadow-indigo-500/20 active:scale-98'}`}
                >
                  <Sparkles className={`w-4 h-4 ${isConsolidating ? 'animate-spin' : ''}`} />
                  <span>{isConsolidating ? 'Consolidating & Distilling...' : 'Optimize & Consolidate Memories'}</span>
                </button>

                <div className="flex items-center space-x-2 pt-2">
                  <input
                    type="text"
                    value={recoverInput}
                    onChange={(e) => setRecoverInput(e.target.value)}
                    placeholder="Enter tombstoned filename..."
                    className="flex-1 bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-[11px] text-slate-200 focus:outline-none focus:border-indigo-500"
                  />
                  <button
                    onClick={handleRecover}
                    className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-bold rounded-lg border border-slate-700 transition"
                  >
                    Recover
                  </button>
                </div>
              </div>

              {consolidationResult && (
                <div className="p-2.5 bg-emerald-950/40 border border-emerald-800/60 rounded-lg text-[11px] text-emerald-300 space-y-1">
                  <div className="font-bold flex items-center space-x-1">
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                    <span>Consolidation Loop Finished!</span>
                  </div>
                  <div>Promoted: {consolidationResult.promoted} | Retained: {consolidationResult.retained}</div>
                </div>
              )}
            </div>
          )}
        </aside>

      </div>
    </div>
  );
}
