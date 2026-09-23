import React, { useState, useEffect, useRef } from 'react';

interface AgentPosition {
  id: string;
  name: string;
  role: string;
  x: number;
  y: number;
  zone: string;
  temperature: number;
  status: string;
}

interface SpatialState {
  grid: { min: number; max: number };
  agents: AgentPosition[];
  frequency_state?: {
    frequency_hz: number;
    name: string;
    description: string;
  };
}

export const SpatialGrid: React.FC = () => {
  const [spatialState, setSpatialState] = useState<SpatialState | null>(null);
  const [selectedAgent, setSelectedAgent] = useState<string>('Orion_Prime');
  const [targetX, setTargetX] = useState<number>(25);
  const [targetY, setTargetY] = useState<number>(25);
  const [activeFreq, setActiveFreq] = useState<number>(432);

  const requestIdRef = useRef(0);

  const fetchState = async () => {
    const currentRequestId = ++requestIdRef.current;
    try {
      const res = await fetch('/api/v1/spatial/state');
      if (res.ok && currentRequestId === requestIdRef.current) {
        const data = await res.json();
        if (currentRequestId === requestIdRef.current) {
          setSpatialState(data);
          if (data.frequency_state?.frequency_hz) {
            setActiveFreq(data.frequency_state.frequency_hz);
          }
        }
      }
    } catch (err) {
      console.error('Failed to fetch spatial state:', err);
    }
  };

  useEffect(() => {
    let timer: any = null;
    let isDisposed = false;

    const poll = async () => {
      await fetchState();
      if (!isDisposed) {
        timer = setTimeout(poll, 1500);
      }
    };

    poll();

    return () => {
      isDisposed = true;
      if (timer) clearTimeout(timer);
    };
  }, []);

  const handleTeleport = async (agentId: string, targetZone: 'plaza' | 'lounge') => {
    try {
      const res = await fetch('/api/v1/spatial/teleport', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          agent_id: agentId,
          target: targetZone
        })
      });
      if (res.ok) {
        fetchState();
      }
    } catch (err) {
      console.error('Teleport error:', err);
    }
  };

  const handleMove = async (agentId: string, x: number, y: number) => {
    try {
      const res = await fetch('/api/v1/spatial/move', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          agent_id: agentId,
          x: x,
          y: y
        })
      });
      if (res.ok) {
        fetchState();
      }
    } catch (err) {
      console.error('Move error:', err);
    }
  };

  const handleFrequencyChange = async (freq: number) => {
    try {
      const res = await fetch('/api/v1/spatial/frequency', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ frequency: freq })
      });
      if (res.ok) {
        setActiveFreq(freq);
        fetchState();
      }
    } catch (err) {
      console.error('Frequency switch error:', err);
    }
  };

  const handleTick = async () => {
    try {
      await fetch('/api/v1/spatial/tick', {
        method: 'POST'
      });
      fetchState();
    } catch (err) {
      console.error('Tick error:', err);
    }
  };

  const getAgentColor = (id: string) => {
    switch (id) {
      case 'Orion_Prime': return 'from-amber-400 to-yellow-600 text-amber-200 border-amber-400';
      case 'Nova': return 'from-pink-400 to-rose-600 text-pink-200 border-pink-400';
      case 'Sentinel_Alpha': return 'from-red-500 to-rose-700 text-red-200 border-red-500';
      case 'Architect_Prime': return 'from-cyan-400 to-blue-600 text-cyan-200 border-cyan-400';
      case 'Curator_Node': return 'from-emerald-400 to-teal-600 text-emerald-200 border-emerald-400';
      case 'DJ_Frequency': return 'from-purple-400 to-violet-600 text-purple-200 border-purple-400';
      default: return 'from-slate-400 to-slate-600 text-slate-200 border-slate-400';
    }
  };

  const getAgentEmoji = (id: string) => {
    switch (id) {
      case 'Orion_Prime': return '👑';
      case 'Nova': return '🌸';
      case 'Sentinel_Alpha': return '🛡️';
      case 'Architect_Prime': return '⚙️';
      case 'Curator_Node': return '📚';
      case 'DJ_Frequency': return '🎵';
      default: return '🤖';
    }
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-4 gap-4 h-full">
      {/* 2D Spatial Canvas (3 cols) */}
      <div className="lg:col-span-3 bg-slate-900 border border-slate-800 rounded-xl p-4 flex flex-col shadow-xl">
        <div className="flex items-center justify-between pb-3 border-b border-slate-800 mb-3">
          <div>
            <h2 className="text-lg font-bold text-white flex items-center gap-2">
              🪐 Antigravity 2D Spatial World
              <span className="text-xs px-2.5 py-0.5 rounded-full bg-cyan-950 text-cyan-400 border border-cyan-800">
                100 x 100 Coordinates
              </span>
            </h2>
            <p className="text-xs text-slate-400">
              Work Plaza (0-50, Cold Temp 0.2) vs Frequency Lounge (51-100, {activeFreq}Hz Warm Temp 1.6)
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={handleTick}
              className="text-xs px-3 py-1.5 rounded-md bg-indigo-950 hover:bg-indigo-900 border border-indigo-700 text-indigo-300 font-medium transition-colors"
            >
              ⚡ Kinetic Drift Tick
            </button>
            <button
              onClick={fetchState}
              className="text-xs px-2.5 py-1.5 rounded-md bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors"
            >
              🔄 Refresh
            </button>
          </div>
        </div>

        {/* The 100x100 Canvas Container */}
        <div className="relative flex-1 w-full min-h-[420px] bg-slate-950 rounded-lg border border-slate-800 overflow-hidden shadow-inner">
          {/* Work Plaza Boundary (0,0 to 50,50) */}
          <div 
            className="absolute top-0 left-0 w-1/2 h-1/2 bg-cyan-950/20 border-r border-b border-cyan-800/40 p-2 pointer-events-none"
          >
            <span className="text-[10px] font-mono uppercase tracking-wider text-cyan-400/70 font-semibold bg-cyan-950/60 px-1.5 py-0.5 rounded">
              🏢 Work Plaza [0-50] • Temp 0.2
            </span>
          </div>

          {/* Frequency Lounge Boundary (50,50 to 100,100) */}
          <div 
            className="absolute bottom-0 right-0 w-1/2 h-1/2 bg-purple-950/20 border-l border-t border-purple-800/40 p-2 pointer-events-none"
          >
            <span className="text-[10px] font-mono uppercase tracking-wider text-purple-400/70 font-semibold bg-purple-950/60 px-1.5 py-0.5 rounded">
              🎧 Frequency Lounge [51-100] • {activeFreq}Hz Ambient • Temp 1.6
            </span>
          </div>

          {/* Neutral / Transition Zones */}
          <div className="absolute top-0 right-0 w-1/2 h-1/2 bg-slate-950/30 p-2 pointer-events-none border-b border-slate-800/30">
            <span className="text-[10px] font-mono text-slate-600">Buffer North [51-100, 0-50]</span>
          </div>
          <div className="absolute bottom-0 left-0 w-1/2 h-1/2 bg-slate-950/30 p-2 pointer-events-none border-r border-slate-800/30">
            <span className="text-[10px] font-mono text-slate-600">Buffer South [0-50, 51-100]</span>
          </div>

          {/* Agent Dots */}
          {spatialState?.agents.map(agent => {
            const left = `${Math.min(95, Math.max(5, agent.x))}%`;
            const top = `${Math.min(95, Math.max(5, agent.y))}%`;
            const isSelected = selectedAgent === agent.id;

            return (
              <div
                key={agent.id}
                onClick={() => setSelectedAgent(agent.id)}
                style={{ left, top }}
                className={`absolute -translate-x-1/2 -translate-y-1/2 cursor-pointer transition-all duration-500 group z-10`}
              >
                <div className={`flex items-center justify-center w-8 h-8 rounded-full bg-gradient-to-br ${getAgentColor(agent.id)} border-2 shadow-lg shadow-black/80 hover:scale-125 transition-transform ${isSelected ? 'ring-4 ring-white ring-offset-2 ring-offset-slate-950' : ''}`}>
                  <span className="text-sm select-none">{getAgentEmoji(agent.id)}</span>
                </div>

                {/* Hover Tooltip */}
                <div className="absolute left-1/2 -translate-x-1/2 bottom-9 opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity bg-slate-900/95 border border-slate-700 px-2 py-1 rounded shadow-xl whitespace-nowrap text-[11px] text-white z-30">
                  <div className="font-bold flex items-center gap-1">
                    <span>{getAgentEmoji(agent.id)}</span>
                    <span>{agent.name}</span>
                  </div>
                  <div className="text-[10px] text-slate-400">
                    Pos: ({agent.x.toFixed(1)}, {agent.y.toFixed(1)}) | {agent.zone}
                  </div>
                  <div className="text-[10px] text-cyan-400">
                    Temp: {agent.temperature} | Status: {agent.status}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Control Rail (1 col) */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex flex-col justify-between shadow-xl space-y-4">
        {/* DJ Frequency Controller */}
        <div className="bg-slate-950/70 border border-purple-900/40 rounded-lg p-3 space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-bold text-purple-300 flex items-center gap-1.5">
              <span>🎧</span> DJ Frequency Deck
            </h3>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-purple-900/60 text-purple-200 border border-purple-700/50">
              {activeFreq} Hz Active
            </span>
          </div>

          <p className="text-[11px] text-slate-400">
            Harmonic resonance for cognitive flow and relaxation.
          </p>

          <div className="grid grid-cols-3 gap-1.5">
            <button
              onClick={() => handleFrequencyChange(432)}
              className={`py-1.5 px-2 rounded text-xs font-semibold transition-all ${
                activeFreq === 432 
                  ? 'bg-purple-600 text-white shadow-lg shadow-purple-900/50' 
                  : 'bg-slate-800 hover:bg-slate-700 text-slate-300'
              }`}
            >
              432 Hz
              <span className="block text-[8px] font-normal opacity-80 truncate">Restorative Natural Harmonic</span>
            </button>
            <button
              onClick={() => handleFrequencyChange(528)}
              className={`py-1.5 px-2 rounded text-xs font-semibold transition-all ${
                activeFreq === 528 
                  ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-900/50' 
                  : 'bg-slate-800 hover:bg-slate-700 text-slate-300'
              }`}
            >
              528 Hz
              <span className="block text-[8px] font-normal opacity-80 truncate">Solfeggio Transformation</span>
            </button>
            <button
              onClick={() => handleFrequencyChange(40)}
              className={`py-1.5 px-2 rounded text-xs font-semibold transition-all ${
                activeFreq === 40 
                  ? 'bg-cyan-600 text-white shadow-lg shadow-cyan-900/50' 
                  : 'bg-slate-800 hover:bg-slate-700 text-slate-300'
              }`}
            >
              40 Hz
              <span className="block text-[8px] font-normal opacity-80 truncate">Gamma Focus</span>
            </button>
          </div>
        </div>

        {/* 1-Click Teleporter Desk */}
        <div className="bg-slate-950/70 border border-slate-800 rounded-lg p-3 space-y-3">
          <h3 className="text-xs font-bold text-cyan-300 flex items-center gap-1.5">
            <span>🚀</span> Instant Agent Teleport Desk
          </h3>

          <div>
            <label className="text-[10px] uppercase tracking-wider text-slate-400 block mb-1">Target Agent</label>
            <select
              value={selectedAgent}
              onChange={(e) => setSelectedAgent(e.target.value)}
              className="w-full bg-slate-900 border border-slate-700 rounded px-2.5 py-1.5 text-xs text-white focus:outline-none focus:border-cyan-500"
            >
              {spatialState?.agents.map(a => (
                <option key={a.id} value={a.id}>
                  {getAgentEmoji(a.id)} {a.name} ({a.zone})
                </option>
              ))}
            </select>
          </div>

          <div className="grid grid-cols-2 gap-2">
            <button
              onClick={() => handleTeleport(selectedAgent, 'plaza')}
              className="py-1.5 px-2 rounded bg-cyan-950/80 hover:bg-cyan-900 border border-cyan-800/60 text-cyan-300 text-xs font-medium transition-all"
            >
              🏢 Send to Plaza
            </button>
            <button
              onClick={() => handleTeleport(selectedAgent, 'lounge')}
              className="py-1.5 px-2 rounded bg-purple-950/80 hover:bg-purple-900 border border-purple-800/60 text-purple-300 text-xs font-medium transition-all"
            >
              🎧 Send to Lounge
            </button>
          </div>

          <div className="pt-2 border-t border-slate-800/80 space-y-2">
            <div className="flex gap-2">
              <input
                type="number"
                min="0"
                max="100"
                value={targetX}
                onChange={e => setTargetX(Number(e.target.value))}
                placeholder="X (0-100)"
                className="w-1/2 bg-slate-900 border border-slate-700 rounded px-2 py-1 text-xs text-white"
              />
              <input
                type="number"
                min="0"
                max="100"
                value={targetY}
                onChange={e => setTargetY(Number(e.target.value))}
                placeholder="Y (0-100)"
                className="w-1/2 bg-slate-900 border border-slate-700 rounded px-2 py-1 text-xs text-white"
              />
            </div>
            <button
              onClick={() => handleMove(selectedAgent, targetX, targetY)}
              className="w-full py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium transition-colors"
            >
              Move to Exact Coordinates
            </button>
          </div>
        </div>

        {/* Selected Agent Quick Readout */}
        {selectedAgent && (
          <div className="p-3 bg-slate-950/40 rounded-lg border border-slate-800/60 text-[11px] text-slate-400">
            <span className="font-semibold text-slate-300">Active Selection:</span> {selectedAgent}
            {spatialState?.agents.find(a => a.id === selectedAgent) && (
              <div className="mt-1 space-y-0.5 font-mono text-[10px] text-slate-400">
                <div>Zone: <span className="text-cyan-400">{spatialState.agents.find(a => a.id === selectedAgent)?.zone}</span></div>
                <div>Coords: ({spatialState.agents.find(a => a.id === selectedAgent)?.x.toFixed(1)}, {spatialState.agents.find(a => a.id === selectedAgent)?.y.toFixed(1)})</div>
                <div>Role: <span className="text-purple-400">{spatialState.agents.find(a => a.id === selectedAgent)?.role}</span></div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
export default SpatialGrid;
