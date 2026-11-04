import React, { useState, useEffect } from 'react';
import axios from 'axios';
import Header from './components/Header';
import KpiCards from './components/KpiCards';
import TabNav from './components/TabNav';
import DebateView from './components/DebateView';
import ResearchView from './components/ResearchView';
import RagView from './components/RagView';
import GovernanceView from './components/GovernanceView';
import ChatPanel from './components/ChatPanel';
import { Loader2, RefreshCw } from 'lucide-react';

export default function App() {
  const [isDark, setIsDark] = useState(true);
  const [activeTab, setActiveTab] = useState('debates');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Data states
  const [kpis, setKpis] = useState(null);
  const [debates, setDebates] = useState(null);
  const [rag, setRag] = useState(null);
  const [research, setResearch] = useState(null);
  const [governance, setGovernance] = useState(null);
  const [models, setModels] = useState(null);

  // Sync dark class on HTML element
  useEffect(() => {
    if (isDark) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [isDark]);

  const toggleTheme = () => setIsDark((prev) => !prev);

  const fetchAllData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [kpiRes, debRes, ragRes, resRes, govRes, modRes] = await Promise.all([
        axios.get('/api/kpis'),
        axios.get('/api/debates'),
        axios.get('/api/rag'),
        axios.get('/api/research'),
        axios.get('/api/governance'),
        axios.get('/api/models'),
      ]);

      setKpis(kpiRes.data);
      setDebates(debRes.data);
      setRag(ragRes.data);
      setResearch(resRes.data);
      setGovernance(govRes.data);
      setModels(modRes.data);
    } catch (err) {
      console.error('Greška pri učitavanju podataka:', err);
      setError('Neuspelo povezivanje sa FastAPI backend serverom.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAllData();
  }, []);

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-[#09090b] text-zinc-950 dark:text-zinc-50 flex flex-col font-sans transition-colors">
      {/* Top Navigation Header */}
      <Header
        isDark={isDark}
        onToggleTheme={toggleTheme}
        modelInfo={models}
        isOnline={!error}
      />

      {/* Main Content Dashboard Container */}
      <main className="flex-1 max-w-[1600px] w-full mx-auto p-6 space-y-6">
        {/* Loading Indicator */}
        {loading && (
          <div className="flex items-center justify-center p-12 text-zinc-500 gap-2">
            <Loader2 className="w-5 h-5 animate-spin text-blue-500" />
            <span className="text-sm">Učitavam metrike i stanje agenata...</span>
          </div>
        )}

        {/* Error Alert */}
        {error && (
          <div className="p-4 rounded-xl border border-rose-200 dark:border-rose-900/40 bg-rose-50 dark:bg-rose-950/20 text-rose-700 dark:text-rose-400 text-xs flex items-center justify-between">
            <span>{error}</span>
            <button
              onClick={fetchAllData}
              className="flex items-center gap-1 font-semibold underline hover:no-underline"
            >
              <RefreshCw className="w-3.5 h-3.5" /> Pokušaj ponovo
            </button>
          </div>
        )}

        {!loading && (
          <>
            {/* Top KPI Cards */}
            <KpiCards kpis={kpis} />

            {/* Tab Navigation */}
            <TabNav activeTab={activeTab} onSelectTab={setActiveTab} />

            {/* Tab Content Panes */}
            <div>
              {activeTab === 'debates' && <DebateView debateData={debates} isDark={isDark} />}
              {activeTab === 'research' && <ResearchView researchData={research} isDark={isDark} />}
              {activeTab === 'rag' && <RagView ragData={rag} />}
              {activeTab === 'governance' && <GovernanceView govData={governance} />}
              {activeTab === 'chat' && <ChatPanel isDark={isDark} modelInfo={models} />}
            </div>
          </>
        )}
      </main>

      {/* Dashboard Footer */}
      <footer className="border-t border-zinc-200 dark:border-zinc-800 py-4 px-6 text-center text-xs text-zinc-400 bg-white/50 dark:bg-[#0c0c0f]/50">
        <div className="max-w-[1600px] mx-auto flex flex-col sm:flex-row items-center justify-between gap-2">
          <span>Antigravity Autonomous Multi-Agent System · Production Build</span>
          <span className="font-mono text-[11px] text-zinc-500">
            Stack: React 18 · Vite · Tailwind · ECharts · FastAPI · LiteRT
          </span>
        </div>
      </footer>
    </div>
  );
}
