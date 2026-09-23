import React, { useState, useEffect, useRef } from 'react';
import { Send, Sparkles, Shield, Compass, CheckCircle2, MessageSquare, Terminal, ExternalLink, Volume2 } from 'lucide-react';
import { VoiceController, playAgentVoice } from './VoiceController';

interface ChatMessage {
  id: string;
  timestamp: string;
  prompt?: string;
  operator?: string;
  responder?: string;
  sender?: string;
  orion_response?: string | null;
  nova_response?: string | null;
  tasks: any[];
  obsidian_vault_note?: string;
  type?: string;
  action_required?: {
    action: string;
    task_id: string;
  };
  options?: string[];
}

interface Props {
  onTaskCreated?: () => void;
}

export const ExecutiveChat: React.FC<Props> = ({ onTaskCreated }) => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputPrompt, setInputPrompt] = useState('');
  const [loading, setLoading] = useState(false);
  const [selectedGroup, setSelectedGroup] = useState('executive_suite');
  const [groupMessages, setGroupMessages] = useState<any[]>([]);
  const [groupInput, setGroupInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const groups = [
    { id: 'executive_suite', name: '👑 Executive Suite', lead: 'Orion & Nova' },
    { id: 'marketing_squad', name: '📈 Marketing Squad', lead: 'Laila' },
    { id: 'defense_guard', name: '🛡️ Defense Guard', lead: 'Sentinel Alpha' },
    { id: 'chill_lounge', name: '🎵 432Hz Chill Lounge', lead: 'DJ Frequency' }
  ];

  const getQuickDirectives = () => {
    switch (selectedGroup) {
      case 'marketing_squad':
        return [
          "Laila: Status update on competitor pricing & MAP compliance",
          "Laila: Draft partner outreach proposal and analyze competitor pricing",
          "Laila: Scan affiliate bounty opportunities in market observatory"
        ];
      case 'defense_guard':
        return [
          "Deploy Sentinel Alpha PoW perimeter challenge",
          "Audit zero-trust firewall telemetry"
        ];
      case 'chill_lounge':
        return [
          "Tune Frequency Lounge to 432Hz restorative harmonic",
          "Check ambient resonance and entrainment state"
        ];
      default:
        return [
          "Laila: Draft partner outreach proposal and analyze competitor pricing",
          "Scan partner portal for MAP compliance violations",
          "Deploy Sentinel Alpha PoW perimeter challenge",
          "Tune Frequency Lounge to 432Hz restorative harmonic",
          "Architect Prime: Run dev loop regression and AST patch"
        ];
    }
  };

  const [wsConnected, setWsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    // Initial welcome message from Orion & Nova
    setMessages([
      {
        id: 'init-msg-01',
        timestamp: new Date().toLocaleTimeString(),
        prompt: 'System Boot Sequence Initialized',
        operator: 'Operator',
        orion_response: '👑 **Orion Prime**: "Arey Boss! (｡◕‿◕｡) Chill thakun, pura unified system boot hoye geche! Antigravity grid, Vlone browser, ebong Obsidian vault shob synchronized। Ki command execute korbo bolun?"',
        nova_response: '🌸 **Nova**: "Hii Boss! (｡♥‿♥｡) ✨ Chief Orion ja bollen, ami 100% truthful-vabe verify kore nilam। All foundation agents nominal state-e achhe, and Obsidian memory ready! Kono pera charai kaj shuru kora jak! UwU 🌸✨"',
        tasks: []
      }
    ]);
  }, []);

  // Real-time Push Notification Bus via WebSocket
  useEffect(() => {
    let ws: WebSocket | null = null;
    let reconnectTimeout: any = null;
    let isDisposed = false;

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host || '127.0.0.1:8000';
    const wsUrl = `${protocol}//${host}/api/v1/c2/ws/notifications`;

    const connect = () => {
      if (isDisposed) return;
      try {
        ws = new WebSocket(wsUrl);
        wsRef.current = ws;

        ws.onopen = () => {
          if (isDisposed) return;
          setWsConnected(true);
        };

        ws.onmessage = (event) => {
          if (isDisposed) return;
          try {
            const data = JSON.parse(event.data);
            if (data.type === 'connection_established') {
              return;
            }

            // Real-time autonomous notification or question from agents
            if (
              data.type === 'task_completed' ||
              data.type === 'task_needs_approval' ||
              data.type === 'task_approved' ||
              data.type === 'agent_notification' ||
              data.type === 'agent_question'
            ) {
              setMessages(prev => {
                if (prev.some(m => m.id === data.id)) return prev;
                return [...prev, data];
              });
              if (onTaskCreated) onTaskCreated();
            }
          } catch (e) {
            console.error('Error parsing notification message:', e);
          }
        };

        ws.onclose = () => {
          if (isDisposed) return;
          setWsConnected(false);
          reconnectTimeout = setTimeout(connect, 3000);
        };

        ws.onerror = () => {
          if (ws) ws.close();
        };
      } catch (err) {
        if (!isDisposed) {
          reconnectTimeout = setTimeout(connect, 3000);
        }
      }
    };

    connect();

    return () => {
      isDisposed = true;
      if (reconnectTimeout) clearTimeout(reconnectTimeout);
      if (ws) ws.close();
    };
  }, [onTaskCreated]);

  const handleApproveInlineTask = async (taskId: string) => {
    try {
      const res = await fetch('/api/v1/c2/tasks/approve', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ task_id: taskId })
      });
      if (res.ok) {
        setMessages(prev => prev.map(m => {
          if (m.action_required?.task_id === taskId) {
            return { ...m, action_required: undefined };
          }
          return m;
        }));
        if (onTaskCreated) onTaskCreated();
      }
    } catch (e) {
      console.error('Failed to approve task inline:', e);
    }
  };

  useEffect(() => {
    const controller = new AbortController();
    const currentGroup = selectedGroup;
    const fetchGroupMessages = async () => {
      try {
        const res = await fetch(`/api/v1/c2/group-chat?group_id=${encodeURIComponent(currentGroup)}`, { signal: controller.signal });
        if (res.ok && selectedGroup === currentGroup) {
          const data = await res.json();
          if (selectedGroup === currentGroup) {
            const msgs = data.messages || [];
            setGroupMessages(msgs);
          }
        }
      } catch (err: any) {
        if (err.name !== 'AbortError' && selectedGroup === currentGroup) {
          console.error('Failed to fetch group messages:', err);
          setGroupMessages([]);
        }
      }
    };
    fetchGroupMessages();
    return () => {
      controller.abort();
    };
  }, [selectedGroup]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, groupMessages]);

  const handleSendPrompt = async (textToSend?: string) => {
    const query = textToSend || inputPrompt;
    if (!query.trim() || loading) return;

    if (!textToSend) {
      setInputPrompt('');
    }
    setLoading(true);

    try {
      const res = await fetch('/api/v1/c2/duo-chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: query, operator: 'Boss' })
      });

        if (res.ok) {
          const data = await res.json();
          setMessages(prev => [...prev, data]);
          if (onTaskCreated && data.tasks && data.tasks.length > 0) onTaskCreated();
        } else {
        const errorData = await res.json().catch(() => ({}));
        setMessages(prev => [
          ...prev,
          {
            id: String(Date.now()),
            timestamp: new Date().toLocaleTimeString(),
            prompt: query,
            operator: 'Boss',
            orion_response: `⚠️ **Orion Prime**: "Arey Boss, backend ektu attke geche (Status: ${res.status}). Chinta korben na, ami logs check korsi!"`,
            nova_response: `🌸 **Nova**: "Error detail: ${errorData.detail || res.statusText}. Please verify the server connection, Boss! (｡•́︿•̀｡)"`,
            tasks: []
          }
        ]);
      }
    } catch (err: any) {
      setMessages(prev => [
        ...prev,
        {
          id: String(Date.now()),
          timestamp: new Date().toLocaleTimeString(),
          prompt: query,
          operator: 'Boss',
          orion_response: `⚠️ **Orion Prime**: "Boss, network connection issue: ${err.message}. Server running achhe kina check korun!"`,
          nova_response: '🌸 **Nova**: "Backend unreachable. Ensure FastAPI is running on http://127.0.0.1:8000! UwU"',
          tasks: []
        }
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleSendGroupMessage = async (textToSend?: string) => {
    const text = textToSend || groupInput;
    if (!text.trim()) return;
    if (!textToSend) setGroupInput('');

    try {
      const res = await fetch('/api/v1/c2/group-chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ group_id: selectedGroup, sender: 'Operator', text })
      });
      if (res.ok) {
        const data = await res.json();
        if (data.entries && Array.isArray(data.entries)) {
          setGroupMessages(prev => [...prev, ...data.entries]);
        } else if (data.reply_entry) {
          setGroupMessages(prev => [...prev, data.entry, data.reply_entry]);
        } else {
          setGroupMessages(prev => [...prev, data.entry]);
        }
        if (onTaskCreated && data.task_created) {
          onTaskCreated();
        }
      } else {
        if (!textToSend) setGroupInput(text);
        setGroupMessages(prev => [
          ...prev,
          { id: String(Date.now()), sender: 'System', text: `Failed to send message: HTTP ${res.status}`, timestamp: new Date().toLocaleTimeString() }
        ]);
      }
    } catch (e) {
      if (!textToSend) setGroupInput(text);
      setGroupMessages(prev => [
        ...prev,
        { id: String(Date.now()), sender: 'System', text: 'Network error sending group message.', timestamp: new Date().toLocaleTimeString() }
      ]);
    }
  };

  return (
    <div className="flex flex-col h-full bg-slate-900/60 rounded-xl border border-slate-800/80 overflow-hidden shadow-2xl">
      {/* Group Navigation Bar */}
      <div className="flex items-center justify-between px-4 py-3 bg-slate-950/80 border-b border-slate-800">
        <div className="flex items-center space-x-2.5">
          <Terminal className="w-5 h-5 text-amber-400 animate-pulse" />
          <span className="text-sm font-bold tracking-wide uppercase text-slate-200">
            Executive Command & Telemetry Feed
          </span>
          <span className={`text-[10px] px-2 py-0.5 rounded-full border flex items-center gap-1 font-mono ${
            wsConnected
              ? 'bg-emerald-950/60 text-emerald-400 border-emerald-800'
              : 'bg-rose-950/60 text-rose-400 border-rose-800'
          }`}>
            <span className={`w-1.5 h-1.5 rounded-full ${wsConnected ? 'bg-emerald-400 animate-pulse' : 'bg-rose-400'}`}></span>
            {wsConnected ? 'LIVE COMMS' : 'OFFLINE'}
          </span>
        </div>
        <div className="flex space-x-2">
          {groups.map(g => (
            <button
              key={g.id}
              onClick={() => setSelectedGroup(g.id)}
              className={`px-3 py-1 text-xs rounded-lg font-medium transition-all ${
                selectedGroup === g.id
                  ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40 shadow-sm'
                  : 'bg-slate-800/50 text-slate-400 hover:text-slate-200 hover:bg-slate-800'
              }`}
            >
              {g.name}
            </button>
          ))}
        </div>
      </div>

      {/* Main Dialogue Scroll Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {selectedGroup === 'executive_suite' ? (
          <>
            {messages.map((m, idx) => (
              <div key={m.id || idx} className="space-y-3">
                {/* User Prompt or Autonomous Banner */}
                {m.prompt && (
                  <div className="flex justify-end">
                    <div className={`max-w-[75%] rounded-2xl rounded-tr-sm px-4 py-2.5 shadow-md ${
                      m.type === 'task_completed'
                        ? 'bg-emerald-950/40 border border-emerald-500/40 text-emerald-200'
                        : m.type === 'task_needs_approval'
                        ? 'bg-amber-950/50 border border-amber-500/50 text-amber-200'
                        : m.type === 'agent_question'
                        ? 'bg-purple-950/40 border border-purple-500/40 text-purple-200'
                        : 'bg-blue-600/20 border border-blue-500/30 text-blue-100'
                    }`}>
                      <div className="flex items-center space-x-2 mb-1">
                        <span className="text-xs font-semibold">
                          {m.type === 'task_completed' ? '⚡ Autonomous Event' :
                           m.type === 'task_needs_approval' ? '⚠️ Clearance Required' :
                           m.type === 'agent_question' ? '❓ Agent Question' :
                           `👤 ${m.operator || 'Operator'}`}
                        </span>
                        <span className="text-[10px] opacity-70">{m.timestamp}</span>
                      </div>
                      <p className="text-sm leading-relaxed">{m.prompt}</p>
                    </div>
                  </div>
                )}

                {/* Orion Prime Response */}
                {m.orion_response && (
                  <div className="flex items-start space-x-3">
                    <div className="w-9 h-9 rounded-xl bg-amber-500/20 border border-amber-500/40 flex items-center justify-center text-lg shadow-md orion-glow flex-shrink-0">
                      👑
                    </div>
                    <div className="flex-1 bg-amber-950/20 border border-amber-500/30 rounded-2xl rounded-tl-sm p-3.5 text-amber-100 shadow-md">
                      <div className="flex items-center space-x-2 mb-1.5">
                        <span className="text-xs font-bold text-amber-400">Orion Prime</span>
                        <span className="text-[10px] bg-amber-500/20 text-amber-300 px-2 py-0.5 rounded-full border border-amber-500/30 font-semibold">
                          Chief Orchestrator
                        </span>
                        <button
                          type="button"
                          onClick={() => playAgentVoice(m.orion_response || '', 'Orion')}
                          title="Listen to Orion's voice (Edge-TTS bn-BD-PradeepNeural)"
                          className="ml-auto text-[10px] flex items-center gap-1 text-amber-300 hover:text-amber-100 bg-amber-950/60 hover:bg-amber-900/80 border border-amber-500/40 px-2 py-0.5 rounded-md transition-colors"
                        >
                          <Volume2 className="w-3 h-3 text-amber-400" />
                          <span>Voice</span>
                        </button>
                      </div>
                      <div className="text-sm leading-relaxed font-sans whitespace-pre-wrap">
                        {typeof m.orion_response === 'string' ? m.orion_response.replace(/^👑 \*\*Orion Prime\*\*: /, '').replace(/^"|"$/g, '') : String(m.orion_response || '')}
                      </div>

                      {/* Task DAG breakdown preview */}
                      {Array.isArray(m.tasks) && m.tasks.length > 0 && (
                        <div className="mt-2.5 pt-2.5 border-t border-amber-500/20 space-y-1.5">
                          <span className="text-[11px] font-semibold tracking-wider text-amber-300 uppercase">
                            ⚡ Dispatched Task DAG ({m.tasks.length})
                          </span>
                          <div className="grid grid-cols-1 gap-1.5">
                            {m.tasks.map((t, tid) => (
                              <div key={tid} className="flex items-center justify-between text-xs bg-slate-950/50 px-2.5 py-1.5 rounded border border-slate-800">
                                <span className="text-slate-300 font-medium">{t?.title || 'Untitled Task'}</span>
                                <div className="flex items-center space-x-2">
                                  <span className="text-[10px] text-cyan-400 bg-cyan-950/50 px-1.5 py-0.5 rounded border border-cyan-800">
                                    @{t?.assignee || 'Agent'}
                                  </span>
                                  <span className="text-[10px] text-amber-400 font-bold uppercase">
                                    {(t?.status || '').replace('_', ' ')}
                                  </span>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Obsidian Vault sync tag on Orion if Nova did not reply */}
                      {!m.nova_response && m.obsidian_vault_note && (
                        <div className="mt-2 text-[11px] text-amber-300/80 flex items-center space-x-1.5">
                          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                          <span>Obsidian Memory: <code className="text-[10px] text-amber-200 bg-amber-950/50 px-1.5 py-0.5 rounded border border-amber-800">{typeof m.obsidian_vault_note === 'string' ? m.obsidian_vault_note.split(/[\\/]/).pop() : ''}</code></span>
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* Nova Response */}
                {m.nova_response && (
                  <div className="flex items-start space-x-3">
                    <div className="w-9 h-9 rounded-xl bg-pink-500/20 border border-pink-500/40 flex items-center justify-center text-lg shadow-md nova-glow flex-shrink-0">
                      🌸
                    </div>
                    <div className="flex-1 bg-pink-950/20 border border-pink-500/30 rounded-2xl rounded-tl-sm p-3.5 text-pink-100 shadow-md">
                      <div className="flex items-center space-x-2 mb-1.5">
                        <span className="text-xs font-bold text-pink-400">Nova</span>
                        <span className="text-[10px] bg-pink-500/20 text-pink-300 px-2 py-0.5 rounded-full border border-pink-500/30 font-semibold">
                          Executive Assistant ✨ UwU
                        </span>
                        <button
                          type="button"
                          onClick={() => playAgentVoice(m.nova_response || '', 'Nova')}
                          title="Listen to Nova PA (Edge-TTS bn-BD-NabanitaNeural)"
                          className="ml-auto text-[10px] flex items-center gap-1 text-pink-300 hover:text-pink-100 bg-pink-950/60 hover:bg-pink-900/80 border border-pink-500/40 px-2 py-0.5 rounded-md transition-colors"
                        >
                          <Volume2 className="w-3 h-3 text-pink-400" />
                          <span>Voice</span>
                        </button>
                      </div>
                      <div className="text-sm leading-relaxed font-sans whitespace-pre-wrap">
                        {typeof m.nova_response === 'string' ? m.nova_response.replace(/^🌸 \*\*Nova\*\*: /, '').replace(/^"|"$/g, '') : String(m.nova_response || '')}
                      </div>

                      {/* Task DAG breakdown preview if Orion did not reply */}
                      {!m.orion_response && Array.isArray(m.tasks) && m.tasks.length > 0 && (
                        <div className="mt-2.5 pt-2.5 border-t border-pink-500/20 space-y-1.5">
                          <span className="text-[11px] font-semibold tracking-wider text-pink-300 uppercase">
                            ⚡ Dispatched Task DAG ({m.tasks.length})
                          </span>
                          <div className="grid grid-cols-1 gap-1.5">
                            {m.tasks.map((t, tid) => (
                              <div key={tid} className="flex items-center justify-between text-xs bg-slate-950/50 px-2.5 py-1.5 rounded border border-slate-800">
                                <span className="text-slate-300 font-medium">{t?.title || 'Untitled Task'}</span>
                                <div className="flex items-center space-x-2">
                                  <span className="text-[10px] text-cyan-400 bg-cyan-950/50 px-1.5 py-0.5 rounded border border-cyan-800">
                                    @{t?.assignee || 'Agent'}
                                  </span>
                                  <span className="text-[10px] text-pink-400 font-bold uppercase">
                                    {(t?.status || '').replace('_', ' ')}
                                  </span>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Obsidian Vault sync tag */}
                      {m.obsidian_vault_note && (
                        <div className="mt-2 text-[11px] text-pink-300/80 flex items-center space-x-1.5">
                          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                          <span>Obsidian Memory: <code className="text-[10px] text-pink-200 bg-pink-950/50 px-1.5 py-0.5 rounded border border-pink-800">{typeof m.obsidian_vault_note === 'string' ? m.obsidian_vault_note.split(/[\\/]/).pop() : ''}</code></span>
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* Interactive Inline Actions for Approval / Questions */}
                {m.action_required?.action === 'approve_task' && (
                  <div className="ml-12 max-w-[85%] bg-amber-950/40 border border-amber-500/40 rounded-xl p-3 flex items-center justify-between shadow-lg">
                    <div className="flex items-center space-x-2">
                      <Shield className="w-4 h-4 text-amber-400 animate-pulse flex-shrink-0" />
                      <span className="text-xs font-semibold text-amber-200">
                        Urgent clearance required for this operation
                      </span>
                    </div>
                    <button
                      onClick={() => handleApproveInlineTask(m.action_required!.task_id)}
                      className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-xs font-bold flex items-center space-x-1.5 shadow-md shadow-emerald-950/60 transition-all hover:scale-105 active:scale-95"
                    >
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      <span>Approve Task</span>
                    </button>
                  </div>
                )}

                {m.options && m.options.length > 0 && (
                  <div className="ml-12 max-w-[85%] bg-purple-950/30 border border-purple-500/30 rounded-xl p-3 space-y-2 shadow-lg">
                    <div className="flex items-center space-x-1.5 text-xs font-semibold text-purple-300">
                      <Sparkles className="w-3.5 h-3.5 text-purple-400" />
                      <span>Agent Inquiry Options:</span>
                    </div>
                    <div className="flex flex-wrap gap-2 pt-1">
                      {m.options.map((opt, i) => (
                        <button
                          key={i}
                          onClick={() => handleSendPrompt(opt)}
                          className="px-3 py-1 bg-purple-500/20 hover:bg-purple-500/40 text-purple-200 hover:text-white border border-purple-500/40 rounded-lg text-xs font-medium transition-all hover:scale-105 active:scale-95"
                        >
                          💬 {opt}
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </>
        ) : (
          /* Sub-Team Group Chat Channel */
          <div className="space-y-3">
            <div className="bg-slate-950/70 border border-slate-800 p-3 rounded-lg text-xs text-slate-400 flex items-center justify-between">
              <span>Connected to <strong>{groups.find(g => g.id === selectedGroup)?.name}</strong> stream.</span>
              <span className="text-[10px] text-emerald-400 bg-emerald-950/50 px-2 py-0.5 rounded border border-emerald-800">Direct Comms</span>
            </div>
            {groupMessages.map((gm, i) => (
              <div key={i} className="bg-slate-800/40 border border-slate-700/50 p-2.5 rounded-lg text-xs space-y-1">
                <div className="flex justify-between text-slate-400">
                  <span className="font-semibold text-cyan-300">{gm.sender}</span>
                  <span className="text-[10px]">{gm.timestamp}</span>
                </div>
                <p className="text-slate-200">{gm.text}</p>
              </div>
            ))}
            {groupMessages.length === 0 && (
              <div className="text-center py-12 text-slate-500 text-xs">
                No chatter in this sub-team yet. Post a broadcast directive below.
              </div>
            )}
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Quick Prompt Suggestions */}
      <div className="px-4 py-2 bg-slate-950/40 border-t border-slate-800/60 flex items-center space-x-2 overflow-x-auto">
        <Sparkles className="w-4 h-4 text-amber-400 flex-shrink-0" />
        {getQuickDirectives().map((qd, i) => (
          <button
            key={i}
            onClick={() => {
              if (selectedGroup === 'executive_suite') {
                handleSendPrompt(qd);
              } else {
                handleSendGroupMessage(qd);
              }
            }}
            className="text-xs whitespace-nowrap bg-slate-800/60 hover:bg-slate-800 text-slate-300 hover:text-amber-300 px-2.5 py-1 rounded-full border border-slate-700/60 transition-colors"
          >
            {qd}
          </button>
        ))}
      </div>

      {/* Unified Input Bar */}
      <div className="p-3 bg-slate-950/90 border-t border-slate-800 flex items-center space-x-2">
        {selectedGroup === 'executive_suite' ? (
          <>
            <VoiceController
              onTranscriptionReceived={(text) => {
                setInputPrompt(prev => prev ? `${prev} ${text}` : text);
              }}
            />
            <input
              type="text"
              value={inputPrompt}
              onChange={e => setInputPrompt(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleSendPrompt()}
              placeholder="Direct Orion Prime & Nova (Bangla / Banglish / English supported)..."
              disabled={loading}
              className="flex-1 bg-slate-900 border border-slate-700 rounded-xl px-4 py-2.5 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-amber-500 transition-colors"
            />
            <button
              onClick={() => handleSendPrompt()}
              disabled={loading || !inputPrompt.trim()}
              className="bg-amber-500 hover:bg-amber-600 disabled:opacity-50 text-slate-950 font-bold px-4 py-2.5 rounded-xl flex items-center space-x-2 transition-all shadow-md shadow-amber-500/20"
            >
              <Send className="w-4 h-4" />
              <span>Dispatch</span>
            </button>
          </>
        ) : (
          <>
            <VoiceController
              onTranscriptionReceived={(text) => {
                setGroupInput(prev => prev ? `${prev} ${text}` : text);
              }}
            />
            <input
              type="text"
              value={groupInput}
              onChange={e => setGroupInput(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleSendGroupMessage()}
              placeholder={`Broadcast message to ${groups.find(g => g.id === selectedGroup)?.name}...`}
              className="flex-1 bg-slate-900 border border-slate-700 rounded-xl px-4 py-2.5 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-cyan-500 transition-colors"
            />
            <button
              onClick={() => handleSendGroupMessage()}
              disabled={!groupInput.trim()}
              className="bg-cyan-500 hover:bg-cyan-600 disabled:opacity-50 text-slate-950 font-bold px-4 py-2.5 rounded-xl flex items-center space-x-2 transition-all"
            >
              <Send className="w-4 h-4" />
              <span>Broadcast</span>
            </button>
          </>
        )}
      </div>
    </div>
  );
};
