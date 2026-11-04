import React, { useState } from 'react';
import { ShieldCheck, CheckCircle2, AlertCircle, Clock, Filter } from 'lucide-react';

export default function GovernanceView({ govData }) {
  const [filterStatus, setFilterStatus] = useState('ALL');

  const tasks = govData?.recent_tasks || [];
  const filteredTasks = tasks.filter((t) => {
    if (filterStatus === 'ALL') return true;
    return t.status.toUpperCase() === filterStatus;
  });

  return (
    <div className="space-y-6">
      {/* Top Summary */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="p-4 rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-[#0c0c0f] shadow-sm">
          <div className="text-xs text-zinc-500 mb-1">Ukupno Zabeleženih Zadataka</div>
          <div className="text-2xl font-bold font-mono text-zinc-900 dark:text-zinc-50">
            {govData?.total_tasks || 0}
          </div>
        </div>
        <div className="p-4 rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-[#0c0c0f] shadow-sm">
          <div className="text-xs text-zinc-500 mb-1">Verifikovano Završenih</div>
          <div className="text-2xl font-bold font-mono text-emerald-500">
            {govData?.completed_count || 0}
          </div>
        </div>
        <div className="p-4 rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-[#0c0c0f] shadow-sm">
          <div className="text-xs text-zinc-500 mb-1">Bezbednosni Status</div>
          <div className="text-sm font-bold text-blue-500 flex items-center gap-1.5 mt-2">
            <ShieldCheck className="w-4 h-4" />
            <span>JudgeGuard 100% Invarijante</span>
          </div>
        </div>
      </div>

      {/* Task Audit Timeline */}
      <div className="bg-white dark:bg-[#0c0c0f] border border-zinc-200 dark:border-zinc-800 rounded-xl overflow-hidden shadow-sm">
        <div className="p-4 border-b border-zinc-200 dark:border-zinc-800 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Clock className="w-4 h-4 text-blue-500" />
            <h4 className="font-bold text-xs uppercase tracking-wider text-zinc-950 dark:text-zinc-50">
              WORK_LOG.md Hronologija & Pre-Action Revizija
            </h4>
          </div>

          <div className="flex items-center gap-2 text-xs">
            <Filter className="w-3.5 h-3.5 text-zinc-400" />
            <select
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value)}
              className="bg-zinc-50 dark:bg-[#09090b] border border-zinc-200 dark:border-zinc-800 rounded-lg px-2.5 py-1 text-xs text-zinc-700 dark:text-zinc-300"
            >
              <option value="ALL">Svi Zadaci</option>
              <option value="COMPLETED">Samo Završeni (✅)</option>
              <option value="STARTING">Samo Pokrenuti (🟡)</option>
            </select>
          </div>
        </div>

        <div className="divide-y divide-zinc-100 dark:divide-zinc-800 max-h-[500px] overflow-y-auto">
          {filteredTasks.length === 0 ? (
            <div className="p-8 text-center text-xs text-zinc-400">
              Nema zadataka za zadati filter.
            </div>
          ) : (
            filteredTasks.map((t, idx) => {
              const isCompleted = t.status === 'Completed';
              return (
                <div key={idx} className="p-4 flex items-center justify-between hover:bg-zinc-50 dark:hover:bg-zinc-850 transition-colors">
                  <div className="flex items-start gap-3">
                    {isCompleted ? (
                      <CheckCircle2 className="w-4 h-4 text-emerald-500 mt-0.5 shrink-0" />
                    ) : (
                      <AlertCircle className="w-4 h-4 text-amber-500 mt-0.5 shrink-0" />
                    )}
                    <div>
                      <div className="text-xs font-semibold text-zinc-900 dark:text-zinc-100">
                        {t.action}
                      </div>
                      <div className="text-[10px] text-zinc-400 font-mono mt-0.5">
                        {t.timestamp || 'Automatska sesija'}
                      </div>
                    </div>
                  </div>

                  <span
                    className={`text-[10px] font-mono font-semibold px-2 py-0.5 rounded-full uppercase ${
                      isCompleted
                        ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400'
                        : 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400'
                    }`}
                  >
                    {t.status}
                  </span>
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}
