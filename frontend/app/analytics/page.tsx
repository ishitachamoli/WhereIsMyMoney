'use client';

import { useEffect, useState, useCallback, useRef, Suspense } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { api } from '@/lib/api';
import {
  CategoryBreakdown,
  MonthlyTrend,
  IncomeVsExpense,
  Transaction,
  FinancialSummary,
  RecurringTransaction,
  TopMerchantsResponse,
  VelocityResponse,
  OutlierTransaction,
  DayPatternsResponse,
  PaymentMethodsResponse,
  IncomeTrend,
} from '@/types';
import {
  CategoryPieChart,
  SpendingTimelineChart,
  IncomeVsExpenseChart,
  IncomeTimelineChart,
  IncomeSourceBreakdownChart,
  TopMerchantsChart,
  DayPatternsChart,
  PaymentMethodsChart,
} from '@/components/charts';
import { CategoryDeepDive } from '@/components/charts/CategoryDeepDive';
import { CategoryBadge } from '@/components/CategoryBadge';
import { TransactionTable } from '@/components/TransactionTable';
import { PageSkeleton } from '@/components/LoadingSkeletons';
import { ErrorBoundary } from '@/components/ErrorBoundary';
import { formatCurrency, getCategoryConfig, CHART_COLORS } from '@/lib/utils';

type TimeGranularity = 'weekly' | 'monthly';

function AnalyticsContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const [summary, setSummary] = useState<FinancialSummary | null>(null);
  const [categories, setCategories] = useState<CategoryBreakdown[]>([]);
  const [timeline, setTimeline] = useState<MonthlyTrend[]>([]);
  const [incomeVsExpenses, setIncomeVsExpenses] = useState<IncomeVsExpense[]>([]);
  const [incomeTimeline, setIncomeTimeline] = useState<IncomeTrend[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [granularity, setGranularity] = useState<TimeGranularity>('monthly');
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [categoryTransactions, setCategoryTransactions] = useState<Transaction[]>([]);
  const [loadingDrilldown, setLoadingDrilldown] = useState(false);
  const [drilldownPage, setDrilldownPage] = useState(1);
  const [drilldownTotal, setDrilldownTotal] = useState(0);
  const [drilldownTotalPages, setDrilldownTotalPages] = useState(0);
  const [drilldownSearch, setDrilldownSearch] = useState('');
  const drilldownSearchTimer = useRef<NodeJS.Timeout | null>(null);
  const DRILLDOWN_PAGE_SIZE = 20;

  // Deep-dive category (from URL param or category selector)
  const [deepDiveCategory, setDeepDiveCategory] = useState<string | null>(
    searchParams.get('category')
  );

  // Sync URL param changes
  useEffect(() => {
    const cat = searchParams.get('category');
    setDeepDiveCategory(cat);
  }, [searchParams]);

  const handleDeepDiveBack = useCallback(() => {
    setDeepDiveCategory(null);
    router.push('/analytics');
  }, [router]);

  const handleDeepDiveSelect = useCallback(
    (category: string) => {
      setDeepDiveCategory(category);
      router.push(`/analytics?category=${encodeURIComponent(category)}`);
    },
    [router]
  );

  // Insights state
  const [recurring, setRecurring] = useState<RecurringTransaction[]>([]);
  const [topMerchants, setTopMerchants] = useState<TopMerchantsResponse | null>(null);
  const [velocity, setVelocity] = useState<VelocityResponse | null>(null);
  const [outliers, setOutliers] = useState<OutlierTransaction[]>([]);
  const [dayPatterns, setDayPatterns] = useState<DayPatternsResponse | null>(null);
  const [paymentMethods, setPaymentMethods] = useState<PaymentMethodsResponse | null>(null);
  const [insightsLoading, setInsightsLoading] = useState(true);

  useEffect(() => {
    async function fetchData() {
      try {
        setLoading(true);
        const [summaryRes, categoriesRes, timelineRes, incExpRes, incomeRes] = await Promise.allSettled([
          api.getSummary(),
          api.getSpendingByCategory(),
          api.getTimeline({ granularity }),
          api.getIncomeVsExpenses(),
          api.getIncomeTimeline(),
        ]);

        if (summaryRes.status === 'fulfilled') setSummary(summaryRes.value);
        if (categoriesRes.status === 'fulfilled') setCategories(categoriesRes.value);
        if (timelineRes.status === 'fulfilled') setTimeline(timelineRes.value);
        if (incExpRes.status === 'fulfilled') setIncomeVsExpenses(incExpRes.value);
        if (incomeRes.status === 'fulfilled') setIncomeTimeline(incomeRes.value);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load analytics');
      } finally {
        setLoading(false);
      }
    }

    fetchData();
  }, [granularity]);

  useEffect(() => {
    async function fetchInsights() {
      try {
        setInsightsLoading(true);
        const [recRes, merchRes, velRes, outRes, dayRes, payRes] = await Promise.allSettled([
          api.getRecurringTransactions(),
          api.getTopMerchants(),
          api.getSpendingVelocity(),
          api.getOutliers(),
          api.getDayPatterns(),
          api.getPaymentMethods(),
        ]);

        if (recRes.status === 'fulfilled') setRecurring(recRes.value);
        if (merchRes.status === 'fulfilled') setTopMerchants(merchRes.value);
        if (velRes.status === 'fulfilled') setVelocity(velRes.value);
        if (outRes.status === 'fulfilled') setOutliers(outRes.value);
        if (dayRes.status === 'fulfilled') setDayPatterns(dayRes.value);
        if (payRes.status === 'fulfilled') setPaymentMethods(payRes.value);
      } catch {
        // Insights are optional — don't block the page
      } finally {
        setInsightsLoading(false);
      }
    }

    fetchInsights();
  }, []);

  const fetchDrilldown = useCallback(async (category: string, page: number, search: string) => {
    try {
      setLoadingDrilldown(true);
      const result = await api.getTransactions({
        category,
        page,
        page_size: DRILLDOWN_PAGE_SIZE,
        sort_by: 'amount',
        sort_order: 'desc',
        search: search || undefined,
      });
      setCategoryTransactions(result.items);
      setDrilldownTotal(result.total);
      setDrilldownTotalPages(result.total_pages);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load category details');
    } finally {
      setLoadingDrilldown(false);
    }
  }, []);

  const handleCategoryDrilldown = async (category: string) => {
    if (selectedCategory === category) {
      setSelectedCategory(null);
      setCategoryTransactions([]);
      return;
    }

    setSelectedCategory(category);
    setDrilldownPage(1);
    setDrilldownSearch('');
    fetchDrilldown(category, 1, '');
  };

  const handleDrilldownPageChange = (newPage: number) => {
    if (!selectedCategory) return;
    setDrilldownPage(newPage);
    fetchDrilldown(selectedCategory, newPage, drilldownSearch);
  };

  const handleDrilldownSearch = (search: string) => {
    if (!selectedCategory) return;
    setDrilldownSearch(search);
    if (drilldownSearchTimer.current) {
      clearTimeout(drilldownSearchTimer.current);
    }
    drilldownSearchTimer.current = setTimeout(() => {
      setDrilldownPage(1);
      fetchDrilldown(selectedCategory, 1, search);
    }, 300);
  };

  if (loading) return <PageSkeleton />;

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-20">
        <div className="text-5xl mb-4">📡</div>
        <h2 className="text-xl font-semibold text-white mb-2">Cannot load analytics</h2>
        <p className="text-zinc-400 text-sm">{error}</p>
      </div>
    );
  }

  const hasData = summary && summary.transaction_count > 0;

  if (!hasData) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-white">Analytics</h1>
          <p className="text-sm text-zinc-400 mt-1">Deep dive into your spending patterns</p>
        </div>

        <div className="bg-zinc-800 rounded-xl p-12 border border-zinc-700/50 text-center">
          <div className="text-6xl mb-4">📈</div>
          <h2 className="text-xl font-semibold text-white mb-2">No data yet</h2>
          <p className="text-sm text-zinc-400 mb-6">
            Upload a bank statement to see detailed analytics and spending insights.
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

  const healthScore = calculateHealthScore(summary);

  // If a deep-dive category is selected, show the deep-dive view
  if (deepDiveCategory) {
    return (
      <div className="space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-white">Analytics</h1>
            <p className="text-sm text-zinc-400 mt-1">Category deep-dive</p>
          </div>
          {/* Category selector dropdown */}
          <select
            value={deepDiveCategory}
            onChange={(e) => handleDeepDiveSelect(e.target.value)}
            className="px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-sm text-white focus:outline-none focus:border-blue-500"
          >
            {categories.map((cat) => (
              <option key={cat.category} value={cat.category}>
                {cat.category}
              </option>
            ))}
          </select>
        </div>
        <CategoryDeepDive
          categoryName={deepDiveCategory}
          onBack={handleDeepDiveBack}
        />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white">Analytics</h1>
          <p className="text-sm text-zinc-400 mt-1">Deep dive into your spending patterns</p>
        </div>
        <div className="flex items-center gap-2 bg-zinc-800 rounded-lg p-1 border border-zinc-700">
          <button
            onClick={() => setGranularity('weekly')}
            className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
              granularity === 'weekly'
                ? 'bg-blue-600 text-white'
                : 'text-zinc-400 hover:text-white'
            }`}
          >
            Weekly
          </button>
          <button
            onClick={() => setGranularity('monthly')}
            className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
              granularity === 'monthly'
                ? 'bg-blue-600 text-white'
                : 'text-zinc-400 hover:text-white'
            }`}
          >
            Monthly
          </button>
        </div>
      </div>

      {/* Financial Health Score */}
      <div className="bg-gradient-to-r from-zinc-800 to-zinc-800/50 rounded-xl p-6 border border-zinc-700/50">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-base font-semibold text-white mb-1">Financial Health Score</h3>
            <p className="text-sm text-zinc-400">
              Based on savings rate, spending consistency, and diversification
            </p>
          </div>
          <div className="flex items-center gap-3">
            <div
              className={`text-4xl font-bold ${
                healthScore >= 80
                  ? 'text-green-400'
                  : healthScore >= 60
                  ? 'text-yellow-400'
                  : healthScore >= 40
                  ? 'text-orange-400'
                  : 'text-red-400'
              }`}
            >
              {healthScore}
            </div>
            <span className="text-sm text-zinc-500">/100</span>
          </div>
        </div>
        <div className="mt-4 h-2 bg-zinc-700 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all duration-500 ${
              healthScore >= 80
                ? 'bg-green-400'
                : healthScore >= 60
                ? 'bg-yellow-400'
                : healthScore >= 40
                ? 'bg-orange-400'
                : 'bg-red-400'
            }`}
            style={{ width: `${healthScore}%` }}
          />
        </div>
      </div>

      {/* ─── INSIGHTS SECTION ─────────────────────────────────────────────── */}
      {!insightsLoading && (
        <>
          {/* Spending Velocity */}
          {velocity && velocity.entries.length > 0 && (
            <div className="bg-zinc-800 rounded-xl p-5 border border-zinc-700/50">
              <h3 className="text-base font-semibold text-white mb-1">💸 Spending Velocity</h3>
              <p className="text-xs text-zinc-500 mb-4">
                How fast you spend after receiving income
              </p>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
                <div className="bg-zinc-900 rounded-lg p-4 text-center">
                  <p className="text-xs text-zinc-500 mb-1">Avg. spent in first 7 days</p>
                  <p className={`text-2xl font-bold ${
                    velocity.overall_risk_level === 'high' ? 'text-red-400' :
                    velocity.overall_risk_level === 'medium' ? 'text-yellow-400' :
                    'text-green-400'
                  }`}>
                    {velocity.average_velocity_7d.toFixed(0)}%
                  </p>
                </div>
                <div className="bg-zinc-900 rounded-lg p-4 text-center">
                  <p className="text-xs text-zinc-500 mb-1">Days to 50% spent</p>
                  <p className="text-2xl font-bold text-white">
                    {velocity.average_days_to_50_percent?.toFixed(0) ?? '—'}
                  </p>
                </div>
                <div className="bg-zinc-900 rounded-lg p-4 text-center">
                  <p className="text-xs text-zinc-500 mb-1">Risk Level</p>
                  <p className={`text-2xl font-bold capitalize ${
                    velocity.overall_risk_level === 'high' ? 'text-red-400' :
                    velocity.overall_risk_level === 'medium' ? 'text-yellow-400' :
                    'text-green-400'
                  }`}>
                    {velocity.overall_risk_level === 'high' ? '🔴' :
                     velocity.overall_risk_level === 'medium' ? '🟡' : '🟢'}{' '}
                    {velocity.overall_risk_level}
                  </p>
                </div>
              </div>
              {velocity.entries.length > 0 && (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="text-zinc-500 text-xs border-b border-zinc-700">
                        <th className="pb-2 text-left">Income Date</th>
                        <th className="pb-2 text-right">Amount</th>
                        <th className="pb-2 text-right">Spent in 7d</th>
                        <th className="pb-2 text-right">Velocity</th>
                        <th className="pb-2 text-right">Burn/Day</th>
                      </tr>
                    </thead>
                    <tbody>
                      {velocity.entries.slice(0, 5).map((entry, idx) => (
                        <tr key={idx} className="border-b border-zinc-800">
                          <td className="py-2 text-zinc-300">{entry.income_date}</td>
                          <td className="py-2 text-right text-green-400">
                            {formatCurrency(entry.income_amount)}
                          </td>
                          <td className="py-2 text-right text-red-400">
                            {formatCurrency(entry.spent_7_days)}
                          </td>
                          <td className={`py-2 text-right font-medium ${
                            entry.velocity_7d_percent > 50 ? 'text-red-400' :
                            entry.velocity_7d_percent > 30 ? 'text-yellow-400' :
                            'text-green-400'
                          }`}>
                            {entry.velocity_7d_percent.toFixed(0)}%
                          </td>
                          <td className="py-2 text-right text-zinc-400">
                            {formatCurrency(entry.daily_burn_rate)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}

          {/* Recurring Payments & Payment Methods */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Recurring Payments */}
            <div className="bg-zinc-800 rounded-xl p-5 border border-zinc-700/50">
              <h3 className="text-base font-semibold text-white mb-1">🔄 Recurring Payments</h3>
              <p className="text-xs text-zinc-500 mb-4">
                Detected subscriptions, EMIs &amp; regular payments
              </p>
              {recurring.length > 0 ? (
                <div className="space-y-3 max-h-[350px] overflow-y-auto">
                  {recurring.map((item, idx) => (
                    <div
                      key={idx}
                      className="flex items-center justify-between p-3 bg-zinc-900 rounded-lg"
                    >
                      <div className="min-w-0 flex-1">
                        <p className="text-sm font-medium text-white truncate">
                          {item.merchant}
                        </p>
                        <p className="text-xs text-zinc-500">
                          {item.frequency} • {item.occurrence_count} occurrences
                          {item.next_expected_date && (
                            <> • Next: {item.next_expected_date}</>
                          )}
                        </p>
                      </div>
                      <div className="text-right ml-3">
                        <p className="text-sm font-semibold text-white">
                          {formatCurrency(item.average_amount)}
                        </p>
                        <p className="text-xs text-zinc-500">
                          Total: {formatCurrency(item.total_spent)}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8 text-zinc-500 text-sm">
                  No recurring patterns detected yet
                </div>
              )}
            </div>

            {/* Payment Methods Pie */}
            <div className="bg-zinc-800 rounded-xl p-5 border border-zinc-700/50">
              <h3 className="text-base font-semibold text-white mb-1">💳 Payment Methods</h3>
              <p className="text-xs text-zinc-500 mb-3">
                UPI vs NEFT vs POS vs others
              </p>
              {paymentMethods && paymentMethods.methods.length > 0 ? (
                <>
                  <PaymentMethodsChart data={paymentMethods.methods} />
                  <div className="mt-3 flex items-center justify-between text-xs">
                    <span className="text-zinc-400">
                      Digital: <span className="text-green-400 font-medium">{paymentMethods.digital_percentage.toFixed(0)}%</span>
                    </span>
                    <span className="text-zinc-400">
                      Most used: <span className="text-indigo-400 font-medium">{paymentMethods.most_used_method}</span>
                    </span>
                  </div>
                </>
              ) : (
                <div className="text-center py-8 text-zinc-500 text-sm">
                  No payment data available
                </div>
              )}
            </div>
          </div>

          {/* Top Merchants */}
          {topMerchants && topMerchants.by_total_spend.length > 0 && (
            <div className="bg-zinc-800 rounded-xl p-5 border border-zinc-700/50">
              <h3 className="text-base font-semibold text-white mb-1">🏪 Top Merchants</h3>
              <p className="text-xs text-zinc-500 mb-4">Where your money goes the most</p>
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <div>
                  <p className="text-xs text-zinc-400 font-medium mb-2 uppercase tracking-wider">
                    By Total Spend
                  </p>
                  <TopMerchantsChart data={topMerchants.by_total_spend} mode="spend" />
                </div>
                <div>
                  <p className="text-xs text-zinc-400 font-medium mb-2 uppercase tracking-wider">
                    By Frequency
                  </p>
                  <TopMerchantsChart data={topMerchants.by_frequency} mode="frequency" />
                </div>
              </div>
            </div>
          )}

          {/* Day-of-Month Patterns */}
          {dayPatterns && dayPatterns.patterns.length > 0 && (
            <div className="bg-zinc-800 rounded-xl p-5 border border-zinc-700/50">
              <h3 className="text-base font-semibold text-white mb-1">📅 Day-of-Month Patterns</h3>
              <p className="text-xs text-zinc-500 mb-4">
                Spending by day of month (1–31) • Peak: Day {dayPatterns.peak_day} ({formatCurrency(dayPatterns.peak_amount)})
              </p>
              <DayPatternsChart
                data={dayPatterns.patterns}
                peakDay={dayPatterns.peak_day}
              />
            </div>
          )}

          {/* Outliers */}
          {outliers.length > 0 && (
            <div className="bg-zinc-800 rounded-xl p-5 border border-zinc-700/50">
              <h3 className="text-base font-semibold text-white mb-1">⚠️ Large Transaction Outliers</h3>
              <p className="text-xs text-zinc-500 mb-4">
                Transactions significantly above your average ({outliers.length} found)
              </p>
              <div className="space-y-2 max-h-[320px] overflow-y-auto">
                {outliers.slice(0, 10).map((txn) => (
                  <div
                    key={txn.transaction_id}
                    className="flex items-center justify-between p-3 bg-zinc-900 rounded-lg"
                  >
                    <div className="min-w-0 flex-1">
                      <p className="text-sm text-white truncate">{txn.description}</p>
                      <p className="text-xs text-zinc-500">
                        {txn.date} • {txn.times_above_average.toFixed(1)}x avg
                        {txn.is_recurring && (
                          <span className="ml-2 text-blue-400">[Recurring]</span>
                        )}
                        {txn.category && (
                          <span className="ml-2 text-zinc-400">• {txn.category}</span>
                        )}
                      </p>
                    </div>
                    <p className="text-sm font-semibold text-red-400 ml-3">
                      {formatCurrency(txn.amount)}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}

      {/* ─── EXISTING ANALYTICS SECTIONS ──────────────────────────────────── */}

      {/* Spending Trends */}
      <div className="bg-zinc-800 rounded-xl p-5 border border-zinc-700/50">
        <h3 className="text-base font-semibold text-white mb-4">
          Spending Trends ({granularity === 'weekly' ? 'Weekly' : 'Monthly'})
        </h3>
        {timeline.length > 0 ? (
          <SpendingTimelineChart data={timeline} />
        ) : (
          <div className="h-64 flex items-center justify-center text-zinc-500">
            No trend data available
          </div>
        )}
      </div>

      {/* Income Analysis */}
      <div className="space-y-6">
        <h3 className="text-base font-semibold text-white">📊 Income Analysis</h3>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Income Trend Chart */}
          <div className="bg-zinc-800 rounded-xl p-5 border border-zinc-700/50">
            <h4 className="text-sm font-semibold text-white mb-4">Monthly Income Trend</h4>
            {incomeTimeline.length > 0 ? (
              <IncomeTimelineChart data={incomeTimeline} />
            ) : (
              <div className="h-64 flex items-center justify-center text-zinc-500">
                No income trend data available
              </div>
            )}
          </div>

          {/* Income Source Breakdown */}
          <div className="bg-zinc-800 rounded-xl p-5 border border-zinc-700/50">
            <h4 className="text-sm font-semibold text-white mb-4">Income Source Breakdown</h4>
            {incomeTimeline.length > 0 ? (
              <IncomeSourceBreakdownChart data={incomeTimeline} />
            ) : (
              <div className="h-64 flex items-center justify-center text-zinc-500">
                No income source data available
              </div>
            )}
          </div>
        </div>

        {/* Income Stability Indicator */}
        {incomeTimeline.length > 0 && (
          <div className="bg-zinc-800 rounded-xl p-5 border border-zinc-700/50">
            <h4 className="text-sm font-semibold text-white mb-4">Income Stability</h4>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="bg-zinc-900 rounded-lg p-4">
                <p className="text-xs text-zinc-500 mb-1">Average Monthly Income</p>
                <p className="text-2xl font-bold text-green-400">
                  {formatCurrency(
                    incomeTimeline.reduce((sum, item) => sum + item.amount, 0) / incomeTimeline.length
                  )}
                </p>
              </div>
              <div className="bg-zinc-900 rounded-lg p-4">
                <p className="text-xs text-zinc-500 mb-1">Highest Monthly Income</p>
                <p className="text-2xl font-bold text-white">
                  {formatCurrency(Math.max(...incomeTimeline.map((item) => item.amount)))}
                </p>
              </div>
              <div className="bg-zinc-900 rounded-lg p-4">
                <p className="text-xs text-zinc-500 mb-1">Income Months Tracked</p>
                <p className="text-2xl font-bold text-white">{incomeTimeline.length}</p>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Month-over-Month Comparison */}
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

      {/* Category Breakdown with Drill-down */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-zinc-800 rounded-xl p-5 border border-zinc-700/50">
          <h3 className="text-base font-semibold text-white mb-4">Category Breakdown</h3>
          {categories.length > 0 ? (
            <CategoryPieChart data={categories} />
          ) : (
            <div className="h-64 flex items-center justify-center text-zinc-500">
              No category data
            </div>
          )}
        </div>

        <div className="bg-zinc-800 rounded-xl p-5 border border-zinc-700/50">
          <h3 className="text-base font-semibold text-white mb-4">Category Details</h3>
          <p className="text-xs text-zinc-500 mb-3">Click a category for deep-dive analytics</p>
          <div className="space-y-2 max-h-[350px] overflow-y-auto">
            {categories.map((cat, idx) => {
              const config = getCategoryConfig(cat.category);
              return (
                <button
                  key={cat.category}
                  onClick={() => handleDeepDiveSelect(cat.category)}
                  className={`w-full flex items-center justify-between p-3 rounded-lg transition-colors ${
                    selectedCategory === cat.category
                      ? 'bg-zinc-700 border border-zinc-600'
                      : 'hover:bg-zinc-700/50'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <div
                      className="w-3 h-3 rounded-full"
                      style={{ backgroundColor: CHART_COLORS[idx % CHART_COLORS.length] }}
                    />
                    <span className="text-sm text-white">
                      {config.emoji} {cat.category}
                    </span>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-medium text-white">
                      {formatCurrency(cat.total_amount)}
                    </p>
                    <p className="text-xs text-zinc-500">
                      {cat.percentage.toFixed(1)}% • {cat.transaction_count} txns
                    </p>
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* Category Drill-down Transactions */}
      {selectedCategory && (
        <div className="bg-zinc-800 rounded-xl p-5 border border-zinc-700/50">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <h3 className="text-base font-semibold text-white">
                Transactions in
              </h3>
              <CategoryBadge category={selectedCategory} />
              <span className="text-xs text-zinc-500">
                ({drilldownTotal} total)
              </span>
            </div>
            <button
              onClick={() => {
                setSelectedCategory(null);
                setCategoryTransactions([]);
              }}
              className="text-sm text-zinc-400 hover:text-white transition-colors"
            >
              ✕ Close
            </button>
          </div>

          {/* Search */}
          <div className="mb-4">
            <input
              type="text"
              placeholder="Search transactions by description..."
              value={drilldownSearch}
              onChange={(e) => handleDrilldownSearch(e.target.value)}
              className="w-full px-4 py-2 bg-zinc-900 border border-zinc-700 rounded-lg text-sm text-white placeholder:text-zinc-500 focus:outline-none focus:border-blue-500 transition-colors"
            />
          </div>

          {loadingDrilldown ? (
            <div className="h-32 flex items-center justify-center">
              <div className="animate-spin w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full" />
            </div>
          ) : (
            <>
              {/* Count indicator */}
              {drilldownTotal > 0 && (
                <div className="text-xs text-zinc-500 mb-3">
                  Showing {(drilldownPage - 1) * DRILLDOWN_PAGE_SIZE + 1}–
                  {Math.min(drilldownPage * DRILLDOWN_PAGE_SIZE, drilldownTotal)} of{' '}
                  {drilldownTotal} transactions
                </div>
              )}

              <div className="max-h-[500px] overflow-y-auto">
                <TransactionTable transactions={categoryTransactions} />
              </div>

              {/* Pagination */}
              {drilldownTotalPages > 1 && (
                <div className="flex items-center justify-between mt-4 pt-4 border-t border-zinc-700">
                  <button
                    onClick={() => handleDrilldownPageChange(drilldownPage - 1)}
                    disabled={drilldownPage <= 1}
                    className="px-3 py-1.5 text-sm rounded-md bg-zinc-700 text-white disabled:opacity-40 disabled:cursor-not-allowed hover:bg-zinc-600 transition-colors"
                  >
                    ← Previous
                  </button>
                  <span className="text-sm text-zinc-400">
                    Page {drilldownPage} of {drilldownTotalPages}
                  </span>
                  <button
                    onClick={() => handleDrilldownPageChange(drilldownPage + 1)}
                    disabled={drilldownPage >= drilldownTotalPages}
                    className="px-3 py-1.5 text-sm rounded-md bg-zinc-700 text-white disabled:opacity-40 disabled:cursor-not-allowed hover:bg-zinc-600 transition-colors"
                  >
                    Next →
                  </button>
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}

function calculateHealthScore(summary: FinancialSummary | null): number {
  if (!summary) return 0;

  let score = 50;

  if (summary.savings_rate >= 30) score += 30;
  else if (summary.savings_rate >= 20) score += 20;
  else if (summary.savings_rate >= 10) score += 10;
  else if (summary.savings_rate < 0) score -= 20;

  if (summary.net_savings > 0) score += 10;
  else score -= 10;

  if (summary.total_expenses < summary.total_income * 0.7) score += 10;

  return Math.max(0, Math.min(100, score));
}

export default function AnalyticsPage() {
  return (
    <ErrorBoundary>
      <Suspense fallback={<PageSkeleton />}>
        <AnalyticsContent />
      </Suspense>
    </ErrorBoundary>
  );
}
