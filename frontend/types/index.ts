export interface Transaction {
  id: number;
  account_id: number;
  transaction_date: string;
  description: string;
  amount: number;
  transaction_type: 'debit' | 'credit';
  balance?: number;
  reference_number?: string;
  merchant_name?: string;
  category: string;
  subcategory?: string;
  confidence_score: number;
  classification_tier: 'rule' | 'zero_shot' | 'llm' | 'manual';
  source: 'upload' | 'manual';
  currency?: string;
  tags?: string[];
  is_recurring: boolean;
  notes?: string;
  metadata?: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface CategoryBreakdown {
  category: string;
  total_amount: number;
  percentage: number;
  transaction_count: number;
  average_transaction: number;
  color?: string;
  subcategories?: {
    name: string;
    amount: number;
    percentage: number;
    transaction_count: number;
  }[];
}

export interface MonthlyTrend {
  month: string;
  income: number;
  expenses: number;
  net: number;
  transaction_count: number;
  savings_rate: number;
}

export interface IncomeVsExpense {
  month: string;
  income: number;
  expenses: number;
}

export interface FinancialSummary {
  total_income: number;
  total_expenses: number;
  net_savings: number;
  savings_rate: number;
  top_category: string;
  top_category_amount: number;
  transaction_count: number;
  date_range: {
    start: string;
    end: string;
  };
}

export interface TopMerchant {
  merchant_name: string;
  category: string;
  total_spent: number;
  transaction_count: number;
  average_transaction: number;
  percentage_of_total: number;
}

export interface UploadSummary {
  total_transactions: number;
  date_range: { start: string; end: string };
  total_income: number;
  total_expenses: number;
  net_cash_flow: number;
  categories_detected: number;
  transactions_needing_review: number;
  processing_time_seconds: number;
}

export interface UploadResponse {
  upload_id: number;
  status: 'success' | 'failed' | 'partial';
  summary?: UploadSummary;
  transactions: Transaction[];
  category_breakdown: CategoryBreakdown[];
  warnings?: string[];
  classification_job_id?: string | null;
}

export interface ClassificationJob {
  id: string;
  user_id: number;
  bank_statement_id?: number | null;
  total_transactions: number;
  classified_transactions: number;
  status: 'pending' | 'running' | 'completed' | 'failed';
  started_at?: string | null;
  completed_at?: string | null;
  error?: string | null;
  progress_percent: number;
}

export interface TransactionTotals {
  credit_amount: number;
  debit_amount: number;
  net_amount: number;
  currency: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  totals?: TransactionTotals;
}

export interface Category {
  id: number;
  name: string;
  icon?: string | null;
  color?: string | null;
  parent_id?: number | null;
  user_id?: number | null;
  is_system: boolean;
}

export interface TransactionFilters {
  category?: string;
  payment_method?: string;
  date_from?: string;
  date_to?: string;
  amount_min?: number;
  amount_max?: number;
  transaction_type?: 'debit' | 'credit';
  search?: string;
  page?: number;
  page_size?: number;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
  needs_review?: boolean;
}

// ─── Insights Types ─────────────────────────────────────────────────────────

export interface RecurringTransaction {
  merchant: string;
  average_amount: number;
  frequency: string;
  occurrence_count: number;
  last_date: string;
  next_expected_date: string | null;
  total_spent: number;
}

export interface InsightTopMerchant {
  merchant: string;
  transaction_count: number;
  total_amount: number;
  average_amount: number;
  percentage_of_total: number;
}

export interface TopMerchantsResponse {
  by_frequency: InsightTopMerchant[];
  by_total_spend: InsightTopMerchant[];
}

export interface VelocityEntry {
  income_date: string;
  income_amount: number;
  spent_7_days: number;
  velocity_7d_percent: number;
  days_to_50_percent: number | null;
  daily_burn_rate: number;
  risk_level: string;
}

export interface VelocityResponse {
  entries: VelocityEntry[];
  average_days_to_50_percent: number | null;
  average_velocity_7d: number;
  overall_risk_level: string;
}

export interface OutlierTransaction {
  transaction_id: number;
  date: string;
  description: string;
  amount: number;
  transaction_type: string;
  times_above_average: number;
  is_recurring: boolean;
  category: string | null;
}

export interface DayPattern {
  day: number;
  transaction_count: number;
  total_amount: number;
  average_amount: number;
}

export interface DayPatternsResponse {
  patterns: DayPattern[];
  peak_day: number;
  peak_amount: number;
  lowest_day: number;
  lowest_amount: number;
}

export interface PaymentMethodEntry {
  method: string;
  transaction_count: number;
  total_amount: number;
  percentage_by_count: number;
  percentage_by_amount: number;
}

export interface PaymentMethodsResponse {
  methods: PaymentMethodEntry[];
  digital_percentage: number;
  most_used_method: string;
}

export interface InsightsSummary {
  top_recurring: RecurringTransaction[];
  top_merchants: InsightTopMerchant[];
  velocity_risk: string;
  average_velocity_7d: number;
  outlier_count: number;
  top_outliers: OutlierTransaction[];
  peak_spending_day: number;
  primary_payment_method: string;
  digital_percentage: number;
}

// ─── Category Deep-Dive Types ────────────────────────────────────────────────

export interface DailySpendingEntry {
  date: string;
  amount: number;
}

export interface MonthlySpendingEntry {
  month: string;
  amount: number;
  change_pct: number | null;
}

export interface TopTransactionEntry {
  date: string;
  description: string;
  amount: number;
}

export interface CategorySummaryData {
  total: number;
  avg_monthly: number;
  pct_of_total: number;
  count: number;
  trend: 'increasing' | 'decreasing' | 'stable';
}

export interface CategoryAnalyticsResponse {
  category: string;
  daily_spending: DailySpendingEntry[];
  monthly_spending: MonthlySpendingEntry[];
  top_transactions: TopTransactionEntry[];
  summary: CategorySummaryData;
}

// ─── Income Timeline Types ──────────────────────────────────────────────────

export interface IncomeSource {
  name: string;
  amount: number;
}

export interface IncomeTrend {
  month: string;
  amount: number;
  change_pct: number | null;
  sources: IncomeSource[];
}

// ─── Budget Types ───────────────────────────────────────────────────────────

export interface Budget {
  id: number;
  category_name: string | null;
  amount: number;
  period: string;
  spent: number;
  remaining: number;
  percentage_used: number;
  is_over_budget: boolean;
  is_active: boolean;
}

export interface BudgetAlert {
  budget_id: number;
  category_name: string | null;
  message: string;
  severity: 'warning' | 'danger' | 'over';
  percentage_used: number;
}

export interface BudgetSummary {
  total_budget: number;
  total_spent: number;
  total_remaining: number;
  total_percentage_used: number;
  days_remaining_in_period: number;
  projected_end_of_period_spend: number;
  budgets: Budget[];
  alerts: BudgetAlert[];
}

export interface BudgetSuggestion {
  category_name: string;
  suggested_amount: number;
  confidence: number;
  rationale: string;
  methodology: 'trend_projection' | 'median_with_buffer' | 'fifty_thirty_twenty' | 'consistency_based';
  avg_monthly_spend: number;
  trend: 'increasing' | 'decreasing' | 'stable';
  months_analyzed: number;
  // Backwards-compatible fields
  average_spending: number;
  reasoning: string;
}

export interface BudgetSuggestionsResponse {
  suggestions: BudgetSuggestion[];
}

export interface BudgetCreatePayload {
  category_name?: string | null;
  amount: number;
  period: string;
}

export interface BudgetUpdatePayload {
  amount?: number;
  period?: string;
  is_active?: boolean;
}

// ─── Subscription Types ─────────────────────────────────────────────────────

export interface Subscription {
  merchant: string;
  monthly_amount: number;
  annual_cost: number;
  frequency: string;
  occurrence_count: number;
  last_date: string;
  next_expected_date: string;
  status: 'active' | 'possibly_cancelled';
}

export interface SubscriptionsResponse {
  subscriptions: Subscription[];
  total_monthly_cost: number;
  total_annual_cost: number;
  active_count: number;
  possibly_cancelled_count: number;
  potential_annual_savings: number;
}

// ─── AI Summary ──────────────────────────────────────────────────────────────

export interface AISummaryOverview {
  total_income: number;
  total_expenses: number;
  net_savings: number;
  savings_rate: number;
  current_month_income: number;
  current_month_expenses: number;
  current_month_savings_rate: number;
  last_month_expenses: number;
  expense_change_pct: number | null;
  transaction_count: number;
}

export interface AISummaryMerchant {
  name: string;
  frequency: number;
  total_spent: number;
}

export interface AISummaryHabits {
  top_category: string | null;
  top_category_amount: number;
  top_category_change_pct: number | null;
  top_merchants: AISummaryMerchant[];
  categories_used: number;
  average_transaction: number;
}

export interface AISummaryAnomaly {
  description: string;
  amount: number;
  category: string;
  average_for_category: number;
  multiplier: number;
}

export interface AISummaryCategoryBreakdown {
  category: string;
  amount: number;
  percentage: number;
}

export interface AISummaryInsights {
  anomalies: AISummaryAnomaly[];
  recurring_payments_total: number;
  spending_trend: string;
  top_category_breakdown: AISummaryCategoryBreakdown[];
}

export interface AISummaryAdvice {
  type: 'warning' | 'caution' | 'info' | 'positive';
  icon: string;
  title: string;
  message: string;
}

export interface AISummaryMonthlyReviewCategory {
  name: string;
  amount: number;
  percentage: number;
  change_vs_previous: number | null;
}

export interface AISummaryMonthlyReview {
  summary_sentence: string;
  comparison_sentence: string | null;
  total_spent: number;
  total_income: number;
  transaction_count: number;
  top_categories: AISummaryMonthlyReviewCategory[];
  biggest_expense: { amount: number; description: string; date: string | null } | null;
  biggest_income: { amount: number; description: string; date: string | null } | null;
  unique_merchants: number;
  average_transaction: number;
  no_spend_days: number;
}

export interface AISummaryFunStat {
  icon: string;
  text: string;
  value: number;
  type: string;
}

export interface AISummarySpendingPersonality {
  emoji: string;
  label: string;
  description: string;
}

export interface AISummaryDetailedInsight {
  title: string;
  icon: string;
  text: string;
}

export interface AISummaryAchievement {
  icon: string;
  title: string;
  type: string;
}

export interface AISummaryPredictions {
  next_month_expense: number;
  annual_subscription_cost: number;
  year_end_savings: number;
  annual_income_projection: number;
  sentences: string[];
}

export interface AISummaryResponse {
  overview: AISummaryOverview;
  habits: AISummaryHabits;
  insights: AISummaryInsights;
  advice: AISummaryAdvice[];
  monthly_review: AISummaryMonthlyReview;
  fun_statistics: AISummaryFunStat[];
  spending_personality: AISummarySpendingPersonality;
  detailed_insights: AISummaryDetailedInsight[];
  achievements: AISummaryAchievement[];
  predictions: AISummaryPredictions;
  generated_at: string;
  period: { start: string; end: string; reference_date?: string; note?: string } | null;
}

// ─── Monthly Personality Tabs + Year Recap ───────────────────────────────────

export type AITone = 'roast' | 'praise' | 'executive' | 'fun';

export interface AvailableMonth {
  month: string; // "2025-03"
  label: string; // "March 2025"
  transaction_count: number;
}

export interface AvailableMonthsResponse {
  months: AvailableMonth[];
}

export interface AIToneMeta {
  emoji: string;
  label: string;
  tagline: string;
}

export interface MonthlySummaryCategory {
  name: string;
  amount: number;
  percentage: number;
  count: number;
}

export interface MonthlySummaryMerchant {
  name: string;
  frequency: number;
  total_spent: number;
}

export interface MonthlySummaryStats {
  total_spent: number;
  total_income: number;
  net_savings: number;
  savings_rate: number;
  transaction_count: number;
  debit_count: number;
  credit_count: number;
  expense_change_pct: number | null;
  top_categories: MonthlySummaryCategory[];
  top_merchants: MonthlySummaryMerchant[];
  biggest_expense: { amount: number; description: string; date: string | null } | null;
  no_spend_days: number;
  average_transaction: number;
}

export interface MonthlySummaryLine {
  icon: string;
  text: string;
}

export interface MonthlySummaryResponse {
  month: string;
  month_label: string;
  tone: AITone;
  meta: AIToneMeta;
  currency: string;
  currency_symbol: string;
  has_data: boolean;
  stats: MonthlySummaryStats;
  lines: MonthlySummaryLine[];
  generated_at: string;
}

export interface YearRecapBiggestTransaction {
  amount: number;
  description: string;
  date: string | null;
  category: string;
}

export interface YearRecapAchievement {
  icon: string;
  title: string;
  description: string;
}

export interface YearRecapHeadlineStats {
  total_spent: number;
  total_income: number;
  net_savings: number;
  savings_rate: number;
  transaction_count: number;
  biggest_month: string | null;
  smallest_month: string | null;
}

export interface YearRecapResponse {
  year: number;
  has_data: boolean;
  personality_title: string;
  personality_emoji: string;
  currency: string;
  currency_symbol: string;
  headline_stats: YearRecapHeadlineStats;
  top_categories: MonthlySummaryCategory[];
  top_merchants: MonthlySummaryMerchant[];
  biggest_transactions: YearRecapBiggestTransaction[];
  surprising_stats: string[];
  achievements: YearRecapAchievement[];
  narrative: string;
  generated_at: string;
}

// ─── Transaction Explainer Types ─────────────────────────────────────────────

export interface TransactionExplanation {
  explanation: string;
  recipient_or_sender: string | null;
  payment_method: string | null;
  reference: string | null;
  category_suggestion: string | null;
  confidence: number;
  direction: string | null;
  card_reference: string | null;
  service: string | null;
}

export interface ExplainBatchItem {
  transaction_id: number;
  description: string;
  amount: number;
  transaction_type: string;
  current_category: string;
  explanation: TransactionExplanation;
}

export interface ExplainBatchResponse {
  items: ExplainBatchItem[];
  total: number;
}
