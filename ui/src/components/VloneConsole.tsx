import React, { useState, useEffect } from 'react';

interface VloneState {
  url: string;
  is_active: boolean;
  title: string;
  elements_count: number;
  reduction_pct: number;
  raw_tokens_estimate?: number;
  token_estimate?: number;
}

export const VloneConsole: React.FC = () => {
  const [targetUrl, setTargetUrl] = useState<string>('https://news.ycombinator.com');
  const [vloneState, setVloneState] = useState<VloneState | null>(null);
  const [cleanContent, setCleanContent] = useState<string>('');
  const [sniffedApis, setSniffedApis] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [actionLog, setActionLog] = useState<string>('');

  // Interact fields
  const [interactAction, setInteractAction] = useState<string>('click');
  const [vloneId, setVloneId] = useState<number>(0);
  const [interactValue, setInteractValue] = useState<string>('');

  const fetchVloneState = async () => {
    try {
      const res = await fetch('/api/v1/vlone/state');
      if (res.ok) {
        const data = await res.json();
        setVloneState(data);
      }
    } catch (err) {
      console.error('Failed to fetch VLONE state:', err);
    }
  };

  const fetchSniffedApis = async () => {
    try {
      const res = await fetch('/api/v1/vlone/sniffed-apis?session_id=default');
      if (res.ok) {
        const data = await res.json();
        setSniffedApis(data.apis || []);
      }
    } catch (err) {
      console.error('Failed to fetch sniffed apis:', err);
    }
  };

  useEffect(() => {
    fetchVloneState();
    fetchSniffedApis();
  }, []);

  const handleOpenPage = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!targetUrl.trim()) return;

    try {
      setLoading(true);
      setActionLog(`Dispatching VLONE headless scraper to: ${targetUrl}...`);
      const res = await fetch('/api/v1/vlone/open', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          url: targetUrl,
          session_id: 'default'
        })
      });

      if (res.ok) {
        const data = await res.json();
        setCleanContent(data.markdown || '');
        setVloneState({
          url: data.url || targetUrl,
          is_active: true,
          title: data.title || targetUrl,
          elements_count: data.elements_count || 0,
          reduction_pct: data.reduction_pct || 0,
          raw_tokens_estimate: data.raw_tokens_estimate || 0,
          token_estimate: data.token_estimate || 0
        });
        await fetchSniffedApis();
        setActionLog(`Success! Page parsed with ${data.reduction_pct}% token reduction.`);
      } else {
        setActionLog(`Failed to open page: ${res.statusText}`);
      }
    } catch (err: any) {
      setActionLog(`Error opening URL: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleInteract = async () => {
    try {
      setLoading(true);
      setActionLog(`Executing ${interactAction} on [data-vlone-id="${vloneId}"]...`);
      const res = await fetch('/api/v1/vlone/interact', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          action: interactAction,
          vlone_id: vloneId,
          value: interactValue,
          session_id: 'default'
        })
      });
      if (res.ok) {
        const data = await res.json();
        setActionLog(`Interaction result: ${JSON.stringify(data.result || data.action)}`);
        fetchVloneState();
      } else {
        setActionLog(`Interaction failed: ${res.statusText}`);
      }
    } catch (err: any) {
      setActionLog(`Error during interaction: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full space-y-4">
      {/* Top Header & URL Bar */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-xl">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-3 border-b border-slate-800 mb-3">
          <div>
            <h2 className="text-lg font-bold text-white flex items-center gap-2">
              ⚡ VLONE Headless Semantic Browser Engine
              <span className="text-xs px-2.5 py-0.5 rounded-full bg-emerald-950 text-emerald-400 border border-emerald-800">
                Playwright + Semantic Pruning
              </span>
            </h2>
            <p className="text-xs text-slate-400">
              Autonomous web scraper with dynamic data-vlone-id stamping and token-reduction optimization.
            </p>
          </div>

          {/* Token Metrics Badge */}
          {vloneState && (
            <div className="flex items-center gap-2 bg-slate-950 px-3 py-1.5 rounded-lg border border-slate-800">
              <div className="text-right">
                <div className="text-[10px] text-slate-400 uppercase tracking-wider">Token Efficiency</div>
                <div className="text-xs font-mono font-bold text-emerald-400">
                  {vloneState.reduction_pct}% reduction
                </div>
              </div>
              <div className="h-6 w-px bg-slate-800 mx-1"></div>
              <div className="text-[10px] text-slate-400">
                <div>Raw: <span className="font-mono text-slate-300">{vloneState.raw_tokens_estimate ?? 0}</span></div>
                <div>Clean: <span className="font-mono text-emerald-400">{vloneState.token_estimate ?? 0}</span></div>
              </div>
            </div>
          )}
        </div>

        {/* URL Input Form */}
        <form onSubmit={handleOpenPage} className="flex gap-2">
          <div className="relative flex-1">
            <span className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-500 text-sm">
              🌐
            </span>
            <input
              type="url"
              value={targetUrl}
              onChange={(e) => setTargetUrl(e.target.value)}
              placeholder="Enter URL to scrape and semantic-prune (e.g. https://news.ycombinator.com)..."
              className="w-full bg-slate-950 border border-slate-700 rounded-lg pl-9 pr-4 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500"
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="px-5 py-2 rounded-lg bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white font-medium text-sm transition-all shadow-lg disabled:opacity-50"
          >
            {loading ? 'Inspecting...' : '⚡ Inspect Page'}
          </button>
        </form>

        {actionLog && (
          <div className="mt-2 text-xs font-mono text-cyan-300 bg-slate-950/80 px-3 py-1.5 rounded border border-slate-800 flex items-center justify-between">
            <span>{actionLog}</span>
            <span className="text-slate-500 text-[10px]">VLONE Kernel Log</span>
          </div>
        )}
      </div>

      {/* Main Console Split */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 flex-1 overflow-hidden">
        {/* Clean Semantic DOM Viewer (2 cols) */}
        <div className="lg:col-span-2 bg-slate-900 border border-slate-800 rounded-xl p-4 flex flex-col shadow-xl overflow-hidden">
          <div className="flex items-center justify-between pb-2 border-b border-slate-800 mb-2">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center gap-1.5">
              <span>📄</span> Pruned Markdown DOM (data-vlone-id Catalog)
            </h3>
            <span className="text-[10px] text-slate-400">
              Noise stripped (scripts, styling, tracking)
            </span>
          </div>

          <div className="flex-1 bg-slate-950 rounded-lg border border-slate-800/80 p-3 overflow-y-auto font-mono text-xs text-slate-300 whitespace-pre-wrap leading-relaxed">
            {cleanContent ? (
              cleanContent
            ) : (
              <div className="h-full flex flex-col items-center justify-center text-slate-600 text-center py-12">
                <span className="text-3xl mb-2">🕸️</span>
                <p>No active page parsed yet.</p>
                <p className="text-[11px] text-slate-600">Enter a URL above and click "Inspect Page" to initiate VLONE scraping.</p>
              </div>
            )}
          </div>
        </div>

        {/* Right Rail: Sniffed APIs & Interactive Testing (1 col) */}
        <div className="space-y-4 flex flex-col">
          {/* Sniffed APIs Container */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-3.5 flex flex-col flex-1 shadow-xl">
            <div className="flex items-center justify-between pb-2 border-b border-slate-800 mb-2">
              <h3 className="text-xs font-bold uppercase tracking-wider text-amber-400 flex items-center gap-1.5">
                <span>📡</span> Sniffed Network APIs
              </h3>
              <span className="text-[10px] bg-amber-950 text-amber-300 px-1.5 py-0.5 rounded border border-amber-800">
                {sniffedApis.length} captured
              </span>
            </div>

            <div className="flex-1 overflow-y-auto space-y-2 pr-1">
              {sniffedApis.length === 0 ? (
                <p className="text-xs text-slate-600 italic text-center py-8">
                  No background API endpoints sniffed on this page.
                </p>
              ) : (
                sniffedApis.map((api, idx) => (
                  <div key={idx} className="p-2 rounded bg-slate-950 border border-slate-800 text-[11px] font-mono space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="px-1 py-0.2 rounded bg-indigo-950 text-indigo-300 border border-indigo-800 text-[10px]">
                        {api.method || 'GET'}
                      </span>
                      <span className="text-slate-500 text-[10px] truncate max-w-[120px]">
                        {api.resource_type || 'xhr'}
                      </span>
                    </div>
                    <div className="text-slate-300 break-all">{api.url}</div>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Action Dispatcher Box */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-3.5 shadow-xl space-y-2.5">
            <h3 className="text-xs font-bold uppercase tracking-wider text-cyan-400 flex items-center gap-1.5">
              <span>🎯</span> Semantic Element Dispatcher
            </h3>

            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="text-[10px] text-slate-400 block mb-0.5">Action</label>
                <select
                  value={interactAction}
                  onChange={(e) => setInteractAction(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded px-2 py-1 text-xs text-white"
                >
                  <option value="click">click</option>
                  <option value="fill">fill</option>
                  <option value="hover">hover</option>
                </select>
              </div>

              <div>
                <label className="text-[10px] text-slate-400 block mb-0.5">data-vlone-id</label>
                <input
                  type="number"
                  value={vloneId}
                  onChange={(e) => setVloneId(Number(e.target.value))}
                  placeholder="ID #"
                  className="w-full bg-slate-950 border border-slate-700 rounded px-2 py-1 text-xs text-white font-mono"
                />
              </div>
            </div>

            {interactAction === 'fill' && (
              <div>
                <label className="text-[10px] text-slate-400 block mb-0.5">Text Value</label>
                <input
                  type="text"
                  value={interactValue}
                  onChange={(e) => setInteractValue(e.target.value)}
                  placeholder="Input text..."
                  className="w-full bg-slate-950 border border-slate-700 rounded px-2 py-1 text-xs text-white"
                />
              </div>
            )}

            <button
              onClick={handleInteract}
              disabled={loading}
              className="w-full py-1.5 rounded bg-cyan-700 hover:bg-cyan-600 text-white font-medium text-xs transition-colors shadow-md disabled:opacity-50"
            >
              Trigger Semantic Action
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
export default VloneConsole;
