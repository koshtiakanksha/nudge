"use client";

import { useEffect, useState } from "react";
import { AlertTriangle, ArrowDownRight, ArrowUpRight, Tag } from "lucide-react";
import { api } from "@/lib/api";
import { DashboardSummary } from "@/types/api";
import { formatCurrency } from "@/lib/format";
import { Card, CardLabel } from "@/components/card";
import { PageHeader } from "@/components/page-header";
import { BufferRing } from "@/components/buffer-ring";

export default function OverviewPage() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .getDashboardSummary()
      .then(setSummary)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <>
        <PageHeader title="Overview" subtitle="Where your money stands this month" />
        <div className="px-8 py-12 text-slate text-sm">Loading your numbers…</div>
      </>
    );
  }

  if (error || !summary) {
    return (
      <>
        <PageHeader title="Overview" subtitle="Where your money stands this month" />
        <div className="px-8 py-12">
          <Card className="border-clay/40 bg-clay/5">
            <p className="text-clay text-sm">
              Couldn&apos;t load your dashboard ({error || "no data"}). Make sure the backend is running and you&apos;ve
              completed onboarding under Settings.
            </p>
          </Card>
        </div>
      </>
    );
  }

  const ceilingPct = summary.spend_ceiling
    ? Math.min(1, summary.month_to_date_spend / summary.spend_ceiling)
    : null;

  return (
    <>
      <PageHeader title="Overview" subtitle="Where your money stands this month" />

      <div className="px-8 py-8 space-y-6 max-w-5xl">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
          <Card className="flex flex-col items-center justify-center md:col-span-1">
            <BufferRing status={summary.buffer_status} />
          </Card>

          <Card className="md:col-span-2">
            <CardLabel>Month to date</CardLabel>
            <div className="flex items-end gap-6 mt-1">
              <div>
                <p className="text-3xl font-display font-semibold">{formatCurrency(summary.month_to_date_spend)}</p>
                <p className="text-xs text-slate mt-1 flex items-center gap-1">
                  <ArrowDownRight size={13} className="text-clay" />
                  spent
                </p>
              </div>
              <div>
                <p className="text-3xl font-display font-semibold text-moss">
                  {formatCurrency(summary.month_to_date_income)}
                </p>
                <p className="text-xs text-slate mt-1 flex items-center gap-1">
                  <ArrowUpRight size={13} className="text-moss" />
                  income
                </p>
              </div>
            </div>

            {summary.spend_ceiling && (
              <div className="mt-5">
                <div className="flex justify-between text-xs text-slate mb-1.5">
                  <span>Spend ceiling</span>
                  <span>{formatCurrency(summary.spend_ceiling)}</span>
                </div>
                <div className="h-2 rounded-full bg-line overflow-hidden">
                  <div
                    className="h-full rounded-full bg-moss"
                    style={{ width: `${(ceilingPct ?? 0) * 100}%` }}
                  />
                </div>
                <p className="text-xs text-slate mt-2">
                  Projected month-end: <strong className="text-ink">{formatCurrency(summary.projected_month_end)}</strong>
                </p>
              </div>
            )}
          </Card>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          <Card>
            <CardLabel>Top categories</CardLabel>
            <div className="space-y-2.5 mt-2">
              {summary.top_categories.length === 0 && (
                <p className="text-sm text-slate">No spending yet this month.</p>
              )}
              {summary.top_categories.map((c) => (
                <div key={c.category} className="flex justify-between items-center text-sm">
                  <span>{c.category}</span>
                  <span className="font-mono text-ink">{formatCurrency(c.amount)}</span>
                </div>
              ))}
            </div>
          </Card>

          <div className="space-y-5">
            <Card className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-full bg-clay/10 flex items-center justify-center shrink-0">
                <AlertTriangle size={17} className="text-clay" />
              </div>
              <div>
                <p className="text-sm font-medium">{summary.recent_anomalies} unusual charges</p>
                <p className="text-xs text-slate">flagged for review this period</p>
              </div>
            </Card>

            <Card className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-full bg-gold/10 flex items-center justify-center shrink-0">
                <Tag size={17} className="text-gold" />
              </div>
              <div>
                <p className="text-sm font-medium">{summary.active_price_watches} active price watches</p>
                <p className="text-xs text-slate">tracking for a better deal</p>
              </div>
            </Card>
          </div>
        </div>
      </div>
    </>
  );
}
