'use client';

import { useEffect, useState } from 'react';
import { useCurrency, CURRENCY_OPTIONS } from '@/lib/currency';

/**
 * Currency selector dropdown for the sidebar.
 * Lets users pick their preferred display currency.
 */
export function CurrencySelector() {
  const { currency, setCurrency } = useCurrency();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) {
    return <div className="h-10" />;
  }

  return (
    <div className="flex items-center gap-3 px-3 py-2.5 w-full rounded-lg text-sm font-medium text-zinc-400">
      <span className="text-lg">💱</span>
      <select
        value={currency}
        onChange={(e) => setCurrency(e.target.value as typeof currency)}
        className="flex-1 bg-transparent border-none text-sm text-zinc-400 hover:text-white cursor-pointer focus:outline-none focus:ring-0 appearance-none"
        style={{ WebkitAppearance: 'none' }}
        title="Display currency"
      >
        {CURRENCY_OPTIONS.map((opt) => (
          <option key={opt.code} value={opt.code}>
            {opt.flag} {opt.symbol} {opt.code}
          </option>
        ))}
      </select>
    </div>
  );
}
