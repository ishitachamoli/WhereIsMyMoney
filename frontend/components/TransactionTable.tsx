import { Transaction } from '@/types';
import { CategoryBadge } from './CategoryBadge';
import { formatCurrency, formatDate } from '@/lib/utils';

interface TransactionTableProps {
  transactions: Transaction[];
  onCategoryEdit?: (id: number, category: string) => void;
  compact?: boolean;
}

export function TransactionTable({
  transactions,
  compact = false,
}: TransactionTableProps) {
  if (!transactions || transactions.length === 0) {
    return (
      <div className="text-center py-12">
        <div className="text-4xl mb-3">📭</div>
        <p className="text-zinc-400">No transactions found</p>
      </div>
    );
  }

  return (
    <>
      {/* Mobile: card list */}
      <div className="md:hidden space-y-2">
        {transactions.map((tx) => (
          <div
            key={tx.id}
            className="bg-zinc-800 rounded-lg p-4 border border-zinc-700 hover:border-zinc-600 transition-colors"
          >
            {/* Header: Date and Amount */}
            <div className="flex justify-between items-start mb-2">
              <span className="text-xs text-zinc-400 font-medium">
                📅 {formatDate(tx.transaction_date)}
              </span>
              <span
                className={`text-sm font-semibold whitespace-nowrap ml-2 ${
                  tx.transaction_type === 'credit'
                    ? 'text-green-400'
                    : 'text-red-400'
                }`}
              >
                {tx.transaction_type === 'credit' ? '+' : '-'}
                {formatCurrency(tx.amount, tx.currency)}
              </span>
            </div>

            {/* Description */}
            <p className="text-sm text-white mb-3 line-clamp-2 break-words">
              {tx.merchant_name || tx.description}
            </p>

            {/* Footer: Category badge and confidence/source indicators */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <CategoryBadge category={tx.category} />
                {tx.confidence_score < 0.7 && (
                  <span
                    title={`Confidence: ${(tx.confidence_score * 100).toFixed(0)}%`}
                    className="text-base"
                  >
                    ⚠️
                  </span>
                )}
                {tx.source === 'manual' && (
                  <span title="Manually added" className="text-base">
                    💵
                  </span>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Desktop: table layout */}
      <div className="hidden md:block overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-zinc-700">
              <th className="text-left text-xs font-medium text-zinc-400 uppercase tracking-wider py-3 px-4">
                Date
              </th>
              <th className="text-left text-xs font-medium text-zinc-400 uppercase tracking-wider py-3 px-4 min-w-[300px]">
                Description
              </th>
              {!compact && (
                <th className="text-left text-xs font-medium text-zinc-400 uppercase tracking-wider py-3 px-4">
                  Category
                </th>
              )}
              <th className="text-right text-xs font-medium text-zinc-400 uppercase tracking-wider py-3 px-4">
                Amount
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-zinc-800">
            {transactions.map((tx) => (
              <tr
                key={tx.id}
                className="hover:bg-zinc-800/50 transition-colors"
              >
                <td className="py-3 px-4 text-sm text-zinc-300 whitespace-nowrap">
                  {formatDate(tx.transaction_date)}
                </td>
                <td className="py-3 px-4 min-w-[300px]">
                  <div className="flex flex-col">
                    <span className="text-sm font-medium text-white whitespace-normal break-words">
                      {tx.merchant_name || tx.description.slice(0, 60)}
                    </span>
                    {!compact && (
                      <span className="text-xs text-zinc-500 whitespace-normal break-words mt-0.5">
                        {tx.description}
                      </span>
                    )}
                  </div>
                </td>
                {!compact && (
                  <td className="py-3 px-4">
                    <CategoryBadge category={tx.category} />
                  </td>
                )}
                <td className="py-3 px-4 text-right whitespace-nowrap">
                  <span
                    className={`text-sm font-medium ${
                      tx.transaction_type === 'credit'
                        ? 'text-green-400'
                        : 'text-red-400'
                    }`}
                  >
                    {tx.transaction_type === 'credit' ? '+' : '-'}
                    {formatCurrency(tx.amount, tx.currency)}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
