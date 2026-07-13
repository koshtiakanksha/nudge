"use client";

import { useState } from "react";
import { Sparkles, Save } from "lucide-react";
import { api } from "@/lib/api";
import { BudgetRecommendation, SmartBudget } from "@/types/api";
import { Card, CardLabel } from "@/components/card";
import { PageHeader } from "@/components/page-header";
import { formatCurrency } from "@/lib/format";

export default function SmartBudgetPage() {
  const [budget, setBudget] = useState<SmartBudget | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const generate = async () => {
    setLoading(true);
    setError(null);
    setMessage(null);
    try {
      setBudget(await api.generateBudgetFromHistory());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Budget generation failed");
    } finally {
      setLoading(false);
    }
  };

  const updateRecommendation = (index: number, patch: Partial<BudgetRecommendation>) => {
    setBudget((prev) => prev ? {
      ...prev,
      recommendations: prev.recommendations.map((rec, i) => i === index ? { ...rec, ...patch } : rec),
    } : prev);
  };

  const save = async () => {
    if (!budget) return;
    setSaving(true);
    setError(null);
    try {
      await api.saveGeneratedBudget({
        month: budget.month,
        income_estimate: budget.income_estimate,
        total_budget: budget.recommendations.reduce((sum, rec) => sum + rec.recommended_amount, 0),
        recommendations: budget.recommendations,
      });
      setMessage("Budget generated successfully and saved.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not save budget");
    } finally {
      setSaving(false);
    }
  };

  const total = budget?.recommendations.reduce((sum, rec) => sum + rec.recommended_amount, 0) || 0;

  return (
    <>
      <PageHeader title="AI Budget Builder" subtitle="Generate an editable budget from uploaded statement history" />
      <div className="px-8 py-6 max-w-5xl space-y-6">
        <Card className="bg-moss/5 border-moss/20">
          <div className="flex items-start justify-between gap-4">
            <div>
              <CardLabel>Smart budget generation</CardLabel>
              <p className="text-sm text-ink">Uses uploaded statement history, recurring expenses, income, and unusual spending exclusions. It will tell you when there is not enough history instead of pretending.</p>
            </div>
            <button onClick={generate} disabled={loading} className="px-4 py-2 bg-moss text-paper rounded-md text-sm font-medium flex items-center gap-1.5 disabled:opacity-60">
              <Sparkles size={15} /> {loading ? "Generating..." : "Generate"}
            </button>
          </div>
        </Card>

        {error && <Card><p className="text-sm text-clay">{error}</p></Card>}
        {message && <Card><p className="text-sm text-moss">{message}</p></Card>}

        {!budget ? (
          <Card><p className="text-sm text-slate">No generated budget yet. Upload and review statements, then generate a recommendation.</p></Card>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-[1fr_300px] gap-5">
            <Card padded={false}>
              <div className="p-4 border-b border-line/60">
                <CardLabel>Suggested category limits</CardLabel>
                <p className="text-sm text-slate">{budget.explanation}</p>
              </div>
              {budget.recommendations.map((rec, i) => (
                <div key={`${rec.category}-${i}`} className="p-4 border-b border-line/60 last:border-b-0">
                  <div className="grid grid-cols-1 md:grid-cols-[1fr_150px] gap-3">
                    <label className="text-sm">
                      <span className="block text-slate mb-1">Category</span>
                      <input value={rec.category} onChange={(e) => updateRecommendation(i, { category: e.target.value })} className="w-full border border-line rounded-md px-3 py-2" />
                    </label>
                    <label className="text-sm">
                      <span className="block text-slate mb-1">Amount</span>
                      <input type="number" min="0" value={rec.recommended_amount} onChange={(e) => updateRecommendation(i, { recommended_amount: Number(e.target.value) || 0 })} className="w-full border border-line rounded-md px-3 py-2" />
                    </label>
                  </div>
                  <p className="text-xs text-slate mt-2">{rec.reasoning}</p>
                </div>
              ))}
            </Card>

            <div className="space-y-5">
              <Card>
                <CardLabel>Budget total</CardLabel>
                <p className="text-3xl font-display font-semibold">{formatCurrency(total)}</p>
                <p className="text-sm text-slate mt-2">Income estimate: {formatCurrency(budget.income_estimate)}</p>
                <button onClick={save} disabled={saving} className="mt-5 w-full px-4 py-2 bg-moss text-paper rounded-md text-sm font-medium flex items-center justify-center gap-1.5 disabled:opacity-60">
                  <Save size={15} /> {saving ? "Saving..." : "Save budget"}
                </button>
              </Card>
              {budget.warnings.length > 0 && (
                <Card className="bg-gold/5 border-gold/20">
                  <CardLabel>Warnings</CardLabel>
                  <div className="space-y-2">
                    {budget.warnings.map((warning, i) => <p key={i} className="text-sm text-ink">{warning}</p>)}
                  </div>
                </Card>
              )}
            </div>
          </div>
        )}
      </div>
    </>
  );
}
