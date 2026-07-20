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
  subcategory?: string | null;
  transaction_type?: string | null;
  is_non_negotiable: boolean;
  is_recurring?: boolean;
  is_anomaly?: boolean;
  is_ignored?: boolean;
  confidence_score?: number | null;
  raw_description?: string | null;
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

export interface BudgetCategory extends BudgetAllocation {
  name: string;
}

export interface BudgetChange {
  category: string;
  previous_amount: number;
  current_amount: number;
  delta: number;
}

export interface Budget {
  id: string;
  month: string;
  monthly_income: number | null;
  total_budget: number | null;
  allocations: Record<string, BudgetAllocation>;
  buffer_reserved: number;
  total_allocated: number;
  generated_by_ai: boolean;
  ai_reasoning: string | null;
  engine_version: string | null;
  prompt_version: string | null;
  constrained_tiers: string[];
  validation_warnings: string[];
  changes_from_previous: BudgetChange[];
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
  model_used: string;
}

export interface Anomaly {
  id: string;
  transaction_id: string;
  transaction_date: string | null;
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
  image_url: string | null;
  current_price: number | null;
  target_price: number | null;
  price_history: PriceHistoryPoint[];
  verdict: "buy_now" | "wait" | "overpriced" | null;
  verdict_reason: string | null;
  confidence: number | null;
  deal_score: number | null;
  affordability_score: number | null;
  buy_wait_recommendation: string | null;
}

export interface PriceHistoryPoint {
  date: string;
  price: number;
}

export interface ProductDeal {
  title: string;
  description: string;
  category: string;
  result_type: "deal" | "product" | "place" | "event" | string;
  location: string | null;
  address: string | null;
  distance_miles: number | null;
  source: string;
  provider: string | null;
  image_url: string | null;
  price: number | null;
  cost: string | null;
  rating: number | null;
  url: string | null;
  external_url: string | null;
  website_url: string | null;
  ticket_url: string | null;
  directions_url: string | null;
  expires_at: string | null;
  starts_at: string | null;
  ends_at: string | null;
  latitude: number | null;
  longitude: number | null;
  last_updated: string | null;
  is_sample: boolean;
  affordability_label: string | null;
}

export type Deal = ProductDeal;

export interface PlaceRecommendation extends ProductDeal {
  result_type: "place";
}

export interface EventRecommendation extends ProductDeal {
  result_type: "event";
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  actions?: { label: string; href: string }[];
  chart_data?: Record<string, unknown> | null;
  created_at?: string;
}

export interface DashboardSummary {
  month_to_date_spend: number;
  month_to_date_income: number;
  buffer_status: number;
  top_categories: { category: string; amount: number }[];
  daily_trend: { date: string; amount: number }[];
  spend_ceiling: number | null;
  projected_month_end: number;
  recent_anomalies: number;
  active_price_watches: number;
}

export interface TodaySummary {
  safe_to_spend_today: number;
  safe_to_spend_message: string;
  can_calculate: boolean;
  has_linked_data: boolean;
  month_to_date_spending: number;
  month_end_forecast: number;
  spending_ceiling: number | null;
  upcoming_bills_total: number;
  budget_health: string;
  top_risk_category: string | null;
  recommended_action: string;
  remaining_safe_money: number;
  income_source: string;
}

export interface AffordabilityCheckRequest {
  item_name: string;
  price: number;
  category: string;
  need_or_want: string;
  purchase_date: string;
  product_url?: string | null;
  notes?: string | null;
}

export interface AffordabilityCheck {
  id: string | null;
  item_name: string;
  price: number;
  category: string;
  need_or_want: string;
  purchase_date: string;
  product_url: string | null;
  notes: string | null;
  verdict: string;
  explanation: string;
  safe_to_spend_before: number;
  safe_to_spend_after: number;
  remaining_before: number;
  remaining_after: number;
  category_impact: Record<string, any>;
  forecast_impact: Record<string, any>;
  upcoming_bill_risk: string;
  suggested_actions: string[];
  created_at: string | null;
}

export interface BudgetCategoryRecord {
  id: string;
  name: string;
  monthly_limit: number;
  category_type: "fixed" | "flexible" | "optional" | "savings" | "not_applicable" | string;
  is_disabled: boolean;
  is_default: boolean;
}

export interface AppMode {
  mode: string;
  badges: string[];
  message: string | null;
}

export interface PlaidItem {
  id: string;
  institution_name: string;
  accounts: { account_id: string; name: string; type: string; mask: string; balance: number }[];
  last_synced_at: string | null;
}

export interface StatementUpload {
  id: string;
  file_name: string;
  file_type: string;
  statement_month: string;
  bank_name: string | null;
  upload_date: string;
  status: "uploaded" | "parsed" | "failed" | "reviewed" | string;
  error_message: string | null;
}

export interface StatementUploadResponse {
  statement: StatementUpload;
  parsed_count: number;
  needs_mapping: boolean;
  message: string;
}

export interface StatementTransaction {
  id: string;
  transaction_id: string;
  date: string;
  description: string;
  merchant_name: string | null;
  amount: number;
  transaction_type: string;
  category: string | null;
  subcategory: string | null;
  bank_name: string | null;
  source_statement_id: string | null;
  raw_description: string | null;
  confidence_score: number | null;
  location_city: string | null;
  location_state: string | null;
  location_country: string | null;
  currency: string;
  is_recurring: boolean;
  is_anomaly: boolean;
  is_ignored: boolean;
}

export interface SpendingSummary {
  total_income: number;
  total_spending: number;
  net_cash_flow: number;
  average_daily_spending: number;
  average_weekly_spending: number;
  savings_rate: number | null;
  transaction_count: number;
  months_of_history: number;
  prediction_message: string | null;
  expected_next_month_spending: number | null;
  expected_next_month_income: number | null;
  cash_left_after_predicted_expenses: number | null;
}

export interface CategorySpend {
  category: string;
  amount: number;
  transaction_count: number;
}

export interface MerchantSpend {
  merchant_name: string;
  amount: number;
  transaction_count: number;
}

export interface SpendingTrend {
  month: string;
  income: number;
  spending: number;
}

export interface Insight {
  title: string;
  detail: string;
  severity: string;
}

export interface RecurringExpense {
  id: string | null;
  merchant_name: string;
  amount: number;
  frequency: string;
  next_expected_date: string | null;
  category: string | null;
  confidence_score: number;
}

export interface StatementAnomaly {
  id: string | null;
  transaction_id: string | null;
  anomaly_type: string;
  explanation: string;
  severity: string;
  user_status: string;
  merchant_name: string | null;
  amount: number | null;
}

export interface BudgetRecommendation {
  category: string;
  recommended_amount: number;
  reasoning: string;
  confidence_score: number;
}

export interface CategoryEvidence {
  typical_range_low: number;
  typical_range_high: number;
  trend: string;
  confidence: number;
}

export interface SmartBudget {
  month: string;
  income_estimate: number;
  total_budget: number;
  recommendations: BudgetRecommendation[];
  warnings: string[];
  explanation: string;
  income_stability: string;
  category_evidence: Record<string, CategoryEvidence>;
}

export interface AllocationEntry {
  allocated: number;
  is_non_neg: boolean;
}

export interface ScenarioChange {
  category: string;
  previous_amount: number;
  current_amount: number;
  delta: number;
}

export interface ScenarioRequest {
  scenario_type: "category_change" | "income_change" | "one_time_expense";
  category?: string;
  new_amount?: number;
  new_income_estimate?: number;
  amount?: number;
}

export interface ScenarioResult {
  scenario: string;
  income_before: number;
  income_after: number;
  spendable_before: number;
  spendable_after: number;
  before_allocations: Record<string, AllocationEntry>;
  after_allocations: Record<string, AllocationEntry>;
  changes: ScenarioChange[];
  risk_level: "none" | "tight" | "over_budget";
  summary: string;
}
