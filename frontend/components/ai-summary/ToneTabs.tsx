'use client';

import { AITone } from '@/types';

export type TabKey = AITone | 'year';

interface TabDef {
  key: TabKey;
  emoji: string;
  label: string;
}

const TABS: TabDef[] = [
  { key: 'roast', emoji: '🔥', label: 'Roast' },
  { key: 'praise', emoji: '🌟', label: 'Praise' },
  { key: 'executive', emoji: '💼', label: 'Executive' },
  { key: 'fun', emoji: '🎉', label: 'Fun' },
  { key: 'year', emoji: '📅', label: 'Year Recap' },
];

interface ToneTabsProps {
  active: TabKey;
  onChange: (key: TabKey) => void;
}

/**
 * The 5-tab bar: Roast | Praise | Executive | Fun | Year Recap.
 *
 * Active tab is emphasized with an accent background; inactive tabs use the
 * dark zinc theme. Tabs scroll horizontally on small screens.
 */
export default function ToneTabs({ active, onChange }: ToneTabsProps) {
  return (
    <div className="flex gap-2 overflow-x-auto pb-1 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
      {TABS.map((tab) => {
        const isActive = tab.key === active;
        return (
          <button
            key={tab.key}
            type="button"
            onClick={() => onChange(tab.key)}
            className={`flex shrink-0 items-center gap-2 rounded-lg border px-4 py-2 text-sm font-medium transition-colors ${
              isActive
                ? 'border-emerald-500 bg-emerald-600 text-white shadow-lg shadow-emerald-900/30'
                : 'border-zinc-700 bg-zinc-800 text-zinc-400 hover:bg-zinc-700 hover:text-zinc-200'
            }`}
          >
            <span className="text-base">{tab.emoji}</span>
            <span>{tab.label}</span>
          </button>
        );
      })}
    </div>
  );
}
