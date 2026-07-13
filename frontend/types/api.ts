export interface UserProfile {
  id: string;
  email: string;
  monthly_income: number | null;
  spend_ceiling: number | null;
  buffer_pct: number;
  location_lat: number | null;
  location_lng: number | null;
  cards: { name: string; cashback_rules: Record<string, number> }[];
  onboarding_complete: boolean;
}

export interface Transaction {
  id: string;
  amount: number;
  date: string;
  merchant_name: string | null;
  category: string | null;
  nudge_category: string | null;
  is_non_negotiable: boolean;
}

export interface TransactionListResponse {
  items: Transaction[];
  total: number;
  page: number;
  page_size: number;
}

export interface BudgetAllocation {
  allocated: number;
  spent: number;
  is_non_neg: boolean;
}

export interface Budget {
  id: string;
  month: string;
  allocations: Record<string, BudgetAllocation>;
  buffer_reserved: number;
  total_allocated: number;
  generated_by_ai: boolean;
  ai_reasoning: string | null;
}

export interface ForecastPoint {
  date: string;
  predicted_spend: number;
  lower_bound: number;
  upper_bound: number;
}

export interface ForecastResponse {
  points: ForecastPoint[];
  month_end_projection: number;
  ceiling: number | null;
  on_track: boolean;
  days_remaining: number;
}

export interface DashboardSummary {
  month_to_date_spend: number;
  month_to_date_income: number;
  buffer_status: number;
  top_categories: { category: string; amount: number }[];
  spend_ceiling: number | null;
  projected_month_end: number;
  recent_anomalies: number;
  active_price_watches: number;
}

export interface Anomaly {
  id: string;
  transaction_id: string;
  merchant_name: string | null;
  amount: number;
  anomaly_score: number;
  ai_context: string | null;
  user_marked_intentional: boolean | null;
  created_at: string;
}

export interface PriceWatch {
  id: string;
  product_url: string;
  product_name: string | null;
  retailer: string | null;
  current_price: number | null;
  target_price: number | null;
  price_history: { date: string; price: number }[];
  verdict: "buy_now" | "wait" | "overpriced" | null;
  confidence: number | null;
}

export interface Deal {
  title: string;
  description: string;
  category: string;
  location: string | null;
  distance_miles: number | null;
  source: string;
  url: string | null;
  expires_at: string | null;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  chart_data?: Record<string, unknown> | null;
  created_at?: string;
}

export interface PlaidItem {
  id: string;
  institution_name: string;
  accounts: { account_id: string; name: string; type: string; mask: string; balance: number }[];
  last_synced_at: string | null;
}
