'use client';

import { TransactionTotals } from '@/types';
import { formatCurrency } from '@/lib/utils';

interface TransactionTotalsBarProps {
  totals: TransactionTotals;
  count: number;
}

/**
 * Strip showing aggregated income / expense / net amounts for the entire
 * filtered transaction set (not just the current page).
 *
 * Green for income, red for expenses, blue for the signed net. The net keeps
 * an explicit +/- sign so users can tell surplus from deficit at a glance.
 */
export function TransactionTotalsBar({ totals, count }: TransactionTotalsBarProps) {
  const { credit_amount, debit_amount, net_amount, currency } = totals;
  const netSign = net_amount >= 0 ? '+' : '-';

  return (
    <div className="flex flex-col sm:flex-row sm:items-center sm:gap-6 gap-2 bg-zinc-800 border border-zinc-700 rounded-xl px-4 py-3 text-sm text-zinc-300">
      <span className="flex items-center gap-1.5">
        💚 <span className="text-zinc-400">Income:</span>
        <span className="font-semibold text-green-400">
          {formatCurrency(credit_amount, currency)}
        </span>
      </span>
      <span className="flex items-center gap-1.5">
        🔴 <span className="text-zinc-400">Expenses:</span>
        <span className="font-semibold text-red-400">
          {formatCurrency(debit_amount, currency)}
        </span>
      </span>
      <span className="flex items-center gap-1.5">
        💰 <span className="text-zinc-400">Net:</span>
        <span className="font-semibold text-blue-400">
          {netSign}
          {formatCurrency(net_amount, currency)}
        </span>
      </span>
      <span className="sm:ml-auto text-zinc-500">
        ({count.toLocaleString()} transaction{count === 1 ? '' : 's'})
      </span>
    </div>
  );
}
