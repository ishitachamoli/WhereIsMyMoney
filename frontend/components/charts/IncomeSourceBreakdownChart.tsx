'use client';

import { useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { IncomeTrend } from '@/types';
import { InteractivePieChart, PieChartEntry } from './InteractivePieChart';

interface IncomeSourceBreakdownChartProps {
  data: IncomeTrend[];
}

const INCOME_COLORS: Record<string, string> = {
  'Salary': '#10b981',
  'Investments': '#f59e0b',
  'Transfers & Refunds': '#8b5cf6',
  'Other Income': '#6b7280',
};

const FALLBACK_COLORS = ['#10b981', '#f59e0b', '#8b5cf6', '#6b7280', '#06b6d4', '#ec4899'];

const SOURCE_CATEGORY_FILTERS: Record<string, string | null> = {
  'Salary': 'Income',
  'Investments': 'Investments',
  'Transfers & Refunds': 'Transfers',
  'Other Income': null,
};

export function IncomeSourceBreakdownChart({ data }: IncomeSourceBreakdownChartProps) {
  const router = useRouter();

  const sourceMap: Record<string, number> = {};
  data.forEach((month) => {
    month.sources.forEach((source) => {
      if (!sourceMap[source.name]) {
        sourceMap[source.name] = 0;
      }
      sourceMap[source.name] += source.amount;
    });
  });

  const sorted = Object.entries(sourceMap)
    .map(([name, amount]) => ({ name, amount: Math.round(amount * 100) / 100 }))
    .sort((a, b) => b.amount - a.amount);

  const totalAmount = sorted.reduce((sum, s) => sum + s.amount, 0);

  const chartData: PieChartEntry[] = sorted.map((item, index) => ({
    name: item.name,
    value: item.amount,
    percentage: totalAmount > 0 ? (item.amount / totalAmount) * 100 : 0,
    fill: INCOME_COLORS[item.name] || FALLBACK_COLORS[index % FALLBACK_COLORS.length],
  }));

  const handleSliceClick = useCallback(
    (entry: PieChartEntry) => {
      const categoryFilter = SOURCE_CATEGORY_FILTERS[entry.name];
      if (categoryFilter) {
        router.push(`/transactions?transaction_type=credit&category=${encodeURIComponent(categoryFilter)}`);
      } else {
        router.push('/transactions?transaction_type=credit');
      }
    },
    [router]
  );

  return <InteractivePieChart data={chartData} onSliceClick={handleSliceClick} />;
}
