import axios, { AxiosProgressEvent } from 'axios';
import {
  Transaction,
  CategoryBreakdown,
  MonthlyTrend,
  IncomeVsExpense,
  FinancialSummary,
  TopMerchant,
  UploadResponse,
  PaginatedResponse,
  Category,
  TransactionFilters,
  RecurringTransaction,
  TopMerchantsResponse,
  VelocityResponse,
  OutlierTransaction,
  DayPatternsResponse,
  PaymentMethodsResponse,
  InsightsSummary,
  CategoryAnalyticsResponse,
  IncomeTrend,
  Budget,
  BudgetSummary,
  BudgetSuggestionsResponse,
  BudgetCreatePayload,
  BudgetUpdatePayload,
  SubscriptionsResponse,
  AISummaryResponse,
  ClassificationJob,
  TransactionExplanation,
  ExplainBatchResponse,
  AITone,
  AvailableMonthsResponse,
  MonthlySummaryResponse,
  YearRecapResponse,
} from '@/types';
import { getSessionToken } from './session';
import { getAccessToken, getRefreshToken, storeTokens, clearAuthTokens } from './auth';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || '';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Attach active token to every request
apiClient.interceptors.request.use((config) => {
  const token = getSessionToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor: on 401, try token refresh then retry
let isRefreshing = false;
let failedQueue: Array<{ resolve: (token: string) => void; reject: (error: unknown) => void }> = [];

function processQueue(error: unknown, token: string | null = null) {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve(token!);
    }
  });
  failedQueue = [];
}

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._retry) {
      const refreshToken = getRefreshToken();
      const accessToken = getAccessToken();

      // Only attempt refresh if we have JWT tokens (not legacy session)
      if (refreshToken && accessToken) {
        if (isRefreshing) {
          return new Promise((resolve, reject) => {
            failedQueue.push({ resolve, reject });
          }).then((token) => {
            originalRequest.headers.Authorization = `Bearer ${token}`;
            return apiClient(originalRequest);
          });
        }

        originalRequest._retry = true;
        isRefreshing = true;

        try {
          const res = await axios.post(`${API_BASE_URL}/api/v1/auth/refresh`, {
            refresh_token: refreshToken,
          });
          const newAccessToken = res.data.access_token;
          storeTokens({ access_token: newAccessToken, refresh_token: refreshToken });
          processQueue(null, newAccessToken);
          originalRequest.headers.Authorization = `Bearer ${newAccessToken}`;
          return apiClient(originalRequest);
        } catch (refreshError) {
          processQueue(refreshError, null);
          clearAuthTokens();
          if (typeof window !== 'undefined') {
            window.location.href = '/login';
          }
          return Promise.reject(refreshError);
        } finally {
          isRefreshing = false;
        }
      }

      // No refresh token available — redirect to login
      if (typeof window !== 'undefined' && !window.location.pathname.startsWith('/login') && !window.location.pathname.startsWith('/register')) {
        clearAuthTokens();
        window.location.href = '/login';
      }
    }

    const detail = error.response?.data?.detail;
    let message: string;
    if (Array.isArray(detail)) {
      message = detail.map((d: Record<string, unknown>) => d.msg || JSON.stringify(d)).join('; ');
    } else if (typeof detail === 'string') {
      message = detail;
    } else if (detail) {
      message = JSON.stringify(detail);
    } else {
      message = error.message || 'An error occurred';
    }
    return Promise.reject(new Error(message));
  }
);

export const api = {
  upload: async (
    file: File,
    bankName: string,
    onProgress?: (progress: number) => void
  ): Promise<UploadResponse> => {
    const formData = new FormData();
    formData.append('file', file);
    if (bankName && bankName !== 'auto') {
      formData.append('bank', bankName);
    }

    const response = await apiClient.post('/api/v1/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 120000,
      onUploadProgress: (event: AxiosProgressEvent) => {
        if (onProgress && event.total) {
          onProgress(Math.round((event.loaded * 100) / event.total));
        }
      },
    });
    return response.data;
  },

  getTransactions: async (
    filters: TransactionFilters = {}
  ): Promise<PaginatedResponse<Transaction>> => {
    const response = await apiClient.get('/api/v1/transactions', {
      params: filters,
    });
    return response.data;
  },

  updateTransaction: async (
    id: number,
    data: { category_id?: number; category_name?: string; notes?: string }
  ): Promise<Transaction> => {
    const response = await apiClient.put(`/api/v1/transactions/${id}`, data);
    return response.data;
  },

  createTransaction: async (data: {
    description: string;
    amount: number;
    transaction_date?: string;
    transaction_type: 'debit' | 'credit';
    category_name?: string;
    source?: 'upload' | 'manual';
  }): Promise<Transaction> => {
    const response = await apiClient.post('/api/v1/transactions', data);
    return response.data;
  },

  getSpendingByCategory: async (params?: {
    start_date?: string;
    end_date?: string;
  }): Promise<CategoryBreakdown[]> => {
    const response = await apiClient.get('/api/v1/analytics/spending-by-category', {
      params,
    });
    return response.data;
  },

  getTimeline: async (params?: {
    granularity?: 'weekly' | 'monthly';
    months?: number;
  }): Promise<MonthlyTrend[]> => {
    const response = await apiClient.get('/api/v1/analytics/timeline', {
      params,
    });
    return response.data;
  },

  getIncomeVsExpenses: async (params?: {
    months?: number;
  }): Promise<IncomeVsExpense[]> => {
    const response = await apiClient.get('/api/v1/analytics/income-vs-expenses', {
      params,
    });
    return response.data;
  },

  getSummary: async (): Promise<FinancialSummary> => {
    const response = await apiClient.get('/api/v1/analytics/summary');
    return response.data;
  },

  classifyBatch: async (transactionIds: number[]): Promise<any> => {
    const response = await apiClient.post('/api/v1/classify/batch', {
      transaction_ids: transactionIds,
    });
    return response.data;
  },

  classifyBatchWithDescriptions: async (
    transactions: { description: string; amount?: number; transaction_type?: string }[]
  ): Promise<any> => {
    const response = await apiClient.post('/api/v1/classify/batch', {
      transactions,
    });
    return response.data;
  },

  bulkUpdateTransactions: async (
    transactionIds: number[] | null,
    categoryName: string,
    filters?: {
      category?: string;
      transaction_type?: 'debit' | 'credit';
      payment_method?: string;
      search?: string;
      needs_review?: boolean;
    }
  ): Promise<{ message: string; updated_count: number }> => {
    const body: any = {
      category_name: categoryName,
    };
    
    if (transactionIds) {
      body.transaction_ids = transactionIds;
    }
    
    if (filters) {
      body.filters = filters;
    }
    
    const response = await apiClient.put('/api/v1/transactions/bulk-update', body);
    return response.data;
  },

  submitFeedback: async (
    transaction: {
      description: string;
      category: string;
      subcategory?: string;
      confidence_score: number;
      classification_tier: string;
      amount: number;
    },
    correctCategory: string,
    correctSubcategory?: string
  ): Promise<void> => {
    await apiClient.post('/api/v1/classify/feedback', {
      transaction_description: transaction.description,
      original_category: transaction.category || 'Uncategorized',
      corrected_category: correctCategory,
      original_subcategory: transaction.subcategory || null,
      corrected_subcategory: correctSubcategory || null,
      original_confidence: transaction.confidence_score,
      original_source: transaction.classification_tier || 'unknown',
      amount: transaction.amount,
    });
  },

  getCategories: async (): Promise<Category[]> => {
    const response = await apiClient.get('/api/v1/categories');
    return response.data;
  },

  createCategory: async (data: { name: string; icon?: string; color?: string }): Promise<Category> => {
    const response = await apiClient.post('/api/v1/categories', data);
    return response.data;
  },

  // ─── Insights Endpoints ─────────────────────────────────────────────────────

  getRecurringTransactions: async (params?: {
    start_date?: string;
    end_date?: string;
  }): Promise<RecurringTransaction[]> => {
    const response = await apiClient.get('/api/v1/insights/recurring', { params });
    return response.data;
  },

  getTopMerchants: async (params?: {
    start_date?: string;
    end_date?: string;
    limit?: number;
  }): Promise<TopMerchantsResponse> => {
    const response = await apiClient.get('/api/v1/insights/top-merchants', { params });
    return response.data;
  },

  getSpendingVelocity: async (params?: {
    start_date?: string;
    end_date?: string;
  }): Promise<VelocityResponse> => {
    const response = await apiClient.get('/api/v1/insights/velocity', { params });
    return response.data;
  },

  getOutliers: async (params?: {
    start_date?: string;
    end_date?: string;
    threshold?: number;
  }): Promise<OutlierTransaction[]> => {
    const response = await apiClient.get('/api/v1/insights/outliers', { params });
    return response.data;
  },

  getDayPatterns: async (params?: {
    start_date?: string;
    end_date?: string;
  }): Promise<DayPatternsResponse> => {
    const response = await apiClient.get('/api/v1/insights/patterns', { params });
    return response.data;
  },

  getPaymentMethods: async (params?: {
    start_date?: string;
    end_date?: string;
  }): Promise<PaymentMethodsResponse> => {
    const response = await apiClient.get('/api/v1/insights/payment-methods', { params });
    return response.data;
  },

  getInsightsSummary: async (params?: {
    start_date?: string;
    end_date?: string;
  }): Promise<InsightsSummary> => {
    const response = await apiClient.get('/api/v1/insights/summary', { params });
    return response.data;
  },

  clearAllData: async (): Promise<{
    message: string;
    deleted_transactions: number;
    deleted_statements: number;
  }> => {
    const response = await apiClient.delete('/api/v1/transactions/data/clear');
    return response.data;
  },

  // ─── Income Timeline ────────────────────────────────────────────────────────

  getIncomeTimeline: async (params?: {
    months?: number;
  }): Promise<IncomeTrend[]> => {
    const response = await apiClient.get('/api/v1/analytics/income-timeline', {
      params,
    });
    return response.data;
  },

  // ─── Category Deep-Dive ─────────────────────────────────────────────────────

  getCategoryAnalytics: async (
    categoryName: string,
    params?: { start_date?: string; end_date?: string }
  ): Promise<CategoryAnalyticsResponse> => {
    const response = await apiClient.get(
      `/api/v1/analytics/category/${encodeURIComponent(categoryName)}`,
      { params }
    );
    return response.data;
  },

  // ─── Budget Endpoints ───────────────────────────────────────────────────────

  getBudgets: async (): Promise<Budget[]> => {
    const response = await apiClient.get('/api/v1/budgets');
    return response.data;
  },

  getBudgetSummary: async (): Promise<BudgetSummary> => {
    const response = await apiClient.get('/api/v1/budgets/summary');
    return response.data;
  },

  createBudget: async (data: BudgetCreatePayload): Promise<Budget> => {
    const response = await apiClient.post('/api/v1/budgets', data);
    return response.data;
  },

  updateBudget: async (id: number, data: BudgetUpdatePayload): Promise<Budget> => {
    const response = await apiClient.put(`/api/v1/budgets/${id}`, data);
    return response.data;
  },

  deleteBudget: async (id: number): Promise<void> => {
    await apiClient.delete(`/api/v1/budgets/${id}`);
  },

  suggestBudgets: async (): Promise<BudgetSuggestionsResponse> => {
    const response = await apiClient.get('/api/v1/budgets/suggest');
    return response.data;
  },

  // ─── Subscriptions ──────────────────────────────────────────────────────────

  getSubscriptions: async (params?: {
    start_date?: string;
    end_date?: string;
  }): Promise<SubscriptionsResponse> => {
    const response = await apiClient.get('/api/v1/insights/subscriptions', { params });
    return response.data;
  },

  // ─── AI Summary ──────────────────────────────────────────────────────────────

  getAISummary: async (refresh?: boolean): Promise<AISummaryResponse> => {
    const params = refresh ? { refresh: 'true', t: Date.now() } : undefined;
    const response = await apiClient.get('/api/v1/ai/summary', { params });
    return response.data;
  },

  getAvailableMonths: async (): Promise<AvailableMonthsResponse> => {
    const response = await apiClient.get('/api/v1/ai/summary/available-months');
    return response.data;
  },

  getMonthlyAISummary: async (
    month: string,
    tone: AITone,
    refresh?: boolean
  ): Promise<MonthlySummaryResponse> => {
    const params: Record<string, string | number> = { month, tone };
    if (refresh) params.t = Date.now();
    const response = await apiClient.get('/api/v1/ai/summary/monthly', { params });
    return response.data;
  },

  getYearlyAIRecap: async (
    year: number,
    refresh?: boolean
  ): Promise<YearRecapResponse> => {
    const params: Record<string, string | number> = { year };
    if (refresh) params.t = Date.now();
    const response = await apiClient.get('/api/v1/ai/summary/yearly', { params });
    return response.data;
  },

  // ─── Classification Jobs ────────────────────────────────────────────────────

  getClassificationJob: async (jobId: string): Promise<ClassificationJob> => {
    const response = await apiClient.get(`/api/v1/jobs/classification/${jobId}`);
    return response.data;
  },

  getActiveClassificationJob: async (): Promise<ClassificationJob | null> => {
    const response = await apiClient.get('/api/v1/jobs/classification/active');
    return response.data;
  },

  // ─── Transaction Explainer ──────────────────────────────────────────────────

  explainTransaction: async (transactionId: number): Promise<TransactionExplanation> => {
    const response = await apiClient.post(`/api/v1/transactions/${transactionId}/explain`);
    return response.data;
  },

  explainTransactionsBatch: async (params: {
    transaction_ids?: number[];
    category?: string;
    limit?: number;
  }): Promise<ExplainBatchResponse> => {
    const response = await apiClient.post('/api/v1/transactions/explain-batch', params);
    return response.data;
  },
};
