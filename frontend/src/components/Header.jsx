import React from 'react';
import { Sun, Moon, Cpu, ShieldCheck, Activity } from 'lucide-react';

export default function Header({ isDark, onToggleTheme, modelInfo, isOnline }) {
  return (
    <header className="border-b border-zinc-200 dark:border-zinc-800 bg-white/80 dark:bg-[#0c0c0f]/80 backdrop-blur-md sticky top-0 z-40 transition-colors">
      <div className="max-w-[1600px] mx-auto px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-600 flex items-center justify-center text-white shadow-md shadow-blue-500/20">
            <Activity className="w-5 h-5 animate-pulse" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold tracking-tight text-zinc-950 dark:text-zinc-50">
                Antigravity Data & Observability
              </h1>
              <span className="text-[10px] uppercase font-mono font-bold tracking-wider px-2 py-0.5 rounded-full bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-800">
                v1.0-live
              </span>
            </div>
            <p className="text-xs text-zinc-500 dark:text-zinc-400">
              Multi-Agent Debates · RAG Knowledge · LiteRT Runtime · Scientific Benchmarks
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {/* Local Runtime Badge */}
          <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-lg border border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-900 text-xs">
            <Cpu className="w-3.5 h-3.5 text-blue-500" />
            <span className="text-zinc-600 dark:text-zinc-300 font-mono">
              {modelInfo?.default_model || 'gemma2:2b'}
            </span>
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-zinc-200 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300 uppercase">
              {modelInfo?.backend || 'CPU'}
            </span>
          </div>

          {/* System Integrity Badge */}
          <div className="hidden md:flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-emerald-200 dark:border-emerald-800/40 bg-emerald-50 dark:bg-emerald-950/20 text-xs text-emerald-700 dark:text-emerald-400">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-500" />
            <span className="font-medium">JudgeGuard Active</span>
          </div>

          {/* Theme Toggle Button */}
          <button
            onClick={onToggleTheme}
            aria-label="Toggle Dark/Light Mode"
            className="p-2 rounded-lg border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 hover:bg-zinc-100 dark:hover:bg-zinc-800 text-zinc-700 dark:text-zinc-300 transition-colors shadow-sm"
          >
            {isDark ? <Sun className="w-4 h-4 text-amber-400" /> : <Moon className="w-4 h-4 text-zinc-600" />}
          </button>
        </div>
      </div>
    </header>
  );
}
