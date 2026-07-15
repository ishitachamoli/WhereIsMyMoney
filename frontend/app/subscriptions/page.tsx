'use client';

import { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import { formatCurrency } from '@/lib/utils';
import { SubscriptionsResponse, Subscription } from '@/types';
import { ErrorBoundary } from '@/components/ErrorBoundary';
import { PageSkeleton } from '@/components/LoadingSkeletons';

function SubscriptionCard({ subscription }: { subscription: Subscription }) {
  const isActive = subscription.status === 'active';

  return (
    <div
      className={`bg-zinc-800 rounded-xl p-5 border transition-colors ${
        isActive ? 'border-green-500/30 hover:border-green-500/50' : 'border-orange-500/30 hover:border-orange-500/50'
      }`}
    >
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1 min-w-0">
          <h4 className="text-sm font-semibold text-white truncate">
            {subscription.merchant}
          </h4>
          <span
            className={`inline-block mt-1 px-2 py-0.5 rounded-full text-[10px] font-medium ${
              isActive
                ? 'bg-green-500/20 text-green-400'
                : 'bg-orange-500/20 text-orange-400'
            }`}
          >
            {isActive ? '● Active' : '● Possibly Cancelled'}
          </span>
        </div>
        <div className="text-right flex-shrink-0 ml-3">
          <p className="text-lg font-bold text-white">
            {formatCurrency(subscription.monthly_amount)}
          </p>
          <p className="text-[10px] text-zinc-500">/month</p>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 mt-4">
        <div>
          <p className="text-[10px] text-zinc-500 uppercase tracking-wide">Annual Cost</p>
          <p className="text-sm font-medium text-zinc-300">
            {formatCurrency(subscription.annual_cost)}
          </p>
        </div>
        <div>
          <p className="text-[10px] text-zinc-500 uppercase tracking-wide">Occurrences</p>
          <p className="text-sm font-medium text-zinc-300">
            {subscription.occurrence_count} payments
          </p>
        </div>
        <div>
          <p className="text-[10px] text-zinc-500 uppercase tracking-wide">Last Payment</p>
          <p className="text-sm font-medium text-zinc-300">{subscription.last_date}</p>
        </div>
        <div>
          <p className="text-[10px] text-zinc-500 uppercase tracking-wide">Next Expected</p>
          <p className="text-sm font-medium text-zinc-300">{subscription.next_expected_date}</p>
        </div>
      </div>
    </div>
  );
}

function SubscriptionsContent() {
  const [data, setData] = useState<SubscriptionsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchData() {
      try {
        setLoading(true);
        const result = await api.getSubscriptions();
        setData(result);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load subscriptions');
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, []);

  if (loading) return <PageSkeleton />;

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-20">
        <div className="text-5xl mb-4">🔄</div>
        <h2 className="text-xl font-semibold text-white mb-2">Cannot load subscriptions</h2>
        <p className="text-zinc-400 text-sm">{error}</p>
      </div>
    );
  }

  if (!data || data.subscriptions.length === 0) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-white">🔄 Subscriptions & Recurring</h1>
          <p className="text-sm text-zinc-400 mt-1">
            Detect and manage your recurring monthly payments
          </p>
        </div>
        <div className="bg-zinc-800 rounded-xl p-12 border border-zinc-700/50 text-center">
          <div className="text-6xl mb-4">🔍</div>
          <h2 className="text-xl font-semibold text-white mb-2">No subscriptions detected</h2>
          <p className="text-sm text-zinc-400 mb-6">
            Upload more bank statements to help us detect recurring monthly payments.
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

  const activeSubscriptions = data.subscriptions.filter((s) => s.status === 'active');
  const cancelledSubscriptions = data.subscriptions.filter((s) => s.status === 'possibly_cancelled');

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white">🔄 Subscriptions & Recurring</h1>
          <p className="text-sm text-zinc-400 mt-1">
            Monthly recurring payments detected from your transaction history
          </p>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-zinc-800 rounded-xl p-5 border border-zinc-700/50">
          <p className="text-xs text-zinc-500 uppercase tracking-wide mb-1">Monthly Spend</p>
          <p className="text-2xl font-bold text-white">{formatCurrency(data.total_monthly_cost)}</p>
          <p className="text-[10px] text-zinc-500 mt-1">recurring per month</p>
        </div>
        <div className="bg-zinc-800 rounded-xl p-5 border border-zinc-700/50">
          <p className="text-xs text-zinc-500 uppercase tracking-wide mb-1">Annual Cost</p>
          <p className="text-2xl font-bold text-red-400">{formatCurrency(data.total_annual_cost)}</p>
          <p className="text-[10px] text-zinc-500 mt-1">projected yearly</p>
        </div>
        <div className="bg-zinc-800 rounded-xl p-5 border border-zinc-700/50">
          <p className="text-xs text-zinc-500 uppercase tracking-wide mb-1">Active</p>
          <p className="text-2xl font-bold text-green-400">{data.active_count}</p>
          <p className="text-[10px] text-zinc-500 mt-1">active subscriptions</p>
        </div>
        <div className="bg-zinc-800 rounded-xl p-5 border border-zinc-700/50">
          <p className="text-xs text-zinc-500 uppercase tracking-wide mb-1">Possibly Cancelled</p>
          <p className="text-2xl font-bold text-orange-400">{data.possibly_cancelled_count}</p>
          <p className="text-[10px] text-zinc-500 mt-1">no recent payment</p>
        </div>
      </div>

      {/* Savings Opportunity */}
      {data.potential_annual_savings > 0 && (
        <div className="bg-gradient-to-r from-emerald-900/30 to-emerald-800/10 rounded-xl p-5 border border-emerald-500/30">
          <div className="flex items-center gap-3">
            <span className="text-3xl">💡</span>
            <div>
              <h3 className="text-sm font-semibold text-emerald-300">Savings Opportunity</h3>
              <p className="text-sm text-zinc-300 mt-1">
                If you cancel{' '}
                <span className="font-semibold text-orange-400">
                  {data.possibly_cancelled_count} unused subscription{data.possibly_cancelled_count !== 1 ? 's' : ''}
                </span>
                , you could save{' '}
                <span className="font-bold text-emerald-400">
                  {formatCurrency(data.potential_annual_savings)}/year
                </span>
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Active Subscriptions */}
      {activeSubscriptions.length > 0 && (
        <div>
          <h2 className="text-lg font-semibold text-white mb-4">
            Active Subscriptions ({activeSubscriptions.length})
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {activeSubscriptions.map((sub) => (
              <SubscriptionCard key={sub.merchant} subscription={sub} />
            ))}
          </div>
        </div>
      )}

      {/* Possibly Cancelled */}
      {cancelledSubscriptions.length > 0 && (
        <div>
          <h2 className="text-lg font-semibold text-white mb-4">
            Possibly Cancelled ({cancelledSubscriptions.length})
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {cancelledSubscriptions.map((sub) => (
              <SubscriptionCard key={sub.merchant} subscription={sub} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default function SubscriptionsPage() {
  return (
    <ErrorBoundary>
      <SubscriptionsContent />
    </ErrorBoundary>
  );
}
