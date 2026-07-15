const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = typeof window !== "undefined" ? localStorage.getItem("nudge_token") : null;
  const isForm = typeof FormData !== "undefined" && options.body instanceof FormData;

  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      ...(isForm ? {} : { "Content-Type": "application/json" }),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ApiError(res.status, body.detail || "Request failed");
  }

  if (res.status === 204) return undefined as T;
  return res.json();
}

export const api = {
  // Users
  getMe: () => request<import("@/types/api").UserProfile>("/users/me"),
  getAppMode: () => request<import("@/types/api").AppMode>("/app-mode"),
  getToday: () => request<import("@/types/api").TodaySummary>("/today"),
  updateMe: (payload: Partial<import("@/types/api").UserProfile>) =>
    request<import("@/types/api").UserProfile>("/users/me", {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),

  // Plaid
  createLinkToken: () => request<{ link_token: string; mock_mode: boolean }>("/plaid/link-token", { method: "POST" }),
  exchangeToken: (publicToken: string, institutionName?: string) =>
    request<import("@/types/api").PlaidItem>("/plaid/exchange-token", {
      method: "POST",
      body: JSON.stringify({ public_token: publicToken, institution_name: institutionName }),
    }),
  listPlaidItems: () => request<import("@/types/api").PlaidItem[]>("/plaid/items"),
  syncItem: (itemId: string) =>
    request<{ new_transactions: number; accounts_synced: number; mock_mode: boolean }>(`/plaid/sync/${itemId}`, {
      method: "POST",
    }),
  disconnectItem: (itemId: string) =>
    request<void>(`/plaid/items/${itemId}`, { method: "DELETE" }),

  // Transactions
  listTransactions: (page = 1, pageSize = 50, category?: string, rangePreset?: string) =>
    request<import("@/types/api").TransactionListResponse>(
      `/transactions?page=${page}&page_size=${pageSize}${category ? `&category=${encodeURIComponent(category)}` : ""}${rangePreset ? `&range_preset=${rangePreset}` : ""}`
    ),
  downloadTransactionsCsv: async (category?: string, rangePreset?: string) => {
    const params = new URLSearchParams();
    if (category) params.set("category", category);
    if (rangePreset) params.set("range_preset", rangePreset);
    const token = typeof window !== "undefined" ? localStorage.getItem("nudge_token") : null;
    const res = await fetch(`${API_BASE}/transactions/export?${params.toString()}`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (!res.ok) throw new ApiError(res.status, "Failed to export transactions");
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `nudge-transactions-${new Date().toISOString().slice(0, 10)}.csv`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  },
  updateTransaction: (id: string, payload: { nudge_category?: string; is_non_negotiable?: boolean }) =>
    request<import("@/types/api").Transaction>(`/transactions/${id}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  updateStatementTransaction: (id: string, payload: Partial<import("@/types/api").StatementTransaction> & { nudge_category?: string; apply_to_similar?: boolean }) =>
    request<import("@/types/api").StatementTransaction>(`/transactions/${id}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  bulkUpdateTransactions: (payload: { transaction_ids: string[]; nudge_category?: string; is_ignored?: boolean; is_recurring?: boolean; apply_to_similar?: boolean }) =>
    request<{ updated: number }>("/transactions/bulk-update", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  // Statement analyzer
  uploadStatement: (formData: FormData) =>
    request<import("@/types/api").StatementUploadResponse>("/statements/upload", {
      method: "POST",
      body: formData,
    }),
  listStatements: () => request<import("@/types/api").StatementUpload[]>("/statements"),
  getStatement: (id: string) => request<import("@/types/api").StatementUpload>(`/statements/${id}`),
  deleteStatement: (id: string) => request<{ deleted: boolean }>(`/statements/${id}`, { method: "DELETE" }),
  listStatementTransactions: (id: string) =>
    request<import("@/types/api").StatementTransaction[]>(`/statements/${id}/transactions`),
  saveReviewedStatements: () => request<{ reviewed_statements: number }>("/statements/review/save", { method: "POST" }),
  getSpendingSummary: () => request<import("@/types/api").SpendingSummary>("/spending/summary"),
  getSpendingCategories: () => request<import("@/types/api").CategorySpend[]>("/spending/categories"),
  getSpendingMerchants: () => request<import("@/types/api").MerchantSpend[]>("/spending/merchants"),
  getSpendingTrends: () => request<import("@/types/api").SpendingTrend[]>("/spending/trends"),
  getInsights: () => request<import("@/types/api").Insight[]>("/insights"),
  getStatementAnomalies: () => request<import("@/types/api").StatementAnomaly[]>("/statement-anomalies"),
  updateStatementAnomaly: (id: string, userStatus: string) =>
    request<import("@/types/api").StatementAnomaly>(`/statement-anomalies/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ user_status: userStatus }),
    }),
  getRecurringExpenses: () => request<import("@/types/api").RecurringExpense[]>("/recurring-expenses"),
  generateBudgetFromHistory: () => request<import("@/types/api").SmartBudget>("/budget/generate-from-history", { method: "POST" }),
  saveGeneratedBudget: (payload: {
    month: string;
    income_estimate?: number | null;
    total_budget?: number | null;
    recommendations: import("@/types/api").BudgetRecommendation[];
  }) =>
    request<{ id: string; saved: boolean }>("/budget/save", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  // Budgets
  generateBudget: (regenerate = false) =>
    request<import("@/types/api").Budget>("/budgets/generate", {
      method: "POST",
      body: JSON.stringify({ regenerate }),
    }),
  getCurrentBudget: () => request<import("@/types/api").Budget>("/budgets/current"),
  saveCurrentBudget: (payload: {
    month?: string;
    monthly_income?: number | null;
    total_budget?: number | null;
    categories: import("@/types/api").BudgetCategory[];
    ai_reasoning?: string | null;
  }) =>
    request<import("@/types/api").Budget>("/budgets/current", {
      method: "PUT",
      body: JSON.stringify(payload),
    }),
  adjustBudget: (category: string, newAllocated: number) =>
    request<import("@/types/api").Budget>("/budgets/adjust", {
      method: "POST",
      body: JSON.stringify({ category, new_allocated: newAllocated }),
    }),

  // Forecast & Dashboard
  getForecast: () => request<import("@/types/api").ForecastResponse>("/forecast"),
  getDashboardSummary: () => request<import("@/types/api").DashboardSummary>("/dashboard/summary"),

  // Anomalies
  scanAnomalies: () => request<import("@/types/api").Anomaly[]>("/anomalies/scan", { method: "POST" }),
  listAnomalies: () => request<import("@/types/api").Anomaly[]>("/anomalies"),
  submitAnomalyFeedback: (id: string, intentional: boolean) =>
    request<import("@/types/api").Anomaly>(`/anomalies/${id}/feedback`, {
      method: "POST",
      body: JSON.stringify({ intentional }),
    }),

  // Price watches
  createPriceWatch: (productUrl: string, targetPrice?: number) =>
    request<import("@/types/api").PriceWatch>("/price-watches", {
      method: "POST",
      body: JSON.stringify({ product_url: productUrl, target_price: targetPrice }),
    }),
  listPriceWatches: () => request<import("@/types/api").PriceWatch[]>("/price-watches"),
  refreshPriceWatch: (id: string) =>
    request<import("@/types/api").PriceWatch>(`/price-watches/${id}/refresh`, { method: "POST" }),
  deletePriceWatch: (id: string) => request<{ deleted: boolean }>(`/price-watches/${id}`, { method: "DELETE" }),

  // Deals
  getDeals: () => request<import("@/types/api").Deal[]>("/deals"),

  // Chat
  checkAffordability: (payload: import("@/types/api").AffordabilityCheckRequest) =>
    request<import("@/types/api").AffordabilityCheck>("/affordability/check", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  getAffordabilityHistory: () => request<import("@/types/api").AffordabilityCheck[]>("/affordability/history"),

  // Budget actions
  listBudgetCategories: () => request<import("@/types/api").BudgetCategoryRecord[]>("/budget/categories"),
  createBudgetCategory: (payload: Omit<import("@/types/api").BudgetCategoryRecord, "id">) =>
    request<import("@/types/api").BudgetCategoryRecord>("/budget/categories", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  updateBudgetCategory: (id: string, payload: Omit<import("@/types/api").BudgetCategoryRecord, "id">) =>
    request<import("@/types/api").BudgetCategoryRecord>(`/budget/categories/${id}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  deleteBudgetCategory: (id: string) => request<{ deleted: boolean }>(`/budget/categories/${id}`, { method: "DELETE" }),
  rebalanceBudget: (payload: { to_category: string; amount: number; from_category?: string | null; action: string }) =>
    request<{ message: string; safe_to_spend_change: number; updated_categories: import("@/types/api").BudgetCategoryRecord[] }>("/budget/rebalance", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  sendChatMessage: (message: string) =>
    request<{ reply: string; chart_data: Record<string, unknown> | null; actions: { label: string; href: string }[] }>("/chat", {
      method: "POST",
      body: JSON.stringify({ message }),
    }),
  getChatHistory: () => request<import("@/types/api").ChatMessage[]>("/chat/history"),
};

export { ApiError };
