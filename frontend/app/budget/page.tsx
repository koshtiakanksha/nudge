"use client";

import { useEffect, useMemo, useState } from "react";
import { AlertTriangle, CheckCircle2, Pencil, Plus, Save, Trash2 } from "lucide-react";
import { api } from "@/lib/api";
import { Budget, BudgetCategory } from "@/types/api";
import { formatCurrency, cn } from "@/lib/format";
import { Card, CardLabel } from "@/components/card";
import { PageHeader } from "@/components/page-header";

const DEFAULT_CATEGORIES = [
  "Rent",
  "Utilities",
  "Groceries",
  "Dining",
  "Transportation",
  "Shopping",
  "Travel",
  "Entertainment",
  "Savings",
  "Other",
];

const OPTIONAL_CATEGORY_QUESTIONS = ["Rent", "Utilities", "Groceries", "Dining", "Shopping", "Transportation"];

function emptyCategory(name = ""): BudgetCategory {
  return { name, allocated: 0, spent: 0, is_non_neg: false };
}

function categoriesFromBudget(budget: Budget): BudgetCategory[] {
  return Object.entries(budget.allocations).map(([name, allocation]) => ({ name, ...allocation }));
}

function statusFor(category: BudgetCategory) {
  if (category.allocated === 0 && category.spent > 0) return "over";
  if (category.allocated === 0) return "under";
  const ratio = category.spent / category.allocated;
  if (ratio > 1) return "over";
  if (ratio >= 0.85) return "near";
  return "under";
}

function parseAmount(value: string) {
  if (value.trim() === "") return 0;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? Math.max(parsed, 0) : 0;
}

export default function BudgetPage() {
  const [budget, setBudget] = useState<Budget | null>(null);
  const [monthlyIncome, setMonthlyIncome] = useState("");
  const [totalBudget, setTotalBudget] = useState("");
  const [categories, setCategories] = useState<BudgetCategory[]>([]);
  const [customCategory, setCustomCategory] = useState("");
  const [trackingCategories, setTrackingCategories] = useState(DEFAULT_CATEGORIES);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .getCurrentBudget()
      .then((result) => {
        setBudget(result);
        setMonthlyIncome(result.monthly_income?.toString() || "");
        setTotalBudget(result.total_budget?.toString() || result.total_allocated.toString());
        setCategories(categoriesFromBudget(result));
      })
      .catch(() => {
        setCategories(DEFAULT_CATEGORIES.map((name) => emptyCategory(name)));
      })
      .finally(() => setLoading(false));
  }, []);

  const totals = useMemo(() => {
    const allocated = categories.reduce((sum, c) => sum + (Number(c.allocated) || 0), 0);
    const spent = categories.reduce((sum, c) => sum + (Number(c.spent) || 0), 0);
    const income = parseAmount(monthlyIncome);
    const ceiling = parseAmount(totalBudget) || allocated;
    return { allocated, spent, remaining: allocated - spent, buffer: Math.max(income - ceiling, 0) };
  }, [categories, monthlyIncome, totalBudget]);

  const updateCategory = (index: number, patch: Partial<BudgetCategory>) => {
    setSaved(false);
    setCategories((prev) => prev.map((category, i) => (i === index ? { ...category, ...patch } : category)));
  };

  const addCategory = (name = "") => {
    setSaved(false);
    setCategories((prev) => [...prev, emptyCategory(name)]);
  };

  const addCustomCategory = () => {
    const name = customCategory.trim();
    if (!name) return;
    setTrackingCategories((prev) => Array.from(new Set([...prev, name])));
    addCategory(name);
    setCustomCategory("");
  };

  const removeCategory = (index: number) => {
    setSaved(false);
    setCategories((prev) => prev.filter((_, i) => i !== index));
  };

  const saveBudget = async () => {
    setSaving(true);
    setSaved(false);
    setError(null);
    try {
      const cleaned = categories
        .map((category) => ({ ...category, name: category.name.trim(), allocated: Number(category.allocated) || 0 }))
        .filter((category) => category.name);
      const result = await api.saveCurrentBudget({
        monthly_income: parseAmount(monthlyIncome),
        total_budget: parseAmount(totalBudget) || cleaned.reduce((sum, c) => sum + c.allocated, 0),
        categories: cleaned,
        ai_reasoning: budget?.ai_reasoning || "Created from your onboarding answers and edited by you.",
      });
      setBudget(result);
      setMonthlyIncome(result.monthly_income?.toString() || monthlyIncome);
      setTotalBudget(result.total_budget?.toString() || totalBudget);
      setCategories(categoriesFromBudget(result));
      setSaved(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not save budget");
    } finally {
      setSaving(false);
    }
  };

  return (
    <>
      <PageHeader title="Budget" subtitle="Create, edit, and adjust your monthly plan whenever life changes" />

      <div className="px-8 py-6 max-w-5xl space-y-6">
        {loading ? (
          <p className="text-sm text-slate">Loading budget…</p>
        ) : (
          <>
            {!budget && (
              <Card className="bg-moss/5 border-moss/20">
                <div className="flex items-start gap-3">
                  <Pencil className="text-moss mt-0.5" size={20} />
                  <div>
                    <p className="font-medium text-ink">Build your first budget</p>
                    <p className="text-sm text-slate mt-1">
                      Answer what you know, skip what you do not, then review and edit every category before saving.
                    </p>
                  </div>
                </div>
              </Card>
            )}

            <div className="grid grid-cols-1 lg:grid-cols-[1fr_320px] gap-5">
              <div className="space-y-5">
                <Card>
                  <CardLabel>Monthly basics</CardLabel>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    <label className="text-sm">
                      <span className="block text-slate mb-1">Monthly income</span>
                      <input
                        type="number"
                        min="0"
                        value={monthlyIncome}
                        onChange={(e) => {
                          setSaved(false);
                          setMonthlyIncome(e.target.value);
                        }}
                        className="w-full border border-line rounded-md px-3 py-2 text-sm"
                      />
                    </label>
                    <label className="text-sm">
                      <span className="block text-slate mb-1">Total monthly budget</span>
                      <input
                        type="number"
                        min="0"
                        value={totalBudget}
                        onChange={(e) => {
                          setSaved(false);
                          setTotalBudget(e.target.value);
                        }}
                        className="w-full border border-line rounded-md px-3 py-2 text-sm"
                      />
                    </label>
                  </div>
                </Card>

                {!budget && (
                  <Card>
                    <CardLabel>Spending questions</CardLabel>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      {OPTIONAL_CATEGORY_QUESTIONS.map((name) => {
                        const index = categories.findIndex((category) => category.name === name);
                        return (
                          <label key={name} className="text-sm">
                            <span className="block text-slate mb-1">Usual {name.toLowerCase()} spend</span>
                            <input
                              type="number"
                              min="0"
                              value={index >= 0 ? categories[index].allocated || "" : ""}
                              onChange={(e) => {
                                if (index >= 0) updateCategory(index, { allocated: parseAmount(e.target.value) });
                              }}
                              className="w-full border border-line rounded-md px-3 py-2 text-sm"
                            />
                          </label>
                        );
                      })}
                    </div>
                    <div className="mt-4">
                      <CardLabel>Categories to track</CardLabel>
                      <div className="flex flex-wrap gap-2">
                        {trackingCategories.map((name) => {
                          const checked = categories.some((category) => category.name === name);
                          return (
                            <label key={name} className="inline-flex items-center gap-2 text-xs border border-line rounded-md px-2.5 py-1.5">
                              <input
                                type="checkbox"
                                checked={checked}
                                onChange={(e) => {
                                  if (e.target.checked) addCategory(name);
                                  else setCategories((prev) => prev.filter((category) => category.name !== name));
                                }}
                              />
                              {name}
                            </label>
                          );
                        })}
                      </div>
                      <div className="flex gap-2 mt-3">
                        <input
                          value={customCategory}
                          onChange={(e) => setCustomCategory(e.target.value)}
                          placeholder="Custom category"
                          className="flex-1 border border-line rounded-md px-3 py-2 text-sm"
                        />
                        <button onClick={addCustomCategory} className="px-3 py-2 border border-line rounded-md text-sm hover:bg-line/40">
                          Add
                        </button>
                      </div>
                    </div>
                  </Card>
                )}

                <Card padded={false}>
                  <div className="p-4 border-b border-line/60 flex items-center justify-between gap-3">
                    <div>
                      <CardLabel>Review categories</CardLabel>
                      <p className="text-xs text-slate">Rename, remove, add, or set any category to $0.</p>
                    </div>
                    <button onClick={() => addCategory()} className="px-3 py-2 border border-line rounded-md text-sm hover:bg-line/40 flex items-center gap-1.5">
                      <Plus size={15} /> Category
                    </button>
                  </div>
                  {categories.length === 0 ? (
                    <p className="p-4 text-sm text-slate">No budget categories added yet.</p>
                  ) : (
                    categories.map((category, index) => {
                      const status = statusFor(category);
                      const remaining = category.allocated - category.spent;
                      const pct = category.allocated > 0 ? Math.min(category.spent / category.allocated, 1) : category.spent > 0 ? 1 : 0;
                      return (
                        <div key={`${category.name}-${index}`} className={cn("p-4", index !== categories.length - 1 && "border-b border-line/60")}>
                          <div className="grid grid-cols-1 md:grid-cols-[1fr_120px_120px_36px] gap-3 items-end">
                            <label className="text-sm">
                              <span className="block text-slate mb-1">Category</span>
                              <input
                                value={category.name}
                                onChange={(e) => updateCategory(index, { name: e.target.value })}
                                className="w-full border border-line rounded-md px-3 py-2 text-sm"
                              />
                            </label>
                            <label className="text-sm">
                              <span className="block text-slate mb-1">Budgeted</span>
                              <input
                                type="number"
                                min="0"
                                value={category.allocated}
                                onChange={(e) => updateCategory(index, { allocated: parseAmount(e.target.value) })}
                                className="w-full border border-line rounded-md px-3 py-2 text-sm"
                              />
                            </label>
                            <div className="text-sm">
                              <span className="block text-slate mb-1">Actual spent</span>
                              <p className="border border-line rounded-md px-3 py-2 bg-paper/60">{formatCurrency(category.spent)}</p>
                            </div>
                            <button
                              onClick={() => removeCategory(index)}
                              className="h-9 rounded-md text-clay hover:bg-clay/10 flex items-center justify-center"
                              title="Delete category"
                            >
                              <Trash2 size={16} />
                            </button>
                          </div>
                          <div className="mt-3">
                            <div className="h-1.5 rounded-full bg-line overflow-hidden">
                              <div
                                className={cn("h-full rounded-full", status === "over" ? "bg-clay" : status === "near" ? "bg-gold" : "bg-moss")}
                                style={{ width: `${pct * 100}%` }}
                              />
                            </div>
                            <div className="flex flex-wrap items-center justify-between gap-2 mt-2 text-xs">
                              <span
                                className={cn(
                                  "px-2 py-0.5 rounded-full font-medium",
                                  status === "over" ? "bg-clay/10 text-clay" : status === "near" ? "bg-gold/10 text-gold" : "bg-moss/10 text-moss"
                                )}
                              >
                                {status === "over" ? "Over budget" : status === "near" ? "Near limit" : "Under budget"}
                              </span>
                              <span className={cn(remaining < 0 ? "text-clay" : "text-slate")}>
                                {remaining < 0
                                  ? `You are ${formatCurrency(Math.abs(remaining))} over your ${category.name || "category"} budget.`
                                  : `${formatCurrency(remaining)} remaining`}
                              </span>
                            </div>
                          </div>
                        </div>
                      );
                    })
                  )}
                </Card>
              </div>

              <div className="space-y-5">
                <Card className="sticky top-6">
                  <CardLabel>Updated totals</CardLabel>
                  <div className="space-y-3 text-sm">
                    <div className="flex justify-between"><span className="text-slate">Budgeted</span><strong>{formatCurrency(totals.allocated)}</strong></div>
                    <div className="flex justify-between"><span className="text-slate">Actual spent</span><strong>{formatCurrency(totals.spent)}</strong></div>
                    <div className="flex justify-between"><span className="text-slate">Remaining</span><strong className={totals.remaining < 0 ? "text-clay" : "text-moss"}>{formatCurrency(totals.remaining)}</strong></div>
                    <div className="flex justify-between"><span className="text-slate">Buffer</span><strong>{formatCurrency(totals.buffer)}</strong></div>
                  </div>
                  {totals.remaining < 0 && (
                    <p className="mt-4 text-xs text-clay flex gap-2">
                      <AlertTriangle size={14} className="shrink-0" />
                      You are over your total category budget, but you can still save this plan.
                    </p>
                  )}
                  <button
                    onClick={saveBudget}
                    disabled={saving}
                    className="mt-5 w-full px-4 py-2 bg-moss text-paper rounded-md text-sm font-medium hover:bg-moss2 transition-colors disabled:opacity-60 flex items-center justify-center gap-1.5"
                  >
                    <Save size={15} /> {saving ? "Saving…" : "Save budget"}
                  </button>
                  {saved && <p className="mt-3 text-sm text-moss flex items-center gap-1.5"><CheckCircle2 size={15} /> Saved.</p>}
                  {error && <p className="mt-3 text-sm text-clay">{error}</p>}
                </Card>
              </div>
            </div>
          </>
        )}
      </div>
    </>
  );
}
