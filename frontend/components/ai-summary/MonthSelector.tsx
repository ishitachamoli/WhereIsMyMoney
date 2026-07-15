'use client';

import { AvailableMonth } from '@/types';

interface MonthSelectorProps {
  months: AvailableMonth[];
  selected: string | null;
  onChange: (month: string) => void;
  disabled?: boolean;
}

/**
 * Month picker with prev/next arrows and a dropdown.
 *
 * Only months that actually have transaction data are selectable. Arrows are
 * disabled at the bounds. `months` is expected newest-first (as returned by the
 * available-months endpoint).
 */
export default function MonthSelector({
  months,
  selected,
  onChange,
  disabled = false,
}: MonthSelectorProps) {
  if (months.length === 0) {
    return null;
  }

  const currentIndex = months.findIndex((m) => m.month === selected);
  const current = currentIndex >= 0 ? months[currentIndex] : months[0];

  // months[] is newest-first: index 0 = newest, last index = oldest.
  const hasNewer = currentIndex > 0;
  const hasOlder = currentIndex < months.length - 1 && currentIndex >= 0;

  const goNewer = () => {
    if (hasNewer) onChange(months[currentIndex - 1].month);
  };
  const goOlder = () => {
    if (hasOlder) onChange(months[currentIndex + 1].month);
  };

  return (
    <div className="flex items-center gap-2">
      <button
        type="button"
        onClick={goOlder}
        disabled={disabled || !hasOlder}
        aria-label="Previous month"
        className="flex h-9 w-9 items-center justify-center rounded-lg border border-zinc-700 bg-zinc-800 text-zinc-300 transition-colors hover:bg-zinc-700 disabled:cursor-not-allowed disabled:opacity-40"
      >
        ←
      </button>

      <div className="relative">
        <select
          value={current.month}
          onChange={(e) => onChange(e.target.value)}
          disabled={disabled}
          aria-label="Select month"
          className="min-w-[160px] cursor-pointer appearance-none rounded-lg border border-zinc-700 bg-zinc-800 py-2 pl-4 pr-9 text-center text-sm font-semibold text-white transition-colors hover:bg-zinc-700 focus:outline-none focus:ring-2 focus:ring-emerald-500/50 disabled:opacity-50"
        >
          {months.map((m) => (
            <option key={m.month} value={m.month}>
              {m.label}
            </option>
          ))}
        </select>
        <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-xs text-zinc-400">
          ▼
        </span>
      </div>

      <button
        type="button"
        onClick={goNewer}
        disabled={disabled || !hasNewer}
        aria-label="Next month"
        className="flex h-9 w-9 items-center justify-center rounded-lg border border-zinc-700 bg-zinc-800 text-zinc-300 transition-colors hover:bg-zinc-700 disabled:cursor-not-allowed disabled:opacity-40"
      >
        →
      </button>
    </div>
  );
}
