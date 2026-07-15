'use client';

import { YearRecapResponse } from '@/types';
import { formatCurrency } from '@/lib/utils';

interface YearRecapViewProps {
  data: YearRecapResponse;
}

/**
 * Spotify-Wrapped-style annual recap.
 *
 * Renders a large personality title, headline stat cards, an animated top-
 * categories bar list, surprising stats, achievement badges, and a closing
 * narrative. Amounts use the response `currency` for consistency.
 */
export default function YearRecapView({ data }: YearRecapViewProps) {
  const { currency } = data;

  if (!data.has_data) {
    return (
      <div className="rounded-xl border border-zinc-700/50 bg-zinc-800 p-12 text-center">
        <div className="mb-4 text-5xl">📭</div>
        <h3 className="mb-2 text-lg font-semibold text-white">
          No data for {data.year}
        </h3>
        <p className="text-sm text-zinc-400">{data.narrative}</p>
      </div>
    );
  }

  const { headline_stats: hs } = data;
  const maxCatAmount = Math.max(
    ...data.top_categories.map((c) => c.amount),
    1
  );

  return (
    <div className="space-y-6">
      {/* Personality hero */}
      <section className="relative overflow-hidden rounded-2xl border border-purple-700/30 bg-gradient-to-br from-fuchsia-900/70 via-purple-900/60 to-indigo-950 p-8 text-center">
        <div className="absolute -left-10 top-0 h-64 w-64 rounded-full bg-fuchsia-500/20 blur-3xl" />
        <div className="absolute -right-10 bottom-0 h-64 w-64 rounded-full bg-indigo-500/20 blur-3xl" />
        <div className="relative">
          <p className="text-sm font-medium uppercase tracking-widest text-fuchsia-300">
            Your {data.year} in Money
          </p>
          <div className="my-4 text-7xl">{data.personality_emoji}</div>
          <h1 className="bg-gradient-to-r from-fuchsia-300 via-white to-indigo-300 bg-clip-text text-4xl font-extrabold text-transparent md:text-5xl">
            {data.personality_title}
          </h1>
        </div>
      </section>

      {/* Headline stats */}
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <BigStat
          label="Total Spent"
          value={formatCurrency(hs.total_spent, currency)}
          gradient="from-red-900/40 to-zinc-900"
        />
        <BigStat
          label="Total Income"
          value={formatCurrency(hs.total_income, currency)}
          gradient="from-green-900/40 to-zinc-900"
        />
        <BigStat
          label="Net Savings"
          value={formatCurrency(hs.net_savings, currency)}
          gradient="from-emerald-900/40 to-zinc-900"
        />
        <BigStat
          label="Savings Rate"
          value={`${hs.savings_rate}%`}
          gradient="from-cyan-900/40 to-zinc-900"
        />
      </div>

      <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
        <BigStat
          label="Transactions"
          value={hs.transaction_count.toLocaleString()}
          gradient="from-blue-900/40 to-zinc-900"
        />
        <BigStat
          label="Biggest Month"
          value={hs.biggest_month ?? '—'}
          gradient="from-amber-900/40 to-zinc-900"
        />
        <BigStat
          label="Smallest Month"
          value={hs.smallest_month ?? '—'}
          gradient="from-teal-900/40 to-zinc-900"
        />
      </div>

      {/* Top categories */}
      {data.top_categories.length > 0 && (
        <section className="rounded-xl border border-zinc-700/50 bg-zinc-800 p-6">
          <h2 className="mb-4 flex items-center gap-2 text-lg font-semibold text-white">
            <span className="text-xl">🏆</span> Your Top Categories
          </h2>
          <div className="space-y-4">
            {data.top_categories.map((cat, idx) => (
              <div key={idx}>
                <div className="mb-1.5 flex items-baseline justify-between">
                  <span className="flex items-center gap-2 font-medium text-zinc-200">
                    <span className="text-sm font-bold text-zinc-500">
                      #{idx + 1}
                    </span>
                    {cat.name}
                  </span>
                  <span className="text-sm font-semibold text-white">
                    {formatCurrency(cat.amount, currency)}
                    <span className="ml-2 text-xs text-zinc-500">
                      {cat.count} txns
                    </span>
                  </span>
                </div>
                <div className="h-3 overflow-hidden rounded-full bg-zinc-700">
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-fuchsia-500 to-indigo-500 transition-all duration-700"
                    style={{ width: `${(cat.amount / maxCatAmount) * 100}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Surprising stats */}
      {data.surprising_stats.length > 0 && (
        <section className="rounded-xl border border-zinc-700/50 bg-zinc-800 p-6">
          <h2 className="mb-4 flex items-center gap-2 text-lg font-semibold text-white">
            <span className="text-xl">🤯</span> Surprising Stats
          </h2>
          <ol className="space-y-3">
            {data.surprising_stats.map((stat, idx) => (
              <li key={idx} className="flex items-start gap-3">
                <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-indigo-600 text-xs font-bold text-white">
                  {idx + 1}
                </span>
                <p className="leading-relaxed text-zinc-200">{stat}</p>
              </li>
            ))}
          </ol>
        </section>
      )}

      {/* Biggest transactions */}
      {data.biggest_transactions.length > 0 && (
        <section className="rounded-xl border border-zinc-700/50 bg-zinc-800 p-6">
          <h2 className="mb-4 flex items-center gap-2 text-lg font-semibold text-white">
            <span className="text-xl">💥</span> Biggest Splurges
          </h2>
          <div className="space-y-2">
            {data.biggest_transactions.map((t, idx) => (
              <div
                key={idx}
                className="flex items-center justify-between rounded-lg bg-zinc-900 p-3"
              >
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-white">
                    {t.description}
                  </p>
                  <p className="text-xs text-zinc-500">{t.category}</p>
                </div>
                <span className="ml-3 text-sm font-semibold text-red-400">
                  {formatCurrency(t.amount, currency)}
                </span>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Achievements */}
      {data.achievements.length > 0 && (
        <section className="rounded-xl border border-zinc-700/50 bg-zinc-800 p-6">
          <h2 className="mb-4 flex items-center gap-2 text-lg font-semibold text-white">
            <span className="text-xl">🎖️</span> Achievements Unlocked
          </h2>
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            {data.achievements.map((ach, idx) => (
              <div
                key={idx}
                className="flex items-start gap-3 rounded-lg border border-amber-700/30 bg-amber-900/20 p-4"
              >
                <span className="text-2xl">{ach.icon}</span>
                <div>
                  <h3 className="text-sm font-semibold text-amber-200">
                    {ach.title}
                  </h3>
                  <p className="text-xs text-zinc-400">{ach.description}</p>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Narrative */}
      <section className="relative overflow-hidden rounded-2xl border border-indigo-700/30 bg-gradient-to-br from-indigo-900/50 to-zinc-900 p-8 text-center">
        <p className="mx-auto max-w-2xl text-lg leading-relaxed text-zinc-100">
          {data.narrative}
        </p>
      </section>
    </div>
  );
}

function BigStat({
  label,
  value,
  gradient,
}: {
  label: string;
  value: string;
  gradient: string;
}) {
  return (
    <div
      className={`rounded-xl border border-white/5 bg-gradient-to-br ${gradient} p-4 text-center`}
    >
      <p className="mb-1 text-xs uppercase tracking-wide text-zinc-400">{label}</p>
      <p className="text-xl font-bold text-white md:text-2xl">{value}</p>
    </div>
  );
}
