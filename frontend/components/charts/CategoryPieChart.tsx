'use client';

import { useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { CategoryBreakdown } from '@/types';
import { CHART_COLORS } from '@/lib/utils';
import { InteractivePieChart, PieChartEntry } from './InteractivePieChart';

interface CategoryPieChartProps {
  data: CategoryBreakdown[];
}

export function CategoryPieChart({ data }: CategoryPieChartProps) {
  const router = useRouter();

  const chartData: PieChartEntry[] = data.slice(0, 10).map((item, index) => ({
    name: item.category,
    value: item.total_amount,
    percentage: item.percentage,
    fill: item.color || CHART_COLORS[index % CHART_COLORS.length],
    tooltipExtras: [
      { label: 'Transactions', value: String(item.transaction_count) },
    ],
  }));

  const handleSliceClick = useCallback(
    (entry: PieChartEntry) => {
      router.push(`/analytics?category=${encodeURIComponent(entry.name)}`);
    },
    [router]
  );

  return <InteractivePieChart data={chartData} onSliceClick={handleSliceClick} />;
}
