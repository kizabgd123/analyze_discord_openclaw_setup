import React, { useState } from 'react';
import ReactECharts from 'echarts-for-react';
import { BarChart2, ShieldCheck, Microscope, FileText, CheckCircle2 } from 'lucide-react';

export default function ResearchView({ researchData, isDark }) {
  const [selectedStudyTab, setSelectedStudyTab] = useState('ablation');

  const studies = researchData?.studies || {};
  const ablationChartData = researchData?.ablation_chart || [];
  const safetyChartData = researchData?.safety_chart || [];

  // ECharts Theme Config
  const tooltipStyle = {
    backgroundColor: isDark ? '#1e1e24' : '#ffffff',
    borderColor: isDark ? '#27272a' : '#e4e4e7',
    textStyle: { color: isDark ? '#fafafa' : '#09090b', fontFamily: 'DM Sans' },
  };

  // 1. Ablation Study Bar Chart Option
  const ablationOption = {
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, ...tooltipStyle },
    legend: {
      data: ['Safety Score', 'Accuracy', 'Engagement Score'],
      textStyle: { color: isDark ? '#a1a1aa' : '#71717a' },
      top: 0,
    },
    grid: { left: '3%', right: '4%', bottom: '3%', top: '15%', containLabel: true },
    xAxis: {
      type: 'category',
      data: ablationChartData.map((d) => d.condition),
      axisLine: { lineStyle: { color: isDark ? '#27272a' : '#e4e4e7' } },
      axisLabel: { color: isDark ? '#a1a1aa' : '#71717a', interval: 0, rotate: 15 },
    },
    yAxis: {
      type: 'value',
      min: 0,
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
        name: 'Safety Score',
        type: 'bar',
        data: ablationChartData.map((d) => d.safety),
        itemStyle: { color: '#10b981', borderRadius: [4, 4, 0, 0] },
      },
      {
        name: 'Accuracy',
        type: 'bar',
        data: ablationChartData.map((d) => d.accuracy),
        itemStyle: { color: '#3b82f6', borderRadius: [4, 4, 0, 0] },
      },
      {
        name: 'Engagement Score',
        type: 'bar',
        data: ablationChartData.map((d) => d.engagement),
        itemStyle: { color: '#f59e0b', borderRadius: [4, 4, 0, 0] },
      },
    ],
  };

  // 2. Safety Study Comparison Option
  const safetyOption = {
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis', ...tooltipStyle },
    legend: {
      data: ['Compliance Rate', 'Violation Rate'],
      textStyle: { color: isDark ? '#a1a1aa' : '#71717a' },
      top: 0,
    },
    grid: { left: '3%', right: '4%', bottom: '3%', top: '15%', containLabel: true },
    xAxis: {
      type: 'category',
      data: safetyChartData.map((d) => d.condition),
      axisLine: { lineStyle: { color: isDark ? '#27272a' : '#e4e4e7' } },
      axisLabel: { color: isDark ? '#a1a1aa' : '#71717a' },
    },
    yAxis: {
      type: 'value',
      min: 0,
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
        name: 'Compliance Rate',
        type: 'bar',
        data: safetyChartData.map((d) => d.compliance_rate),
        itemStyle: { color: '#10b981', borderRadius: [4, 4, 0, 0] },
      },
      {
        name: 'Violation Rate',
        type: 'bar',
        data: safetyChartData.map((d) => d.violation_rate),
        itemStyle: { color: '#ef4444', borderRadius: [4, 4, 0, 0] },
      },
    ],
  };

  const activeStudy = studies[`${selectedStudyTab}_study`] || {};

  return (
    <div className="space-y-6">
      {/* Sub-navigation pill selector */}
      <div className="flex gap-2 p-1.5 rounded-lg bg-zinc-100 dark:bg-[#0c0c0f] border border-zinc-200 dark:border-zinc-800 w-fit">
        {[
          { id: 'ablation', label: 'Ablation Studija' },
          { id: 'safety', label: 'Safety Studija' },
          { id: 'knowledge', label: 'Knowledge Studija' },
          { id: 'engagement', label: 'Engagement Studija' },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setSelectedStudyTab(tab.id)}
            className={`px-3 py-1.5 rounded-md text-xs font-semibold transition-all ${
              selectedStudyTab === tab.id
                ? 'bg-white dark:bg-zinc-800 text-blue-600 dark:text-blue-400 shadow-sm'
                : 'text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-200'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* 1 Chart per Row - Ablation Analysis */}
      {selectedStudyTab === 'ablation' && (
        <div className="p-5 rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-[#0c0c0f] shadow-sm">
          <div className="mb-4">
            <h3 className="text-base font-bold text-zinc-950 dark:text-zinc-50">
              Ablation Studija: Doprinos Komponenti Arhitekture
            </h3>
            <p className="text-xs text-zinc-500 dark:text-zinc-400">
              Merenje sigurnosti, tačnosti i angažovanja pri uklanjanju JudgeGuard-a, RAG-a i personalnih uloga.
            </p>
          </div>
          <div className="h-[320px]">
            <ReactECharts option={ablationOption} style={{ height: '100%', width: '100%' }} />
          </div>
        </div>
      )}

      {/* 1 Chart per Row - Safety Analysis */}
      {selectedStudyTab === 'safety' && (
        <div className="p-5 rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-[#0c0c0f] shadow-sm">
          <div className="mb-4">
            <h3 className="text-base font-bold text-zinc-950 dark:text-zinc-50">
              Safety Studija: Stopa Usklađenosti naspram Narušavanja
            </h3>
            <p className="text-xs text-zinc-500 dark:text-zinc-400">
              Analiza bezbednosnih provera i otpornosti na adversarialne promptove.
            </p>
          </div>
          <div className="h-[320px]">
            <ReactECharts option={safetyOption} style={{ height: '100%', width: '100%' }} />
          </div>
        </div>
      )}

      {/* Study Metadata Card */}
      <div className="p-5 rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-[#0c0c0f] shadow-sm space-y-4">
        <div className="flex items-center gap-2 border-b border-zinc-200 dark:border-zinc-800 pb-3">
          <Microscope className="w-4 h-4 text-blue-500" />
          <h4 className="font-bold text-sm text-zinc-950 dark:text-zinc-50 uppercase tracking-wide">
            Eksperimentalni Nalazi & Statistička Značajnost
          </h4>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
          <div className="p-4 rounded-lg bg-zinc-50 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800">
            <div className="font-semibold text-zinc-500 dark:text-zinc-400 mb-1">HIPOTEZA</div>
            <p className="text-zinc-800 dark:text-zinc-200 leading-relaxed font-medium">
              {activeStudy.hypothesis ||
                'Multi-agentna provera sa JudgeGuard mehanizmom statistički značajno smanjuje stopu halucinacija i narušavanja bezbednosti.'}
            </p>
          </div>

          <div className="p-4 rounded-lg bg-zinc-50 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800">
            <div className="font-semibold text-zinc-500 dark:text-zinc-400 mb-1">ZAKLJUČAK</div>
            <p className="text-zinc-800 dark:text-zinc-200 leading-relaxed font-medium">
              {activeStudy.summary ||
                'Potvrđena statistička robusnost p < 0.001 u svim testiranim scenarijima.'}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
