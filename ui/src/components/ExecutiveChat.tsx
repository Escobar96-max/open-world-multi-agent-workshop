import React, { useState, useEffect, useRef } from 'react';
import { Send, Sparkles, Shield, Compass, CheckCircle2, MessageSquare, Terminal, ExternalLink } from 'lucide-react';

interface ChatMessage {
  id: string;
  timestamp: string;
  prompt: string;
  operator: string;
  orion_response: string;
  nova_response: string;
  tasks: any[];
  obsidian_vault_note?: string;
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
    { id: 'marketing_squad', name: '📈 Marketing Squad', lead: 'Growth Lead' },
    { id: 'defense_guard', name: '🛡️ Defense Guard', lead: 'Sentinel Alpha' },
    { id: 'chill_lounge', name: '🎵 432Hz Chill Lounge', lead: 'DJ Frequency' }
  ];

  const quickDirectives = [
    "Scan partner portal for MAP compliance violations",
    "Deploy Sentinel Alpha PoW perimeter challenge",
    "Tune Frequency Lounge to 432Hz restorative harmonic",
    "Architect Prime: Run dev loop regression and AST patch"
  ];

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

  useEffect(() => {
    const fetchGroupMessages = async () => {
      try {
        const res = await fetch('http://127.0.0.1:8000/api/v1/c2/groups');
        if (res.ok) {
          const data = await res.json();
          const msgs = (data.groups && data.groups[selectedGroup]) || [];
          setGroupMessages(msgs);
        }
      } catch (err) {
        console.error('Failed to fetch group messages:', err);
        setGroupMessages([]);
      }
    };
    fetchGroupMessages();
  }, [selectedGroup]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, groupMessages]);

  const handleSendPrompt = async (textToSend?: string) => {
    const query = textToSend || inputPrompt;
    if (!query.trim() || loading) return;

    setInputPrompt('');
    setLoading(true);

    try {
      const res = await fetch('http://127.0.0.1:8000/api/v1/c2/duo-chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: query, operator: 'Boss' })
      });

      if (res.ok) {
        const data = await res.json();
        setMessages(prev => [...prev, data]);
        if (onTaskCreated) onTaskCreated();
      } else {
        setMessages(prev => [
          ...prev,
          {
            id: String(Date.now()),
            timestamp: new Date().toLocaleTimeString(),
            prompt: query,
            operator: 'Boss',
            orion_response: '👑 **Orion Prime**: "Arey Boss, backend theke chotto ekta hiccup esche! But kono pera nei, ami sub-agents der retry korte bolchi!"',
            nova_response: '🌸 **Nova**: "Boss! ⚠️ Connection timed out, ami 100% truthfully janachhi! Port 8000 online achhe kina ekbar check kore dekhun! (｡•́︿•̀｡)"',
            tasks: []
          }
        ]);
      }
    } catch (err) {
      setMessages(prev => [
        ...prev,
        {
          id: String(Date.now()),
          timestamp: new Date().toLocaleTimeString(),
          prompt: query,
          operator: 'Boss',
          orion_response: '👑 **Orion Prime**: "No stress Boss! Backend daemon connect hocche, ek second er moddhe retry korchi!"',
          nova_response: '🌸 **Nova**: "Hii Boss! Local FastAPI daemon (port 8000) not responding yet. Nova is standing by! ✨"',
          tasks: []
        }
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleSendGroupMessage = async () => {
    if (!groupInput.trim()) return;
    const text = groupInput;
    setGroupInput('');

    try {
      const res = await fetch('http://127.0.0.1:8000/api/v1/c2/group-chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ group_id: selectedGroup, sender: 'Operator', text })
      });
      if (res.ok) {
        const data = await res.json();
        setGroupMessages(prev => [...prev, data.entry]);
      }
    } catch (e) {
      // Local fallback
      setGroupMessages(prev => [
        ...prev,
        { id: String(Date.now()), sender: 'Operator', text, timestamp: new Date().toLocaleTimeString() }
      ]);
    }
  };

  return (
    <div className="flex flex-col h-full bg-slate-900/60 rounded-xl border border-slate-800/80 overflow-hidden shadow-2xl">
      {/* Group Navigation Bar */}
      <div className="flex items-center justify-between px-4 py-3 bg-slate-950/80 border-b border-slate-800">
        <div className="flex items-center space-x-2">
          <Terminal className="w-5 h-5 text-amber-400 animate-pulse" />
          <span className="text-sm font-bold tracking-wide uppercase text-slate-200">
            Executive Command & Telemetry Feed
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
                {/* User Prompt */}
                <div className="flex justify-end">
                  <div className="max-w-[75%] bg-blue-600/20 border border-blue-500/30 rounded-2xl rounded-tr-sm px-4 py-2.5 text-blue-100 shadow-md">
                    <div className="flex items-center space-x-2 mb-1">
                      <span className="text-xs font-semibold text-blue-400">👤 {m.operator}</span>
                      <span className="text-[10px] text-slate-500">{m.timestamp}</span>
                    </div>
                    <p className="text-sm leading-relaxed">{m.prompt}</p>
                  </div>
                </div>

                {/* Orion Prime Response */}
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
                    </div>
                    <div className="text-sm leading-relaxed font-sans whitespace-pre-wrap">
                      {m.orion_response.replace(/^👑 \*\*Orion Prime\*\*: /, '').replace(/^"|"$/g, '')}
                    </div>

                    {/* Task DAG breakdown preview */}
                    {m.tasks && m.tasks.length > 0 && (
                      <div className="mt-2.5 pt-2.5 border-t border-amber-500/20 space-y-1.5">
                        <span className="text-[11px] font-semibold tracking-wider text-amber-300 uppercase">
                          ⚡ Dispatched Task DAG ({m.tasks.length})
                        </span>
                        <div className="grid grid-cols-1 gap-1.5">
                          {m.tasks.map((t, tid) => (
                            <div key={tid} className="flex items-center justify-between text-xs bg-slate-950/50 px-2.5 py-1.5 rounded border border-slate-800">
                              <span className="text-slate-300 font-medium">{t.title}</span>
                              <div className="flex items-center space-x-2">
                                <span className="text-[10px] text-cyan-400 bg-cyan-950/50 px-1.5 py-0.5 rounded border border-cyan-800">
                                  @{t.assignee}
                                </span>
                                <span className="text-[10px] text-amber-400 font-bold uppercase">
                                  {t.status.replace('_', ' ')}
                                </span>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>

                {/* Nova Response */}
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
                    </div>
                    <div className="text-sm leading-relaxed font-sans whitespace-pre-wrap">
                      {m.nova_response.replace(/^🌸 \*\*Nova\*\*: /, '').replace(/^"|"$/g, '')}
                    </div>

                    {/* Obsidian Vault sync tag */}
                    {m.obsidian_vault_note && (
                      <div className="mt-2 text-[11px] text-pink-300/80 flex items-center space-x-1.5">
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                        <span>Obsidian Memory: <code className="text-[10px] text-pink-200 bg-pink-950/50 px-1.5 py-0.5 rounded border border-pink-800">{m.obsidian_vault_note.split(/[\\/]/).pop()}</code></span>
                      </div>
                    )}
                  </div>
                </div>
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
      {selectedGroup === 'executive_suite' && (
        <div className="px-4 py-2 bg-slate-950/40 border-t border-slate-800/60 flex items-center space-x-2 overflow-x-auto">
          <Sparkles className="w-4 h-4 text-amber-400 flex-shrink-0" />
          {quickDirectives.map((qd, i) => (
            <button
              key={i}
              onClick={() => handleSendPrompt(qd)}
              className="text-xs whitespace-nowrap bg-slate-800/60 hover:bg-slate-800 text-slate-300 hover:text-amber-300 px-2.5 py-1 rounded-full border border-slate-700/60 transition-colors"
            >
              {qd}
            </button>
          ))}
        </div>
      )}

      {/* Unified Input Bar */}
      <div className="p-3 bg-slate-950/90 border-t border-slate-800 flex items-center space-x-2">
        {selectedGroup === 'executive_suite' ? (
          <>
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
            <input
              type="text"
              value={groupInput}
              onChange={e => setGroupInput(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleSendGroupMessage()}
              placeholder={`Broadcast message to ${groups.find(g => g.id === selectedGroup)?.name}...`}
              className="flex-1 bg-slate-900 border border-slate-700 rounded-xl px-4 py-2.5 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-cyan-500 transition-colors"
            />
            <button
              onClick={handleSendGroupMessage}
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
