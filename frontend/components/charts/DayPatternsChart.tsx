'use client';

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts';
import { DayPattern } from '@/types';
import { formatCurrency } from '@/lib/utils';

interface DayPatternsChartProps {
  data: DayPattern[];
  peakDay: number;
}

export function DayPatternsChart({ data, peakDay }: DayPatternsChartProps) {
  const maxAmount = Math.max(...data.map((d) => d.total_amount));

  const chartData = data.map((item) => ({
    day: item.day,
    amount: item.total_amount,
    count: item.transaction_count,
    isPeak: item.day === peakDay,
  }));

  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={chartData} margin={{ top: 5, right: 10, left: 10, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#3f3f46" vertical={false} />
        <XAxis
          dataKey="day"
          tick={{ fill: '#a1a1aa', fontSize: 10 }}
          interval={2}
        />
        <YAxis
          tick={{ fill: '#a1a1aa', fontSize: 10 }}
          tickFormatter={(v) => formatCurrency(v)}
          width={70}
        />
        <Tooltip
          contentStyle={{
            backgroundColor: '#27272a',
            border: '1px solid #3f3f46',
            borderRadius: '8px',
            color: '#fff',
          }}
          formatter={(value: number) => [formatCurrency(value), 'Total Spent']}
          labelFormatter={(label) => `Day ${label}`}
        />
        <Bar dataKey="amount" radius={[2, 2, 0, 0]}>
          {chartData.map((entry, index) => (
            <Cell
              key={`cell-${index}`}
              fill={
                entry.amount === 0
                  ? '#27272a'
                  : entry.isPeak
                  ? '#ef4444'
                  : `rgba(99, 102, 241, ${0.3 + (entry.amount / maxAmount) * 0.7})`
              }
            />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
