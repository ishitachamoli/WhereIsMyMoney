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
import { IncomeTrend } from '@/types';
import { formatCurrency, formatCurrencyAxis, formatMonth, formatPercentChange, getMonthName } from '@/lib/utils';

interface IncomeTimelineChartProps {
  data: IncomeTrend[];
}

function CustomTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  const income = payload[0]?.value ?? 0;
  const dataIndex = payload[0]?.payload?._index;
  const prevIncome = payload[0]?.payload?._prev;
  const changeStr = prevIncome !== undefined ? formatPercentChange(income, prevIncome) : 'N/A';
  const changePct = payload[0]?.payload?.change_pct ?? null;

  return (
    <div className="bg-zinc-800 border border-zinc-600 rounded-lg p-3 shadow-xl">
      <p className="text-white font-medium text-sm mb-1">{getMonthName(label)}</p>
      <div className="text-zinc-300 text-xs space-y-1 mb-2">
        <div>Income: <span className="text-green-400 font-medium">{formatCurrency(income)}</span></div>
        <div>vs Previous: <span className={`font-medium ${income > (prevIncome ?? 0) ? 'text-green-400' : 'text-red-400'}`}>{changeStr}</span></div>
      </div>
      {payload[0]?.payload?.sources && payload[0]?.payload?.sources.length > 0 && (
        <div className="border-t border-zinc-600 pt-2 mt-2">
          <p className="text-zinc-400 text-xs font-medium mb-1">Sources:</p>
          <div className="space-y-0.5">
            {payload[0]?.payload?.sources.map((source: any, idx: number) => (
              <div key={idx} className="text-zinc-300">
                <span className="text-zinc-400">{source.name}:</span> <span className="text-green-400">{formatCurrency(source.amount)}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export function IncomeTimelineChart({ data }: IncomeTimelineChartProps) {
  const enrichedData = data.map((item, index) => ({
    ...item,
    _index: index,
    _prev: index > 0 ? data[index - 1].amount : undefined,
  }));

  return (
    <ResponsiveContainer width="100%" height={320}>
      <AreaChart data={enrichedData} margin={{ top: 10, right: 20, left: 10, bottom: 5 }}>
        <defs>
          <linearGradient id="incomeGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
            <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
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
          dataKey="amount"
          stroke="#10b981"
          strokeWidth={2.5}
          fill="url(#incomeGradient)"
          dot={{ fill: '#10b981', r: 4, strokeWidth: 2, stroke: '#1c1917' }}
          activeDot={{ r: 6, fill: '#10b981', stroke: '#fff', strokeWidth: 2 }}
          animationDuration={1000}
          animationEasing="ease-out"
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}
