'use client';

import { useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { PaymentMethodEntry } from '@/types';
import { InteractivePieChart, PieChartEntry } from './InteractivePieChart';

interface PaymentMethodsChartProps {
  data: PaymentMethodEntry[];
  onMethodClick?: (method: string) => void;
}

const METHOD_COLORS: Record<string, string> = {
  UPI: '#6366f1',
  NEFT: '#f59e0b',
  IMPS: '#10b981',
  POS: '#ec4899',
  RTGS: '#8b5cf6',
  ATM: '#ef4444',
  'Auto-Debit': '#06b6d4',
  Cheque: '#64748b',
  Other: '#6b7280',
};

export function PaymentMethodsChart({ data, onMethodClick }: PaymentMethodsChartProps) {
  const router = useRouter();

  const chartData: PieChartEntry[] = data.map((item) => ({
    name: item.method,
    value: item.total_amount,
    percentage: item.percentage_by_count,
    fill: METHOD_COLORS[item.method] || '#6b7280',
    tooltipExtras: [
      { label: 'Transactions', value: String(item.transaction_count) },
    ],
  }));

  const handleSliceClick = useCallback(
    (entry: PieChartEntry) => {
      if (onMethodClick) {
        onMethodClick(entry.name);
      } else {
        router.push(`/transactions?payment_method=${encodeURIComponent(entry.name)}`);
      }
    },
    [router, onMethodClick]
  );

  return <InteractivePieChart data={chartData} onSliceClick={handleSliceClick} />;
}
