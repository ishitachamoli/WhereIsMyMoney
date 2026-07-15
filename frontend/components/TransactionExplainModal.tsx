'use client';

import { useState } from 'react';
import { api } from '@/lib/api';
import { TransactionExplanation, ExplainBatchItem, Transaction } from '@/types';
import { formatCurrency } from '@/lib/utils';

interface ExplainSingleModalProps {
  transaction: Transaction;
  onClose: () => void;
  onApplyCategory: (transactionId: number, categoryName: string) => void;
}

export function ExplainSingleModal({ transaction, onClose, onApplyCategory }: ExplainSingleModalProps) {
  const [explanation, setExplanation] = useState<TransactionExplanation | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [applied, setApplied] = useState(false);

  const fetchExplanation = async () => {
    try {
      setLoading(true);
      setError(null);
      const result = await api.explainTransaction(transaction.id);
      setExplanation(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to explain transaction');
    } finally {
      setLoading(false);
    }
  };

  // Fetch on mount
  if (!explanation && !loading && !error) {
    fetchExplanation();
  }

  const handleApplyCategory = () => {
    if (explanation?.category_suggestion) {
      onApplyCategory(transaction.id, explanation.category_suggestion);
      setApplied(true);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" />
      <div
        className="relative bg-zinc-900 border border-zinc-700 rounded-2xl shadow-2xl max-w-lg w-full max-h-[80vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="sticky top-0 bg-zinc-900 border-b border-zinc-700 px-6 py-4 flex items-center justify-between rounded-t-2xl">
          <h3 className="text-lg font-semibold text-white flex items-center gap-2">
            💡 Transaction Explanation
          </h3>
          <button
            onClick={onClose}
            className="text-zinc-400 hover:text-white transition-colors text-xl"
          >
            ✕
          </button>
        </div>

        {/* Content */}
        <div className="px-6 py-5 space-y-4">
          {/* Original description */}
          <div className="bg-zinc-800/50 rounded-lg p-3 border border-zinc-700/50">
            <p className="text-xs text-zinc-400 mb-1">Original Description</p>
            <p className="text-sm text-zinc-200 font-mono break-all">{transaction.description}</p>
            <div className="flex items-center gap-3 mt-2">
              <span className={`text-sm font-semibold ${transaction.transaction_type === 'credit' ? 'text-green-400' : 'text-red-400'}`}>
                {transaction.transaction_type === 'credit' ? '+' : '-'}{formatCurrency(transaction.amount, transaction.currency)}
              </span>
              <span className="text-xs text-zinc-500">• {transaction.category}</span>
            </div>
          </div>

          {loading && (
            <div className="flex flex-col items-center justify-center py-8 gap-3">
              <div className="animate-spin w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full" />
              <p className="text-sm text-zinc-400">Analyzing transaction...</p>
            </div>
          )}

          {error && (
            <div className="bg-red-900/20 border border-red-700/50 rounded-lg p-4 text-center">
              <p className="text-sm text-red-300">{error}</p>
              <button
                onClick={fetchExplanation}
                className="mt-2 text-xs text-red-400 hover:text-red-300 underline"
              >
                Retry
              </button>
            </div>
          )}

          {explanation && (
            <>
              {/* Plain English explanation */}
              <div className="bg-blue-900/20 border border-blue-700/40 rounded-lg p-4">
                <p className="text-sm text-blue-100 leading-relaxed">{explanation.explanation}</p>
              </div>

              {/* Extracted details */}
              <div className="grid grid-cols-2 gap-3">
                {explanation.recipient_or_sender && (
                  <DetailCard
                    label={explanation.direction === 'incoming' ? 'Sender' : 'Recipient'}
                    value={explanation.recipient_or_sender}
                    icon="👤"
                  />
                )}
                {explanation.payment_method && (
                  <DetailCard label="Payment Method" value={explanation.payment_method} icon="💳" />
                )}
                {explanation.reference && (
                  <DetailCard label="Reference" value={explanation.reference} icon="🔢" />
                )}
                {explanation.service && (
                  <DetailCard label="Service" value={explanation.service} icon="🏦" />
                )}
                {explanation.card_reference && (
                  <DetailCard label="Card" value={explanation.card_reference} icon="💳" />
                )}
                {explanation.direction && (
                  <DetailCard
                    label="Direction"
                    value={explanation.direction === 'incoming' ? '⬇️ Incoming' : '⬆️ Outgoing'}
                    icon="↔️"
                  />
                )}
              </div>

              {/* Confidence meter */}
              <div className="flex items-center gap-3">
                <span className="text-xs text-zinc-400">Confidence:</span>
                <div className="flex-1 h-2 bg-zinc-700 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full ${
                      explanation.confidence >= 0.7 ? 'bg-green-400' : explanation.confidence >= 0.4 ? 'bg-yellow-400' : 'bg-red-400'
                    }`}
                    style={{ width: `${explanation.confidence * 100}%` }}
                  />
                </div>
                <span className="text-xs text-zinc-300 font-medium">
                  {(explanation.confidence * 100).toFixed(0)}%
                </span>
              </div>

              {/* Category suggestion */}
              {explanation.category_suggestion && explanation.category_suggestion !== transaction.category && (
                <div className="bg-purple-900/20 border border-purple-700/40 rounded-lg p-3 flex items-center justify-between">
                  <div>
                    <p className="text-xs text-purple-300">Suggested Category</p>
                    <p className="text-sm text-white font-medium">{explanation.category_suggestion}</p>
                  </div>
                  <button
                    onClick={handleApplyCategory}
                    disabled={applied}
                    className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                      applied
                        ? 'bg-green-800 text-green-200 cursor-default'
                        : 'bg-purple-600 hover:bg-purple-700 text-white'
                    }`}
                  >
                    {applied ? '✓ Applied' : 'Apply'}
                  </button>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function DetailCard({ label, value, icon }: { label: string; value: string; icon: string }) {
  return (
    <div className="bg-zinc-800/50 rounded-lg p-3 border border-zinc-700/30">
      <p className="text-xs text-zinc-400 flex items-center gap-1">
        <span>{icon}</span> {label}
      </p>
      <p className="text-sm text-white font-medium mt-0.5 break-all">{value}</p>
    </div>
  );
}

// ─── Batch Explanation Modal ─────────────────────────────────────────────────

interface ExplainBatchModalProps {
  transactionIds: number[];
  onClose: () => void;
  onApplyCategory: (transactionId: number, categoryName: string) => void;
}

export function ExplainBatchModal({ transactionIds, onClose, onApplyCategory }: ExplainBatchModalProps) {
  const [items, setItems] = useState<ExplainBatchItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [appliedIds, setAppliedIds] = useState<Set<number>>(new Set());

  const fetchExplanations = async () => {
    try {
      setLoading(true);
      setError(null);
      const result = await api.explainTransactionsBatch({
        transaction_ids: transactionIds,
      });
      setItems(result.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to explain transactions');
    } finally {
      setLoading(false);
    }
  };

  // Fetch on mount
  if (items.length === 0 && !loading && !error) {
    fetchExplanations();
  }

  const handleApplyCategory = (transactionId: number, categoryName: string) => {
    onApplyCategory(transactionId, categoryName);
    setAppliedIds((prev) => new Set([...Array.from(prev), transactionId]));
  };

  const handleApplyAll = () => {
    items.forEach((item) => {
      if (
        item.explanation.category_suggestion &&
        item.explanation.category_suggestion !== item.current_category &&
        !appliedIds.has(item.transaction_id)
      ) {
        handleApplyCategory(item.transaction_id, item.explanation.category_suggestion);
      }
    });
  };

  const suggestedCount = items.filter(
    (i) => i.explanation.category_suggestion && i.explanation.category_suggestion !== i.current_category && !appliedIds.has(i.transaction_id)
  ).length;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" />
      <div
        className="relative bg-zinc-900 border border-zinc-700 rounded-2xl shadow-2xl max-w-3xl w-full max-h-[85vh] flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="sticky top-0 bg-zinc-900 border-b border-zinc-700 px-6 py-4 flex items-center justify-between rounded-t-2xl z-10">
          <div>
            <h3 className="text-lg font-semibold text-white flex items-center gap-2">
              💡 Batch Transaction Explanations
            </h3>
            <p className="text-xs text-zinc-400 mt-0.5">
              {loading ? 'Analyzing...' : `${items.length} transactions explained`}
            </p>
          </div>
          <div className="flex items-center gap-3">
            {suggestedCount > 0 && (
              <button
                onClick={handleApplyAll}
                className="px-3 py-1.5 bg-purple-600 hover:bg-purple-700 text-white rounded-lg text-xs font-medium transition-colors"
              >
                Apply All ({suggestedCount})
              </button>
            )}
            <button
              onClick={onClose}
              className="text-zinc-400 hover:text-white transition-colors text-xl"
            >
              ✕
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
          {loading && (
            <div className="flex flex-col items-center justify-center py-12 gap-3">
              <div className="animate-spin w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full" />
              <p className="text-sm text-zinc-400">Analyzing {transactionIds.length} transactions...</p>
            </div>
          )}

          {error && (
            <div className="bg-red-900/20 border border-red-700/50 rounded-lg p-4 text-center">
              <p className="text-sm text-red-300">{error}</p>
              <button
                onClick={fetchExplanations}
                className="mt-2 text-xs text-red-400 hover:text-red-300 underline"
              >
                Retry
              </button>
            </div>
          )}

          {items.map((item) => (
            <BatchExplainCard
              key={item.transaction_id}
              item={item}
              applied={appliedIds.has(item.transaction_id)}
              onApplyCategory={handleApplyCategory}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

function BatchExplainCard({
  item,
  applied,
  onApplyCategory,
}: {
  item: ExplainBatchItem;
  applied: boolean;
  onApplyCategory: (transactionId: number, categoryName: string) => void;
}) {
  const { explanation } = item;
  const hasSuggestion = explanation.category_suggestion && explanation.category_suggestion !== item.current_category;

  return (
    <div className="bg-zinc-800/50 border border-zinc-700/50 rounded-xl p-4 space-y-3">
      {/* Header: description + amount */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <p className="text-xs text-zinc-500 font-mono break-all line-clamp-1">{item.description}</p>
        </div>
        <span className={`text-sm font-semibold whitespace-nowrap ${item.transaction_type === 'credit' ? 'text-green-400' : 'text-red-400'}`}>
          {item.transaction_type === 'credit' ? '+' : '-'}₹{item.amount.toLocaleString()}
        </span>
      </div>

      {/* Explanation */}
      <p className="text-sm text-blue-100 bg-blue-900/15 border border-blue-800/30 rounded-lg px-3 py-2">
        {explanation.explanation}
      </p>

      {/* Key details row */}
      <div className="flex flex-wrap gap-2 text-xs">
        {explanation.recipient_or_sender && (
          <span className="inline-flex items-center gap-1 px-2 py-1 bg-zinc-700/50 rounded text-zinc-300">
            👤 {explanation.recipient_or_sender}
          </span>
        )}
        {explanation.payment_method && (
          <span className="inline-flex items-center gap-1 px-2 py-1 bg-zinc-700/50 rounded text-zinc-300">
            💳 {explanation.payment_method}
          </span>
        )}
        {explanation.service && (
          <span className="inline-flex items-center gap-1 px-2 py-1 bg-zinc-700/50 rounded text-zinc-300">
            🏦 {explanation.service}
          </span>
        )}
        <span className="inline-flex items-center gap-1 px-2 py-1 bg-zinc-700/50 rounded text-zinc-300">
          📁 {item.current_category}
        </span>
      </div>

      {/* Category suggestion */}
      {hasSuggestion && (
        <div className="flex items-center justify-between bg-purple-900/15 border border-purple-700/30 rounded-lg px-3 py-2">
          <span className="text-xs text-purple-200">
            Suggest: <span className="font-medium text-white">{explanation.category_suggestion}</span>
          </span>
          <button
            onClick={() => onApplyCategory(item.transaction_id, explanation.category_suggestion!)}
            disabled={applied}
            className={`px-2.5 py-1 rounded text-xs font-medium transition-colors ${
              applied
                ? 'bg-green-800 text-green-200 cursor-default'
                : 'bg-purple-600 hover:bg-purple-700 text-white'
            }`}
          >
            {applied ? '✓ Applied' : 'Apply'}
          </button>
        </div>
      )}
    </div>
  );
}
