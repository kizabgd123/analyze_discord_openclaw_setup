import React from 'react';
import { ArrowUpRight, ArrowDownRight, ArrowRight, MessageSquare, Database, Cpu, CheckCircle } from 'lucide-react';

export default function KpiCards({ kpis }) {
  if (!kpis) return null;

  const cards = [
    {
      key: 'total_debates',
      data: kpis.total_debates,
      icon: MessageSquare,
      iconColor: 'text-blue-500',
    },
    {
      key: 'avg_consensus',
      data: kpis.avg_consensus,
      icon: CheckCircle,
      iconColor: 'text-emerald-500',
    },
    {
      key: 'rag_chunks',
      data: kpis.rag_chunks,
      icon: Database,
      iconColor: 'text-purple-500',
    },
    {
      key: 'local_llm',
      data: kpis.local_llm,
      icon: Cpu,
      iconColor: 'text-amber-500',
    },
  ];

  const getDeltaStyle = (type) => {
    switch (type) {
      case 'up':
        return 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400';
      case 'down':
        return 'bg-rose-100 text-rose-700 dark:bg-rose-900/30 dark:text-rose-400';
      case 'warn':
      default:
        return 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400';
    }
  };

  const renderArrow = (type) => {
    switch (type) {
      case 'up':
        return <ArrowUpRight className="w-3 h-3 inline mr-0.5" />;
      case 'down':
        return <ArrowDownRight className="w-3 h-3 inline mr-0.5" />;
      default:
        return <ArrowRight className="w-3 h-3 inline mr-0.5" />;
    }
  };

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      {cards.map(({ key, data, icon: Icon, iconColor }) => {
        if (!data) return null;
        return (
          <div
            key={key}
            className="p-5 rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-[#0c0c0f] shadow-sm hover:border-zinc-300 dark:hover:border-zinc-700 transition-all flex flex-col justify-between"
          >
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-medium text-zinc-500 dark:text-zinc-400">
                {data.label}
              </span>
              <div className={`p-2 rounded-lg bg-zinc-100 dark:bg-zinc-850 ${iconColor}`}>
                <Icon className="w-4 h-4" />
              </div>
            </div>

            <div className="flex items-baseline justify-between mt-1">
              <div className="text-2xl font-bold tracking-tight text-zinc-950 dark:text-zinc-50 font-mono">
                {data.value}
              </div>

              {data.delta && (
                <div
                  className={`text-xs font-semibold px-2 py-0.5 rounded-full flex items-center ${getDeltaStyle(
                    data.delta_type
                  )}`}
                >
                  {renderArrow(data.delta_type)}
                  <span>{data.delta}</span>
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
