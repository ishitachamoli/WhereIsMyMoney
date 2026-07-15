'use client';

import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { MonthlyTrend } from '@/types';
import { formatCurrency, formatCurrencyAxis, formatMonth, formatPercentChange, getMonthName } from '@/lib/utils';

interface SpendingTimelineChartProps {
  data: MonthlyTrend[];
}

function CustomTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  const expenses = payload[0]?.value ?? 0;
  const dataIndex = payload[0]?.payload?._index;
  const prevExpenses = payload[0]?.payload?._prev;
  const changeStr = prevExpenses !== undefined ? formatPercentChange(expenses, prevExpenses) : 'N/A';

  return (
    <div className="bg-zinc-800 border border-zinc-600 rounded-lg p-3 shadow-xl">
      <p className="text-white font-medium text-sm mb-1">{getMonthName(label)}</p>
      <div className="text-zinc-300 text-xs space-y-0.5">
        <div>Expenses: <span className="text-red-400 font-medium">{formatCurrency(expenses)}</span></div>
        <div>vs Previous: <span className={`font-medium ${expenses > (prevExpenses ?? 0) ? 'text-red-400' : 'text-green-400'}`}>{changeStr}</span></div>
      </div>
    </div>
  );
}

export function SpendingTimelineChart({ data }: SpendingTimelineChartProps) {
  const enrichedData = data.map((item, index) => ({
    ...item,
    _index: index,
    _prev: index > 0 ? data[index - 1].expenses : undefined,
  }));

  return (
    <ResponsiveContainer width="100%" height={320}>
      <AreaChart data={enrichedData} margin={{ top: 10, right: 20, left: 10, bottom: 5 }}>
        <defs>
          <linearGradient id="expenseGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#ef4444" stopOpacity={0.3} />
            <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#3f3f46" vertical={false} />
        <XAxis
          dataKey="month"
          tickFormatter={formatMonth}
          stroke="#71717a"
          fontSize={12}
          tickLine={false}
          axisLine={{ stroke: '#3f3f46' }}
        />
        <YAxis
          stroke="#71717a"
          fontSize={12}
          tickFormatter={formatCurrencyAxis}
          tickLine={false}
          axisLine={false}
          width={60}
        />
        <Tooltip content={<CustomTooltip />} />
        <Area
          type="monotone"
          dataKey="expenses"
          stroke="#ef4444"
          strokeWidth={2.5}
          fill="url(#expenseGradient)"
          dot={{ fill: '#ef4444', r: 4, strokeWidth: 2, stroke: '#1c1917' }}
          activeDot={{ r: 6, fill: '#ef4444', stroke: '#fff', strokeWidth: 2 }}
          animationDuration={1000}
          animationEasing="ease-out"
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}
