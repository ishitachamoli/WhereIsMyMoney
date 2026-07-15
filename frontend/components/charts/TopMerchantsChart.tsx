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
import { InsightTopMerchant } from '@/types';
import { formatCurrency } from '@/lib/utils';

interface TopMerchantsChartProps {
  data: InsightTopMerchant[];
  mode: 'frequency' | 'spend';
}

const BAR_COLORS = [
  '#6366f1', '#8b5cf6', '#a78bfa', '#c4b5fd', '#ddd6fe',
  '#e0e7ff', '#c7d2fe', '#a5b4fc', '#818cf8', '#6366f1',
];

export function TopMerchantsChart({ data, mode }: TopMerchantsChartProps) {
  const chartData = data.slice(0, 10).map((item, idx) => ({
    name: item.merchant.length > 18 ? item.merchant.slice(0, 18) + '…' : item.merchant,
    value: mode === 'frequency' ? item.transaction_count : item.total_amount,
    fullName: item.merchant,
    count: item.transaction_count,
    amount: item.total_amount,
    color: BAR_COLORS[idx % BAR_COLORS.length],
  }));

  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={chartData} layout="vertical" margin={{ left: 10, right: 20 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#3f3f46" />
        <XAxis
          type="number"
          tick={{ fill: '#a1a1aa', fontSize: 11 }}
          tickFormatter={(v) => mode === 'spend' ? formatCurrency(v) : String(v)}
        />
        <YAxis
          type="category"
          dataKey="name"
          width={130}
          tick={{ fill: '#a1a1aa', fontSize: 11 }}
        />
        <Tooltip
          contentStyle={{
            backgroundColor: '#27272a',
            border: '1px solid #3f3f46',
            borderRadius: '8px',
            color: '#fff',
          }}
          formatter={(value: number) => [
            mode === 'spend' ? formatCurrency(value) : `${value} transactions`,
            mode === 'spend' ? 'Total Spent' : 'Frequency',
          ]}
          labelFormatter={(label) => {
            const item = chartData.find((d) => d.name === label);
            return item?.fullName || label;
          }}
        />
        <Bar dataKey="value" radius={[0, 4, 4, 0]}>
          {chartData.map((entry, index) => (
            <Cell key={`cell-${index}`} fill={entry.color} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
