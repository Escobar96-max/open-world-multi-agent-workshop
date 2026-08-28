import React, { useState } from 'react';
import OpenWorldVisualizer from './open-world-visualizer';
import AgentObsidianDashboard from './agent-obsidian-dashboard';

export default function App() {
  const [viewMode, setViewMode] = useState('open-world'); // 'open-world' | 'vault-dashboard'

  return (
    <div className="w-screen h-screen bg-[#070b14] overflow-hidden">
      {viewMode === 'open-world' ? (
        <OpenWorldVisualizer onOpenFullVault={() => setViewMode('vault-dashboard')} />
      ) : (
        <div className="flex flex-col h-screen">
          <div className="bg-[#0b0f19] border-b border-slate-800 px-4 py-2 flex justify-between items-center text-xs">
            <span className="font-bold text-cyan-400 font-mono">OBSIDIAN VAULT & KNOWLEDGE GRAPH VIEW</span>
            <button
              onClick={() => setViewMode('open-world')}
              className="px-3 py-1 bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold rounded-lg transition text-xs font-mono"
            >
              ← Back to Open World Visualizer
            </button>
          </div>
          <div className="flex-1 overflow-hidden">
            <AgentObsidianDashboard />
          </div>
        </div>
      )}
    </div>
  );
}
