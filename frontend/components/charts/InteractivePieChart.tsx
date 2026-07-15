'use client';

import { useCallback, useState } from 'react';
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Tooltip,
  Sector,
} from 'recharts';
import { formatCurrency } from '@/lib/utils';

export interface PieChartEntry {
  name: string;
  value: number;
  percentage: number;
  fill: string;
  /** Secondary display value shown in legend right column (defaults to formatCurrency(value)) */
  displayAmount?: number;
  /** Extra tooltip lines: [{label, value}] */
  tooltipExtras?: { label: string; value: string }[];
}

export interface InteractivePieChartProps {
  data: PieChartEntry[];
  onSliceClick?: (entry: PieChartEntry, index: number) => void;
}

function renderActiveShape(props: any) {
  const {
    cx, cy, innerRadius, outerRadius, startAngle, endAngle, fill, payload,
  } = props;

  return (
    <g>
      <Sector
        cx={cx}
        cy={cy}
        innerRadius={innerRadius - 2}
        outerRadius={outerRadius + 6}
        startAngle={startAngle}
        endAngle={endAngle}
        fill={fill}
        opacity={0.9}
      />
      <Sector
        cx={cx}
        cy={cy}
        innerRadius={innerRadius - 2}
        outerRadius={outerRadius + 6}
        startAngle={startAngle}
        endAngle={endAngle}
        fill={fill}
        opacity={0.3}
      />
      <text
        x={cx}
        y={cy - 10}
        textAnchor="middle"
        fill="#fff"
        fontSize={14}
        fontWeight={600}
      >
        {payload.name}
      </text>
      <text
        x={cx}
        y={cy + 12}
        textAnchor="middle"
        fill="#a1a1aa"
        fontSize={12}
      >
        {formatCurrency(payload.displayAmount ?? payload.value)} ({payload.percentage.toFixed(1)}%)
      </text>
    </g>
  );
}

function CustomTooltip({ active, payload }: any) {
  if (!active || !payload?.length) return null;
  const data = payload[0].payload as PieChartEntry;
  return (
    <div className="bg-zinc-800 border border-zinc-600 rounded-lg p-3 shadow-xl">
      <div className="flex items-center gap-2 mb-1">
        <div className="w-3 h-3 rounded-full" style={{ backgroundColor: data.fill }} />
        <span className="text-white font-medium text-sm">{data.name}</span>
      </div>
      <div className="text-zinc-300 text-xs space-y-0.5 ml-5">
        <div>Amount: <span className="text-white font-medium">{formatCurrency(data.displayAmount ?? data.value)}</span></div>
        <div>Share: <span className="text-white font-medium">{data.percentage.toFixed(1)}%</span></div>
        {data.tooltipExtras?.map((extra, i) => (
          <div key={i}>{extra.label}: <span className="text-white font-medium">{extra.value}</span></div>
        ))}
      </div>
    </div>
  );
}

export function InteractivePieChart({ data, onSliceClick }: InteractivePieChartProps) {
  const [activeIndex, setActiveIndex] = useState<number | undefined>(undefined);

  const onPieEnter = useCallback((_: any, index: number) => {
    setActiveIndex(index);
  }, []);

  const onPieLeave = useCallback(() => {
    setActiveIndex(undefined);
  }, []);

  const handleSliceClick = useCallback(
    (index: number) => {
      if (onSliceClick) {
        onSliceClick(data[index], index);
      }
    },
    [data, onSliceClick]
  );

  if (data.length === 0) {
    return (
      <div className="h-[280px] flex items-center justify-center text-zinc-500">
        No data available
      </div>
    );
  }

  return (
    <div className="flex flex-col lg:flex-row items-center gap-4">
      <div className="w-full lg:w-3/5 min-h-[280px]">
        <ResponsiveContainer width="100%" height={280}>
          <PieChart>
            <Pie
              data={data}
              cx="50%"
              cy="50%"
              innerRadius={60}
              outerRadius={100}
              paddingAngle={2}
              dataKey="value"
              activeIndex={activeIndex}
              activeShape={renderActiveShape}
              onMouseEnter={onPieEnter}
              onMouseLeave={onPieLeave}
              onClick={(_: any, index: number) => handleSliceClick(index)}
              className="cursor-pointer"
              animationDuration={800}
              animationEasing="ease-out"
            >
              {data.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.fill} stroke="transparent" />
              ))}
            </Pie>
            <Tooltip content={<CustomTooltip />} />
          </PieChart>
        </ResponsiveContainer>
      </div>
      <div className="w-full lg:w-2/5 space-y-1.5 max-h-[280px] overflow-y-auto pr-2">
        {data.map((entry, index) => (
          <button
            key={index}
            onClick={() => handleSliceClick(index)}
            onMouseEnter={() => setActiveIndex(index)}
            onMouseLeave={() => setActiveIndex(undefined)}
            className={`w-full flex items-center gap-2 px-2 py-1.5 rounded-md text-left transition-colors hover:bg-zinc-700/50 ${
              activeIndex === index ? 'bg-zinc-700/50' : ''
            }`}
          >
            <div
              className="w-3 h-3 rounded-full flex-shrink-0"
              style={{ backgroundColor: entry.fill }}
            />
            <span className="text-xs text-zinc-300 truncate flex-1">{entry.name}</span>
            <span className="text-xs text-zinc-400 font-medium whitespace-nowrap">
              {formatCurrency(entry.displayAmount ?? entry.value)}
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}
