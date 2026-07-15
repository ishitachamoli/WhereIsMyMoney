'use client';

import { Suspense, useEffect, useState, useCallback, useRef } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { api } from '@/lib/api';
import { Transaction, TransactionFilters, PaginatedResponse, Category } from '@/types';
import { CategoryBadge } from '@/components/CategoryBadge';
import { formatCurrency, formatDate } from '@/lib/utils';
import { ErrorBoundary } from '@/components/ErrorBoundary';
import { TableSkeleton } from '@/components/LoadingSkeletons';
import { ExplainSingleModal, ExplainBatchModal } from '@/components/TransactionExplainModal';
import { TransactionTotalsBar } from '@/components/TransactionTotalsBar';

function TransactionsContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const initialNeedsReview = searchParams.get('needs_review') === 'true';
  const initialCategory = searchParams.get('category') || undefined;
  const initialPaymentMethod = searchParams.get('payment_method') || undefined;
  const initialTransactionType = (searchParams.get('transaction_type') as 'debit' | 'credit' | null) || undefined;
  const initialSearch = searchParams.get('search') || undefined;

  const [data, setData] = useState<PaginatedResponse<Transaction> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState<TransactionFilters>({
    page: 1,
    page_size: 20,
    sort_by: 'transaction_date',
    sort_order: 'desc',
    needs_review: initialNeedsReview || undefined,
    category: initialCategory,
    payment_method: initialPaymentMethod,
    transaction_type: initialTransactionType,
    search: initialSearch,
  });
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [selectAllAcrossPages, setSelectAllAcrossPages] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editCategoryId, setEditCategoryId] = useState<number | null>(null);
  const [searchInput, setSearchInput] = useState(initialSearch || '');
  const [reclassifying, setReclassifying] = useState(false);
  const [categories, setCategories] = useState<Category[]>([]);
  const [isCreatingCategory, setIsCreatingCategory] = useState(false);
  const [newCategoryName, setNewCategoryName] = useState('');
  const [savingCategory, setSavingCategory] = useState(false);
  const [bulkCategoryMode, setBulkCategoryMode] = useState(false);
  const [bulkCategoryId, setBulkCategoryId] = useState<number | null>(null);
  const [bulkUpdating, setBulkUpdating] = useState(false);
  const newCategoryInputRef = useRef<HTMLInputElement>(null);
  const [explainTransaction, setExplainTransaction] = useState<Transaction | null>(null);
  const [showBatchExplain, setShowBatchExplain] = useState(false);
  const [explainCache, setExplainCache] = useState<Record<number, true>>({});

  const fetchTransactions = useCallback(async () => {
    try {
      setLoading(true);
      const result = await api.getTransactions(filters);
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load transactions');
    } finally {
      setLoading(false);
    }
  }, [filters]);

  const fetchCategories = useCallback(async () => {
    try {
      const cats = await api.getCategories();
      setCategories(cats);
    } catch {
      // Non-critical — categories dropdown will just be empty
    }
  }, []);

  useEffect(() => {
    fetchTransactions();
  }, [fetchTransactions]);

  useEffect(() => {
    fetchCategories();
  }, [fetchCategories]);

  const clearFilter = (filterKey: keyof TransactionFilters) => {
    setFilters((prev) => {
      const next = { ...prev, [filterKey]: undefined, page: 1 };
      return next;
    });
    if (filterKey === 'search') {
      setSearchInput('');
    }
    const params = new URLSearchParams(window.location.search);
    params.delete(filterKey);
    router.replace(`/transactions${params.toString() ? '?' + params.toString() : ''}`);
  };

  const handleSearch = () => {
    setFilters((prev) => ({ ...prev, search: searchInput || undefined, page: 1 }));
  };

  const handleSort = (field: string) => {
    setFilters((prev) => ({
      ...prev,
      sort_by: field,
      sort_order: prev.sort_by === field && prev.sort_order === 'asc' ? 'desc' : 'asc',
    }));
  };

  const handleCategorySelect = async (tx: Transaction, categoryId: number) => {
    const category = categories.find((c) => c.id === categoryId);
    if (!category) return;
    try {
      setSavingCategory(true);
      await api.updateTransaction(tx.id, { category_id: categoryId });
      setEditingId(null);
      setEditCategoryId(null);
      setIsCreatingCategory(false);
      fetchTransactions();
      api.submitFeedback(tx, category.name).catch(() => {});
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update');
    } finally {
      setSavingCategory(false);
    }
  };

  const handleCreateAndAssignCategory = async (tx: Transaction) => {
    const name = newCategoryName.trim();
    if (!name) return;
    try {
      setSavingCategory(true);
      const newCat = await api.createCategory({ name });
      setCategories((prev) => [...prev, newCat]);
      await api.updateTransaction(tx.id, { category_id: newCat.id });
      setEditingId(null);
      setEditCategoryId(null);
      setIsCreatingCategory(false);
      setNewCategoryName('');
      fetchTransactions();
      api.submitFeedback(tx, newCat.name).catch(() => {});
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create category');
    } finally {
      setSavingCategory(false);
    }
  };

  const startEditing = (tx: Transaction) => {
    setEditingId(tx.id);
    const matchingCat = categories.find((c) => c.name === tx.category);
    setEditCategoryId(matchingCat?.id ?? null);
    setIsCreatingCategory(false);
    setNewCategoryName('');
  };

  const cancelEditing = () => {
    setEditingId(null);
    setEditCategoryId(null);
    setIsCreatingCategory(false);
    setNewCategoryName('');
  };

  const handleBulkReclassify = async () => {
    if (selectedIds.size === 0 || !data) return;
    try {
      setReclassifying(true);
      const selectedTransactions = data.items.filter((t) => selectedIds.has(t.id));
      const transactions = selectedTransactions.map((t) => ({
        description: t.description,
        amount: t.amount,
        transaction_type: t.transaction_type,
      }));
      await api.classifyBatchWithDescriptions(transactions);
      setSelectedIds(new Set());
      fetchTransactions();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Reclassification failed');
    } finally {
      setReclassifying(false);
    }
  };

  const handleBulkSetCategory = async () => {
    if (selectedIds.size === 0 || !bulkCategoryId) return;
    const category = categories.find((c) => c.id === bulkCategoryId);
    if (!category) return;
    try {
      setBulkUpdating(true);
      
      if (selectAllAcrossPages) {
        // Bulk update using filter criteria
        const filterCriteria = {
          category: filters.category,
          transaction_type: filters.transaction_type,
          payment_method: filters.payment_method,
          search: filters.search,
          needs_review: filters.needs_review,
        };
        await api.bulkUpdateTransactions(null, category.name, filterCriteria);
      } else {
        // Bulk update using transaction IDs (current page only)
        await api.bulkUpdateTransactions(Array.from(selectedIds), category.name);
      }
      
      setSelectedIds(new Set());
      setSelectAllAcrossPages(false);
      setBulkCategoryMode(false);
      setBulkCategoryId(null);
      fetchTransactions();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Bulk update failed');
    } finally {
      setBulkUpdating(false);
    }
  };

  const handleApplyCategoryFromExplain = async (transactionId: number, categoryName: string) => {
    try {
      await api.updateTransaction(transactionId, { category_name: categoryName });
      fetchTransactions();
    } catch {
      // Non-critical, silently fail
    }
  };

  const toggleSelect = (id: number) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const toggleSelectAll = () => {
    if (!data) return;
    if (selectedIds.size === data.items.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(data.items.map((t) => t.id)));
    }
  };

  const SortIcon = ({ field }: { field: string }) => {
    if (filters.sort_by !== field) return <span className="text-zinc-600 ml-1">↕</span>;
    return (
      <span className="text-blue-400 ml-1">
        {filters.sort_order === 'asc' ? '↑' : '↓'}
      </span>
    );
  };

  const getSortLabel = () => {
    if (filters.sort_by === 'transaction_date') {
      return filters.sort_order === 'desc' ? '↓ Newest' : '↑ Oldest';
    } else if (filters.sort_by === 'amount') {
      return filters.sort_order === 'desc' ? '↓ Highest' : '↑ Lowest';
    } else {
      return filters.sort_order === 'desc' ? '↓ Z-A' : '↑ A-Z';
    }
  };

  const activeFilterBadges = [];
  if (filters.category) {
    activeFilterBadges.push({ key: 'category' as const, label: `Category: ${filters.category}` });
  }
  if (filters.payment_method) {
    activeFilterBadges.push({ key: 'payment_method' as const, label: `Payment: ${filters.payment_method}` });
  }
  if (filters.transaction_type) {
    const typeLabel = filters.transaction_type === 'credit' ? 'Income' : 'Expenses';
    activeFilterBadges.push({ key: 'transaction_type' as const, label: `Type: ${typeLabel}` });
  }
  if (filters.search) {
    activeFilterBadges.push({ key: 'search' as const, label: `Search: ${filters.search}` });
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white">Transactions</h1>
          <p className="text-sm text-zinc-400 mt-1">
            {data ? `${data.total} total transactions` : 'Loading...'}
          </p>
        </div>
        <div className="flex items-center gap-3">
          {selectedIds.size > 0 && (
            <>
              <span className="text-sm text-zinc-400">{selectedIds.size} selected</span>
              <button
                onClick={handleBulkReclassify}
                disabled={reclassifying}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-zinc-700 text-white rounded-lg text-sm font-medium transition-colors"
              >
                {reclassifying ? 'Classifying...' : '🤖 AI Reclassify'}
              </button>
              <button
                onClick={() => setBulkCategoryMode(true)}
                className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg text-sm font-medium transition-colors"
              >
                📝 Set Category
              </button>
              <button
                onClick={() => setShowBatchExplain(true)}
                className="px-4 py-2 bg-amber-600 hover:bg-amber-700 text-white rounded-lg text-sm font-medium transition-colors"
              >
                💡 Explain Selected
              </button>
              <button
                onClick={() => { setSelectedIds(new Set()); setBulkCategoryMode(false); setSelectAllAcrossPages(false); }}
                className="px-3 py-2 text-zinc-400 hover:text-white text-sm transition-colors"
              >
                ✕ Clear
              </button>
            </>
          )}
          <button
            onClick={() =>
              setFilters((prev) => ({
                ...prev,
                needs_review: prev.needs_review ? undefined : true,
                page: 1,
              }))
            }
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              filters.needs_review
                ? 'bg-yellow-600 hover:bg-yellow-700 text-white'
                : 'bg-zinc-700 hover:bg-zinc-600 text-zinc-300'
            }`}
          >
            ⚠️ Needs Review
          </button>
        </div>
      </div>

      {/* Active Filter Badges */}
      {activeFilterBadges.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {activeFilterBadges.map((badge) => (
            <span
              key={badge.key}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-blue-900/30 border border-blue-700/50 rounded-lg text-sm text-blue-200"
            >
              {badge.label}
              <button
                onClick={() => clearFilter(badge.key)}
                className="ml-1 text-blue-400 hover:text-white transition-colors"
                title="Remove filter"
              >
                ✕
              </button>
            </span>
          ))}
        </div>
      )}

      {/* Select All Across Pages Banner */}
      {selectedIds.size > 0 && data && selectedIds.size === data.items.length && data.total > data.items.length && !selectAllAcrossPages && (
        <div className="flex items-center gap-3 p-3 bg-blue-900/20 border border-blue-700/50 rounded-lg">
          <span className="text-sm text-blue-200">
            {selectedIds.size} selected on this page of {data.total} matching transactions
          </span>
          <button
            onClick={() => setSelectAllAcrossPages(true)}
            className="text-sm font-medium text-blue-400 hover:text-blue-300 underline transition-colors"
          >
            Select all {data.total} transactions
          </button>
        </div>
      )}

      {/* Bulk Category Selector */}
      {bulkCategoryMode && selectedIds.size > 0 && (
        <div className="flex items-center gap-3 p-4 bg-purple-900/20 border border-purple-700/50 rounded-xl">
          <span className="text-sm text-purple-200">
            Set category for {selectAllAcrossPages && data ? `${data.total}` : selectedIds.size} transactions:
          </span>
          <select
            value={bulkCategoryId ?? ''}
            onChange={(e) => setBulkCategoryId(Number(e.target.value) || null)}
            className="bg-zinc-900 border border-zinc-600 rounded-lg px-3 py-1.5 text-sm text-white focus:outline-none focus:ring-2 focus:ring-purple-500"
            autoFocus
          >
            <option value="" disabled>Select category</option>
            {categories.map((cat) => (
              <option key={cat.id} value={cat.id}>
                {cat.name}
              </option>
            ))}
          </select>
          <button
            onClick={handleBulkSetCategory}
            disabled={!bulkCategoryId || bulkUpdating}
            className="px-4 py-1.5 bg-purple-600 hover:bg-purple-700 disabled:bg-zinc-700 text-white rounded-lg text-sm font-medium transition-colors"
          >
            {bulkUpdating ? 'Updating...' : 'Apply'}
          </button>
          <button
            onClick={() => { setBulkCategoryMode(false); setBulkCategoryId(null); }}
            className="px-3 py-1.5 text-zinc-400 hover:text-white text-sm transition-colors"
          >
            Cancel
          </button>
        </div>
      )}

      {/* Filters */}
      <div className="bg-zinc-800 rounded-xl p-4 border border-zinc-700/50">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-6 gap-3">
          <div className="lg:col-span-2">
            <div className="flex gap-2">
              <input
                type="text"
                placeholder="Search transactions..."
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                className="flex-1 bg-zinc-900 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-white placeholder:text-zinc-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <button
                onClick={handleSearch}
                className="px-3 py-2 bg-zinc-700 hover:bg-zinc-600 rounded-lg text-sm text-white transition-colors"
              >
                🔍
              </button>
            </div>
          </div>
          <select
            value={filters.category || ''}
            onChange={(e) =>
              setFilters((prev) => ({
                ...prev,
                category: e.target.value || undefined,
                page: 1,
              }))
            }
            className="bg-zinc-900 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">All Categories</option>
            {categories.map((cat) => (
              <option key={cat.id} value={cat.name}>{cat.name}</option>
            ))}
          </select>
          <select
            value={filters.transaction_type || ''}
            onChange={(e) =>
              setFilters((prev) => ({
                ...prev,
                transaction_type: (e.target.value as 'debit' | 'credit') || undefined,
                page: 1,
              }))
            }
            className="bg-zinc-900 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">All Types</option>
            <option value="debit">Expenses</option>
            <option value="credit">Income</option>
          </select>
          <select
            value={filters.payment_method || ''}
            onChange={(e) =>
              setFilters((prev) => ({
                ...prev,
                payment_method: e.target.value || undefined,
                page: 1,
              }))
            }
            className="bg-zinc-900 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">All Payment Methods</option>
            <option value="UPI">UPI</option>
            <option value="NEFT">NEFT</option>
            <option value="IMPS">IMPS</option>
            <option value="POS">POS</option>
            <option value="RTGS">RTGS</option>
            <option value="ATM">ATM</option>
            <option value="Auto-Debit">Auto-Debit</option>
            <option value="Cheque">Cheque</option>
            <option value="Other">Other</option>
          </select>
          <input
            type="date"
            value={filters.date_from || ''}
            onChange={(e) =>
              setFilters((prev) => ({ ...prev, date_from: e.target.value || undefined, page: 1 }))
            }
            className="bg-zinc-900 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <select
            value={filters.page_size || 20}
            onChange={(e) =>
              setFilters((prev) => ({
                ...prev,
                page_size: parseInt(e.target.value),
                page: 1,
              }))
            }
            className="bg-zinc-900 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="10">10 per page</option>
            <option value="25">25 per page</option>
            <option value="50">50 per page</option>
            <option value="100">100 per page</option>
            <option value="200">200 per page</option>
          </select>
        </div>
      </div>

      {/* Needs Review Banner */}
      {filters.needs_review && (
        <div className="flex items-center justify-between p-4 bg-yellow-900/20 border border-yellow-700/50 rounded-xl">
          <div className="flex items-center gap-3">
            <span className="text-xl">⚠️</span>
            <div>
              <p className="text-sm font-medium text-yellow-200">
                Showing transactions that need category review
              </p>
              <p className="text-xs text-yellow-400/70 mt-0.5">
                These have low classification confidence — click a category to correct it
              </p>
            </div>
          </div>
          <button
            onClick={() => setFilters((prev) => ({ ...prev, needs_review: undefined, page: 1 }))}
            className="px-3 py-1.5 bg-zinc-700 hover:bg-zinc-600 text-white rounded-lg text-xs font-medium transition-colors"
          >
            Show All
          </button>
        </div>
      )}

      {error && (
        <div className="p-4 bg-red-900/30 border border-red-800 rounded-lg">
          <p className="text-sm text-red-300">{error}</p>
        </div>
      )}

      {/* Filtered Totals Bar */}
      {!loading && data && data.totals && data.items.length > 0 && (
        <TransactionTotalsBar totals={data.totals} count={data.total} />
      )}

      {loading ? (
        <TableSkeleton rows={10} />
      ) : data && data.items.length > 0 ? (
        <div className="bg-zinc-800 rounded-xl border border-zinc-700/50 overflow-hidden">
          {/* Mobile sort controls */}
          <div className="md:hidden flex gap-2 p-3 pb-0">
            <select
              className="bg-zinc-900 text-white rounded px-3 py-2 text-sm border border-zinc-700 focus:outline-none focus:ring-1 focus:ring-blue-500"
              value={filters.sort_by || 'transaction_date'}
              onChange={(e) => setFilters((prev) => ({ ...prev, sort_by: e.target.value, page: 1 }))}
            >
              <option value="transaction_date">Sort by Date</option>
              <option value="amount">Sort by Amount</option>
              <option value="description">Sort by Name</option>
            </select>
            <button
              className="bg-zinc-900 text-white rounded px-3 py-2 text-sm border border-zinc-700 hover:bg-zinc-700 transition-colors"
              onClick={() => setFilters((prev) => ({ ...prev, sort_order: prev.sort_order === 'desc' ? 'asc' : 'desc', page: 1 }))}
            >
              {getSortLabel()}
            </button>
          </div>

          {/* Mobile: Select All on this page button */}
          <div className="md:hidden flex gap-2 p-3 border-t border-zinc-700">
            <button
              onClick={toggleSelectAll}
              className="flex-1 px-3 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg text-sm text-white font-medium transition-colors"
            >
              {selectedIds.size === data.items.length && data.items.length > 0 ? '✓ Deselect All' : '☐ Select All on this page'}
            </button>
          </div>

          {/* Mobile: Card layout */}
          <div className="md:hidden space-y-2 p-3">
            {data.items.map((tx) => (
              <div
                key={tx.id}
                className={`bg-zinc-900 rounded-lg p-4 border transition-colors ${
                  selectedIds.has(tx.id) ? 'border-blue-500 bg-blue-900/20' : 'border-zinc-700 hover:border-zinc-600'
                } ${tx.confidence_score < 0.7 ? 'border-l-2 border-l-yellow-500' : ''}`}
              >
                {/* Header: Checkbox, Date, Amount */}
                <div className="flex justify-between items-start mb-3">
                  <div className="flex items-start gap-3 flex-1">
                    <input
                      type="checkbox"
                      checked={selectedIds.has(tx.id)}
                      onChange={() => toggleSelect(tx.id)}
                      className="rounded border-zinc-600 bg-zinc-800 text-blue-500 focus:ring-blue-500 mt-1"
                    />
                    <div className="flex flex-col">
                      <span className="text-xs text-zinc-400 font-medium">
                        📅 {formatDate(tx.transaction_date)}
                      </span>
                    </div>
                  </div>
                  <span
                    className={`text-sm font-semibold whitespace-nowrap ml-2 ${
                      tx.transaction_type === 'credit'
                        ? 'text-green-400'
                        : 'text-red-400'
                    }`}
                  >
                    {tx.transaction_type === 'credit' ? '+' : '-'}
                    {formatCurrency(tx.amount, tx.currency)}
                  </span>
                </div>

                {/* Description */}
                <p className="text-sm text-white mb-2 line-clamp-2 break-words">
                  {tx.source === 'manual' && (
                    <span className="inline-flex items-center mr-1.5 px-1.5 py-0.5 bg-amber-900/40 border border-amber-700/50 rounded text-[10px] text-amber-300 font-medium" title="Cash / manual entry">
                      💵 Cash
                    </span>
                  )}
                  {tx.merchant_name || tx.description.slice(0, 60)}
                </p>

                {/* Explain button - mobile */}
                <button
                  onClick={() => setExplainTransaction(tx)}
                  className="inline-flex items-center gap-1 px-2 py-1 mb-3 bg-amber-900/30 hover:bg-amber-900/50 border border-amber-700/40 rounded-md text-xs text-amber-200 transition-colors"
                  title="Explain this transaction"
                >
                  💡 Explain
                </button>

                {/* Category and Confidence */}
                <div className="space-y-2">
                  {/* Category Edit */}
                  <div>
                    {editingId === tx.id ? (
                      <div className="flex flex-col gap-2">
                        {savingCategory ? (
                          <span className="text-xs text-zinc-400 animate-pulse">Saving...</span>
                        ) : isCreatingCategory ? (
                          <div className="flex items-center gap-1">
                            <input
                              ref={newCategoryInputRef}
                              type="text"
                              value={newCategoryName}
                              onChange={(e) => setNewCategoryName(e.target.value)}
                              placeholder="Category name"
                              className="flex-1 bg-zinc-800 border border-zinc-600 rounded px-2 py-1.5 text-xs text-white focus:outline-none focus:ring-1 focus:ring-blue-500"
                              autoFocus
                              onKeyDown={(e) => {
                                if (e.key === 'Enter') handleCreateAndAssignCategory(tx);
                                if (e.key === 'Escape') setIsCreatingCategory(false);
                              }}
                            />
                            <button
                              onClick={() => handleCreateAndAssignCategory(tx)}
                              className="text-green-400 hover:text-green-300 text-sm font-medium"
                              title="Create & assign"
                            >
                              ✓
                            </button>
                            <button
                              onClick={() => setIsCreatingCategory(false)}
                              className="text-zinc-400 hover:text-zinc-300 text-sm"
                              title="Back to list"
                            >
                              ←
                            </button>
                          </div>
                        ) : (
                          <div className="flex flex-col gap-1">
                            <select
                              value={editCategoryId ?? ''}
                              onChange={(e) => {
                                const val = e.target.value;
                                if (val === '__new__') {
                                  setIsCreatingCategory(true);
                                  setTimeout(() => newCategoryInputRef.current?.focus(), 0);
                                } else {
                                  setEditCategoryId(Number(val));
                                }
                              }}
                              className="w-full bg-zinc-800 border border-zinc-600 rounded px-2 py-1.5 text-xs text-white focus:outline-none focus:ring-1 focus:ring-blue-500"
                              autoFocus
                            >
                              <option value="" disabled>Select category</option>
                              {categories.map((cat) => (
                                <option key={cat.id} value={cat.id}>
                                  {cat.name}
                                </option>
                              ))}
                              <option value="__new__">+ Add new category</option>
                            </select>
                            <div className="flex gap-1 justify-end">
                              <button
                                onClick={() => {
                                  if (editCategoryId) handleCategorySelect(tx, editCategoryId);
                                }}
                                disabled={!editCategoryId}
                                className="text-green-400 hover:text-green-300 disabled:text-zinc-600 text-sm font-medium"
                                title="Confirm"
                              >
                                ✓ Confirm
                              </button>
                              <button
                                onClick={cancelEditing}
                                className="text-zinc-400 hover:text-zinc-300 text-sm font-medium"
                                title="Cancel"
                              >
                                ✕ Cancel
                              </button>
                            </div>
                          </div>
                        )}
                      </div>
                    ) : (
                      <button
                        onClick={() => startEditing(tx)}
                        className="hover:opacity-80 flex items-center gap-1.5 w-full p-2 rounded bg-zinc-800/50 hover:bg-zinc-800 transition-colors"
                        title="Click to edit category"
                      >
                        {tx.confidence_score < 0.7 && (
                          <span className="text-yellow-400 text-xs flex-shrink-0" title="Low confidence — needs review">⚠️</span>
                        )}
                        <CategoryBadge category={tx.category} />
                      </button>
                    )}
                  </div>

                  {/* Confidence Bar */}
                  <div className="flex items-center gap-2">
                    <div className="flex-1 h-1.5 bg-zinc-700 rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full ${
                          tx.confidence_score >= 0.8
                            ? 'bg-green-400'
                            : tx.confidence_score >= 0.5
                            ? 'bg-yellow-400'
                            : 'bg-red-400'
                        }`}
                        style={{ width: `${tx.confidence_score * 100}%` }}
                      />
                    </div>
                    <span className="text-xs text-zinc-500 whitespace-nowrap">
                      {(tx.confidence_score * 100).toFixed(0)}%
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Desktop: Table layout */}
          <div className="hidden md:block overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-zinc-700 bg-zinc-800/80">
                  <th className="py-3 px-4 w-10">
                    <input
                      type="checkbox"
                      checked={selectedIds.size === data.items.length && data.items.length > 0}
                      onChange={toggleSelectAll}
                      className="rounded border-zinc-600 bg-zinc-900 text-blue-500 focus:ring-blue-500"
                    />
                  </th>
                  <th
                    className="text-left text-xs font-medium text-zinc-400 uppercase py-3 px-4 cursor-pointer hover:text-zinc-200"
                    onClick={() => handleSort('transaction_date')}
                  >
                    Date <SortIcon field="transaction_date" />
                  </th>
                  <th className="text-left text-xs font-medium text-zinc-400 uppercase py-3 px-4 min-w-[300px]">
                    Description
                  </th>
                  <th className="text-left text-xs font-medium text-zinc-400 uppercase py-3 px-4">
                    Category
                  </th>
                  <th className="text-left text-xs font-medium text-zinc-400 uppercase py-3 px-4">
                    Confidence
                  </th>
                  <th
                    className="text-right text-xs font-medium text-zinc-400 uppercase py-3 px-4 cursor-pointer hover:text-zinc-200"
                    onClick={() => handleSort('amount')}
                  >
                    Amount <SortIcon field="amount" />
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-800">
                {data.items.map((tx) => (
                  <tr
                    key={tx.id}
                    className={`hover:bg-zinc-700/30 transition-colors ${
                      selectedIds.has(tx.id) ? 'bg-blue-900/20' : ''
                    } ${tx.confidence_score < 0.7 ? 'border-l-2 border-l-yellow-500' : ''}`}
                  >
                    <td className="py-3 px-4">
                      <input
                        type="checkbox"
                        checked={selectedIds.has(tx.id)}
                        onChange={() => toggleSelect(tx.id)}
                        className="rounded border-zinc-600 bg-zinc-900 text-blue-500 focus:ring-blue-500"
                      />
                    </td>
                    <td className="py-3 px-4 text-sm text-zinc-300 whitespace-nowrap">
                      {formatDate(tx.transaction_date)}
                    </td>
                    <td className="py-3 px-4 min-w-[300px]">
                      <div className="flex flex-col">
                        <span className="text-sm font-medium text-white whitespace-normal break-words">
                          {tx.source === 'manual' && (
                            <span className="inline-flex items-center mr-1.5 px-1.5 py-0.5 bg-amber-900/40 border border-amber-700/50 rounded text-[10px] text-amber-300 font-medium" title="Cash / manual entry">
                              💵 Cash
                            </span>
                          )}
                          {tx.merchant_name || tx.description.slice(0, 60)}
                        </span>
                        <div className="flex items-center gap-2 mt-0.5">
                          <span className="text-xs text-zinc-500 whitespace-normal break-words flex-1">
                            {tx.description}
                          </span>
                          <button
                            onClick={() => setExplainTransaction(tx)}
                            className="flex-shrink-0 opacity-50 hover:opacity-100 text-amber-400 hover:text-amber-300 transition-opacity text-xs"
                            title="Explain this transaction"
                          >
                            💡
                          </button>
                        </div>
                      </div>
                    </td>
                    <td className="py-3 px-4">
                      {editingId === tx.id ? (
                        <div className="flex items-center gap-2">
                          {savingCategory ? (
                            <span className="text-xs text-zinc-400 animate-pulse">Saving...</span>
                          ) : isCreatingCategory ? (
                            <div className="flex items-center gap-1">
                              <input
                                ref={newCategoryInputRef}
                                type="text"
                                value={newCategoryName}
                                onChange={(e) => setNewCategoryName(e.target.value)}
                                placeholder="Category name"
                                className="bg-zinc-900 border border-zinc-600 rounded px-2 py-1 text-xs text-white w-28 focus:outline-none focus:ring-1 focus:ring-blue-500"
                                autoFocus
                                onKeyDown={(e) => {
                                  if (e.key === 'Enter') handleCreateAndAssignCategory(tx);
                                  if (e.key === 'Escape') setIsCreatingCategory(false);
                                }}
                              />
                              <button
                                onClick={() => handleCreateAndAssignCategory(tx)}
                                className="text-green-400 hover:text-green-300 text-sm"
                                title="Create & assign"
                              >
                                ✓
                              </button>
                              <button
                                onClick={() => setIsCreatingCategory(false)}
                                className="text-zinc-400 hover:text-zinc-300 text-sm"
                                title="Back to list"
                              >
                                ←
                              </button>
                            </div>
                          ) : (
                            <div className="flex items-center gap-1">
                              <select
                                value={editCategoryId ?? ''}
                                onChange={(e) => {
                                  const val = e.target.value;
                                  if (val === '__new__') {
                                    setIsCreatingCategory(true);
                                    setTimeout(() => newCategoryInputRef.current?.focus(), 0);
                                  } else {
                                    setEditCategoryId(Number(val));
                                  }
                                }}
                                className="bg-zinc-900 border border-zinc-600 rounded px-2 py-1 text-xs text-white w-36 focus:outline-none focus:ring-1 focus:ring-blue-500"
                                autoFocus
                              >
                                <option value="" disabled>Select category</option>
                                {categories.map((cat) => (
                                  <option key={cat.id} value={cat.id}>
                                    {cat.name}
                                  </option>
                                ))}
                                <option value="__new__">+ Add new category</option>
                              </select>
                              <button
                                onClick={() => {
                                  if (editCategoryId) handleCategorySelect(tx, editCategoryId);
                                }}
                                disabled={!editCategoryId}
                                className="text-green-400 hover:text-green-300 disabled:text-zinc-600 text-sm"
                                title="Confirm"
                              >
                                ✓
                              </button>
                              <button
                                onClick={cancelEditing}
                                className="text-zinc-400 hover:text-zinc-300 text-sm"
                                title="Cancel"
                              >
                                ✕
                              </button>
                            </div>
                          )}
                        </div>
                      ) : (
                        <button
                          onClick={() => startEditing(tx)}
                          className="hover:opacity-80 flex items-center gap-1.5"
                          title="Click to edit category"
                        >
                          {tx.confidence_score < 0.7 && (
                            <span className="text-yellow-400 text-xs" title="Low confidence — needs review">⚠️</span>
                          )}
                          <CategoryBadge category={tx.category} />
                        </button>
                      )}
                    </td>
                    <td className="py-3 px-4">
                      <div className="flex items-center gap-2">
                        <div className="w-12 h-1.5 bg-zinc-700 rounded-full overflow-hidden">
                          <div
                            className={`h-full rounded-full ${
                              tx.confidence_score >= 0.8
                                ? 'bg-green-400'
                                : tx.confidence_score >= 0.5
                                ? 'bg-yellow-400'
                                : 'bg-red-400'
                            }`}
                            style={{ width: `${tx.confidence_score * 100}%` }}
                          />
                        </div>
                        <span className="text-xs text-zinc-500">
                          {(tx.confidence_score * 100).toFixed(0)}%
                        </span>
                      </div>
                    </td>
                    <td className="py-3 px-4 text-right whitespace-nowrap">
                      <span
                        className={`text-sm font-medium ${
                          tx.transaction_type === 'credit'
                            ? 'text-green-400'
                            : 'text-red-400'
                        }`}
                      >
                        {tx.transaction_type === 'credit' ? '+' : '-'}
                        {formatCurrency(tx.amount, tx.currency)}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {data.total_pages > 1 && (
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 px-4 py-4 border-t border-zinc-700">
              <p className="text-sm text-zinc-400 text-center sm:text-left">
                Page {data.page} of {data.total_pages}
              </p>
              <div className="flex gap-2 w-full sm:w-auto">
                <button
                  onClick={() => setFilters((prev) => ({ ...prev, page: (prev.page || 1) - 1 }))}
                  disabled={data.page <= 1}
                  className="flex-1 sm:flex-initial px-4 py-2.5 sm:px-3 sm:py-1.5 bg-zinc-700 hover:bg-zinc-600 disabled:opacity-40 disabled:hover:bg-zinc-700 rounded-lg text-sm font-medium text-white transition-colors"
                >
                  ← Prev
                </button>
                <button
                  onClick={() => setFilters((prev) => ({ ...prev, page: (prev.page || 1) + 1 }))}
                  disabled={data.page >= data.total_pages}
                  className="flex-1 sm:flex-initial px-4 py-2.5 sm:px-3 sm:py-1.5 bg-zinc-700 hover:bg-zinc-600 disabled:opacity-40 disabled:hover:bg-zinc-700 rounded-lg text-sm font-medium text-white transition-colors"
                >
                  Next →
                </button>
              </div>
            </div>
          )}
        </div>
      ) : (
        <div className="bg-zinc-800 rounded-xl p-12 border border-zinc-700/50 text-center">
          {filters.needs_review ? (
            <>
              <div className="text-5xl mb-4">🎉</div>
              <h3 className="text-lg font-semibold text-white mb-2">All caught up!</h3>
              <p className="text-sm text-zinc-400 mb-4">
                No transactions need category review right now.
              </p>
              <button
                onClick={() => setFilters((prev) => ({ ...prev, needs_review: undefined, page: 1 }))}
                className="inline-block px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium transition-colors"
              >
                View All Transactions
              </button>
            </>
          ) : (
            <>
              <div className="text-5xl mb-4">📭</div>
              <h3 className="text-lg font-semibold text-white mb-2">No transactions yet</h3>
              <p className="text-sm text-zinc-400 mb-4">
                Upload a bank statement to get started
              </p>
              <a
                href="/upload"
                className="inline-block px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium transition-colors"
              >
                Upload Statement
              </a>
            </>
          )}
        </div>
      )}

      {/* Single Transaction Explain Modal */}
      {explainTransaction && (
        <ExplainSingleModal
          transaction={explainTransaction}
          onClose={() => setExplainTransaction(null)}
          onApplyCategory={handleApplyCategoryFromExplain}
        />
      )}

      {/* Batch Transaction Explain Modal */}
      {showBatchExplain && selectedIds.size > 0 && (
        <ExplainBatchModal
          transactionIds={Array.from(selectedIds)}
          onClose={() => setShowBatchExplain(false)}
          onApplyCategory={handleApplyCategoryFromExplain}
        />
      )}
    </div>
  );
}

export default function TransactionsPage() {
  return (
    <ErrorBoundary>
      <Suspense fallback={<TableSkeleton rows={10} />}>
        <TransactionsContent />
      </Suspense>
    </ErrorBoundary>
  );
}
