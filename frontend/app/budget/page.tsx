"use client";

import { useEffect, useState } from "react";
import { Sparkles } from "lucide-react";
import { api } from "@/lib/api";
import { Budget } from "@/types/api";
import { formatCurrency, cn } from "@/lib/format";
import { Card, CardLabel } from "@/components/card";
import { PageHeader } from "@/components/page-header";

export default function BudgetPage() {
  const [budget, setBudget] = useState<Budget | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .getCurrentBudget()
      .then(setBudget)
      .catch(() => setBudget(null))
      .finally(() => setLoading(false));
  }, []);

  const handleGenerate = async (regenerate: boolean) => {
    setGenerating(true);
    setError(null);
    try {
      const result = await api.generateBudget(regenerate);
      setBudget(result);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not generate budget");
    } finally {
      setGenerating(false);
    }
  };

  const handleAdjust = async (category: string, newAmount: number) => {
    const updated = await api.adjustBudget(category, newAmount);
    setBudget(updated);
  };

  return (
    <>
      <PageHeader title="Budget" subtitle="An AI-built plan based on how you actually spend" />

      <div className="px-8 py-6 max-w-3xl">
        {loading ? (
          <p className="text-sm text-slate">Loading…</p>
        ) : !budget ? (
          <Card className="text-center py-10">
            <Sparkles className="mx-auto text-gold mb-3" size={28} />
            <p className="text-ink font-medium mb-1">No budget yet for this month</p>
            <p className="text-sm text-slate mb-5">
              Nudge will look at your last 3 months of spending and build a plan that protects your essentials.
            </p>
            <button
              onClick={() => handleGenerate(false)}
              disabled={generating}
              className="px-5 py-2 bg-moss text-paper rounded-md text-sm font-medium hover:bg-moss2 transition-colors disabled:opacity-60"
            >
              {generating ? "Building your budget…" : "Generate my budget"}
            </button>
            {error && <p className="text-clay text-sm mt-3">{error}</p>}
          </Card>
        ) : (
          <div className="space-y-5">
            <Card className="bg-moss/5 border-moss/20">
              <CardLabel>Why this allocation</CardLabel>
              <p className="text-sm text-ink leading-relaxed">{budget.ai_reasoning}</p>
            </Card>

            <div className="flex justify-between items-baseline">
              <div>
                <p className="text-xs text-slate uppercase tracking-wide">Total allocated</p>
                <p className="text-2xl font-display font-semibold">{formatCurrency(budget.total_allocated)}</p>
              </div>
              <div className="text-right">
                <p className="text-xs text-slate uppercase tracking-wide">Buffer reserved</p>
                <p className="text-2xl font-display font-semibold text-moss">
                  {formatCurrency(budget.buffer_reserved)}
                </p>
              </div>
              <button
                onClick={() => handleGenerate(true)}
                disabled={generating}
                className="px-3 py-1.5 border border-line rounded-md text-xs hover:bg-line/40 transition-colors"
              >
                Regenerate
              </button>
            </div>

            <Card padded={false}>
              {Object.entries(budget.allocations).map(([category, alloc], i) => {
                const pct = alloc.allocated > 0 ? Math.min(1, alloc.spent / alloc.allocated) : 0;
                return (
                  <div
                    key={category}
                    className={cn("p-4", i !== Object.keys(budget.allocations).length - 1 && "border-b border-line/60")}
                  >
                    <div className="flex justify-between items-center mb-2">
                      <span className="text-sm font-medium flex items-center gap-2">
                        {category}
                        {alloc.is_non_neg && (
                          <span className="text-[10px] uppercase bg-clay/10 text-clay px-1.5 py-0.5 rounded-sm">
                            essential
                          </span>
                        )}
                      </span>
                      <div className="flex items-center gap-2">
                        <span className="text-sm text-slate">{formatCurrency(alloc.spent)} of</span>
                        <input
                          type="number"
                          defaultValue={alloc.allocated}
                          onBlur={(e) => {
                            const val = parseFloat(e.target.value);
                            if (!isNaN(val) && val !== alloc.allocated) handleAdjust(category, val);
                          }}
                          className="w-20 text-sm font-mono text-right border border-line rounded-sm px-1.5 py-0.5"
                        />
                      </div>
                    </div>
                    <div className="h-1.5 rounded-full bg-line overflow-hidden">
                      <div
                        className={cn("h-full rounded-full", pct >= 1 ? "bg-clay" : "bg-moss")}
                        style={{ width: `${pct * 100}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </Card>
          </div>
        )}
      </div>
    </>
  );
}
