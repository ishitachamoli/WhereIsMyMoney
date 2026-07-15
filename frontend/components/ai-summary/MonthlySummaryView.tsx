'use client';

import { MonthlySummaryResponse } from '@/types';
import { formatCurrency } from '@/lib/utils';

interface MonthlySummaryViewProps {
  data: MonthlySummaryResponse;
}

/**
 * Renders the tone-phrased lines plus a stats grid for a single month.
 *
 * The phrased `lines` already embed the dominant currency symbol (server-side);
 * the stat cards below use the response `currency` so amounts stay consistent
 * regardless of the browser's stored preference.
 */
export default function MonthlySummaryView({ data }: MonthlySummaryViewProps) {
  const { meta, stats, lines, currency, has_data } = data;

  if (!has_data) {
    return (
      <div className="rounded-xl border border-zinc-700/50 bg-zinc-800 p-12 text-center">
        <div className="mb-4 text-5xl">🗓️</div>
        <h3 className="mb-2 text-lg font-semibold text-white">
          No transactions for {data.month_label}
        </h3>
        <p className="text-sm text-zinc-400">
          Pick a different month from the selector above.
        </p>
      </div>
    );
  }

  const isExecutive = data.tone === 'executive';

  return (
    <div className="space-y-6">
      {/* Tone header */}
      <div className="flex items-center gap-3">
        <span className="text-3xl">{meta.emoji}</span>
        <div>
          <h2 className="text-xl font-bold text-white">
            {meta.label} — {data.month_label}
          </h2>
          <p className="text-sm text-zinc-400">{meta.tagline}</p>
        </div>
      </div>

      {/* Phrased lines */}
      <section
        className={`rounded-xl border p-6 ${
          isExecutive
            ? 'border-zinc-700/60 bg-zinc-800'
            : 'border-zinc-700/50 bg-gradient-to-br from-zinc-800 to-zinc-900'
        }`}
      >
        <div className="space-y-4">
          {lines.map((line, idx) => (
            <div key={idx} className="flex items-start gap-3">
              {line.icon && (
                <span
                  className={`shrink-0 ${
                    line.icon === '•' ? 'mt-1 text-emerald-400' : 'text-2xl'
                  }`}
                >
                  {line.icon}
                </span>
              )}
              <p
                className={`leading-relaxed text-zinc-200 ${
                  isExecutive ? 'text-sm' : 'text-base'
                }`}
              >
                {line.text}
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* Stats grid */}
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <StatCard
          label="Total Spent"
          value={formatCurrency(stats.total_spent, currency)}
          color="text-red-400"
        />
        <StatCard
          label="Total Income"
          value={formatCurrency(stats.total_income, currency)}
          color="text-green-400"
        />
        <StatCard
          label="Net Savings"
          value={formatCurrency(stats.net_savings, currency)}
          color={stats.net_savings >= 0 ? 'text-emerald-400' : 'text-red-400'}
        />
        <StatCard
          label="Savings Rate"
          value={`${stats.savings_rate}%`}
          color={stats.savings_rate >= 20 ? 'text-emerald-400' : 'text-zinc-200'}
        />
        <StatCard
          label="Transactions"
          value={stats.transaction_count.toLocaleString()}
          color="text-blue-400"
        />
        <StatCard
          label="Avg Transaction"
          value={formatCurrency(stats.average_transaction, currency)}
          color="text-zinc-200"
        />
        <StatCard
          label="No-Spend Days"
          value={stats.no_spend_days.toString()}
          color="text-emerald-400"
        />
        {stats.expense_change_pct !== null && (
          <StatCard
            label="vs Prev Month"
            value={`${stats.expense_change_pct > 0 ? '↑' : '↓'}${Math.abs(
              stats.expense_change_pct
            )}%`}
            color={stats.expense_change_pct > 0 ? 'text-red-400' : 'text-green-400'}
          />
        )}
      </div>

      {/* Top categories */}
      {stats.top_categories.length > 0 && (
        <section className="rounded-xl border border-zinc-700/50 bg-zinc-800 p-6">
          <h3 className="mb-4 text-sm font-medium text-zinc-400">Top Categories</h3>
          <div className="space-y-3">
            {stats.top_categories.map((cat, idx) => (
              <div key={idx} className="flex items-center gap-3">
                <div className="flex-1">
                  <div className="mb-1 flex justify-between text-sm">
                    <span className="font-medium text-zinc-300">{cat.name}</span>
                    <span className="text-zinc-400">{cat.percentage}%</span>
                  </div>
                  <div className="h-2 overflow-hidden rounded-full bg-zinc-700">
                    <div
                      className="h-full rounded-full bg-emerald-500 transition-all"
                      style={{ width: `${Math.min(cat.percentage, 100)}%` }}
                    />
                  </div>
                </div>
                <span className="w-24 text-right text-sm font-semibold text-white">
                  {formatCurrency(cat.amount, currency)}
                </span>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

function StatCard({
  label,
  value,
  color,
}: {
  label: string;
  value: string;
  color: string;
}) {
  return (
    <div className="rounded-lg bg-zinc-900 p-3 text-center">
      <p className="mb-1 text-xs text-zinc-500">{label}</p>
      <p className={`text-lg font-bold ${color}`}>{value}</p>
    </div>
  );
}
