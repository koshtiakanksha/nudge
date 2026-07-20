"use client";

import { useEffect, useState } from "react";
import { Sliders, TrendingUp, TrendingDown, AlertTriangle } from "lucide-react";
import { api } from "@/lib/api";
import { BudgetCategoryRecord, ScenarioRequest, ScenarioResult } from "@/types/api";
import { formatCurrency, cn } from "@/lib/format";
import { Card, CardLabel } from "@/components/card";
import { PageHeader } from "@/components/page-header";

type ScenarioType = ScenarioRequest["scenario_type"];

const SCENARIO_TABS: { type: ScenarioType; label: string }[] = [
  { type: "category_change", label: "Category change" },
  { type: "income_change", label: "Income change" },
  { type: "one_time_expense", label: "One-time expense" },
];

const RISK_STYLES: Record<ScenarioResult["risk_level"], string> = {
  none: "bg-moss/10 text-moss",
  tight: "bg-gold/10 text-gold",
  over_budget: "bg-clay/10 text-clay",
};

const RISK_LABELS: Record<ScenarioResult["risk_level"], string> = {
  none: "No new risk",
  tight: "Getting tight",
  over_budget: "Over budget",
};

export default function ScenariosPage() {
  const [scenarioType, setScenarioType] = useState<ScenarioType>("category_change");
  const [categories, setCategories] = useState<BudgetCategoryRecord[]>([]);
  const [category, setCategory] = useState("");
  const [newAmount, setNewAmount] = useState("");
  const [newIncome, setNewIncome] = useState("");
  const [expenseAmount, setExpenseAmount] = useState("");
  const [result, setResult] = useState<ScenarioResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.listBudgetCategories()
      .then((cats) => {
        setCategories(cats);
        if (cats.length > 0) setCategory(cats[0].name);
      })
      .catch(() => {});
  }, []);

  const run = async () => {
    setLoading(true);
    setError(null);
    try {
      let payload: ScenarioRequest;
      if (scenarioType === "category_change") {
        if (!category || newAmount === "") {
          setError("Pick a category and enter a new monthly amount.");
          setLoading(false);
          return;
        }
        payload = { scenario_type: "category_change", category, new_amount: Number(newAmount) };
      } else if (scenarioType === "income_change") {
        if (newIncome === "") {
          setError("Enter a new monthly income.");
          setLoading(false);
          return;
        }
        payload = { scenario_type: "income_change", new_income_estimate: Number(newIncome) };
      } else {
        if (expenseAmount === "") {
          setError("Enter the unexpected expense amount.");
          setLoading(false);
          return;
        }
        payload = { scenario_type: "one_time_expense", amount: Number(expenseAmount) };
      }
      setResult(await api.simulateScenario(payload));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Simulation failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <PageHeader title="What If" subtitle="Simulate a change and see how it ripples through your budget before it happens" />
      <div className="px-8 py-6 max-w-5xl space-y-6">
        <Card>
          <div className="flex gap-2 mb-5">
            {SCENARIO_TABS.map((tab) => (
              <button
                key={tab.type}
                onClick={() => { setScenarioType(tab.type); setResult(null); setError(null); }}
                className={cn(
                  "px-3 py-1.5 rounded-md text-sm font-medium",
                  scenarioType === tab.type ? "bg-ink text-paper" : "bg-line/40 text-slate"
                )}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {scenarioType === "category_change" && (
            <div className="flex items-end gap-4">
              <label className="text-sm flex-1">
                <span className="block text-slate mb-1">Category</span>
                <select value={category} onChange={(e) => setCategory(e.target.value)} className="w-full border border-line rounded-md px-3 py-2">
                  {categories.map((c) => <option key={c.id} value={c.name}>{c.name}</option>)}
                </select>
              </label>
              <label className="text-sm flex-1">
                <span className="block text-slate mb-1">New monthly amount</span>
                <input type="number" min="0" value={newAmount} onChange={(e) => setNewAmount(e.target.value)} placeholder="e.g. 1200" className="w-full border border-line rounded-md px-3 py-2" />
              </label>
            </div>
          )}

          {scenarioType === "income_change" && (
            <label className="text-sm block max-w-xs">
              <span className="block text-slate mb-1">New monthly income</span>
              <input type="number" min="0" value={newIncome} onChange={(e) => setNewIncome(e.target.value)} placeholder="e.g. 4200" className="w-full border border-line rounded-md px-3 py-2" />
            </label>
          )}

          {scenarioType === "one_time_expense" && (
            <label className="text-sm block max-w-xs">
              <span className="block text-slate mb-1">Unexpected expense amount</span>
              <input type="number" min="0" value={expenseAmount} onChange={(e) => setExpenseAmount(e.target.value)} placeholder="e.g. 400" className="w-full border border-line rounded-md px-3 py-2" />
            </label>
          )}

          <button onClick={run} disabled={loading} className="mt-5 px-4 py-2 bg-moss text-paper rounded-md text-sm font-medium flex items-center gap-1.5 disabled:opacity-60">
            <Sliders size={15} /> {loading ? "Simulating..." : "Run simulation"}
          </button>
        </Card>

        {error && <Card><p className="text-sm text-clay">{error}</p></Card>}

        {result && (
          <>
            <Card className={cn(result.risk_level !== "none" && "bg-clay/5 border-clay/20")}>
              <div className="flex items-start justify-between gap-4">
                <div>
                  <CardLabel>Result</CardLabel>
                  <p className="text-sm text-ink">{result.summary}</p>
                </div>
                <span className={cn("text-xs px-2 py-1 rounded-full font-medium flex items-center gap-1 shrink-0", RISK_STYLES[result.risk_level])}>
                  <AlertTriangle size={12} /> {RISK_LABELS[result.risk_level]}
                </span>
              </div>
              <div className="grid grid-cols-2 gap-6 mt-4 pt-4 border-t border-line">
                <div>
                  <p className="text-xs text-slate">Spendable before</p>
                  <p className="text-xl font-display font-semibold">{formatCurrency(result.spendable_before)}</p>
                </div>
                <div>
                  <p className="text-xs text-slate">Spendable after</p>
                  <p className="text-xl font-display font-semibold">{formatCurrency(result.spendable_after)}</p>
                </div>
              </div>
            </Card>

            <Card>
              <CardLabel>What changes</CardLabel>
              {result.changes.length === 0 ? (
                <p className="text-sm text-slate">No category allocations changed.</p>
              ) : (
                <div className="space-y-2">
                  {result.changes.map((c) => (
                    <div key={c.category} className="flex items-center justify-between py-2 border-b border-line last:border-0">
                      <div className="flex items-center gap-2">
                        {c.delta > 0 ? <TrendingUp size={14} className="text-moss" /> : <TrendingDown size={14} className="text-clay" />}
                        <span className="text-sm text-ink">{c.category}</span>
                      </div>
                      <div className="text-sm text-slate">
                        {formatCurrency(c.previous_amount)} → <span className="text-ink font-medium">{formatCurrency(c.current_amount)}</span>
                        <span className={cn("ml-2", c.delta > 0 ? "text-moss" : "text-clay")}>
                          ({c.delta > 0 ? "+" : ""}{formatCurrency(c.delta)})
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </Card>
          </>
        )}
      </div>
    </>
  );
}
