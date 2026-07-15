'use client';

import { useCallback, useEffect, useState } from 'react';
import { api } from '@/lib/api';
import {
  AITone,
  AvailableMonth,
  MonthlySummaryResponse,
  YearRecapResponse,
} from '@/types';
import { PageSkeleton } from '@/components/LoadingSkeletons';
import MonthSelector from '@/components/ai-summary/MonthSelector';
import ToneTabs, { TabKey } from '@/components/ai-summary/ToneTabs';
import MonthlySummaryView from '@/components/ai-summary/MonthlySummaryView';
import YearRecapView from '@/components/ai-summary/YearRecapView';

export default function AISummaryPage() {
  const [months, setMonths] = useState<AvailableMonth[]>([]);
  const [selectedMonth, setSelectedMonth] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<TabKey>('roast');

  const [monthlyCache, setMonthlyCache] = useState<Record<string, MonthlySummaryResponse>>({});
  const [yearCache, setYearCache] = useState<Record<number, YearRecapResponse>>({});

  const [initialLoading, setInitialLoading] = useState(true);
  const [contentLoading, setContentLoading] = useState(false);
  const [regenerating, setRegenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasNoData, setHasNoData] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  // Derive the recap year from the newest available month (months are newest-first).
  const recapYear = months.length > 0 ? parseInt(months[0].month.slice(0, 4), 10) : null;

  // ─── Initial load: available months ──────────────────────────────────────
  useEffect(() => {
    async function init() {
      try {
        setInitialLoading(true);
        const data = await api.getAvailableMonths();
        if (data.months.length === 0) {
          setHasNoData(true);
          return;
        }
        setMonths(data.months);
        setSelectedMonth(data.months[0].month);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load AI summary');
      } finally {
        setInitialLoading(false);
      }
    }
    init();
  }, []);

  // ─── Fetch helpers (with client-side caching) ─────────────────────────────
  const fetchMonthly = useCallback(
    async (month: string, tone: AITone, refresh = false) => {
      const cacheKey = `${month}|${tone}`;
      if (!refresh && monthlyCache[cacheKey]) return;
      setContentLoading(true);
      setError(null);
      try {
        const data = await api.getMonthlyAISummary(month, tone, refresh);
        setMonthlyCache((prev) => ({ ...prev, [cacheKey]: data }));
        setLastUpdated(new Date());
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load summary');
      } finally {
        setContentLoading(false);
      }
    },
    [monthlyCache]
  );

  const fetchYear = useCallback(
    async (year: number, refresh = false) => {
      if (!refresh && yearCache[year]) return;
      setContentLoading(true);
      setError(null);
      try {
        const data = await api.getYearlyAIRecap(year, refresh);
        setYearCache((prev) => ({ ...prev, [year]: data }));
        setLastUpdated(new Date());
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load year recap');
      } finally {
        setContentLoading(false);
      }
    },
    [yearCache]
  );

  // ─── React to tab / month changes ─────────────────────────────────────────
  useEffect(() => {
    if (hasNoData) return;
    if (activeTab === 'year') {
      if (recapYear !== null) fetchYear(recapYear);
    } else if (selectedMonth) {
      fetchMonthly(selectedMonth, activeTab);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTab, selectedMonth, recapYear, hasNoData]);

  // ─── Regenerate currently active view ─────────────────────────────────────
  const handleRegenerate = async () => {
    setRegenerating(true);
    try {
      if (activeTab === 'year') {
        if (recapYear !== null) await fetchYear(recapYear, true);
      } else if (selectedMonth) {
        await fetchMonthly(selectedMonth, activeTab, true);
      }
    } finally {
      setRegenerating(false);
    }
  };

  const formatLastUpdated = () => {
    if (!lastUpdated) return 'Unknown';
    const diffMins = Math.floor((Date.now() - lastUpdated.getTime()) / 60000);
    if (diffMins < 1) return 'Just now';
    if (diffMins === 1) return '1 minute ago';
    if (diffMins < 60) return `${diffMins} minutes ago`;
    const diffHours = Math.floor(diffMins / 60);
    if (diffHours === 1) return '1 hour ago';
    if (diffHours < 24) return `${diffHours} hours ago`;
    const diffDays = Math.floor(diffHours / 24);
    return diffDays === 1 ? '1 day ago' : `${diffDays} days ago`;
  };

  // ─── Render states ─────────────────────────────────────────────────────────
  if (initialLoading) return <PageSkeleton />;

  if (hasNoData) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-white">🤖 AI Summary</h1>
          <p className="mt-1 text-sm text-zinc-400">Your personalized financial insights</p>
        </div>
        <div className="rounded-xl border border-zinc-700/50 bg-zinc-800 p-12 text-center">
          <div className="mb-4 text-6xl">📊</div>
          <h2 className="mb-2 text-xl font-semibold text-white">No data yet</h2>
          <p className="mb-6 text-sm text-zinc-400">
            Upload a bank statement to get your personalized AI financial summary.
          </p>
          <a
            href="/upload"
            className="inline-block rounded-lg bg-blue-600 px-6 py-3 text-sm font-medium text-white transition-colors hover:bg-blue-700"
          >
            Upload Statement →
          </a>
        </div>
      </div>
    );
  }

  const isYear = activeTab === 'year';
  const monthlyData = selectedMonth
    ? monthlyCache[`${selectedMonth}|${activeTab}`]
    : undefined;
  const yearData = recapYear !== null ? yearCache[recapYear] : undefined;

  return (
    <div className="space-y-6 pb-8">
      {/* Header */}
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">🤖 AI Summary</h1>
          <p className="mt-1 text-sm text-zinc-400">
            {isYear
              ? 'Your year in money, wrapped'
              : 'Pick a month and a personality'}
          </p>
        </div>
        <div className="flex items-center gap-4">
          <button
            onClick={handleRegenerate}
            disabled={regenerating || contentLoading}
            className="flex items-center gap-2 rounded-lg border border-zinc-700 bg-zinc-800 px-4 py-2 text-white transition-colors hover:bg-zinc-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {regenerating ? '⏳ Regenerating...' : '🔄 Regenerate'}
          </button>
          {lastUpdated && (
            <span className="whitespace-nowrap text-xs text-zinc-500">
              Last updated: {formatLastUpdated()}
            </span>
          )}
        </div>
      </div>

      {/* Controls: month selector (hidden on year tab) + tabs */}
      <div className="space-y-3">
        {!isYear && (
          <MonthSelector
            months={months}
            selected={selectedMonth}
            onChange={setSelectedMonth}
            disabled={contentLoading}
          />
        )}
        <ToneTabs active={activeTab} onChange={setActiveTab} />
      </div>

      {/* Error */}
      {error && (
        <div className="rounded-lg border border-red-700/40 bg-red-900/20 p-4 text-sm text-red-300">
          {error}
        </div>
      )}

      {/* Content */}
      {contentLoading && !monthlyData && !yearData ? (
        <div className="rounded-xl border border-zinc-700/50 bg-zinc-800 p-12 text-center">
          <div className="mb-3 text-4xl">🤖</div>
          <p className="text-sm text-zinc-400">Crunching the numbers...</p>
        </div>
      ) : isYear ? (
        yearData && <YearRecapView data={yearData} />
      ) : (
        monthlyData && <MonthlySummaryView data={monthlyData} />
      )}
    </div>
  );
}
