'use client';

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine,
  Cell,
  LabelList,
} from 'recharts';
import { IncomeVsExpense } from '@/types';
import { formatCurrency, formatCurrencyAxis, formatMonth, getMonthName } from '@/lib/utils';

interface IncomeVsExpenseChartProps {
  data: IncomeVsExpense[];
}

interface EnrichedEntry extends IncomeVsExpense {
  savings: number;
  savingsRate: number;
}

function CustomTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  const income = payload.find((p: any) => p.dataKey === 'income')?.value ?? 0;
  const expenses = payload.find((p: any) => p.dataKey === 'expenses')?.value ?? 0;
  const savings = income - expenses;
  const savingsRate = income > 0 ? (savings / income) * 100 : 0;

  return (
    <div className="bg-zinc-800 border border-zinc-600 rounded-lg p-3 shadow-xl">
      <p className="text-white font-medium text-sm mb-2">{getMonthName(label)}</p>
      <div className="text-xs space-y-1">
        <div className="flex items-center gap-2">
          <div className="w-2.5 h-2.5 rounded-sm bg-emerald-500" />
          <span className="text-zinc-300">Income:</span>
          <span className="text-emerald-400 font-medium ml-auto">{formatCurrency(income)}</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-2.5 h-2.5 rounded-sm bg-red-500" />
          <span className="text-zinc-300">Expenses:</span>
          <span className="text-red-400 font-medium ml-auto">{formatCurrency(expenses)}</span>
        </div>
        <div className="border-t border-zinc-600 pt-1 mt-1">
          <div className="flex items-center gap-2">
            <div className="w-2.5 h-2.5 rounded-sm bg-blue-500" />
            <span className="text-zinc-300">Net Savings:</span>
            <span className={`font-medium ml-auto ${savings >= 0 ? 'text-blue-400' : 'text-orange-400'}`}>
              {savings >= 0 ? '+' : ''}{formatCurrency(savings)}
            </span>
          </div>
          <div className="flex items-center gap-2 mt-0.5">
            <div className="w-2.5 h-2.5" />
            <span className="text-zinc-400">Savings Rate:</span>
            <span className={`font-medium ml-auto ${savingsRate >= 20 ? 'text-green-400' : savingsRate >= 0 ? 'text-yellow-400' : 'text-red-400'}`}>
              {savingsRate.toFixed(1)}%
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}

function renderBarLabel(props: any) {
  const { x, y, width, value } = props;
  if (!value || value === 0) return null;
  return (
    <text
      x={x + width / 2}
      y={y - 8}
      textAnchor="middle"
      fill="#a1a1aa"
      fontSize={10}
      fontWeight={500}
    >
      {formatCurrencyAxis(value)}
    </text>
  );
}

export function IncomeVsExpenseChart({ data }: IncomeVsExpenseChartProps) {
  const enrichedData: EnrichedEntry[] = data.map((item) => ({
    ...item,
    savings: item.income - item.expenses,
    savingsRate: item.income > 0 ? ((item.income - item.expenses) / item.income) * 100 : 0,
  }));

  return (
    <ResponsiveContainer width="100%" height={360}>
      <BarChart data={enrichedData} margin={{ top: 25, right: 20, left: 10, bottom: 5 }} barGap={4}>
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
        <Legend
          wrapperStyle={{ paddingTop: '12px' }}
          formatter={(value: string) => (
            <span className="text-zinc-300 text-xs">
              {value === 'income' ? '💰 Income' : value === 'expenses' ? '💸 Expenses' : value}
            </span>
          )}
        />
        <ReferenceLine y={0} stroke="#3f3f46" />
        <Bar
          dataKey="income"
          fill="#10b981"
          radius={[4, 4, 0, 0]}
          animationDuration={800}
          animationEasing="ease-out"
        >
          <LabelList dataKey="income" content={renderBarLabel} />
        </Bar>
        <Bar
          dataKey="expenses"
          fill="#ef4444"
          radius={[4, 4, 0, 0]}
          animationDuration={800}
          animationEasing="ease-out"
        >
          <LabelList dataKey="expenses" content={renderBarLabel} />
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
