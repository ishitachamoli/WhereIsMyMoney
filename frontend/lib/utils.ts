import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

const CURRENCY_SYMBOLS: Record<string, string> = {
  INR: '₹',
  EUR: '€',
  USD: '$',
  GBP: '£',
  JPY: '¥',
  CHF: 'CHF ',
  SEK: 'kr',
  NOK: 'kr',
  DKK: 'kr',
  PLN: 'zł',
  CZK: 'Kč',
  CAD: 'C$',
  AUD: 'A$',
  NZD: 'NZ$',
};

function getPreferredCurrency(): string {
  if (typeof window === 'undefined') return 'INR';
  return localStorage.getItem('wimm_currency') || 'INR';
}

function getCurrencySymbol(currency?: string): string {
  const resolved = currency || getPreferredCurrency();
  return CURRENCY_SYMBOLS[resolved.toUpperCase()] ?? `${resolved} `;
}

function getLocaleForCurrency(currency?: string): string {
  const resolved = currency || getPreferredCurrency();
  if (resolved === 'INR') return 'en-IN';
  return 'en-US';
}

export function formatCurrency(amount: number, currency?: string): string {
  const resolved = currency || getPreferredCurrency();
  const absAmount = Math.abs(amount);
  const symbol = getCurrencySymbol(resolved);
  const locale = getLocaleForCurrency(resolved);
  return `${symbol}${absAmount.toLocaleString(locale, {
    minimumFractionDigits: 0,
    maximumFractionDigits: resolved !== 'INR' ? 2 : 0,
  })}`;
}

export function formatCurrencyShort(amount: number, currency?: string): string {
  const resolved = currency || getPreferredCurrency();
  const absAmount = Math.abs(amount);
  const symbol = getCurrencySymbol(resolved);
  if (resolved !== 'INR') {
    if (absAmount >= 1000000) {
      return `${symbol}${(absAmount / 1000000).toFixed(1)}M`;
    }
    if (absAmount >= 1000) {
      return `${symbol}${(absAmount / 1000).toFixed(1)}K`;
    }
    return `${symbol}${absAmount.toFixed(0)}`;
  }
  if (absAmount >= 10000000) {
    return `${symbol}${(absAmount / 10000000).toFixed(1)}Cr`;
  }
  if (absAmount >= 100000) {
    return `${symbol}${(absAmount / 100000).toFixed(1)}L`;
  }
  if (absAmount >= 1000) {
    return `${symbol}${(absAmount / 1000).toFixed(1)}K`;
  }
  return `${symbol}${absAmount.toFixed(0)}`;
}

export function formatDate(dateStr: string): string {
  const date = new Date(dateStr);
  return date.toLocaleDateString('en-IN', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  });
}

export function formatMonth(dateStr: string): string {
  const date = new Date(dateStr);
  return date.toLocaleDateString('en-US', { month: 'short', year: '2-digit' });
}

export function getMonthName(dateStr: string): string {
  const date = new Date(dateStr);
  return date.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
}

export function formatCurrencyAxis(value: number): string {
  return formatCurrencyShort(value);
}

export function formatPercentChange(current: number, previous: number): string {
  if (previous === 0) return current > 0 ? '+∞%' : '0%';
  const pct = ((current - previous) / previous) * 100;
  const sign = pct >= 0 ? '+' : '';
  return `${sign}${pct.toFixed(1)}%`;
}

export function getPercentageColor(percentage: number): string {
  if (percentage >= 80) return 'text-green-400';
  if (percentage >= 60) return 'text-yellow-400';
  if (percentage >= 40) return 'text-orange-400';
  return 'text-red-400';
}

export const CATEGORY_CONFIG: Record<string, { emoji: string; color: string }> = {
  'Food & Dining': { emoji: '🍔', color: '#FF6384' },
  'Groceries': { emoji: '🛒', color: '#36A2EB' },
  'Transportation': { emoji: '🚗', color: '#FFCE56' },
  'Shopping': { emoji: '🛍️', color: '#4BC0C0' },
  'Entertainment': { emoji: '🎬', color: '#9966FF' },
  'Health & Fitness': { emoji: '💊', color: '#FF9F40' },
  'Bills & Utilities': { emoji: '💡', color: '#FF6384' },
  'Rent & Housing': { emoji: '🏠', color: '#C9CBCF' },
  'Education': { emoji: '📚', color: '#4BC0C0' },
  'Travel': { emoji: '✈️', color: '#36A2EB' },
  'Investments': { emoji: '📈', color: '#4ade80' },
  'Insurance': { emoji: '🛡️', color: '#a78bfa' },
  'Personal Care': { emoji: '💅', color: '#f472b6' },
  'Gifts & Donations': { emoji: '🎁', color: '#fb923c' },
  'Subscriptions': { emoji: '📱', color: '#22d3ee' },
  'ATM Withdrawal': { emoji: '🏧', color: '#94a3b8' },
  'Transfer': { emoji: '🔄', color: '#6b7280' },
  'Salary': { emoji: '💰', color: '#4ade80' },
  'Freelance': { emoji: '💼', color: '#34d399' },
  'Refund': { emoji: '↩️', color: '#60a5fa' },
  'Interest': { emoji: '🏦', color: '#a3e635' },
  'Other Income': { emoji: '💵', color: '#86efac' },
  'Other': { emoji: '📌', color: '#94a3b8' },
};

export function getCategoryConfig(category: string): { emoji: string; color: string } {
  return CATEGORY_CONFIG[category] || { emoji: '📌', color: '#94a3b8' };
}

export const CHART_COLORS = [
  '#8b5cf6', '#06b6d4', '#f59e0b', '#10b981', '#ef4444',
  '#3b82f6', '#ec4899', '#14b8a6', '#f97316', '#6366f1',
  '#84cc16', '#e879f9', '#0ea5e9', '#fbbf24', '#a855f7',
];
