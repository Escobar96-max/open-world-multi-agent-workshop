import React, { useState, useEffect } from 'react';

interface Task {
  task_id: string;
  title: string;
  assigned_to: string;
  status: 'in_progress' | 'needs_approval' | 'completed';
  confidence_score: number;
  output_summary: string;
  requires_operator_signoff: boolean;
}

interface TaskKanbanProps {
  refreshTrigger?: number;
}

export const TaskKanban: React.FC<TaskKanbanProps> = ({ refreshTrigger }) => {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(false);
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  const fetchTasks = async () => {
    try {
      setLoading(true);
      const res = await fetch('http://127.0.0.1:8000/api/v1/c2/tasks');
      if (res.ok) {
        const data = await res.json();
        setTasks(data.tasks || []);
      }
    } catch (err) {
      console.error('Failed to fetch tasks:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTasks();
    const interval = setInterval(fetchTasks, 3000);
    return () => clearInterval(interval);
  }, [refreshTrigger]);

  const handleApprove = async (taskId: string) => {
    try {
      const res = await fetch(`http://127.0.0.1:8000/api/v1/c2/tasks/approve?task_id=${encodeURIComponent(taskId)}`, {
        method: 'POST'
      });
      if (res.ok) {
        setActionMessage(`Approved task ${taskId} successfully!`);
        setTimeout(() => setActionMessage(null), 3000);
        fetchTasks();
      }
    } catch (err) {
      console.error('Error approving task:', err);
    }
  };

  const inProgress = tasks.filter(t => t.status === 'in_progress');
  const needsApproval = tasks.filter(t => t.status === 'needs_approval');
  const completed = tasks.filter(t => t.status === 'completed');

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex flex-col h-full shadow-xl">
      <div className="flex items-center justify-between pb-3 border-b border-slate-800 mb-4">
        <div>
          <h2 className="text-lg font-bold text-white flex items-center gap-2">
            📋 Dynamic C2 Task Kanban
            <span className="text-xs px-2 py-0.5 rounded-full bg-indigo-900/60 text-indigo-300 border border-indigo-700/50">
              {tasks.length} total
            </span>
          </h2>
          <p className="text-xs text-slate-400">Real-time DAG task pipeline monitored by Orion & Nova</p>
        </div>
        <button
          onClick={fetchTasks}
          className="text-xs px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors"
        >
          {loading ? 'Refreshing...' : '🔄 Refresh'}
        </button>
      </div>

      {actionMessage && (
        <div className="mb-3 px-3 py-1.5 rounded-md bg-emerald-950/80 border border-emerald-500/40 text-emerald-300 text-xs flex items-center gap-2">
          <span>✨</span>
          <span>{actionMessage}</span>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 flex-1 overflow-y-auto">
        {/* In Progress */}
        <div className="bg-slate-950/60 border border-slate-800/80 rounded-lg p-3 flex flex-col">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-amber-400 flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full bg-amber-400 animate-pulse"></span>
              In-Progress
            </span>
            <span className="text-xs bg-amber-950/60 text-amber-300 px-1.5 py-0.2 rounded border border-amber-800/40">
              {inProgress.length}
            </span>
          </div>
          <div className="space-y-2 flex-1 overflow-y-auto pr-1">
            {inProgress.length === 0 ? (
              <p className="text-xs text-slate-600 italic text-center py-6">No active tasks</p>
            ) : (
              inProgress.map(task => (
                <div key={task.task_id} className="p-2.5 rounded bg-slate-900/90 border border-slate-800 text-xs space-y-1 hover:border-amber-500/40 transition-colors">
                  <div className="font-medium text-slate-200">{task.title}</div>
                  <div className="flex items-center justify-between text-[11px] text-slate-400">
                    <span className="px-1.5 py-0.5 rounded bg-slate-800 text-slate-300">🤖 {task.assigned_to}</span>
                    <span className="text-amber-400 font-mono">{(task.confidence_score * 100).toFixed(0)}% conf</span>
                  </div>
                  {task.output_summary && (
                    <p className="text-[11px] text-slate-400 bg-slate-950/50 p-1.5 rounded line-clamp-2">
                      {task.output_summary}
                    </p>
                  )}
                </div>
              ))
            )}
          </div>
        </div>

        {/* Needs Approval */}
        <div className="bg-slate-950/60 border border-rose-900/30 rounded-lg p-3 flex flex-col">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-rose-400 flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full bg-rose-400 animate-ping"></span>
              Needs Approval (Operator Signoff)
            </span>
            <span className="text-xs bg-rose-950/60 text-rose-300 px-1.5 py-0.2 rounded border border-rose-800/40">
              {needsApproval.length}
            </span>
          </div>
          <div className="space-y-2 flex-1 overflow-y-auto pr-1">
            {needsApproval.length === 0 ? (
              <p className="text-xs text-slate-600 italic text-center py-6">Queue is clean</p>
            ) : (
              needsApproval.map(task => (
                <div key={task.task_id} className="p-2.5 rounded bg-slate-900/90 border border-rose-900/50 text-xs space-y-2 shadow-md">
                  <div className="font-semibold text-rose-200">{task.title}</div>
                  <div className="flex items-center justify-between text-[11px]">
                    <span className="px-1.5 py-0.5 rounded bg-slate-800 text-slate-300">👤 {task.assigned_to}</span>
                    <span className="text-rose-400 font-mono">Requires Review</span>
                  </div>
                  <p className="text-[11px] text-slate-300 bg-slate-950/70 p-1.5 rounded border border-rose-900/30">
                    {task.output_summary || 'Task completed pending operator review.'}
                  </p>
                  <button
                    onClick={() => handleApprove(task.task_id)}
                    className="w-full py-1 rounded bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white font-medium text-xs shadow-lg transition-all"
                  >
                    ✓ 1-Click Operator Signoff
                  </button>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Completed */}
        <div className="bg-slate-950/60 border border-slate-800/80 rounded-lg p-3 flex flex-col">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-emerald-400 flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full bg-emerald-400"></span>
              Completed
            </span>
            <span className="text-xs bg-emerald-950/60 text-emerald-300 px-1.5 py-0.2 rounded border border-emerald-800/40">
              {completed.length}
            </span>
          </div>
          <div className="space-y-2 flex-1 overflow-y-auto pr-1">
            {completed.length === 0 ? (
              <p className="text-xs text-slate-600 italic text-center py-6">No completed tasks yet</p>
            ) : (
              completed.map(task => (
                <div key={task.task_id} className="p-2.5 rounded bg-slate-900/90 border border-slate-800/80 text-xs space-y-1 opacity-80 hover:opacity-100 transition-opacity">
                  <div className="font-medium text-slate-300 line-through decoration-emerald-500/60">{task.title}</div>
                  <div className="flex items-center justify-between text-[11px] text-slate-500">
                    <span>{task.assigned_to}</span>
                    <span className="text-emerald-400 font-mono">100% synced</span>
                  </div>
                  <div className="text-[10px] text-emerald-500/80 bg-emerald-950/20 px-1.5 py-0.5 rounded border border-emerald-900/30">
                    Obsidian Vault: Synchronized with #operator_directive
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
export default TaskKanban;
