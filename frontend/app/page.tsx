"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { AlertTriangle, ArrowRight, CheckCircle2, Receipt, Wallet } from "lucide-react";
import { Bar, BarChart, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "@/lib/api";
import { TodaySummary, DashboardSummary } from "@/types/api";
import { formatCurrency } from "@/lib/format";
import { Card, CardLabel } from "@/components/card";
import { PageHeader } from "@/components/page-header";

const CATEGORY_COLORS = ["#2F5D50", "#C1622D", "#B8923F", "#4A7A8C", "#5B6760"];

export default function TodayPage() {
  const [today, setToday] = useState<TodaySummary | null>(null);
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .getToday()
      .then(setToday)
      .catch((e) => setError(e instanceof Error ? e.message : "Could not load Today"))
      .finally(() => setLoading(false));
    api.getDashboardSummary().then(setSummary).catch(() => {});
  }, []);

  return (
    <>
      <PageHeader title="Today" subtitle="Your spending decision center" />
      <div className="px-8 py-8 max-w-5xl space-y-6">
        {loading ? (
          <p className="text-sm text-slate">Calculating today&apos;s safe-to-spend amount...</p>
        ) : error ? (
          <Card className="border-clay/40 bg-clay/5">
            <p className="text-sm text-clay">{error}. Make sure the backend is running.</p>
          </Card>
        ) : today && !today.can_calculate ? (
          <Card className="text-center py-10">
            <Wallet className="mx-auto text-slate mb-3" size={28} />
            {today.has_linked_data ? (
              <>
                <p className="text-lg font-display font-semibold">
                  Your account is connected. Set your monthly income or spend ceiling to calculate your safe-to-spend amount.
                </p>
                <div className="flex justify-center gap-3 mt-5">
                  <Link href="/settings" className="px-4 py-2 bg-moss text-paper rounded-md text-sm">Go to Settings</Link>
                </div>
              </>
            ) : (
              <>
                <p className="text-lg font-display font-semibold">Connect a bank account or upload a statement to calculate your safe-to-spend amount.</p>
                <div className="flex justify-center gap-3 mt-5">
                  <Link href="/transactions" className="px-4 py-2 bg-moss text-paper rounded-md text-sm">Connect bank</Link>
                  <Link href="/statements" className="px-4 py-2 border border-line rounded-md text-sm">Upload statement</Link>
                </div>
              </>
            )}
          </Card>
        ) : today ? (
          <>
            <Card className="bg-moss/5 border-moss/20">
              <CardLabel>Safe to spend today</CardLabel>
              <p className="text-4xl font-display font-semibold text-moss">{formatCurrency(today.safe_to_spend_today)}</p>
              <p className="text-lg text-ink mt-2">{today.safe_to_spend_message}</p>
              <Link href="/afford" className="inline-flex items-center gap-1.5 mt-4 text-sm text-moss hover:underline">
                Check a purchase <ArrowRight size={14} />
              </Link>
            </Card>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
              <Metric label="Spent this month" value={formatCurrency(today.month_to_date_spending)} />
              <Metric label="Forecast month-end" value={formatCurrency(today.month_end_forecast)} />
              <Metric label="Spending ceiling" value={today.spending_ceiling ? formatCurrency(today.spending_ceiling) : "Not set"} />
              <Metric label="Bills still coming" value={formatCurrency(today.upcoming_bills_total)} icon={<Receipt size={17} />} />
              <Metric label="Budget health" value={today.budget_health} icon={today.budget_health === "On track" ? <CheckCircle2 size={17} /> : <AlertTriangle size={17} />} />
              <Metric label="Top risk category" value={today.top_risk_category || "None yet"} />
            </div>

            <Card>
              <CardLabel>Recommended action</CardLabel>
              <p className="text-lg font-medium">{today.recommended_action}</p>
              <div className="flex flex-wrap gap-3 mt-4">
                <Link href="/budget" className="px-3 py-2 border border-line rounded-md text-sm hover:bg-line/40">View budget</Link>
                <Link href="/forecast" className="px-3 py-2 border border-line rounded-md text-sm hover:bg-line/40">View forecast</Link>
                <Link href="/chat" className="px-3 py-2 border border-line rounded-md text-sm hover:bg-line/40">Ask Nudge</Link>
              </div>
            </Card>

            {summary && summary.top_categories.length > 0 && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                <Card>
                  <CardLabel>Spending by category this month</CardLabel>
                  <div className="h-56 mt-2">
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie
                          data={summary.top_categories}
                          dataKey="amount"
                          nameKey="category"
                          cx="50%"
                          cy="50%"
                          innerRadius={45}
                          outerRadius={80}
                          paddingAngle={2}
                        >
                          {summary.top_categories.map((_, i) => (
                            <Cell key={i} fill={CATEGORY_COLORS[i % CATEGORY_COLORS.length]} />
                          ))}
                        </Pie>
                        <Tooltip formatter={(value: number) => formatCurrency(value)} />
                      </PieChart>
                    </ResponsiveContainer>
                  </div>
                  <div className="flex flex-wrap gap-x-4 gap-y-1.5 mt-2">
                    {summary.top_categories.map((c, i) => (
                      <div key={c.category} className="flex items-center gap-1.5 text-xs text-slate">
                        <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: CATEGORY_COLORS[i % CATEGORY_COLORS.length] }} />
                        {c.category} · {formatCurrency(c.amount)}
                      </div>
                    ))}
                  </div>
                </Card>

                {summary.daily_trend.length > 0 && (
                  <Card>
                    <CardLabel>Daily spend, last 30 days</CardLabel>
                    <div className="h-56 mt-2">
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={summary.daily_trend}>
                          <CartesianGrid strokeDasharray="3 3" stroke="#DDD6C5" vertical={false} />
                          <XAxis dataKey="date" tick={{ fontSize: 11 }} tickFormatter={(d) => d.slice(5)} />
                          <YAxis tick={{ fontSize: 11 }} />
                          <Tooltip formatter={(value: number) => formatCurrency(value)} />
                          <Bar dataKey="amount" fill="#2F5D50" radius={[3, 3, 0, 0]} />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  </Card>
                )}
              </div>
            )}
          </>
        ) : null}
      </div>
    </>
  );
}

function Metric({ label, value, icon }: { label: string; value: string; icon?: React.ReactNode }) {
  return (
    <Card>
      <div className="flex items-center justify-between">
        <p className="text-xs text-slate uppercase tracking-wide">{label}</p>
        {icon}
      </div>
      <p className="text-2xl font-display font-semibold mt-2">{value}</p>
    </Card>
  );
}
