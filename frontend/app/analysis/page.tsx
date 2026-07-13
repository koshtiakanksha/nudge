"use client";

import { useEffect, useState } from "react";
import { Bar, BarChart, CartesianGrid, Cell, Legend, Line, LineChart, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "@/lib/api";
import { CategorySpend, Insight, MerchantSpend, SpendingSummary, SpendingTrend } from "@/types/api";
import { Card, CardLabel } from "@/components/card";
import { PageHeader } from "@/components/page-header";
import { formatCurrency } from "@/lib/format";

const COLORS = ["#55715f", "#c4974f", "#b86f52", "#64748b", "#7c8f68", "#9f6a5f", "#445b65", "#8a7f62"];

export default function AnalysisPage() {
  const [summary, setSummary] = useState<SpendingSummary | null>(null);
  const [categories, setCategories] = useState<CategorySpend[]>([]);
  const [merchants, setMerchants] = useState<MerchantSpend[]>([]);
  const [trends, setTrends] = useState<SpendingTrend[]>([]);
  const [insights, setInsights] = useState<Insight[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      api.getSpendingSummary(),
      api.getSpendingCategories(),
      api.getSpendingMerchants(),
      api.getSpendingTrends(),
      api.getInsights(),
    ])
      .then(([summaryRes, categoryRes, merchantRes, trendRes, insightRes]) => {
        setSummary(summaryRes);
        setCategories(categoryRes);
        setMerchants(merchantRes);
        setTrends(trendRes);
        setInsights(insightRes);
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Could not load analysis"))
      .finally(() => setLoading(false));
  }, []);

  return (
    <>
      <PageHeader title="Spending Analysis" subtitle="Patterns, trends, merchants, and AI-assisted insights from uploaded statements" />
      <div className="px-8 py-6 max-w-6xl space-y-6">
        {loading ? (
          <p className="text-sm text-slate">Analyzing spending...</p>
        ) : error ? (
          <Card><p className="text-sm text-clay">{error}</p></Card>
        ) : !summary || summary.transaction_count === 0 ? (
          <Card><p className="text-sm text-slate">No statement transactions found. Upload a statement to view analysis.</p></Card>
        ) : (
          <>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <Metric label="Income" value={formatCurrency(summary.total_income)} />
              <Metric label="Spending" value={formatCurrency(summary.total_spending)} />
              <Metric label="Net cash flow" value={formatCurrency(summary.net_cash_flow)} />
              <Metric label="Avg weekly spend" value={formatCurrency(summary.average_weekly_spending)} />
            </div>

            {summary.prediction_message ? (
              <Card className="bg-gold/5 border-gold/20"><p className="text-sm text-ink">{summary.prediction_message}</p></Card>
            ) : (
              <Card className="bg-moss/5 border-moss/20">
                <CardLabel>Upcoming month prediction</CardLabel>
                <p className="text-sm">Expected spending: <strong>{formatCurrency(summary.expected_next_month_spending || 0)}</strong> · Expected income: <strong>{formatCurrency(summary.expected_next_month_income || 0)}</strong> · Cash left: <strong>{formatCurrency(summary.cash_left_after_predicted_expenses || 0)}</strong></p>
              </Card>
            )}

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
              <Card>
                <CardLabel>Category spending</CardLabel>
                {categories.length === 0 ? <p className="text-sm text-slate">No spending categories yet.</p> : (
                  <div className="h-72">
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie data={categories} dataKey="amount" nameKey="category" innerRadius={58} outerRadius={96}>
                          {categories.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                        </Pie>
                        <Tooltip formatter={(value) => formatCurrency(Number(value))} />
                        <Legend />
                      </PieChart>
                    </ResponsiveContainer>
                  </div>
                )}
              </Card>

              <Card>
                <CardLabel>Monthly trend</CardLabel>
                {trends.length === 0 ? <p className="text-sm text-slate">Upload at least one statement to see trends.</p> : (
                  <div className="h-72">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={trends}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="month" tick={{ fontSize: 11 }} />
                        <YAxis tickFormatter={(v) => `$${v}`} tick={{ fontSize: 11 }} />
                        <Tooltip formatter={(value) => formatCurrency(Number(value))} />
                        <Legend />
                        <Line type="monotone" dataKey="spending" stroke="#b86f52" strokeWidth={2} />
                        <Line type="monotone" dataKey="income" stroke="#55715f" strokeWidth={2} />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                )}
              </Card>

              <Card>
                <CardLabel>Top merchants</CardLabel>
                {merchants.length === 0 ? <p className="text-sm text-slate">No merchant spending found.</p> : (
                  <div className="h-72">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={merchants.slice(0, 8)}>
                        <XAxis dataKey="merchant_name" tick={{ fontSize: 10 }} interval={0} angle={-20} height={70} />
                        <YAxis tickFormatter={(v) => `$${v}`} tick={{ fontSize: 11 }} />
                        <Tooltip formatter={(value) => formatCurrency(Number(value))} />
                        <Bar dataKey="amount" fill="#c4974f" />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                )}
              </Card>

              <Card>
                <CardLabel>AI insights</CardLabel>
                {insights.length === 0 ? <p className="text-sm text-slate">No insights yet. Upload more history for better recommendations.</p> : (
                  <div className="space-y-3">
                    {insights.map((insight, i) => (
                      <div key={i} className="border border-line rounded-md p-3">
                        <p className="text-sm font-medium">{insight.title}</p>
                        <p className="text-sm text-slate mt-1">{insight.detail}</p>
                      </div>
                    ))}
                  </div>
                )}
              </Card>
            </div>
          </>
        )}
      </div>
    </>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <Card>
      <p className="text-xs text-slate uppercase tracking-wide">{label}</p>
      <p className="text-2xl font-display font-semibold mt-1">{value}</p>
    </Card>
  );
}
