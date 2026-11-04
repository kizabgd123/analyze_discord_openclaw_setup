import React, { useState } from 'react';
import ReactECharts from 'echarts-for-react';
import {
  Search,
  Filter,
  X,
  ChevronsLeft,
  ChevronLeft,
  ChevronRight,
  ChevronsRight,
  Users,
  ShieldAlert,
  Award,
  ArrowRight,
} from 'lucide-react';

export default function DebateView({ debateData, isDark }) {
  const [selectedSession, setSelectedSession] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [currentPage, setCurrentPage] = useState(1);
  const rowsPerPage = 5;

  const sessions = debateData?.sessions || [];
  const souls = debateData?.souls || [];
  const convergence = debateData?.convergence_chart || [];

  // Filtered sessions
  const filteredSessions = sessions.filter((s) => {
    const matchesSearch =
      s.topic.toLowerCase().includes(searchQuery.toLowerCase()) ||
      s.id.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesStatus = statusFilter === 'ALL' || s.status.toUpperCase() === statusFilter;
    return matchesSearch && matchesStatus;
  });

  const totalPages = Math.ceil(filteredSessions.length / rowsPerPage) || 1;
  const paginatedSessions = filteredSessions.slice(
    (currentPage - 1) * rowsPerPage,
    currentPage * rowsPerPage
  );

  // ECharts Multi-Agent Convergence Radar / Line Option
  const chartOption = {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'axis',
      backgroundColor: isDark ? '#1e1e24' : '#ffffff',
      borderColor: isDark ? '#27272a' : '#e4e4e7',
      textStyle: { color: isDark ? '#fafafa' : '#09090b', fontFamily: 'DM Sans' },
    },
    legend: {
      data: ['Strategist', 'Critic', 'Evaluator', 'Architect'],
      textStyle: { color: isDark ? '#a1a1aa' : '#71717a' },
      top: 0,
    },
    grid: { left: '3%', right: '4%', bottom: '3%', top: '15%', containLabel: true },
    xAxis: {
      type: 'category',
      data: convergence.map((c) => c.round),
      axisLine: { lineStyle: { color: isDark ? '#27272a' : '#e4e4e7' } },
      axisLabel: { color: isDark ? '#a1a1aa' : '#71717a' },
    },
    yAxis: {
      type: 'value',
      min: 0.5,
      max: 1.0,
      axisLine: { lineStyle: { color: isDark ? '#27272a' : '#e4e4e7' } },
      splitLine: { lineStyle: { color: isDark ? '#1e1e24' : '#f4f4f5' } },
      axisLabel: {
        color: isDark ? '#a1a1aa' : '#71717a',
        formatter: (val) => `${Math.round(val * 100)}%`,
      },
    },
    series: [
      {
        name: 'Strategist',
        type: 'line',
        smooth: true,
        data: convergence.map((c) => c.Strategist),
        itemStyle: { color: '#3b82f6' },
      },
      {
        name: 'Critic',
        type: 'line',
        smooth: true,
        data: convergence.map((c) => c.Critic),
        itemStyle: { color: '#ef4444' },
      },
      {
        name: 'Evaluator',
        type: 'line',
        smooth: true,
        data: convergence.map((c) => c.Evaluator),
        itemStyle: { color: '#10b981' },
      },
      {
        name: 'Architect',
        type: 'line',
        smooth: true,
        data: convergence.map((c) => c.Architect),
        itemStyle: { color: '#8b5cf6' },
      },
    ],
  };

  const getScoreFill = (score) => {
    if (score >= 0.9) return 'bg-emerald-500';
    if (score >= 0.75) return 'bg-orange-400';
    return 'bg-rose-500';
  };

  return (
    <div className="space-y-6">
      {/* Convergence ECharts Banner (1 Chart per Row) */}
      <div className="p-5 rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-[#0c0c0f] shadow-sm">
        <div className="mb-3 flex items-center justify-between">
          <div>
            <h2 className="text-base font-bold text-zinc-950 dark:text-zinc-50">
              Konvergencija Konsenzusa Agenata Kroz Runde
            </h2>
            <p className="text-xs text-zinc-500 dark:text-zinc-400">
              Prikaz slaganja stavova između 4 specijalizovana agenta tokom iterativnih debata.
            </p>
          </div>
          <span className="text-xs font-mono font-semibold px-2.5 py-1 rounded bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 border border-blue-200 dark:border-blue-800">
            Real-time Track
          </span>
        </div>
        <div className="h-[240px]">
          <ReactECharts option={chartOption} style={{ height: '100%', width: '100%' }} />
        </div>
      </div>

      {/* Main Split Layout */}
      <div className="flex gap-6 items-start transition-all duration-300">
        {/* Primary Data Table */}
        <div
          className={`${
            selectedSession ? 'w-full lg:w-2/3' : 'w-full'
          } bg-white dark:bg-[#0c0c0f] border border-zinc-200 dark:border-zinc-800 rounded-xl overflow-hidden shadow-sm transition-all duration-300`}
        >
          {/* Table Toolbar */}
          <div className="p-4 border-b border-zinc-200 dark:border-zinc-800 flex flex-wrap items-center justify-between gap-3">
            <div className="relative flex-1 min-w-[200px] max-w-md">
              <Search className="w-4 h-4 text-zinc-400 absolute left-3 top-2.5" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => {
                  setSearchQuery(e.target.value);
                  setCurrentPage(1);
                }}
                placeholder="Pretraži temu debate ili kanal..."
                className="w-full bg-zinc-50 dark:bg-[#09090b] border border-zinc-200 dark:border-zinc-800 rounded-lg pl-9 pr-3 py-1.5 text-xs focus:outline-none focus:ring-2 focus:ring-blue-500 text-zinc-950 dark:text-zinc-100"
              />
            </div>

            <div className="flex items-center gap-2">
              <Filter className="w-3.5 h-3.5 text-zinc-400" />
              <select
                value={statusFilter}
                onChange={(e) => {
                  setStatusFilter(e.target.value);
                  setCurrentPage(1);
                }}
                className="bg-zinc-50 dark:bg-[#09090b] border border-zinc-200 dark:border-zinc-800 rounded-lg px-2.5 py-1.5 text-xs text-zinc-700 dark:text-zinc-300 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="ALL">Svi Statusi</option>
                <option value="AKTIVNA">Aktivna</option>
                <option value="ZAVRŠENA">Završena</option>
              </select>
            </div>
          </div>

          {/* Table */}
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="sticky top-0 bg-zinc-100 dark:bg-zinc-900 text-zinc-500 dark:text-zinc-400 font-medium border-b border-zinc-200 dark:border-zinc-800">
                <tr>
                  <th className="py-3 px-4">Debatna Tema</th>
                  <th className="py-3 px-4">Runda / Turn</th>
                  <th className="py-3 px-4">Konsenzus</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4 text-right">Akcija</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-100 dark:divide-zinc-800">
                {paginatedSessions.length === 0 ? (
                  <tr>
                    <td colSpan="5" className="py-8 text-center text-zinc-400">
                      Nema pronađenih debata za zadati filter.
                    </td>
                  </tr>
                ) : (
                  paginatedSessions.map((s) => {
                    const isSelected = selectedSession?.id === s.id;
                    const scorePct = Math.round(s.consensus_score * 100);
                    return (
                      <tr
                        key={s.id}
                        onClick={() => setSelectedSession(s)}
                        className={`cursor-pointer transition-colors ${
                          isSelected
                            ? 'bg-blue-50 dark:bg-blue-900/30'
                            : 'hover:bg-zinc-50 dark:hover:bg-zinc-850'
                        }`}
                      >
                        <td className="py-3.5 px-4">
                          <div className="font-semibold text-zinc-950 dark:text-zinc-100">
                            {s.topic}
                          </div>
                          <div className="text-[11px] text-zinc-400 font-mono mt-0.5">
                            ID: {s.channel_id || s.id}
                          </div>
                        </td>

                        <td className="py-3.5 px-4 font-mono text-zinc-600 dark:text-zinc-300">
                          R{s.round} / T{s.turn}
                        </td>

                        <td className="py-3.5 px-4 min-w-[140px]">
                          <div className="flex items-center gap-2">
                            <div className="flex-1 h-2 bg-zinc-200 dark:bg-zinc-700 rounded-full overflow-hidden">
                              <div
                                className={`h-full ${getScoreFill(s.consensus_score)}`}
                                style={{ width: `${scorePct}%` }}
                              />
                            </div>
                            <span className="font-mono text-xs font-semibold text-zinc-700 dark:text-zinc-300">
                              {scorePct}%
                            </span>
                          </div>
                        </td>

                        <td className="py-3.5 px-4">
                          <span
                            className={`px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase ${
                              s.status === 'Aktivna'
                                ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400'
                                : 'bg-zinc-200 text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300'
                            }`}
                          >
                            {s.status}
                          </span>
                        </td>

                        <td className="py-3.5 px-4 text-right">
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              setSelectedSession(s);
                            }}
                            className="p-1 rounded hover:bg-zinc-200 dark:hover:bg-zinc-700 text-zinc-500 hover:text-blue-500 transition-colors"
                          >
                            <ArrowRight className="w-4 h-4" />
                          </button>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>

          {/* Icon-Only Pagination */}
          <div className="p-3 border-t border-zinc-200 dark:border-zinc-800 flex items-center justify-between text-xs text-zinc-500">
            <span>
              Strana {currentPage} od {totalPages} ({filteredSessions.length} ukupno)
            </span>
            <div className="flex items-center gap-1">
              <button
                disabled={currentPage === 1}
                onClick={() => setCurrentPage(1)}
                className="p-1.5 rounded hover:bg-zinc-100 dark:hover:bg-zinc-800 disabled:opacity-30 disabled:cursor-not-allowed"
                title="Prva strana"
              >
                <ChevronsLeft className="w-4 h-4" />
              </button>
              <button
                disabled={currentPage === 1}
                onClick={() => setCurrentPage((p) => p - 1)}
                className="p-1.5 rounded hover:bg-zinc-100 dark:hover:bg-zinc-800 disabled:opacity-30 disabled:cursor-not-allowed"
                title="Prethodna strana"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <button
                disabled={currentPage === totalPages}
                onClick={() => setCurrentPage((p) => p + 1)}
                className="p-1.5 rounded hover:bg-zinc-100 dark:hover:bg-zinc-800 disabled:opacity-30 disabled:cursor-not-allowed"
                title="Sledeća strana"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
              <button
                disabled={currentPage === totalPages}
                onClick={() => setCurrentPage(totalPages)}
                className="p-1.5 rounded hover:bg-zinc-100 dark:hover:bg-zinc-800 disabled:opacity-30 disabled:cursor-not-allowed"
                title="Poslednja strana"
              >
                <ChevronsRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>

        {/* Slide-In Investigation Side Panel */}
        {selectedSession && (
          <div className="w-full lg:w-1/3 bg-white dark:bg-[#0c0c0f] border border-zinc-200 dark:border-zinc-800 rounded-xl p-5 shadow-lg space-y-4 transition-all">
            <div className="flex items-center justify-between border-b border-zinc-200 dark:border-zinc-800 pb-3">
              <div className="flex items-center gap-2">
                <Award className="w-4 h-4 text-blue-500" />
                <h3 className="font-bold text-sm text-zinc-950 dark:text-zinc-50">
                  Inspekcija Debate
                </h3>
              </div>
              <button
                onClick={() => setSelectedSession(null)}
                className="p-1 rounded hover:bg-zinc-100 dark:hover:bg-zinc-800 text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div>
              <div className="text-xs font-semibold text-zinc-500 dark:text-zinc-400 mb-1">
                TEMA RASPRAVE
              </div>
              <p className="text-sm font-medium text-zinc-900 dark:text-zinc-100">
                {selectedSession.topic}
              </p>
            </div>

            <div className="grid grid-cols-2 gap-2 text-xs">
              <div className="p-2.5 rounded-lg bg-zinc-50 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800">
                <span className="text-zinc-400 block text-[10px] uppercase">Runda</span>
                <span className="font-bold text-zinc-800 dark:text-zinc-200">
                  {selectedSession.round}
                </span>
              </div>
              <div className="p-2.5 rounded-lg bg-zinc-50 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800">
                <span className="text-zinc-400 block text-[10px] uppercase">Slaganje</span>
                <span className="font-bold text-emerald-500">
                  {Math.round(selectedSession.consensus_score * 100)}%
                </span>
              </div>
            </div>

            {/* Turn History Transcript */}
            <div>
              <div className="text-xs font-semibold text-zinc-500 dark:text-zinc-400 mb-2">
                ARGUMENTI AGENATA (TRANSKRIPT)
              </div>
              <div className="space-y-2 max-h-[300px] overflow-y-auto pr-1">
                {selectedSession.history && selectedSession.history.length > 0 ? (
                  selectedSession.history.map((h, i) => (
                    <div
                      key={i}
                      className="p-3 rounded-lg bg-zinc-50 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 text-xs"
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span className="font-bold text-blue-600 dark:text-blue-400">
                          {h.agent}
                        </span>
                        <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-zinc-200 dark:bg-zinc-800 text-zinc-500">
                          {h.role}
                        </span>
                      </div>
                      <p className="text-zinc-700 dark:text-zinc-300 leading-relaxed">
                        {h.message}
                      </p>
                    </div>
                  ))
                ) : (
                  <p className="text-xs text-zinc-400 italic">
                    Nema zabeleženih replika za ovu sesiju.
                  </p>
                )}
              </div>
            </div>

            {/* Action Buttons */}
            <div className="pt-2 flex gap-2 border-t border-zinc-200 dark:border-zinc-800">
              <button
                onClick={() => alert(`Konsenzus potvrđen za temu: ${selectedSession.topic}`)}
                className="flex-1 bg-emerald-600 hover:bg-emerald-700 text-white font-medium text-xs py-2 px-3 rounded-lg shadow-sm transition-colors text-center"
              >
                Potvrdi Konsenzus
              </button>
              <button
                onClick={() => setSelectedSession(null)}
                className="bg-zinc-200 dark:bg-zinc-800 hover:bg-zinc-300 dark:hover:bg-zinc-700 text-zinc-700 dark:text-zinc-200 font-medium text-xs py-2 px-3 rounded-lg transition-colors"
              >
                Zatvori
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Soul Personas Row */}
      <div className="p-5 rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-[#0c0c0f] shadow-sm space-y-3">
        <div className="flex items-center gap-2">
          <Users className="w-4 h-4 text-blue-500" />
          <h3 className="font-bold text-sm text-zinc-950 dark:text-zinc-50">
            Aktivne Soul Personalnosti Agenata
          </h3>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
          {souls.map((soul) => (
            <div
              key={soul.id}
              className="p-3.5 rounded-lg border border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-900 flex flex-col justify-between"
            >
              <div>
                <span className="font-bold text-xs text-zinc-900 dark:text-zinc-100 block">
                  {soul.name}
                </span>
                <span className="text-[11px] text-blue-600 dark:text-blue-400 font-medium block mt-0.5">
                  {soul.role}
                </span>
                <p className="text-[11px] text-zinc-500 dark:text-zinc-400 mt-2 line-clamp-3">
                  {soul.system_prompt_preview}
                </p>
              </div>
              <div className="mt-3 pt-2 border-t border-zinc-200 dark:border-zinc-800 text-[10px] font-mono text-zinc-400 truncate">
                NLM: {soul.notebook_id.slice(0, 12)}...
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
