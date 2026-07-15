'use client';

import { useEffect, useState, useCallback } from 'react';
import { api } from '@/lib/api';
import { formatCurrency } from '@/lib/utils';
import { Budget, BudgetSummary, BudgetSuggestion, Category } from '@/types';
import { ErrorBoundary } from '@/components/ErrorBoundary';
import { PageSkeleton } from '@/components/LoadingSkeletons';

function ProgressBar({ percentage }: { percentage: number }) {
  const clamped = Math.min(percentage, 100);
  let colorClass = 'bg-green-500';
  if (percentage >= 90) colorClass = 'bg-red-500';
  else if (percentage >= 70) colorClass = 'bg-yellow-500';

  return (
    <div className="w-full h-3 bg-zinc-700 rounded-full overflow-hidden">
      <div
        className={`h-full rounded-full transition-all duration-500 ${colorClass}`}
        style={{ width: `${clamped}%` }}
      />
    </div>
  );
}

function BudgetCard({
  budget,
  onEdit,
  onDelete,
}: {
  budget: Budget;
  onEdit: (budget: Budget) => void;
  onDelete: (id: number) => void;
}) {
  return (
    <div className="bg-zinc-800 rounded-xl p-5 border border-zinc-700/50 hover:border-zinc-600 transition-colors">
      {budget.is_over_budget && (
        <div className="mb-3 px-3 py-1.5 bg-red-900/30 border border-red-800/50 rounded-lg">
          <p className="text-xs font-medium text-red-400">
            🚨 {formatCurrency(budget.spent - budget.amount)} over budget!
          </p>
        </div>
      )}
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-white">
          {budget.category_name || '💰 Overall Budget'}
        </h3>
        <span className="text-xs text-zinc-500 capitalize">{budget.period}</span>
      </div>
      <ProgressBar percentage={budget.percentage_used} />
      <div className="flex items-center justify-between mt-2">
        <p className="text-xs text-zinc-400">
          {formatCurrency(budget.spent)} / {formatCurrency(budget.amount)}
        </p>
        <p
          className={`text-xs font-medium ${
            budget.percentage_used >= 90
              ? 'text-red-400'
              : budget.percentage_used >= 70
              ? 'text-yellow-400'
              : 'text-green-400'
          }`}
        >
          {budget.percentage_used.toFixed(0)}% used
        </p>
      </div>
      <div className="flex items-center gap-2 mt-4">
        <button
          onClick={() => onEdit(budget)}
          className="flex-1 px-3 py-1.5 text-xs bg-zinc-700 hover:bg-zinc-600 text-zinc-300 rounded-lg transition-colors"
        >
          ✏️ Edit
        </button>
        <button
          onClick={() => onDelete(budget.id)}
          className="flex-1 px-3 py-1.5 text-xs bg-red-900/20 hover:bg-red-900/40 text-red-400 rounded-lg transition-colors"
        >
          🗑️ Delete
        </button>
      </div>
    </div>
  );
}

function HealthCard({ summary }: { summary: BudgetSummary }) {
  return (
    <div className="bg-zinc-800 rounded-xl p-5 border border-zinc-700/50">
      <h3 className="text-base font-semibold text-white mb-4">📊 Budget Health</h3>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div>
          <p className="text-xs text-zinc-400">Total Budgeted</p>
          <p className="text-lg font-bold text-white">{formatCurrency(summary.total_budget)}</p>
        </div>
        <div>
          <p className="text-xs text-zinc-400">Total Spent</p>
          <p className="text-lg font-bold text-white">{formatCurrency(summary.total_spent)}</p>
        </div>
        <div>
          <p className="text-xs text-zinc-400">Days Remaining</p>
          <p className="text-lg font-bold text-white">{summary.days_remaining_in_period}</p>
        </div>
        <div>
          <p className="text-xs text-zinc-400">Projected Spend</p>
          <p
            className={`text-lg font-bold ${
              summary.projected_end_of_period_spend > summary.total_budget
                ? 'text-red-400'
                : 'text-green-400'
            }`}
          >
            {formatCurrency(summary.projected_end_of_period_spend)}
          </p>
        </div>
      </div>
      <div className="mt-4">
        <ProgressBar percentage={summary.total_percentage_used} />
        <p className="text-xs text-zinc-400 mt-1">
          Overall: {summary.total_percentage_used.toFixed(0)}% of total budget used
        </p>
      </div>
    </div>
  );
}

function CreateBudgetModal({
  categories,
  onClose,
  onCreated,
  editBudget,
}: {
  categories: Category[];
  onClose: () => void;
  onCreated: () => void;
  editBudget: Budget | null;
}) {
  const [categoryName, setCategoryName] = useState<string>(editBudget?.category_name || '');
  const [amount, setAmount] = useState<string>(editBudget?.amount?.toString() || '');
  const [period, setPeriod] = useState<string>(editBudget?.period || 'monthly');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    const parsedAmount = parseFloat(amount);
    if (!parsedAmount || parsedAmount <= 0) {
      setError('Please enter a valid amount');
      return;
    }

    setSubmitting(true);
    try {
      if (editBudget) {
        await api.updateBudget(editBudget.id, { amount: parsedAmount, period });
      } else {
        await api.createBudget({
          category_name: categoryName || null,
          amount: parsedAmount,
          period,
        });
      }
      onCreated();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save budget');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-zinc-800 rounded-xl p-6 border border-zinc-700 w-full max-w-md">
        <h2 className="text-lg font-semibold text-white mb-4">
          {editBudget ? '✏️ Edit Budget' : '➕ Create Budget'}
        </h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          {!editBudget && (
            <div>
              <label className="block text-sm text-zinc-400 mb-1">Category</label>
              <select
                value={categoryName}
                onChange={(e) => setCategoryName(e.target.value)}
                className="w-full px-3 py-2 bg-zinc-700 border border-zinc-600 rounded-lg text-white text-sm focus:outline-none focus:border-blue-500"
              >
                <option value="">Overall (Total Budget)</option>
                {categories.map((cat) => (
                  <option key={cat.id} value={cat.name}>
                    {cat.icon} {cat.name}
                  </option>
                ))}
              </select>
            </div>
          )}
          <div>
            <label className="block text-sm text-zinc-400 mb-1">Amount (₹)</label>
            <input
              type="number"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              placeholder="e.g. 5000"
              min="1"
              step="100"
              className="w-full px-3 py-2 bg-zinc-700 border border-zinc-600 rounded-lg text-white text-sm focus:outline-none focus:border-blue-500"
              required
            />
          </div>
          <div>
            <label className="block text-sm text-zinc-400 mb-1">Period</label>
            <select
              value={period}
              onChange={(e) => setPeriod(e.target.value)}
              className="w-full px-3 py-2 bg-zinc-700 border border-zinc-600 rounded-lg text-white text-sm focus:outline-none focus:border-blue-500"
            >
              <option value="monthly">Monthly</option>
              <option value="weekly">Weekly</option>
              <option value="yearly">Yearly</option>
            </select>
          </div>
          {error && <p className="text-sm text-red-400">{error}</p>}
          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              disabled={submitting}
              className="flex-1 px-4 py-2 bg-zinc-700 hover:bg-zinc-600 text-white rounded-lg transition-colors disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="flex-1 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors disabled:opacity-50"
            >
              {submitting ? 'Saving...' : editBudget ? 'Update' : 'Create'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function TrendIndicator({ trend }: { trend: string }) {
  if (trend === 'increasing') return <span className="text-red-400" title="Spending increasing">↗️</span>;
  if (trend === 'decreasing') return <span className="text-green-400" title="Spending decreasing">↘️</span>;
  return <span className="text-zinc-400" title="Spending stable">→</span>;
}

function MethodologyBadge({ methodology }: { methodology: string }) {
  const badges: Record<string, { label: string; color: string }> = {
    trend_projection: { label: 'Trend', color: 'bg-purple-900/40 text-purple-300 border-purple-700/50' },
    median_with_buffer: { label: 'Median+IQR', color: 'bg-amber-900/40 text-amber-300 border-amber-700/50' },
    fifty_thirty_twenty: { label: '50/30/20', color: 'bg-cyan-900/40 text-cyan-300 border-cyan-700/50' },
    consistency_based: { label: 'Consistent', color: 'bg-green-900/40 text-green-300 border-green-700/50' },
  };

  const badge = badges[methodology] || { label: methodology, color: 'bg-zinc-700 text-zinc-300 border-zinc-600' };

  return (
    <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium border ${badge.color}`}>
      {badge.label}
    </span>
  );
}

function ConfidenceBar({ confidence }: { confidence: number }) {
  const pct = Math.round(confidence * 100);
  let color = 'bg-green-500';
  if (confidence < 0.6) color = 'bg-red-500';
  else if (confidence < 0.8) color = 'bg-yellow-500';

  return (
    <div className="flex items-center gap-1.5" title={`${pct}% confidence`}>
      <div className="w-12 h-1.5 bg-zinc-600 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-[10px] text-zinc-500">{pct}%</span>
    </div>
  );
}

function SuggestionsPanel({
  suggestions,
  onAccept,
  onClose,
}: {
  suggestions: BudgetSuggestion[];
  onAccept: (suggestion: BudgetSuggestion) => void;
  onClose: () => void;
}) {
  if (suggestions.length === 0) {
    return (
      <div className="bg-zinc-800 rounded-xl p-5 border border-zinc-700/50">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-base font-semibold text-white">🤖 AI Suggestions</h3>
          <button onClick={onClose} className="text-xs text-zinc-400 hover:text-white">
            ✕ Close
          </button>
        </div>
        <p className="text-sm text-zinc-400">
          Not enough spending history to generate suggestions. Upload more transactions first.
        </p>
      </div>
    );
  }

  return (
    <div className="bg-zinc-800 rounded-xl p-5 border border-blue-800/30">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-base font-semibold text-white">🤖 Smart Budget Suggestions</h3>
        <button onClick={onClose} className="text-xs text-zinc-400 hover:text-white">
          ✕ Close
        </button>
      </div>
      <p className="text-xs text-zinc-400 mb-4">
        AI-driven suggestions using trend analysis, outlier detection &amp; consistency scoring
      </p>
      <div className="space-y-3">
        {suggestions.map((suggestion) => (
          <div
            key={suggestion.category_name}
            className="p-4 bg-zinc-700/50 rounded-lg border border-zinc-600/30 hover:border-zinc-500/50 transition-colors"
          >
            <div className="flex items-start justify-between gap-3">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1.5">
                  <p className="text-sm font-semibold text-white">{suggestion.category_name}</p>
                  <TrendIndicator trend={suggestion.trend} />
                  <MethodologyBadge methodology={suggestion.methodology} />
                </div>
                <p className="text-xs text-zinc-300 leading-relaxed mb-2">
                  {suggestion.rationale}
                </p>
                <div className="flex items-center gap-4 flex-wrap">
                  <p className="text-xs text-blue-400 font-medium">
                    💡 {formatCurrency(suggestion.suggested_amount)}/month
                  </p>
                  <p className="text-xs text-zinc-500">
                    Avg: {formatCurrency(suggestion.avg_monthly_spend)} · {suggestion.months_analyzed} mo analyzed
                  </p>
                  <ConfidenceBar confidence={suggestion.confidence} />
                </div>
              </div>
              <button
                onClick={() => onAccept(suggestion)}
                className="px-3 py-1.5 text-xs bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors whitespace-nowrap shrink-0"
              >
                Accept
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function BudgetsContent() {
  const [summary, setSummary] = useState<BudgetSummary | null>(null);
  const [categories, setCategories] = useState<Category[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [editBudget, setEditBudget] = useState<Budget | null>(null);
  const [suggestions, setSuggestions] = useState<BudgetSuggestion[] | null>(null);
  const [suggestLoading, setSuggestLoading] = useState(false);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      const [summaryRes, categoriesRes] = await Promise.all([
        api.getBudgetSummary(),
        api.getCategories(),
      ]);
      setSummary(summaryRes);
      setCategories(categoriesRes);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load budgets');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleDelete = async (id: number) => {
    try {
      await api.deleteBudget(id);
      fetchData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete');
    }
  };

  const handleSuggest = async () => {
    setSuggestLoading(true);
    try {
      const res = await api.suggestBudgets();
      setSuggestions(res.suggestions);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to get suggestions');
    } finally {
      setSuggestLoading(false);
    }
  };

  const handleAcceptSuggestion = async (suggestion: BudgetSuggestion) => {
    try {
      await api.createBudget({
        category_name: suggestion.category_name,
        amount: suggestion.suggested_amount,
        period: 'monthly',
      });
      setSuggestions((prev) =>
        prev ? prev.filter((s) => s.category_name !== suggestion.category_name) : null
      );
      fetchData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create budget');
    }
  };

  if (loading) return <PageSkeleton />;

  if (error && !summary) {
    return (
      <div className="flex flex-col items-center justify-center py-20">
        <div className="text-5xl mb-4">📡</div>
        <h2 className="text-xl font-semibold text-white mb-2">Cannot load budgets</h2>
        <p className="text-zinc-400 text-sm">{error}</p>
      </div>
    );
  }

  const budgets = summary?.budgets || [];

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-white">Budgets</h1>
          <p className="text-sm text-zinc-400 mt-1">Set spending limits and track them in real-time</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={handleSuggest}
            disabled={suggestLoading}
            className="px-4 py-2 text-sm bg-purple-600/20 hover:bg-purple-600/30 text-purple-300 border border-purple-700/50 rounded-lg transition-colors disabled:opacity-50"
          >
            {suggestLoading ? '🔄 Loading...' : '🤖 Suggest Budgets'}
          </button>
          <button
            onClick={() => { setEditBudget(null); setShowCreate(true); }}
            className="px-4 py-2 text-sm bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
          >
            ➕ Create Budget
          </button>
        </div>
      </div>

      {error && (
        <div className="px-4 py-2 bg-red-900/20 border border-red-800/50 rounded-lg">
          <p className="text-sm text-red-400">{error}</p>
        </div>
      )}

      {summary && budgets.length > 0 && <HealthCard summary={summary} />}

      {suggestions !== null && (
        <SuggestionsPanel
          suggestions={suggestions}
          onAccept={handleAcceptSuggestion}
          onClose={() => setSuggestions(null)}
        />
      )}

      {budgets.length === 0 ? (
        <div className="bg-zinc-800 rounded-xl p-12 border border-zinc-700/50 text-center">
          <div className="text-6xl mb-4">💰</div>
          <h2 className="text-xl font-semibold text-white mb-2">No budgets yet</h2>
          <p className="text-sm text-zinc-400 mb-6">
            Create your first budget to start tracking spending limits, or let AI suggest budgets based on your history.
          </p>
          <div className="flex justify-center gap-3">
            <button
              onClick={handleSuggest}
              disabled={suggestLoading}
              className="px-5 py-2.5 bg-purple-600/20 hover:bg-purple-600/30 text-purple-300 border border-purple-700/50 rounded-lg text-sm transition-colors disabled:opacity-50"
            >
              🤖 Suggest Budgets
            </button>
            <button
              onClick={() => { setEditBudget(null); setShowCreate(true); }}
              className="px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm transition-colors"
            >
              ➕ Create Budget
            </button>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {budgets.map((budget) => (
            <BudgetCard
              key={budget.id}
              budget={budget}
              onEdit={(b) => { setEditBudget(b); setShowCreate(true); }}
              onDelete={handleDelete}
            />
          ))}
        </div>
      )}

      {summary && summary.alerts.length > 0 && (
        <div className="bg-zinc-800 rounded-xl p-5 border border-zinc-700/50">
          <h3 className="text-base font-semibold text-white mb-3">⚠️ Alerts</h3>
          <div className="space-y-2">
            {summary.alerts.map((alert) => (
              <div
                key={alert.budget_id}
                className={`px-3 py-2 rounded-lg text-sm ${
                  alert.severity === 'over'
                    ? 'bg-red-900/20 text-red-400 border border-red-800/30'
                    : alert.severity === 'danger'
                    ? 'bg-orange-900/20 text-orange-400 border border-orange-800/30'
                    : 'bg-yellow-900/20 text-yellow-400 border border-yellow-800/30'
                }`}
              >
                <span className="font-medium">{alert.category_name || 'Overall'}</span>: {alert.message}
              </div>
            ))}
          </div>
        </div>
      )}

      {(showCreate || editBudget) && (
        <CreateBudgetModal
          categories={categories}
          editBudget={editBudget}
          onClose={() => { setShowCreate(false); setEditBudget(null); }}
          onCreated={fetchData}
        />
      )}
    </div>
  );
}

export default function BudgetsPage() {
  return (
    <ErrorBoundary>
      <BudgetsContent />
    </ErrorBoundary>
  );
}
