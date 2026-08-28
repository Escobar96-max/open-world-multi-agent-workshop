import React, { useState, useEffect, useRef } from 'react';
import { 
  Folder, FileText, Hash, Link as LinkIcon, CheckSquare, Square, 
  Search, RefreshCw, Save, Edit3, Eye, Sparkles, Brain, Cpu, 
  ShieldAlert, Activity, GitBranch, ExternalLink, ChevronRight,
  Database, Info, Clock, UserCheck, Flame, CloudRain, Wind, Trees,
  Play, Pause, RotateCcw, Droplets
} from 'lucide-react';

const API_BASE = 'http://localhost:3001';

export default function AgentObsidianDashboard() {
  const [vaultConfig, setVaultConfig] = useState(null);
  const [files, setFiles] = useState([]);
  const [activeFile, setActiveFile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedTag, setSelectedTag] = useState(null);
  const [selectedAgent, setSelectedAgent] = useState(null);
  const [isEditing, setIsEditing] = useState(false);
  const [editContent, setEditContent] = useState('');
  const [graphData, setGraphData] = useState({ nodes: [], links: [] });
  const [activeTab, setActiveTab] = useState('ca-grid'); // 'ca-grid' | 'reader' | 'graph' | 'tasks'
  const [saveStatus, setSaveStatus] = useState(null);

  // Cellular Automata Simulation State
  const [caState, setCaState] = useState(null);
  const [caAutoPlay, setCaAutoPlay] = useState(true);
  const [caToolMode, setCaToolMode] = useState('fire'); // 'fire' | 'rain' | 'tree'

  const graphCanvasRef = useRef(null);
  const caCanvasRef = useRef(null);
  const caAutoRef = useRef(null);

  // Fetch all vault files & config from local Obsidian backend
  const loadVaultData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [configRes, filesRes, graphRes] = await Promise.all([
        fetch(`${API_BASE}/api/vault/config`),
        fetch(`${API_BASE}/api/vault/files`),
        fetch(`${API_BASE}/api/vault/graph`)
      ]);

      const config = await configRes.json();
      const filesData = await filesRes.json();
      const graph = await graphRes.json();

      setVaultConfig(config);
      setFiles(filesData.files || []);
      setGraphData(graph);

      if (filesData.files && filesData.files.length > 0 && !activeFile) {
        setActiveFile(filesData.files[0]);
        setEditContent(filesData.files[0].rawContent);
      }
    } catch (err) {
      console.error("Error loading vault:", err);
      setError("Could not connect to Obsidian Vault API.");
    } finally {
      setLoading(false);
    }
  };

  // Fetch Cellular Automata state
  const loadCAState = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/ca/state`);
      const json = await res.json();
      if (json.status === 'success') {
        setCaState(json.data);
      }
    } catch (err) {
      console.error("Error loading CA state:", err);
    }
  };

  const stepCA = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/ca/step`, { method: 'POST' });
      const json = await res.json();
      if (json.status === 'success') {
        setCaState(json.data);
      }
    } catch (err) {
      console.error("Error stepping CA:", err);
    }
  };

  const triggerFire = async (x = null, y = null) => {
    try {
      const res = await fetch(`${API_BASE}/api/ca/trigger-fire`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(x !== null && y !== null ? { x, y } : {})
      });
      const json = await res.json();
      if (json.status === 'success') {
        setCaState(json.data);
      }
    } catch (err) {
      console.error("Error triggering fire:", err);
    }
  };

  const toggleRain = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/ca/toggle-rain`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ active: !caState?.rainActive, intensity: 0.75 })
      });
      const json = await res.json();
      if (json.status === 'success') {
        setCaState(json.data);
      }
    } catch (err) {
      console.error("Error toggling rain:", err);
    }
  };

  const setWind = async (direction, speed = 1.2) => {
    try {
      const res = await fetch(`${API_BASE}/api/ca/set-wind`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ direction, speed })
      });
      const json = await res.json();
      if (json.status === 'success') {
        setCaState(json.data);
      }
    } catch (err) {
      console.error("Error setting wind:", err);
    }
  };

  const resetCA = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/ca/reset`, { method: 'POST' });
      const json = await res.json();
      if (json.status === 'success') {
        setCaState(json.data);
      }
    } catch (err) {
      console.error("Error resetting CA:", err);
    }
  };

  // Initial load
  useEffect(() => {
    loadVaultData();
    loadCAState();
  }, []);

  // Auto-play loop for Cellular Automata
  useEffect(() => {
    if (caAutoPlay && activeTab === 'ca-grid') {
      caAutoRef.current = setInterval(stepCA, 180);
    } else {
      if (caAutoRef.current) clearInterval(caAutoRef.current);
    }
    return () => {
      if (caAutoRef.current) clearInterval(caAutoRef.current);
    };
  }, [caAutoPlay, activeTab]);

  // Handle canvas click to spark fire or drop rain
  const handleCanvasClick = (e) => {
    if (!caCanvasRef.current || !caState) return;
    const rect = caCanvasRef.current.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const clickY = e.clientY - rect.top;

    const cellW = rect.width / caState.width;
    const cellH = rect.height / caState.height;

    const gx = Math.floor(clickX / cellW);
    const gy = Math.floor(clickY / cellH);

    if (caToolMode === 'fire') {
      triggerFire(gx, gy);
    } else if (caToolMode === 'rain') {
      toggleRain();
    }
  };

  // Render Cellular Automata Grid Canvas
  useEffect(() => {
    if (activeTab !== 'ca-grid' || !caCanvasRef.current || !caState) return;

    const canvas = caCanvasRef.current;
    const ctx = canvas.getContext('2d');
    const { width, height, grid, rainDrops, rainActive } = caState;

    const cellW = canvas.width / width;
    const cellH = canvas.height / height;

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Draw Grid Cells
    for (let y = 0; y < height; y++) {
      for (let x = 0; x < width; x++) {
        const cell = grid[y][x];
        const px = x * cellW;
        const py = y * cellH;

        if (cell === 1) {
          // Healthy Forest / Trees
          ctx.fillStyle = '#059669';
          ctx.fillRect(px, py, cellW, cellH);
          ctx.fillStyle = '#10b981';
          ctx.fillRect(px + 1, py + 1, cellW - 2, cellH - 2);
        } else if (cell === 2) {
          // Burning Fire / Wildfire
          const pulse = Math.sin(Date.now() * 0.01 + x + y) * 0.2;
          ctx.fillStyle = pulse > 0 ? '#ef4444' : '#f97316';
          ctx.fillRect(px, py, cellW, cellH);
          ctx.fillStyle = '#fef08a';
          ctx.fillRect(px + 2, py + 2, cellW - 4, cellH - 4);
        } else if (cell === 3) {
          // Charred Ash / Burnt Ground
          ctx.fillStyle = '#334155';
          ctx.fillRect(px, py, cellW, cellH);
          ctx.fillStyle = '#1e293b';
          ctx.fillRect(px + 1, py + 1, cellW - 2, cellH - 2);
        } else if (cell === 4) {
          // Lake / Water
          ctx.fillStyle = '#0284c7';
          ctx.fillRect(px, py, cellW, cellH);
          ctx.fillStyle = '#38bdf8';
          ctx.fillRect(px + 1, py + 1, cellW - 2, cellH - 2);
        } else if (cell === 5) {
          // Rock Barrier
          ctx.fillStyle = '#78716c';
          ctx.fillRect(px, py, cellW, cellH);
        } else {
          // Empty Soil
          ctx.fillStyle = '#0f172a';
          ctx.fillRect(px, py, cellW, cellH);
        }
      }
    }

    // Draw Raindrops & Storm Effect
    if (rainDrops && rainDrops.length > 0) {
      ctx.strokeStyle = '#38bdf8';
      ctx.lineWidth = 1.8;
      rainDrops.forEach(drop => {
        const rx = drop.x * cellW;
        const ry = drop.y * cellH;
        ctx.beginPath();
        ctx.moveTo(rx, ry);
        ctx.lineTo(rx + drop.vx * 3, ry + drop.vy * 4);
        ctx.stroke();
      });
    }

  }, [caState, activeTab]);

  // Update active file & edit content
  const selectFile = (file) => {
    setActiveFile(file);
    setEditContent(file.rawContent);
    setIsEditing(false);
  };

  const handleWikilinkClick = (target) => {
    const cleanTarget = target.replace(/\.md$/, '').toLowerCase();
    const found = files.find(f => 
      f.title.toLowerCase() === cleanTarget || 
      f.filename.replace(/\.md$/, '').toLowerCase() === cleanTarget
    );
    if (found) {
      selectFile(found);
      setActiveTab('reader');
    }
  };

  const saveFile = async () => {
    if (!activeFile) return;
    setSaveStatus('Saving...');
    try {
      const res = await fetch(`${API_BASE}/api/vault/save`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          path: activeFile.path,
          content: editContent
        })
      });
      const data = await res.json();
      if (data.status === 'success') {
        setSaveStatus('Saved!');
        setActiveFile(data.note);
        setIsEditing(false);
        loadVaultData();
        setTimeout(() => setSaveStatus(null), 2500);
      }
    } catch (err) {
      setSaveStatus('Save failed');
      setTimeout(() => setSaveStatus(null), 3000);
    }
  };

  const toggleTask = async (taskText, currentCompleted) => {
    if (!activeFile) return;
    const oldPattern = new RegExp(`-\\s*\\[${currentCompleted ? '[xX]' : ' '}\\]\\s*${escapeRegex(taskText)}`, 'g');
    const newReplacement = `- [${currentCompleted ? ' ' : 'x'}] ${taskText}`;
    const newRaw = activeFile.rawContent.replace(oldPattern, newReplacement);

    try {
      const res = await fetch(`${API_BASE}/api/vault/save`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          path: activeFile.path,
          content: newRaw
        })
      });
      const data = await res.json();
      if (data.status === 'success') {
        setActiveFile(data.note);
        setEditContent(data.note.rawContent);
        setFiles(prev => prev.map(f => f.path === data.note.path ? data.note : f));
      }
    } catch (err) {
      console.error("Failed to toggle task:", err);
    }
  };

  function escapeRegex(string) {
    return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  }

  const filteredFiles = files.filter(f => {
    const matchesSearch = searchQuery === '' || 
      f.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      f.rawContent.toLowerCase().includes(searchQuery.toLowerCase());
    
    const matchesTag = !selectedTag || f.tags.includes(selectedTag);
    const matchesAgent = !selectedAgent || (f.frontmatter.agent && f.frontmatter.agent.toLowerCase().includes(selectedAgent.toLowerCase()));

    return matchesSearch && matchesTag && matchesAgent;
  });

  const allTags = Array.from(new Set(files.flatMap(f => f.tags || [])));
  const allAgents = Array.from(new Set(files.map(f => f.frontmatter.agent).filter(Boolean)));
  const allTasks = files.flatMap(f => (f.tasks || []).map(t => ({ ...t, sourceFile: f })));

  return (
    <div className="flex flex-col h-screen w-full bg-[#090d16] text-slate-100 font-sans overflow-hidden">
      
      {/* TOP STATUS & VAULT HEADER */}
      <header className="h-14 border-b border-slate-800 bg-[#0c121e] px-6 flex items-center justify-between shrink-0">
        <div className="flex items-center space-x-3">
          <div className="p-1.5 bg-cyan-950 text-cyan-400 border border-cyan-700/60 rounded-lg flex items-center justify-center">
            <Brain className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="font-bold text-sm tracking-wide text-white">OBSIDIAN AGENT & PHYSICAL GRID HUB</h1>
              <span className="text-[10px] bg-emerald-950 text-emerald-400 border border-emerald-800 px-2 py-0.5 rounded font-mono flex items-center space-x-1">
                <span className="w-1.5 h-1.5 bg-emerald-400 rounded-full animate-pulse"></span>
                <span>PHYSICAL SIM LIVE</span>
              </span>
            </div>
            <p className="text-[11px] text-slate-400 font-mono truncate max-w-md">
              {vaultConfig?.vaultPath || 'Connecting to vault...'}
            </p>
          </div>
        </div>

        {/* Global Vault & CA Stats */}
        <div className="flex items-center space-x-6 text-xs font-mono">
          <div className="flex items-center space-x-2">
            <Trees className="w-3.5 h-3.5 text-emerald-400" />
            <span className="text-slate-400">Forest:</span>
            <span className="font-bold text-emerald-300">{caState?.stats?.treePercent || 0}%</span>
          </div>

          <div className="flex items-center space-x-2">
            <Flame className="w-3.5 h-3.5 text-rose-400" />
            <span className="text-slate-400">Fires:</span>
            <span className="font-bold text-rose-400">{caState?.stats?.burning || 0}</span>
          </div>

          <div className="flex items-center space-x-2">
            <CloudRain className="w-3.5 h-3.5 text-cyan-400" />
            <span className="text-slate-400">Rain:</span>
            <span className={`font-bold ${caState?.rainActive ? 'text-cyan-400 animate-pulse' : 'text-slate-500'}`}>
              {caState?.rainActive ? 'ACTIVE' : 'OFF'}
            </span>
          </div>

          <button 
            onClick={loadVaultData}
            title="Reload from local disk"
            className="p-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-md border border-slate-700 transition"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </header>

      {/* 3-COLUMN MAIN DASHBOARD WORKSPACE */}
      <div className="flex-1 flex overflow-hidden">
        
        {/* LEFT COLUMN: FILE TREE & TAG FILTERS (260px) */}
        <aside className="w-72 border-r border-slate-800/80 bg-[#0b0f19] flex flex-col shrink-0">
          
          {/* Search Box */}
          <div className="p-3 border-b border-slate-800">
            <div className="relative">
              <Search className="w-4 h-4 text-slate-400 absolute left-2.5 top-2.5" />
              <input 
                type="text"
                placeholder="Search notes, tags, memory..."
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                className="w-full bg-slate-900 border border-slate-700/80 rounded-lg pl-8 pr-3 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500 font-sans"
              />
            </div>
          </div>

          {/* Filter Pills (Agents & Tags) */}
          <div className="px-3 py-2 border-b border-slate-800 flex flex-col space-y-2">
            <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Filter by Agent</div>
            <div className="flex flex-wrap gap-1">
              <button 
                onClick={() => setSelectedAgent(null)}
                className={`text-[10px] px-2 py-0.5 rounded border transition ${!selectedAgent ? 'bg-cyan-500/20 text-cyan-300 border-cyan-500/50' : 'bg-slate-900 text-slate-400 border-slate-800'}`}
              >
                All
              </button>
              {allAgents.map(ag => (
                <button 
                  key={ag}
                  onClick={() => setSelectedAgent(selectedAgent === ag ? null : ag)}
                  className={`text-[10px] px-2 py-0.5 rounded border transition ${selectedAgent === ag ? 'bg-rose-500/20 text-rose-300 border-rose-500/50' : 'bg-slate-900 text-slate-400 border-slate-800'}`}
                >
                  {ag}
                </button>
              ))}
            </div>

            {allTags.length > 0 && (
              <>
                <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mt-1">Tags</div>
                <div className="flex flex-wrap gap-1 max-h-16 overflow-y-auto">
                  {allTags.map(tag => (
                    <button 
                      key={tag}
                      onClick={() => setSelectedTag(selectedTag === tag ? null : tag)}
                      className={`text-[10px] px-1.5 py-0.5 rounded border font-mono transition ${selectedTag === tag ? 'bg-cyan-950 text-cyan-300 border-cyan-600' : 'bg-slate-900 text-slate-500 border-slate-800'}`}
                    >
                      {tag}
                    </button>
                  ))}
                </div>
              </>
            )}
          </div>

          {/* Note List */}
          <div className="flex-1 overflow-y-auto p-2 space-y-1">
            <div className="text-[10px] font-bold text-slate-500 uppercase px-2 py-1">Vault Files ({filteredFiles.length})</div>
            {filteredFiles.map(file => {
              const isActive = activeFile && activeFile.path === file.path;
              return (
                <div 
                  key={file.path}
                  onClick={() => {
                    selectFile(file);
                    setActiveTab('reader');
                  }}
                  className={`p-2.5 rounded-lg cursor-pointer transition flex items-start space-x-2.5 border ${
                    isActive 
                      ? 'bg-slate-800/90 text-cyan-300 border-cyan-500/40 shadow-sm' 
                      : 'hover:bg-slate-900 text-slate-300 border-transparent'
                  }`}
                >
                  <FileText className={`w-4 h-4 mt-0.5 shrink-0 ${isActive ? 'text-cyan-400' : 'text-slate-500'}`} />
                  <div className="flex-1 min-w-0">
                    <div className="text-xs font-semibold truncate">{file.title}</div>
                    <div className="text-[10px] text-slate-500 truncate font-mono mt-0.5">{file.path}</div>
                    {file.frontmatter.agent && (
                      <span className="inline-block mt-1 text-[9px] bg-rose-950/60 text-rose-300 border border-rose-800/60 px-1 rounded">
                        {file.frontmatter.agent}
                      </span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </aside>

        {/* CENTER COLUMN: MAIN WORKSPACE (Flex-1) */}
        <main className="flex-1 flex flex-col bg-[#080c14] overflow-hidden">
          
          {/* Main Tab Navigation Bar */}
          <div className="h-12 border-b border-slate-800 bg-[#0d121f] px-6 flex items-center justify-between shrink-0">
            <div className="flex items-center space-x-3">
              <div className="flex bg-slate-900 border border-slate-800 rounded-lg p-0.5 text-xs font-medium">
                <button 
                  onClick={() => setActiveTab('ca-grid')}
                  className={`px-3.5 py-1 rounded-md transition flex items-center space-x-1.5 ${activeTab === 'ca-grid' ? 'bg-emerald-500 text-slate-950 font-bold shadow-sm' : 'text-slate-400 hover:text-white'}`}
                >
                  <Flame className="w-3.5 h-3.5" />
                  <span>Physical CA Grid</span>
                </button>
                <button 
                  onClick={() => setActiveTab('reader')}
                  className={`px-3.5 py-1 rounded-md transition ${activeTab === 'reader' ? 'bg-cyan-500 text-slate-950 font-bold shadow-sm' : 'text-slate-400 hover:text-white'}`}
                >
                  Document
                </button>
                <button 
                  onClick={() => setActiveTab('graph')}
                  className={`px-3.5 py-1 rounded-md transition ${activeTab === 'graph' ? 'bg-cyan-500 text-slate-950 font-bold shadow-sm' : 'text-slate-400 hover:text-white'}`}
                >
                  Memory Graph
                </button>
                <button 
                  onClick={() => setActiveTab('tasks')}
                  className={`px-3.5 py-1 rounded-md transition ${activeTab === 'tasks' ? 'bg-cyan-500 text-slate-950 font-bold shadow-sm' : 'text-slate-400 hover:text-white'}`}
                >
                  All Tasks
                </button>
              </div>
            </div>

            {/* Context Actions */}
            {activeTab === 'reader' && (
              <div className="flex items-center space-x-2">
                <button 
                  onClick={() => setIsEditing(!isEditing)}
                  className="flex items-center space-x-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold rounded-lg border border-slate-700 transition"
                >
                  {isEditing ? <Eye className="w-3.5 h-3.5" /> : <Edit3 className="w-3.5 h-3.5" />}
                  <span>{isEditing ? 'Preview' : 'Edit Note'}</span>
                </button>

                {isEditing && (
                  <button 
                    onClick={saveFile}
                    className="flex items-center space-x-1.5 px-3 py-1.5 bg-cyan-500 hover:bg-cyan-400 text-slate-950 text-xs font-bold rounded-lg transition"
                  >
                    <Save className="w-3.5 h-3.5" />
                    <span>{saveStatus || 'Save to Disk'}</span>
                  </button>
                )}
              </div>
            )}
          </div>

          {/* MAIN TAB CONTENT */}
          <div className="flex-1 overflow-y-auto p-6">
            
            {/* VIEW TAB 1: ENVIRONMENTAL CELLULAR AUTOMATA PHYSICAL GRID */}
            {activeTab === 'ca-grid' && (
              <div className="max-w-5xl mx-auto space-y-4">
                
                {/* Visual Viewport Card */}
                <div className="bg-slate-950 border border-slate-800 rounded-xl overflow-hidden shadow-2xl relative">
                  
                  {/* Viewport Top Bar */}
                  <div className="bg-slate-900/90 px-4 py-2.5 border-b border-slate-800 flex justify-between items-center text-xs">
                    <div className="flex items-center space-x-3">
                      <span className="font-bold text-emerald-400 flex items-center space-x-1.5">
                        <Trees className="w-4 h-4" />
                        <span>2D PHYSICAL GRID: WILDFIRE & RAIN SIMULATION</span>
                      </span>
                      <span className="text-[10px] bg-slate-800 text-slate-400 px-2 py-0.5 rounded font-mono">
                        Tick {caState?.tick || 0}
                      </span>
                    </div>

                    <div className="flex items-center space-x-3 text-[11px] font-mono">
                      <span className="text-emerald-400">🌲 Forest {caState?.stats?.treePercent}%</span>
                      <span className="text-rose-400">🔥 Fires {caState?.stats?.burning}</span>
                      <span className="text-slate-400">░ Ash {caState?.stats?.ashPercent}%</span>
                    </div>
                  </div>

                  {/* CA Canvas */}
                  <canvas 
                    ref={caCanvasRef} 
                    width={800} 
                    height={460}
                    onClick={handleCanvasClick}
                    className="w-full h-[460px] bg-[#090d16] block cursor-crosshair"
                    title="Click to spark fire or drop rain depending on selected tool"
                  />

                  {/* Canvas Click Hint */}
                  <div className="absolute bottom-3 left-3 bg-slate-950/80 backdrop-blur border border-slate-800 px-3 py-1.5 rounded-lg text-[10px] text-slate-400 font-mono flex items-center space-x-2">
                    <span className="text-amber-400">💡 Hint:</span>
                    <span>Click anywhere on the grid to {caToolMode === 'fire' ? 'ignite a wildfire spark 🔥' : 'toggle rainfall 🌧️'}</span>
                  </div>
                </div>

                {/* CA MISSION CONTROL PANEL */}
                <div className="bg-slate-900/90 p-4 rounded-xl border border-slate-800 flex flex-wrap items-center justify-between gap-4 shadow-md">
                  
                  {/* Execution Controls */}
                  <div className="flex items-center space-x-2">
                    <button 
                      onClick={() => setCaAutoPlay(!caAutoPlay)}
                      className={`px-4 py-2 rounded-lg font-bold text-xs flex items-center space-x-1.5 transition ${caAutoPlay ? 'bg-amber-500 hover:bg-amber-400 text-slate-950' : 'bg-emerald-500 hover:bg-emerald-400 text-slate-950'}`}
                    >
                      {caAutoPlay ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
                      <span>{caAutoPlay ? 'Pause' : 'Auto Play'}</span>
                    </button>

                    <button 
                      onClick={stepCA}
                      className="px-3.5 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold rounded-lg border border-slate-700 transition"
                    >
                      Step 1 Tick
                    </button>

                    <button 
                      onClick={resetCA}
                      className="p-2 bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white text-xs rounded-lg border border-slate-700 transition"
                      title="Reset Terrain"
                    >
                      <RotateCcw className="w-4 h-4" />
                    </button>
                  </div>

                  {/* Interactive Spawners */}
                  <div className="flex items-center space-x-2">
                    <button 
                      onClick={() => triggerFire()}
                      className="px-3.5 py-2 bg-rose-600 hover:bg-rose-500 text-white font-bold text-xs rounded-lg transition flex items-center space-x-1.5 shadow-md active:scale-95"
                    >
                      <Flame className="w-3.5 h-3.5" />
                      <span>Ignite Wildfire</span>
                    </button>

                    <button 
                      onClick={toggleRain}
                      className={`px-3.5 py-2 rounded-lg font-bold text-xs transition flex items-center space-x-1.5 shadow-md active:scale-95 ${caState?.rainActive ? 'bg-cyan-500 text-slate-950' : 'bg-cyan-950 text-cyan-300 border border-cyan-700'}`}
                    >
                      <CloudRain className="w-3.5 h-3.5" />
                      <span>{caState?.rainActive ? 'Stop Rain' : 'Summon Rainstorm'}</span>
                    </button>
                  </div>

                  {/* Wind Vector Controls */}
                  <div className="flex items-center space-x-1.5 text-xs">
                    <span className="text-slate-400 text-[10px] uppercase font-bold mr-1 flex items-center space-x-1">
                      <Wind className="w-3 h-3 text-cyan-400" />
                      <span>Wind:</span>
                    </span>
                    <button onClick={() => setWind([1, 0])} className="px-2 py-1 bg-slate-800 hover:bg-slate-700 text-cyan-300 text-xs rounded border border-slate-700 font-mono">East →</button>
                    <button onClick={() => setWind([-1, 0])} className="px-2 py-1 bg-slate-800 hover:bg-slate-700 text-cyan-300 text-xs rounded border border-slate-700 font-mono">West ←</button>
                    <button onClick={() => setWind([0, -1])} className="px-2 py-1 bg-slate-800 hover:bg-slate-700 text-cyan-300 text-xs rounded border border-slate-700 font-mono">North ↑</button>
                    <button onClick={() => setWind([0, 1])} className="px-2 py-1 bg-slate-800 hover:bg-slate-700 text-cyan-300 text-xs rounded border border-slate-700 font-mono">South ↓</button>
                  </div>

                </div>

              </div>
            )}

            {/* VIEW TAB 2: MARKDOWN DOCUMENT VIEWER & EDITOR */}
            {activeTab === 'reader' && activeFile && (
              <div className="max-w-4xl mx-auto space-y-6">
                
                {/* YAML Frontmatter Metadata Card */}
                {Object.keys(activeFile.frontmatter).length > 0 && (
                  <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 shadow-sm">
                    <div className="text-[10px] font-mono uppercase tracking-wider text-slate-500 mb-2 font-bold flex items-center space-x-1.5">
                      <Info className="w-3.5 h-3.5 text-cyan-400" />
                      <span>FRONTMATTER METADATA</span>
                    </div>
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                      {activeFile.frontmatter.agent && (
                        <div>
                          <span className="text-slate-500 block text-[10px]">AGENT:</span>
                          <span className="font-semibold text-rose-300">{activeFile.frontmatter.agent}</span>
                        </div>
                      )}
                      {activeFile.frontmatter.type && (
                        <div>
                          <span className="text-slate-500 block text-[10px]">TYPE:</span>
                          <span className="font-mono text-cyan-300">{activeFile.frontmatter.type}</span>
                        </div>
                      )}
                      {activeFile.frontmatter.status && (
                        <div>
                          <span className="text-slate-500 block text-[10px]">STATUS:</span>
                          <span className="font-semibold text-emerald-400 uppercase">{activeFile.frontmatter.status}</span>
                        </div>
                      )}
                      {activeFile.frontmatter.created && (
                        <div>
                          <span className="text-slate-500 block text-[10px]">CREATED:</span>
                          <span className="font-mono text-slate-300">{new Date(activeFile.frontmatter.created).toLocaleDateString()}</span>
                        </div>
                      )}
                    </div>

                    {activeFile.tags && activeFile.tags.length > 0 && (
                      <div className="flex flex-wrap gap-1.5 mt-3 pt-3 border-t border-slate-800">
                        {activeFile.tags.map(t => (
                          <span key={t} className="text-[10px] bg-slate-950 text-cyan-400 border border-cyan-800/50 px-2 py-0.5 rounded font-mono">
                            {t}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                {isEditing ? (
                  <div className="flex flex-col space-y-2">
                    <div className="text-xs text-slate-400 flex justify-between items-center">
                      <span>Editing raw markdown content in Obsidian format:</span>
                      <span className="font-mono text-[10px]">Autosave disabled • Press 'Save to Disk'</span>
                    </div>
                    <textarea 
                      value={editContent}
                      onChange={e => setEditContent(e.target.value)}
                      rows={22}
                      className="w-full bg-slate-950 border border-slate-700 rounded-xl p-4 font-mono text-xs text-slate-200 focus:outline-none focus:border-cyan-500 leading-relaxed resize-y"
                    />
                  </div>
                ) : (
                  <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-6 shadow-md text-slate-200 leading-relaxed text-sm space-y-4">
                    <MarkdownViewer 
                      body={activeFile.body} 
                      onWikilinkClick={handleWikilinkClick}
                      onTaskToggle={toggleTask}
                    />
                  </div>
                )}

              </div>
            )}

            {/* VIEW TAB 3: KNOWLEDGE GRAPH VISUALIZER */}
            {activeTab === 'graph' && (
              <div className="flex flex-col items-center justify-center h-full">
                <div className="w-full max-w-4xl bg-slate-950 border border-slate-800 rounded-xl overflow-hidden shadow-2xl relative">
                  <div className="bg-slate-900/80 px-4 py-2 border-b border-slate-800 flex justify-between items-center text-xs">
                    <span className="font-bold text-slate-200 flex items-center space-x-2">
                      <GitBranch className="w-4 h-4 text-cyan-400" />
                      <span>OBSIDIAN KNOWLEDGE GRAPH NETWORK</span>
                    </span>
                    <span className="text-[11px] text-slate-400 font-mono">
                      {graphData.nodes.length} Nodes • {graphData.links.length} Wikilink Connections
                    </span>
                  </div>
                  <canvas 
                    ref={graphCanvasRef} 
                    width={800} 
                    height={460} 
                    className="w-full h-[460px] bg-[#070b12] block"
                  />
                </div>
              </div>
            )}

            {/* VIEW TAB 4: GLOBAL TASK CHECKLIST */}
            {activeTab === 'tasks' && (
              <div className="max-w-3xl mx-auto space-y-4">
                <div className="flex justify-between items-center pb-2 border-b border-slate-800">
                  <h2 className="font-bold text-base text-white">Vault-Wide Agent Tasks</h2>
                  <span className="text-xs text-slate-400 font-mono">
                    {allTasks.filter(t => t.completed).length} of {allTasks.length} Completed
                  </span>
                </div>

                <div className="space-y-2">
                  {allTasks.map((t, idx) => (
                    <div 
                      key={idx}
                      className="bg-slate-900/80 border border-slate-800 p-3 rounded-lg flex items-center justify-between hover:border-slate-700 transition"
                    >
                      <div className="flex items-center space-x-3">
                        <button 
                          onClick={() => {
                            setActiveFile(t.sourceFile);
                            toggleTask(t.text, t.completed);
                          }}
                          className="text-cyan-400 hover:text-cyan-300"
                        >
                          {t.completed ? <CheckSquare className="w-4 h-4 text-emerald-400" /> : <Square className="w-4 h-4 text-slate-500" />}
                        </button>
                        <span className={`text-xs ${t.completed ? 'line-through text-slate-500' : 'text-slate-200'}`}>
                          {t.text}
                        </span>
                      </div>
                      <span 
                        onClick={() => {
                          selectFile(t.sourceFile);
                          setActiveTab('reader');
                        }}
                        className="text-[10px] text-cyan-400 font-mono hover:underline cursor-pointer flex items-center space-x-1"
                      >
                        <span>{t.sourceFile.title}</span>
                        <ChevronRight className="w-3 h-3" />
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

          </div>
        </main>

        {/* RIGHT COLUMN: LINKED MENTIONS & METRICS (280px) */}
        {activeTab === 'reader' && activeFile && (
          <aside className="w-72 border-l border-slate-800/80 bg-[#0b0f19] flex flex-col p-4 space-y-5 shrink-0 overflow-y-auto">
            <div>
              <div className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center space-x-1.5 mb-2.5">
                <LinkIcon className="w-3.5 h-3.5 text-cyan-400" />
                <span>Outgoing Wikilinks ({activeFile.wikilinks.length})</span>
              </div>
              {activeFile.wikilinks.length === 0 ? (
                <div className="text-xs text-slate-600 italic">No outgoing links in this note.</div>
              ) : (
                <div className="space-y-1.5">
                  {activeFile.wikilinks.map((wl, idx) => (
                    <button
                      key={idx}
                      onClick={() => handleWikilinkClick(wl.target)}
                      className="w-full text-left p-2 rounded bg-slate-900/80 hover:bg-slate-800 border border-slate-800/80 hover:border-cyan-500/40 text-xs text-cyan-300 font-mono transition flex items-center justify-between group"
                    >
                      <span className="truncate">[[{wl.alias || wl.target}]]</span>
                      <ExternalLink className="w-3 h-3 text-slate-500 group-hover:text-cyan-400" />
                    </button>
                  ))}
                </div>
              )}
            </div>

            <div>
              <div className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center space-x-1.5 mb-2.5">
                <GitBranch className="w-3.5 h-3.5 text-rose-400" />
                <span>Inbound Backlinks</span>
              </div>
              {(() => {
                const activeId = activeFile.filename.replace(/\.md$/, '').toLowerCase();
                const backlinks = files.filter(f => 
                  f.path !== activeFile.path &&
                  f.wikilinks.some(w => w.target.replace(/\.md$/, '').toLowerCase() === activeId)
                );

                if (backlinks.length === 0) {
                  return <div className="text-xs text-slate-600 italic">No inbound links referencing this note.</div>;
                }

                return (
                  <div className="space-y-1.5">
                    {backlinks.map((bf) => (
                      <button
                        key={bf.path}
                        onClick={() => {
                          selectFile(bf);
                          setActiveTab('reader');
                        }}
                        className="w-full text-left p-2 rounded bg-slate-900/80 hover:bg-slate-800 border border-slate-800/80 hover:border-rose-500/40 text-xs text-rose-300 font-mono transition flex items-center justify-between group"
                      >
                        <span className="truncate">{bf.title}</span>
                        <ChevronRight className="w-3 h-3 text-slate-500 group-hover:text-rose-400" />
                      </button>
                    ))}
                  </div>
                );
              })()}
            </div>

            <div className="pt-4 border-t border-slate-800/80 text-[11px] space-y-2 text-slate-400">
              <div className="flex justify-between">
                <span>File Size:</span>
                <span className="font-mono text-slate-200">{activeFile.size} bytes</span>
              </div>
              <div className="flex justify-between">
                <span>Tasks in Note:</span>
                <span className="font-mono text-slate-200">{activeFile.tasks.length}</span>
              </div>
              <div className="flex justify-between">
                <span>Last Modified:</span>
                <span className="font-mono text-slate-200">{new Date(activeFile.modifiedAt).toLocaleTimeString()}</span>
              </div>
            </div>
          </aside>
        )}

      </div>
    </div>
  );
}

function MarkdownViewer({ body, onWikilinkClick, onTaskToggle }) {
  const lines = body.split(/\r?\n/);

  return (
    <div className="space-y-2 font-sans">
      {lines.map((line, idx) => {
        if (line.startsWith('# ')) {
          return <h1 key={idx} className="text-xl font-bold text-white border-b border-slate-800 pb-2 mt-4">{renderInlineElements(line.slice(2), onWikilinkClick)}</h1>;
        }
        if (line.startsWith('## ')) {
          return <h2 key={idx} className="text-base font-bold text-cyan-400 mt-4">{renderInlineElements(line.slice(3), onWikilinkClick)}</h2>;
        }
        if (line.startsWith('### ')) {
          return <h3 key={idx} className="text-sm font-semibold text-slate-200 mt-3">{renderInlineElements(line.slice(4), onWikilinkClick)}</h3>;
        }

        const taskMatch = line.match(/^\s*-\s*\[([ xX])\]\s*(.*)$/);
        if (taskMatch) {
          const completed = taskMatch[1].toLowerCase() === 'x';
          const text = taskMatch[2];
          return (
            <div key={idx} className="flex items-center space-x-2.5 py-1">
              <button 
                onClick={() => onTaskToggle(text, completed)}
                className="text-cyan-400 hover:text-cyan-300 mt-0.5"
              >
                {completed ? <CheckSquare className="w-4 h-4 text-emerald-400" /> : <Square className="w-4 h-4 text-slate-500" />}
              </button>
              <span className={`text-xs ${completed ? 'line-through text-slate-500' : 'text-slate-200'}`}>
                {renderInlineElements(text, onWikilinkClick)}
              </span>
            </div>
          );
        }

        if (line.startsWith('- ')) {
          return (
            <div key={idx} className="flex items-start space-x-2 text-xs py-0.5 text-slate-300">
              <span className="text-cyan-400 font-bold">•</span>
              <span>{renderInlineElements(line.slice(2), onWikilinkClick)}</span>
            </div>
          );
        }

        if (!line.trim()) {
          return <div key={idx} className="h-2" />;
        }

        return (
          <p key={idx} className="text-xs text-slate-300 leading-relaxed">
            {renderInlineElements(line, onWikilinkClick)}
          </p>
        );
      })}
    </div>
  );
}

function renderInlineElements(text, onWikilinkClick) {
  const parts = [];
  const regex = /\[\[(.*?)\]\]|\*\*(.*?)\*\*|`([^`]+)`/g;
  let lastIndex = 0;
  let match;

  while ((match = regex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push(text.substring(lastIndex, match.index));
    }

    if (match[1]) {
      const [target, alias] = match[1].split('|');
      parts.push(
        <button
          key={match.index}
          onClick={() => onWikilinkClick(target)}
          className="text-cyan-400 hover:text-cyan-300 font-mono bg-cyan-950/60 border border-cyan-800/60 px-1.5 py-0.5 rounded text-[11px] transition inline-flex items-center space-x-0.5 mx-0.5"
        >
          <span>[[{alias || target}]]</span>
        </button>
      );
    } else if (match[2]) {
      parts.push(<strong key={match.index} className="font-bold text-white">{match[2]}</strong>);
    } else if (match[3]) {
      parts.push(<code key={match.index} className="bg-slate-950 text-rose-300 px-1.5 py-0.5 rounded font-mono text-[11px] border border-slate-800">{match[3]}</code>);
    }

    lastIndex = regex.lastIndex;
  }

  if (lastIndex < text.length) {
    parts.push(text.substring(lastIndex));
  }

  return parts;
}
