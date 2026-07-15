'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { api } from '@/lib/api';
import { Category } from '@/types';

export default function AddTransactionPage() {
  const router = useRouter();
  const amountRef = useRef<HTMLInputElement>(null);

  const [amount, setAmount] = useState('');
  const [description, setDescription] = useState('');
  const [transactionType, setTransactionType] = useState<'debit' | 'credit'>('debit');
  const [categoryName, setCategoryName] = useState('');
  const [transactionDate, setTransactionDate] = useState(
    new Date().toISOString().split('T')[0]
  );
  const [categories, setCategories] = useState<Category[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [addAnother, setAddAnother] = useState(false);

  const fetchCategories = useCallback(async () => {
    try {
      const cats = await api.getCategories();
      setCategories(cats);
    } catch {
      // Non-critical
    }
  }, []);

  useEffect(() => {
    fetchCategories();
  }, [fetchCategories]);

  useEffect(() => {
    amountRef.current?.focus();
  }, []);

  const resetForm = () => {
    setAmount('');
    setDescription('');
    setTransactionType('debit');
    setCategoryName('');
    setTransactionDate(new Date().toISOString().split('T')[0]);
    setError(null);
    setTimeout(() => amountRef.current?.focus(), 50);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);

    const numericAmount = parseFloat(amount);
    if (!amount || isNaN(numericAmount) || numericAmount <= 0) {
      setError('Please enter a valid amount greater than 0');
      return;
    }
    if (!description.trim()) {
      setError('Please enter a description');
      return;
    }

    try {
      setSubmitting(true);
      await api.createTransaction({
        description: description.trim(),
        amount: numericAmount,
        transaction_date: transactionDate,
        transaction_type: transactionType,
        category_name: categoryName || undefined,
        source: 'manual',
      });
      setSuccess('Transaction added! 🎉');

      if (addAnother) {
        resetForm();
        setSuccess('Transaction added! Ready for another.');
      } else {
        setTimeout(() => router.push('/transactions'), 1200);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to add transaction');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="max-w-lg mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">💵 Add Cash Transaction</h1>
        <p className="text-sm text-zinc-400 mt-1">
          Quickly log cash payments that don&apos;t appear in bank statements
        </p>
      </div>

      {success && (
        <div className="p-4 bg-green-900/30 border border-green-700/50 rounded-xl flex items-center gap-3">
          <span className="text-lg">✅</span>
          <p className="text-sm text-green-300">{success}</p>
        </div>
      )}

      {error && (
        <div className="p-4 bg-red-900/30 border border-red-800 rounded-xl flex items-center gap-3">
          <span className="text-lg">⚠️</span>
          <p className="text-sm text-red-300">{error}</p>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-5">
        {/* Amount */}
        <div>
          <label htmlFor="amount" className="block text-sm font-medium text-zinc-300 mb-1.5">
            Amount *
          </label>
          <div className="relative">
            <span className="absolute left-4 top-1/2 -translate-y-1/2 text-zinc-400 text-lg font-medium">
              ₹
            </span>
            <input
              ref={amountRef}
              id="amount"
              type="number"
              inputMode="decimal"
              step="0.01"
              min="0.01"
              placeholder="0"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              className="w-full pl-10 pr-4 py-4 bg-zinc-800 border border-zinc-700 rounded-xl text-2xl font-bold text-white placeholder:text-zinc-600 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
        </div>

        {/* Type Toggle */}
        <div>
          <label className="block text-sm font-medium text-zinc-300 mb-1.5">
            Type
          </label>
          <div className="grid grid-cols-2 gap-2">
            <button
              type="button"
              onClick={() => setTransactionType('debit')}
              className={`py-3 px-4 rounded-xl text-sm font-medium transition-all ${
                transactionType === 'debit'
                  ? 'bg-red-600 text-white ring-2 ring-red-400'
                  : 'bg-zinc-800 text-zinc-400 border border-zinc-700 hover:bg-zinc-700'
              }`}
            >
              💸 Expense
            </button>
            <button
              type="button"
              onClick={() => setTransactionType('credit')}
              className={`py-3 px-4 rounded-xl text-sm font-medium transition-all ${
                transactionType === 'credit'
                  ? 'bg-green-600 text-white ring-2 ring-green-400'
                  : 'bg-zinc-800 text-zinc-400 border border-zinc-700 hover:bg-zinc-700'
              }`}
            >
              💰 Income
            </button>
          </div>
        </div>

        {/* Description */}
        <div>
          <label htmlFor="description" className="block text-sm font-medium text-zinc-300 mb-1.5">
            Description *
          </label>
          <input
            id="description"
            type="text"
            placeholder="e.g., Vegetables from local market"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            className="w-full px-4 py-3 bg-zinc-800 border border-zinc-700 rounded-xl text-white placeholder:text-zinc-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>

        {/* Category Dropdown */}
        <div>
          <label htmlFor="category" className="block text-sm font-medium text-zinc-300 mb-1.5">
            Category
          </label>
          <select
            id="category"
            value={categoryName}
            onChange={(e) => setCategoryName(e.target.value)}
            className="w-full px-4 py-3 bg-zinc-800 border border-zinc-700 rounded-xl text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent appearance-none"
          >
            <option value="">Select category (optional)</option>
            {categories.map((cat) => (
              <option key={cat.id} value={cat.name}>
                {cat.name}
              </option>
            ))}
          </select>
        </div>

        {/* Date */}
        <div>
          <label htmlFor="date" className="block text-sm font-medium text-zinc-300 mb-1.5">
            Date
          </label>
          <input
            id="date"
            type="date"
            value={transactionDate}
            onChange={(e) => setTransactionDate(e.target.value)}
            className="w-full px-4 py-3 bg-zinc-800 border border-zinc-700 rounded-xl text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>

        {/* Add Another Checkbox */}
        <label className="flex items-center gap-3 cursor-pointer">
          <input
            type="checkbox"
            checked={addAnother}
            onChange={(e) => setAddAnother(e.target.checked)}
            className="w-5 h-5 rounded border-zinc-600 bg-zinc-800 text-blue-500 focus:ring-blue-500 focus:ring-offset-0"
          />
          <span className="text-sm text-zinc-300">Add another after saving</span>
        </label>

        {/* Submit Button */}
        <button
          type="submit"
          disabled={submitting}
          className="w-full py-4 bg-blue-600 hover:bg-blue-700 disabled:bg-zinc-700 disabled:text-zinc-500 text-white rounded-xl text-base font-semibold transition-colors"
        >
          {submitting ? 'Adding...' : '✓ Add Transaction'}
        </button>
      </form>
    </div>
  );
}
