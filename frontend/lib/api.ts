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

  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
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

  // Transactions
  listTransactions: (page = 1, pageSize = 50, category?: string) =>
    request<import("@/types/api").TransactionListResponse>(
      `/transactions?page=${page}&page_size=${pageSize}${category ? `&category=${encodeURIComponent(category)}` : ""}`
    ),
  updateTransaction: (id: string, payload: { nudge_category?: string; is_non_negotiable?: boolean }) =>
    request<import("@/types/api").Transaction>(`/transactions/${id}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),

  // Budgets
  generateBudget: (regenerate = false) =>
    request<import("@/types/api").Budget>("/budgets/generate", {
      method: "POST",
      body: JSON.stringify({ regenerate }),
    }),
  getCurrentBudget: () => request<import("@/types/api").Budget>("/budgets/current"),
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
  sendChatMessage: (message: string) =>
    request<{ reply: string; chart_data: Record<string, unknown> | null }>("/chat", {
      method: "POST",
      body: JSON.stringify({ message }),
    }),
  getChatHistory: () => request<import("@/types/api").ChatMessage[]>("/chat/history"),
};

export { ApiError };
