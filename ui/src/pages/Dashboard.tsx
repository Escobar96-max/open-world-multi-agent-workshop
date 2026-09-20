import React, { useState } from 'react';
import { ExecutiveChat } from '../components/ExecutiveChat';
import { TaskKanban } from '../components/TaskKanban';
import { SpatialGrid } from '../components/SpatialGrid';
import { VloneConsole } from '../components/VloneConsole';

type ActiveTab = 'c2_desk' | 'spatial_grid' | 'vlone_engine';

export const Dashboard: React.FC = () => {
  const [activeTab, setActiveTab] = useState<ActiveTab>('c2_desk');
  const [refreshKanbanKey, setRefreshKanbanKey] = useState<number>(0);

  const handleTaskCreated = () => {
    setRefreshKanbanKey(prev => prev + 1);
  };

  return (
    <div className="flex flex-col h-screen w-screen bg-slate-950 text-slate-100 overflow-hidden font-sans select-none">
      {/* Top Universal C2 Bar */}
      <header className="h-14 bg-slate-900/90 border-b border-slate-800 px-4 flex items-center justify-between shadow-lg z-20 backdrop-blur-md">
        <div className="flex items-center gap-3">
          <div className="h-8 w-8 rounded-lg bg-gradient-to-tr from-amber-500 via-rose-500 to-indigo-600 flex items-center justify-center text-white font-bold text-sm shadow-md">
            AG
          </div>
          <div>
            <div className="text-sm font-black tracking-wide bg-gradient-to-r from-amber-200 via-pink-300 to-indigo-300 bg-clip-text text-transparent">
              ANTIGRAVITY // UNIFIED C2 EXECUTIVE
            </div>
            <div className="text-[10px] text-slate-400 flex items-center gap-2">
              <span>Dual-Executive Desk:</span>
              <span className="text-amber-400 font-medium">👑 Orion Prime</span>
              <span>&</span>
              <span className="text-pink-400 font-medium">🌸 Nova</span>
            </div>
          </div>
        </div>

        {/* Center Tab Switcher */}
        <div className="flex items-center bg-slate-950 p-1 rounded-lg border border-slate-800 space-x-1">
          <button
            onClick={() => setActiveTab('c2_desk')}
            className={`px-3 py-1 rounded-md text-xs font-semibold transition-all flex items-center gap-1.5 ${
              activeTab === 'c2_desk'
                ? 'bg-slate-800 text-amber-300 shadow-sm'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
            }`}
          >
            <span>💬</span> Executive C2 Desk
          </button>
          <button
            onClick={() => setActiveTab('spatial_grid')}
            className={`px-3 py-1 rounded-md text-xs font-semibold transition-all flex items-center gap-1.5 ${
              activeTab === 'spatial_grid'
                ? 'bg-slate-800 text-cyan-300 shadow-sm'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
            }`}
          >
            <span>🪐</span> Spatial World & DJ
          </button>
          <button
            onClick={() => setActiveTab('vlone_engine')}
            className={`px-3 py-1 rounded-md text-xs font-semibold transition-all flex items-center gap-1.5 ${
              activeTab === 'vlone_engine'
                ? 'bg-slate-800 text-emerald-300 shadow-sm'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
            }`}
          >
            <span>⚡</span> VLONE Engine
          </button>
        </div>

        {/* Right Status Badges */}
        <div className="flex items-center gap-2.5 text-[11px]">
          <div className="flex items-center gap-1.5 bg-slate-950 px-2.5 py-1 rounded-md border border-purple-900/50 text-purple-300 font-mono">
            <span className="h-2 w-2 rounded-full bg-purple-400 animate-pulse"></span>
            432Hz Ambient
          </div>
          <div className="flex items-center gap-1.5 bg-slate-950 px-2.5 py-1 rounded-md border border-emerald-900/50 text-emerald-300 font-mono">
            <span className="h-2 w-2 rounded-full bg-emerald-400"></span>
            Vault: ./vault/
          </div>
        </div>
      </header>

      {/* Main View Container */}
      <main className="flex-1 overflow-hidden p-3 bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950">
        {activeTab === 'c2_desk' && (
          <div className="grid grid-cols-1 xl:grid-cols-12 gap-3 h-full overflow-hidden">
            {/* Executive Chat (7 cols) */}
            <div className="xl:col-span-7 h-full overflow-hidden">
              <ExecutiveChat onTaskCreated={handleTaskCreated} />
            </div>

            {/* Task Kanban Rail (5 cols) */}
            <div className="xl:col-span-5 h-full overflow-hidden">
              <TaskKanban refreshTrigger={refreshKanbanKey} />
            </div>
          </div>
        )}

        {activeTab === 'spatial_grid' && (
          <div className="h-full overflow-hidden">
            <SpatialGrid />
          </div>
        )}

        {activeTab === 'vlone_engine' && (
          <div className="h-full overflow-hidden">
            <VloneConsole />
          </div>
        )}
      </main>
    </div>
  );
};
export default Dashboard;
