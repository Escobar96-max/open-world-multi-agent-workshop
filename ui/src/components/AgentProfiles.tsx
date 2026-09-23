import React, { useState, useEffect } from 'react';
import { 
  Bot, 
  Sparkles, 
  Play, 
  CheckCircle2, 
  Clock, 
  Globe, 
  Youtube, 
  FlaskConical, 
  BookOpen, 
  Flame, 
  Cpu, 
  Check, 
  ChevronRight, 
  Terminal,
  Activity
} from 'lucide-react';

interface AgentProfile {
  agent_id: string;
  name: string;
  icon: string;
  role: string;
  specialized_in: string;
  responsibilities: string;
  current_topic: string;
  task_challenge: string;
  progress_pct: number;
  current_stage: string;
  stages_completed: {
    web_docs?: boolean;
    youtube_transcript?: boolean;
    soup_pytest?: boolean;
    vault_persisted?: boolean;
  };
  logs: string[];
  acquired_skills: string[];
  vault_path: string;
}

export const AgentProfiles: React.FC = () => {
  const [agents, setAgents] = useState<AgentProfile[]>([]);
  const [selectedAgentId, setSelectedAgentId] = useState<string>('Bob');
  const [topicInput, setTopicInput] = useState<string>('');
  const [taskInput, setTaskInput] = useState<string>('');
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [feedbackMsg, setFeedbackMsg] = useState<string | null>(null);

  const fetchAgents = async () => {
    try {
      const res = await fetch('http://127.0.0.1:8000/api/v1/training/agents');
      if (res.ok) {
        const data = await res.json();
        setAgents(data);
        if (data.length > 0 && !selectedAgentId) {
          setSelectedAgentId(data[0].agent_id);
        }
      }
    } catch (err) {
      console.error('Failed to fetch agent profiles:', err);
    }
  };

  useEffect(() => {
    fetchAgents();
  }, []);

  // Poll when any agent is actively training
  useEffect(() => {
    const isAnyTraining = agents.some(a => a.progress_pct > 0 && a.progress_pct < 100);
    const intervalTime = isAnyTraining ? 1500 : 4000;

    const timer = setInterval(() => {
      fetchAgents();
    }, intervalTime);

    return () => clearInterval(timer);
  }, [agents]);

  const selectedAgent = agents.find(a => a.agent_id === selectedAgentId) || agents[0];

  const handleStartTraining = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!topicInput.trim() || !selectedAgent) return;

    setIsSubmitting(true);
    setFeedbackMsg(null);
    try {
      const res = await fetch('http://127.0.0.1:8000/api/v1/training/assign', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          agent_id: selectedAgent.agent_id,
          topic: topicInput.trim(),
          task: taskInput.trim() || 'Verify architectural implementation and solve test suite'
        })
      });

      if (res.ok) {
        setFeedbackMsg(`🚀 Training initiated for ${selectedAgent.name}! Ingesting Web + YouTube + Soup Zero.`);
        setTopicInput('');
        setTaskInput('');
        fetchAgents();
      } else {
        const err = await res.json();
        setFeedbackMsg(`⚠️ Error: ${err.detail || 'Failed to start training'}`);
      }
    } catch (err: any) {
      setFeedbackMsg(`⚠️ Network error: ${err.message}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  const activeTrainingCount = agents.filter(a => a.progress_pct > 0 && a.progress_pct < 100).length;

  return (
    <div className="h-full flex flex-col bg-slate-950 text-slate-100 rounded-xl border border-slate-800 shadow-2xl overflow-hidden font-sans">
      {/* Top Header Bar */}
      <div className="h-14 px-5 bg-slate-900/80 border-b border-slate-800/80 flex items-center justify-between backdrop-blur-md">
        <div className="flex items-center gap-3">
          <div className="h-8 w-8 rounded-lg bg-indigo-600/30 border border-indigo-500/40 flex items-center justify-center text-indigo-400">
            <Bot className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-sm font-black tracking-wider uppercase bg-gradient-to-r from-cyan-400 via-indigo-300 to-purple-400 bg-clip-text text-transparent">
              🎴 Agent Profiles & Training Ground
            </h2>
            <p className="text-[11px] text-slate-400">
              Multi-Source Ingestion: Google Web Docs ➔ YouTube Transcripts ➔ Soup Zero Deterministic RLVR Sandbox
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-[11px] px-3 py-1 rounded-full bg-slate-950 border border-slate-800 text-slate-300 font-mono">
            Active Agents: <strong className="text-indigo-400">{agents.length}</strong>
          </span>
          <span className={`text-[11px] px-3 py-1 rounded-full border font-mono flex items-center gap-1.5 ${
            activeTrainingCount > 0
              ? 'bg-amber-950/60 border-amber-700/80 text-amber-300'
              : 'bg-slate-950 border-slate-800 text-slate-400'
          }`}>
            <span className={`w-1.5 h-1.5 rounded-full ${activeTrainingCount > 0 ? 'bg-amber-400 animate-ping' : 'bg-slate-600'}`}></span>
            Training In-Flight: <strong>{activeTrainingCount}</strong>
          </span>
        </div>
      </div>

      {/* Main Split Grid */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-12 overflow-hidden">
        {/* Left Column: Agent Roster */}
        <div className="lg:col-span-4 border-r border-slate-800/80 bg-slate-950/60 flex flex-col overflow-hidden">
          <div className="p-3 bg-slate-900/40 border-b border-slate-800/60 flex items-center justify-between">
            <span className="text-xs font-bold text-slate-300 flex items-center gap-1.5">
              <span>👥</span> Agent Roster
            </span>
            <span className="text-[10px] text-slate-500 uppercase tracking-widest font-mono">Select to Inspect</span>
          </div>

          <div className="flex-1 overflow-y-auto p-2.5 space-y-2">
            {agents.map((agent) => {
              const isSelected = selectedAgent?.agent_id === agent.agent_id;
              const isTraining = agent.progress_pct > 0 && agent.progress_pct < 100;
              const isCompleted = agent.progress_pct === 100;

              return (
                <button
                  key={agent.agent_id}
                  onClick={() => {
                    setSelectedAgentId(agent.agent_id);
                    setFeedbackMsg(null);
                  }}
                  className={`w-full text-left p-3 rounded-xl border transition-all duration-200 flex items-center justify-between group ${
                    isSelected
                      ? 'bg-indigo-950/40 border-indigo-500/60 shadow-lg shadow-indigo-950/50 scale-[1.01]'
                      : 'bg-slate-900/40 border-slate-800/60 hover:bg-slate-900 hover:border-slate-700 text-slate-300'
                  }`}
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <div className="h-9 w-9 rounded-lg bg-slate-800 border border-slate-700 flex items-center justify-center text-lg flex-shrink-0 shadow-inner">
                      {agent.icon || '🤖'}
                    </div>
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-bold text-slate-100 truncate">
                          {agent.name}
                        </span>
                        {isSelected && (
                          <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse"></span>
                        )}
                      </div>
                      <p className="text-[11px] text-slate-400 truncate">
                        {agent.role}
                      </p>
                    </div>
                  </div>

                  <div className="flex flex-col items-end gap-1 flex-shrink-0 ml-2">
                    {isTraining ? (
                      <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded-full bg-amber-950/80 border border-amber-600/70 text-amber-300 flex items-center gap-1 animate-pulse">
                        <Flame className="w-2.5 h-2.5 text-amber-400" />
                        {agent.progress_pct}%
                      </span>
                    ) : isCompleted ? (
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-emerald-950/80 border border-emerald-700/80 text-emerald-300 flex items-center gap-1">
                        <Check className="w-2.5 h-2.5" />
                        Trained
                      </span>
                    ) : (
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-slate-800/80 border border-slate-700/60 text-slate-400">
                        Idle
                      </span>
                    )}

                    {isTraining && (
                      <div className="w-14 h-1.5 bg-slate-800 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-gradient-to-r from-amber-500 to-cyan-400 transition-all duration-300"
                          style={{ width: `${agent.progress_pct}%` }}
                        ></div>
                      </div>
                    )}
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* Right Column: Inspector & Training Suite */}
        <div className="lg:col-span-8 flex flex-col overflow-y-auto bg-slate-900/20">
          {selectedAgent ? (
            <div className="p-5 space-y-5">
              {/* Agent Overview Header */}
              <div className="p-4 rounded-xl bg-gradient-to-r from-slate-900 via-indigo-950/30 to-slate-900 border border-slate-800 flex items-start justify-between shadow-md">
                <div className="flex items-center gap-4">
                  <div className="h-14 w-14 rounded-2xl bg-indigo-900/30 border border-indigo-500/40 flex items-center justify-center text-3xl shadow-lg">
                    {selectedAgent.icon || '🤖'}
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <h3 className="text-lg font-black text-white">
                        {selectedAgent.name}
                      </h3>
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-indigo-950 border border-indigo-700/60 text-indigo-300">
                        {selectedAgent.role}
                      </span>
                    </div>
                    <p className="text-xs text-slate-300 mt-1">
                      <strong className="text-slate-400">Specialization:</strong> {selectedAgent.specialized_in}
                    </p>
                    <p className="text-[11px] text-slate-400 mt-0.5">
                      <strong className="text-slate-500">Core Scope:</strong> {selectedAgent.responsibilities}
                    </p>
                  </div>
                </div>

                <div className="text-right">
                  <span className="text-[10px] uppercase tracking-wider text-slate-500 block font-mono">Cognitive Status</span>
                  <span className={`text-xs font-bold font-mono px-2.5 py-1 rounded-md inline-block mt-1 ${
                    selectedAgent.progress_pct > 0 && selectedAgent.progress_pct < 100
                      ? 'bg-amber-950/80 text-amber-300 border border-amber-700'
                      : 'bg-emerald-950/60 text-emerald-300 border border-emerald-800'
                  }`}>
                    {selectedAgent.progress_pct > 0 && selectedAgent.progress_pct < 100 ? '⚡ ACTIVE TRAINING' : 'ACTIVE / IDLE'}
                  </span>
                </div>
              </div>

              {/* Acquired Skills Badges */}
              <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800/80 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-slate-300 flex items-center gap-1.5">
                    <BookOpen className="w-3.5 h-3.5 text-cyan-400" />
                    Obsidian Vault Verified Skills (#skill_acquired)
                  </span>
                  <span className="text-[10px] font-mono text-slate-500">
                    {selectedAgent.acquired_skills.length} Certified Masteries
                  </span>
                </div>
                <div className="flex flex-wrap gap-2 pt-1">
                  {selectedAgent.acquired_skills.length > 0 ? (
                    selectedAgent.acquired_skills.map((skill, idx) => (
                      <span
                        key={idx}
                        className="text-[11px] px-2.5 py-1 rounded-lg bg-indigo-950/50 border border-indigo-700/60 text-indigo-200 flex items-center gap-1.5 shadow-sm"
                      >
                        <Sparkles className="w-3 h-3 text-cyan-400" />
                        {skill}
                      </span>
                    ))
                  ) : (
                    <span className="text-xs text-slate-500 italic">
                      No external certifications logged yet. Assign a training topic below to ingest knowledge.
                    </span>
                  )}
                </div>
              </div>

              {/* Active Training Status & Progress */}
              <div className="p-4 rounded-xl bg-slate-950/90 border border-slate-800 space-y-4 shadow-lg">
                <div className="flex items-center justify-between">
                  <div>
                    <span className="text-xs uppercase tracking-wider text-slate-500 font-mono block">Current Ingestion Topic</span>
                    <h4 className="text-sm font-bold text-cyan-300 flex items-center gap-2 mt-0.5">
                      <Cpu className="w-4 h-4 text-cyan-400" />
                      "{selectedAgent.current_topic}"
                    </h4>
                  </div>
                  <div className="text-right">
                    <span className="text-xs font-mono font-black text-emerald-400 text-base">
                      {selectedAgent.progress_pct}%
                    </span>
                    <span className="text-[10px] text-slate-400 block font-mono">
                      {selectedAgent.current_stage}
                    </span>
                  </div>
                </div>

                {/* Main Visual Progress Bar */}
                <div className="space-y-1.5">
                  <div className="w-full h-3 bg-slate-900 rounded-full border border-slate-800 overflow-hidden p-0.5">
                    <div
                      className="h-full rounded-full bg-gradient-to-r from-cyan-500 via-indigo-500 to-emerald-400 transition-all duration-500 shadow-md shadow-cyan-900/50"
                      style={{ width: `${selectedAgent.progress_pct}%` }}
                    ></div>
                  </div>
                </div>

                {/* 3-Tier Multi-Source Pipeline Stages */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-2.5 pt-1">
                  {/* Stage 1: Web Docs */}
                  <div className={`p-2.5 rounded-lg border text-xs flex items-center gap-2.5 ${
                    selectedAgent.stages_completed?.web_docs
                      ? 'bg-emerald-950/40 border-emerald-700/60 text-emerald-200'
                      : selectedAgent.progress_pct > 0 && selectedAgent.progress_pct < 35
                      ? 'bg-amber-950/40 border-amber-700/60 text-amber-200 animate-pulse'
                      : 'bg-slate-900/60 border-slate-800 text-slate-400'
                  }`}>
                    <Globe className="w-4 h-4 flex-shrink-0" />
                    <div className="min-w-0">
                      <div className="font-semibold flex items-center gap-1">
                        1. Google Docs Sweep
                        {selectedAgent.stages_completed?.web_docs && <CheckCircle2 className="w-3 h-3 text-emerald-400" />}
                      </div>
                      <span className="text-[10px] opacity-75">Vlone Semantic Ingest</span>
                    </div>
                  </div>

                  {/* Stage 2: YouTube Transcripts */}
                  <div className={`p-2.5 rounded-lg border text-xs flex items-center gap-2.5 ${
                    selectedAgent.stages_completed?.youtube_transcript
                      ? 'bg-emerald-950/40 border-emerald-700/60 text-emerald-200'
                      : selectedAgent.progress_pct >= 35 && selectedAgent.progress_pct < 70
                      ? 'bg-amber-950/40 border-amber-700/60 text-amber-200 animate-pulse'
                      : 'bg-slate-900/60 border-slate-800 text-slate-400'
                  }`}>
                    <Youtube className="w-4 h-4 flex-shrink-0" />
                    <div className="min-w-0">
                      <div className="font-semibold flex items-center gap-1">
                        2. YouTube Transcripts
                        {selectedAgent.stages_completed?.youtube_transcript && <CheckCircle2 className="w-3 h-3 text-emerald-400" />}
                      </div>
                      <span className="text-[10px] opacity-75">Code Pattern Digest</span>
                    </div>
                  </div>

                  {/* Stage 3: Soup Zero RLVR */}
                  <div className={`p-2.5 rounded-lg border text-xs flex items-center gap-2.5 ${
                    selectedAgent.stages_completed?.soup_pytest
                      ? 'bg-emerald-950/40 border-emerald-700/60 text-emerald-200'
                      : selectedAgent.progress_pct >= 70 && selectedAgent.progress_pct < 100
                      ? 'bg-amber-950/40 border-amber-700/60 text-amber-200 animate-pulse'
                      : 'bg-slate-900/60 border-slate-800 text-slate-400'
                  }`}>
                    <FlaskConical className="w-4 h-4 flex-shrink-0" />
                    <div className="min-w-0">
                      <div className="font-semibold flex items-center gap-1">
                        3. Soup Zero Sandbox
                        {selectedAgent.stages_completed?.soup_pytest && <CheckCircle2 className="w-3 h-3 text-emerald-400" />}
                      </div>
                      <span className="text-[10px] opacity-75">AST Deterministic Pytest</span>
                    </div>
                  </div>
                </div>

                {/* Backstage Training Log Output */}
                {selectedAgent.logs && selectedAgent.logs.length > 0 && (
                  <div className="bg-slate-950 border border-slate-800 rounded-lg p-2.5 space-y-1">
                    <span className="text-[10px] font-mono text-slate-400 uppercase tracking-widest flex items-center gap-1">
                      <Terminal className="w-3 h-3 text-emerald-400" />
                      Live Training Telemetry
                    </span>
                    <div className="font-mono text-[11px] text-slate-300 space-y-1 max-h-24 overflow-y-auto">
                      {selectedAgent.logs.map((log, lIdx) => (
                        <div key={lIdx} className="leading-relaxed">
                          {log}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* Assignment Form */}
              <div className="p-4 rounded-xl bg-slate-950/80 border border-slate-800/80 space-y-3 shadow-md">
                <span className="text-xs font-bold text-slate-200 flex items-center gap-2">
                  <Play className="w-3.5 h-3.5 text-emerald-400" />
                  Assign New Training Topic & Task Challenge
                </span>

                <form onSubmit={handleStartTraining} className="space-y-3">
                  <div>
                    <label className="text-[11px] font-mono text-slate-400 block mb-1">
                      Training Topic (e.g. FastAPI Async WebSockets Optimization)
                    </label>
                    <input
                      type="text"
                      value={topicInput}
                      onChange={(e) => setTopicInput(e.target.value)}
                      placeholder="Enter topic name..."
                      className="w-full bg-slate-900 border border-slate-700/80 rounded-lg px-3.5 py-2 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-cyan-500 transition-colors"
                      required
                    />
                  </div>

                  <div>
                    <label className="text-[11px] font-mono text-slate-400 block mb-1">
                      Practical Task Challenge for Soup Zero Verification
                    </label>
                    <input
                      type="text"
                      value={taskInput}
                      onChange={(e) => setTaskInput(e.target.value)}
                      placeholder="e.g. Implement low-latency broadcast loop with AST test validation..."
                      className="w-full bg-slate-900 border border-slate-700/80 rounded-lg px-3.5 py-2 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-cyan-500 transition-colors"
                    />
                  </div>

                  {feedbackMsg && (
                    <div className="p-2 rounded-lg bg-slate-900 border border-indigo-700/50 text-xs text-indigo-300 font-mono">
                      {feedbackMsg}
                    </div>
                  )}

                  <div className="flex items-center justify-between pt-1">
                    <div className="flex items-center gap-2">
                      <span className="text-[11px] text-slate-400">
                        Targeting: <strong className="text-white">{selectedAgent.name}</strong>
                      </span>
                    </div>

                    <button
                      type="submit"
                      disabled={isSubmitting || !topicInput.trim()}
                      className="px-4 py-2 bg-gradient-to-r from-emerald-600 via-teal-600 to-cyan-600 hover:from-emerald-500 hover:to-cyan-500 text-white rounded-lg text-xs font-bold flex items-center gap-2 shadow-lg shadow-emerald-950/60 disabled:opacity-50 transition-all hover:scale-[1.02] active:scale-[0.98]"
                    >
                      {isSubmitting ? (
                        <>
                          <Activity className="w-3.5 h-3.5 animate-spin" />
                          <span>Dispatching...</span>
                        </>
                      ) : (
                        <>
                          <span>🚀</span>
                          <span>Launch YouTube + Web + Soup Training</span>
                        </>
                      )}
                    </button>
                  </div>
                </form>
              </div>
            </div>
          ) : (
            <div className="h-full flex items-center justify-center text-slate-500 text-xs font-mono">
              Select an agent from the roster to inspect profile and assign training.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
