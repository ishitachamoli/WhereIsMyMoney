'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts';
import { api } from '@/lib/api';
import { CategoryAnalyticsResponse } from '@/types';
import { formatCurrency, formatCurrencyAxis, formatDate, getCategoryConfig } from '@/lib/utils';

interface CategoryDeepDiveProps {
  categoryName: string;
  onBack: () => void;
}

function CustomBarTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  const amount = payload[0]?.value ?? 0;
  const changePct = payload[0]?.payload?.change_pct;
  return (
    <div className="bg-zinc-800 border border-zinc-600 rounded-lg p-3 shadow-xl">
      <p className="text-white font-medium text-sm mb-1">{label}</p>
      <div className="text-xs text-zinc-300 space-y-0.5">
        <div>Amount: <span className="text-white font-medium">{formatCurrency(amount)}</span></div>
        {changePct !== null && changePct !== undefined && (
          <div>
            vs Previous:{' '}
            <span className={`font-medium ${changePct > 0 ? 'text-red-400' : 'text-green-400'}`}>
              {changePct > 0 ? '+' : ''}{changePct}%
            </span>
          </div>
        )}
      </div>
    </div>
  );
}

function CustomLineTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  const amount = payload[0]?.value ?? 0;
  return (
    <div className="bg-zinc-800 border border-zinc-600 rounded-lg p-3 shadow-xl">
      <p className="text-white font-medium text-sm mb-1">{label}</p>
      <div className="text-xs text-zinc-300">
        Spent: <span className="text-white font-medium">{formatCurrency(amount)}</span>
      </div>
    </div>
  );
}

export function CategoryDeepDive({ categoryName, onBack }: CategoryDeepDiveProps) {
  const router = useRouter();
  const [data, setData] = useState<CategoryAnalyticsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const config = getCategoryConfig(categoryName);

  useEffect(() => {
    async function fetchData() {
      try {
        setLoading(true);
        setError(null);
        const result = await api.getCategoryAnalytics(categoryName);
        setData(result);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load category analytics');
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, [categoryName]);

  if (loading) {
    return (
      <div className="space-y-4 animate-pulse">
        <div className="h-8 bg-zinc-700 rounded w-48" />
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-24 bg-zinc-700 rounded-xl" />
          ))}
        </div>
        <div className="h-64 bg-zinc-700 rounded-xl" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-12">
        <p className="text-red-400 mb-4">{error}</p>
        <button onClick={onBack} className="text-blue-400 hover:text-blue-300 text-sm">
          ← Back to overview
        </button>
      </div>
    );
  }

  if (!data) return null;

  const { summary, daily_spending, monthly_spending, top_transactions } = data;

  // Find top 3 months for highlighting
  const sortedMonths = [...monthly_spending].sort((a, b) => b.amount - a.amount);
  const top3Months = new Set(sortedMonths.slice(0, 3).map((m) => m.month));

  const trendIcon = summary.trend === 'increasing' ? '📈' : summary.trend === 'decreasing' ? '📉' : '➡️';
  const trendColor = summary.trend === 'increasing' ? 'text-red-400' : summary.trend === 'decreasing' ? 'text-green-400' : 'text-zinc-400';

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <button
          onClick={onBack}
          className="text-zinc-400 hover:text-white transition-colors p-1 rounded hover:bg-zinc-700"
        >
          ←
        </button>
        <span className="text-2xl">{config.emoji}</span>
        <div>
          <h2 className="text-xl font-bold text-white">{categoryName}</h2>
          <p className="text-xs text-zinc-400">Category deep-dive analytics</p>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        <div className="bg-zinc-800 rounded-xl p-4 border border-zinc-700/50">
          <p className="text-xs text-zinc-400 mb-1">Total Spent</p>
          <p className="text-lg font-bold text-white">{formatCurrency(summary.total)}</p>
        </div>
        <div className="bg-zinc-800 rounded-xl p-4 border border-zinc-700/50">
          <p className="text-xs text-zinc-400 mb-1">Avg Monthly</p>
          <p className="text-lg font-bold text-white">{formatCurrency(summary.avg_monthly)}</p>
        </div>
        <div className="bg-zinc-800 rounded-xl p-4 border border-zinc-700/50">
          <p className="text-xs text-zinc-400 mb-1">% of Total</p>
          <p className="text-lg font-bold text-white">{summary.pct_of_total.toFixed(1)}%</p>
        </div>
        <div className="bg-zinc-800 rounded-xl p-4 border border-zinc-700/50">
          <p className="text-xs text-zinc-400 mb-1">Transactions</p>
          <p className="text-lg font-bold text-white">{summary.count}</p>
        </div>
        <div className="bg-zinc-800 rounded-xl p-4 border border-zinc-700/50">
          <p className="text-xs text-zinc-400 mb-1">Trend</p>
          <p className={`text-lg font-bold capitalize ${trendColor}`}>
            {trendIcon} {summary.trend}
          </p>
        </div>
      </div>

      {/* Monthly Breakdown */}
      {monthly_spending.length > 0 && (
        <div className="bg-zinc-800 rounded-xl p-5 border border-zinc-700/50">
          <h3 className="text-base font-semibold text-white mb-4">Monthly Breakdown</h3>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={monthly_spending} margin={{ top: 10, right: 20, left: 10, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#3f3f46" vertical={false} />
              <XAxis
                dataKey="month"
                stroke="#71717a"
                fontSize={11}
                tickLine={false}
                axisLine={{ stroke: '#3f3f46' }}
              />
              <YAxis
                stroke="#71717a"
                fontSize={11}
                tickFormatter={formatCurrencyAxis}
                tickLine={false}
                axisLine={false}
                width={55}
              />
              <Tooltip content={<CustomBarTooltip />} />
              <Bar
                dataKey="amount"
                radius={[4, 4, 0, 0]}
                animationDuration={800}
              >
                {monthly_spending.map((entry, index) => (
                  <Cell
                    key={`cell-${index}`}
                    fill={top3Months.has(entry.month) ? '#f59e0b' : config.color || '#8b5cf6'}
                    opacity={top3Months.has(entry.month) ? 1 : 0.7}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
          <p className="text-xs text-zinc-500 mt-2">
            🟡 Top 3 spending months highlighted
          </p>
        </div>
      )}

      {/* Daily Spending */}
      {daily_spending.length > 0 && (
        <div className="bg-zinc-800 rounded-xl p-5 border border-zinc-700/50">
          <h3 className="text-base font-semibold text-white mb-4">Daily Spending Pattern</h3>
          <ResponsiveContainer width="100%" height={240}>
            <LineChart data={daily_spending} margin={{ top: 10, right: 20, left: 10, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#3f3f46" vertical={false} />
              <XAxis
                dataKey="date"
                stroke="#71717a"
                fontSize={10}
                tickLine={false}
                axisLine={{ stroke: '#3f3f46' }}
                interval="preserveStartEnd"
              />
              <YAxis
                stroke="#71717a"
                fontSize={11}
                tickFormatter={formatCurrencyAxis}
                tickLine={false}
                axisLine={false}
                width={55}
              />
              <Tooltip content={<CustomLineTooltip />} />
              <Line
                type="monotone"
                dataKey="amount"
                stroke={config.color || '#8b5cf6'}
                strokeWidth={1.5}
                dot={false}
                activeDot={{ r: 4, fill: config.color || '#8b5cf6', stroke: '#fff', strokeWidth: 2 }}
                animationDuration={1000}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Top Transactions */}
      {top_transactions.length > 0 && (
        <div className="bg-zinc-800 rounded-xl p-5 border border-zinc-700/50">
          <h3 className="text-base font-semibold text-white mb-4">Top Transactions</h3>
          <div className="space-y-2">
            {top_transactions.map((txn, i) => (
              <div
                key={i}
                className="flex items-center gap-3 px-3 py-2 rounded-lg bg-zinc-700/30 border border-zinc-700/50"
              >
                <span className="text-xs text-zinc-500 font-mono w-5">#{i + 1}</span>
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-zinc-200 truncate">{txn.description}</p>
                  <p className="text-xs text-zinc-500">{formatDate(txn.date)}</p>
                </div>
                <span className="text-sm font-semibold text-white whitespace-nowrap">
                  {formatCurrency(txn.amount)}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* View All Transactions Button */}
      <div className="flex justify-center">
        <button
          onClick={() => router.push(`/transactions?category=${encodeURIComponent(categoryName)}`)}
          className="px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium transition-colors inline-flex items-center gap-2"
        >
          View All Transactions →
        </button>
      </div>
    </div>
  );
}
