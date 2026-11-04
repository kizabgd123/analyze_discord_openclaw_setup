import React from 'react';
import { MessageSquare, BarChart3, Database, ShieldCheck, Sparkles } from 'lucide-react';

export default function TabNav({ activeTab, onSelectTab }) {
  const tabs = [
    { id: 'debates', label: 'Multi-Agent Debate', icon: MessageSquare },
    { id: 'research', label: 'Naučne Studije & Benchmark', icon: BarChart3 },
    { id: 'rag', label: 'RAG Baza Znanja', icon: Database },
    { id: 'governance', label: 'JudgeGuard & Revizija', icon: ShieldCheck },
    { id: 'chat', label: 'AI Data Chat Asistent', icon: Sparkles },
  ];

  return (
    <div className="border-b border-zinc-200 dark:border-zinc-800 flex overflow-x-auto gap-2">
      {tabs.map((tab) => {
        const Icon = tab.icon;
        const isActive = activeTab === tab.id;
        return (
          <button
            key={tab.id}
            onClick={() => onSelectTab(tab.id)}
            className={`flex items-center gap-2 py-3 px-4 font-medium text-sm transition-all whitespace-nowrap border-b-2 -mb-[1px] ${
              isActive
                ? 'border-blue-600 text-blue-600 dark:border-blue-500 dark:text-blue-400 font-semibold'
                : 'border-transparent text-zinc-500 dark:text-zinc-400 hover:text-zinc-800 dark:hover:text-zinc-200 hover:border-zinc-300 dark:hover:border-zinc-700'
            }`}
          >
            <Icon className={`w-4 h-4 ${isActive ? 'text-blue-600 dark:text-blue-400' : 'text-zinc-400'}`} />
            <span>{tab.label}</span>
          </button>
        );
      })}
    </div>
  );
}
