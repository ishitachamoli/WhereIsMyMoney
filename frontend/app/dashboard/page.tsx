'use client';

import { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import { formatCurrency } from '@/lib/utils';
import { useCurrency } from '@/lib/currency';
import { FinancialSummary, CategoryBreakdown, MonthlyTrend, IncomeVsExpense, Transaction, IncomeTrend, Budget } from '@/types';
import { CategoryPieChart, SpendingTimelineChart, IncomeVsExpenseChart, IncomeTimelineChart } from '@/components/charts';
import { TransactionTable } from '@/components/TransactionTable';
import { PageSkeleton } from '@/components/LoadingSkeletons';
import { ErrorBoundary } from '@/components/ErrorBoundary';

interface DashboardData {
  summary: FinancialSummary | null;
  categories: CategoryBreakdown[];
  timeline: MonthlyTrend[];
  incomeVsExpenses: IncomeVsExpense[];
  incomeTimeline: IncomeTrend[];
  recentTransactions: Transaction[];
  budgets: Budget[];
}

function SummaryCard({
  title,
  value,
  subtitle,
  icon,
  trend,
}: {
  title: string;
  value: string;
  subtitle?: string;
  icon: string;
  trend?: 'up' | 'down' | 'neutral';
}) {
  return (
    <div className="bg-zinc-800 rounded-xl p-5 border border-zinc-700/50 hover:border-zinc-600 transition-colors">
      <div className="flex items-center justify-between mb-3">
        <span className="text-sm font-medium text-zinc-400">{title}</span>
        <span className="text-2xl">{icon}</span>
      </div>
      <p className="text-2xl font-bold text-white">{value}</p>
      {subtitle && (
        <p
          className={`text-xs mt-1 ${
            trend === 'up'
              ? 'text-green-400'
              : trend === 'down'
              ? 'text-red-400'
              : 'text-zinc-500'
          }`}
        >
          {subtitle}
        </p>
      )}
    </div>
  );
}

function DashboardContent() {
  const { currency } = useCurrency();
  const [data, setData] = useState<DashboardData>({
    summary: null,
    categories: [],
    timeline: [],
    incomeVsExpenses: [],
    incomeTimeline: [],
    recentTransactions: [],
    budgets: [],
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [clearing, setClearing] = useState(false);
  const [showClearConfirm, setShowClearConfirm] = useState(false);

  useEffect(() => {
    async function fetchData() {
      try {
        setLoading(true);
        const [summary, categories, timeline, incomeVsExpenses, incomeTimeline, transactionsRes, budgetsRes] =
          await Promise.allSettled([
            api.getSummary(),
            api.getSpendingByCategory(),
            api.getTimeline({ granularity: 'monthly' }),
            api.getIncomeVsExpenses(),
            api.getIncomeTimeline(),
            api.getTransactions({ page: 1, page_size: 10, sort_by: 'transaction_date', sort_order: 'desc' }),
            api.getBudgets(),
          ]);

        setData({
          summary: summary.status === 'fulfilled' ? summary.value : null,
          categories: categories.status === 'fulfilled' ? categories.value : [],
          timeline: timeline.status === 'fulfilled' ? timeline.value : [],
          incomeVsExpenses: incomeVsExpenses.status === 'fulfilled' ? incomeVsExpenses.value : [],
          incomeTimeline: incomeTimeline.status === 'fulfilled' ? incomeTimeline.value : [],
          recentTransactions:
            transactionsRes.status === 'fulfilled' ? transactionsRes.value.items : [],
          budgets: budgetsRes.status === 'fulfilled' ? budgetsRes.value : [],
        });
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load dashboard');
      } finally {
        setLoading(false);
      }
    }

    fetchData();
  }, []);

  const handleClearAllData = async () => {
    setClearing(true);
    try {
      await api.clearAllData();
      // Refresh the page to show empty state
      window.location.reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to clear data');
      setShowClearConfirm(false);
    } finally {
      setClearing(false);
    }
  };

  if (loading) return <PageSkeleton />;

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-20">
        <div className="text-5xl mb-4">📡</div>
        <h2 className="text-xl font-semibold text-white mb-2">Cannot connect to API</h2>
        <p className="text-zinc-400 text-sm mb-4">{error}</p>
        <p className="text-zinc-500 text-xs">Make sure the backend server is running on port 8000</p>
      </div>
    );
  }

  const { summary, categories, timeline, incomeVsExpenses, incomeTimeline, recentTransactions, budgets } = data;

  const hasData = summary && summary.transaction_count > 0;

  if (!hasData) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-white">Dashboard</h1>
            <p className="text-sm text-zinc-400 mt-1">Your financial overview at a glance</p>
          </div>
          <button
            onClick={() => setShowClearConfirm(true)}
            disabled={clearing}
            className="px-3 py-2 text-sm bg-red-900/20 text-red-400 hover:bg-red-900/30 border border-red-900/50 hover:border-red-800 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            title="Delete all transactions and bank statements"
          >
            🗑️ Clear All Data
          </button>
        </div>

        {showClearConfirm && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <div className="bg-zinc-800 rounded-lg p-6 border border-zinc-700 max-w-sm">
              <h2 className="text-lg font-semibold text-white mb-2">Clear All Data?</h2>
              <p className="text-sm text-zinc-400 mb-6">
                Are you sure? This will delete all your transactions and analytics. This cannot be undone.
              </p>
              <div className="flex gap-3">
                <button
                  onClick={() => setShowClearConfirm(false)}
                  disabled={clearing}
                  className="flex-1 px-4 py-2 bg-zinc-700 hover:bg-zinc-600 text-white rounded-lg transition-colors disabled:opacity-50"
                >
                  Cancel
                </button>
                <button
                  onClick={handleClearAllData}
                  disabled={clearing}
                  className="flex-1 px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {clearing ? 'Clearing...' : 'Delete All'}
                </button>
              </div>
            </div>
          </div>
        )}

        <div className="bg-zinc-800 rounded-xl p-12 border border-zinc-700/50 text-center">
          <div className="text-6xl mb-4">📊</div>
          <h2 className="text-xl font-semibold text-white mb-2">No data yet</h2>
          <p className="text-sm text-zinc-400 mb-6">
            Upload a bank statement to get started and see your financial overview here.
          </p>
          <a
            href="/upload"
            className="inline-block px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium transition-colors"
          >
            Upload Statement →
          </a>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Dashboard</h1>
          <p className="text-sm text-zinc-400 mt-1">Your financial overview at a glance</p>
        </div>
        <button
          onClick={() => setShowClearConfirm(true)}
          disabled={clearing}
          className="px-3 py-2 text-sm bg-red-900/20 text-red-400 hover:bg-red-900/30 border border-red-900/50 hover:border-red-800 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          title="Delete all transactions and bank statements"
        >
          🗑️ Clear All Data
        </button>
      </div>

      {showClearConfirm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-zinc-800 rounded-lg p-6 border border-zinc-700 max-w-sm">
            <h2 className="text-lg font-semibold text-white mb-2">Clear All Data?</h2>
            <p className="text-sm text-zinc-400 mb-6">
              Are you sure? This will delete all your transactions and analytics. This cannot be undone.
            </p>
            <div className="flex gap-3">
              <button
                onClick={() => setShowClearConfirm(false)}
                disabled={clearing}
                className="flex-1 px-4 py-2 bg-zinc-700 hover:bg-zinc-600 text-white rounded-lg transition-colors disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                onClick={handleClearAllData}
                disabled={clearing}
                className="flex-1 px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {clearing ? 'Clearing...' : 'Delete All'}
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <SummaryCard
          title="Total Income"
          value={formatCurrency(summary.total_income, currency)}
          icon="💰"
          subtitle={`${summary.transaction_count} transactions`}
          trend="up"
        />
        <SummaryCard
          title="Total Expenses"
          value={formatCurrency(summary.total_expenses, currency)}
          icon="💸"
          trend="down"
        />
        <SummaryCard
          title="Savings Rate"
          value={`${summary.savings_rate.toFixed(1)}%`}
          icon="🎯"
          subtitle={`Net: ${formatCurrency(summary.net_savings, currency)}`}
          trend={summary.savings_rate >= 20 ? 'up' : 'down'}
        />
        <SummaryCard
          title="Top Category"
          value={summary.top_category || 'N/A'}
          icon="🏷️"
          subtitle={
            summary.top_category_amount
              ? formatCurrency(summary.top_category_amount, currency)
              : undefined
          }
        />
      </div>

      {budgets.length > 0 && (
        <div className="bg-zinc-800 rounded-xl p-5 border border-zinc-700/50">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-base font-semibold text-white">💰 Budget Status</h3>
            <a
              href="/budgets"
              className="text-sm text-blue-400 hover:text-blue-300 transition-colors"
            >
              View All Budgets →
            </a>
          </div>
          <div className="space-y-3">
            {budgets
              .sort((a, b) => b.percentage_used - a.percentage_used)
              .slice(0, 3)
              .map((budget) => (
                <div key={budget.id} className="flex items-center gap-3">
                  <span className="text-sm text-zinc-300 w-32 truncate">
                    {budget.category_name || 'Overall'}
                  </span>
                  <div className="flex-1 h-2 bg-zinc-700 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all ${
                        budget.percentage_used >= 90
                          ? 'bg-red-500'
                          : budget.percentage_used >= 70
                          ? 'bg-yellow-500'
                          : 'bg-green-500'
                      }`}
                      style={{ width: `${Math.min(budget.percentage_used, 100)}%` }}
                    />
                  </div>
                  <span
                    className={`text-xs font-medium w-12 text-right ${
                      budget.percentage_used >= 90
                        ? 'text-red-400'
                        : budget.percentage_used >= 70
                        ? 'text-yellow-400'
                        : 'text-green-400'
                    }`}
                  >
                    {budget.percentage_used.toFixed(0)}%
                  </span>
                </div>
              ))}
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-zinc-800 rounded-xl p-5 border border-zinc-700/50">
          <h3 className="text-base font-semibold text-white mb-4">Spending by Category</h3>
          {categories.length > 0 ? (
            <CategoryPieChart data={categories} />
          ) : (
            <div className="h-64 flex items-center justify-center text-zinc-500">
              No spending data available
            </div>
          )}
        </div>

        <div className="bg-zinc-800 rounded-xl p-5 border border-zinc-700/50">
          <h3 className="text-base font-semibold text-white mb-4">Monthly Spending Trend</h3>
          {timeline.length > 0 ? (
            <SpendingTimelineChart data={timeline} />
          ) : (
            <div className="h-64 flex items-center justify-center text-zinc-500">
              No timeline data available
            </div>
          )}
        </div>
      </div>

      <div className="bg-zinc-800 rounded-xl p-5 border border-zinc-700/50">
        <h3 className="text-base font-semibold text-white mb-4">Income Trend</h3>
        {incomeTimeline.length > 0 ? (
          <IncomeTimelineChart data={incomeTimeline} />
        ) : (
          <div className="h-64 flex items-center justify-center text-zinc-500">
            No income data available
          </div>
        )}
      </div>

      <div className="bg-zinc-800 rounded-xl p-5 border border-zinc-700/50">
        <h3 className="text-base font-semibold text-white mb-4">Income vs Expenses</h3>
        {incomeVsExpenses.length > 0 ? (
          <IncomeVsExpenseChart data={incomeVsExpenses} />
        ) : (
          <div className="h-64 flex items-center justify-center text-zinc-500">
            No comparison data available
          </div>
        )}
      </div>

      <div className="bg-zinc-800 rounded-xl p-5 border border-zinc-700/50">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-base font-semibold text-white">Recent Transactions</h3>
          <a
            href="/transactions"
            className="text-sm text-blue-400 hover:text-blue-300 transition-colors"
          >
            View All →
          </a>
        </div>
        <TransactionTable transactions={recentTransactions} compact />
      </div>
    </div>
  );
}

export default function DashboardPage() {
  return (
    <ErrorBoundary>
      <DashboardContent />
    </ErrorBoundary>
  );
}
