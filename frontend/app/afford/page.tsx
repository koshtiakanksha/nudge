"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Tag, Wallet } from "lucide-react";
import { api } from "@/lib/api";
import { AffordabilityCheck } from "@/types/api";
import { formatCurrency, formatDate, cn } from "@/lib/format";
import { Card, CardLabel } from "@/components/card";
import { PageHeader } from "@/components/page-header";

const CATEGORIES = ["Dining", "Groceries", "Shopping", "Transportation", "Travel", "Entertainment", "Healthcare", "Utilities", "Savings", "Other"];

const VERDICT_STYLES: Record<string, string> = {
  "Safe to buy": "bg-moss/10 text-moss",
  "Buy with adjustment": "bg-gold/10 text-gold",
  Wait: "bg-gold/10 text-gold",
  "Not recommended": "bg-clay/10 text-clay",
  "Good deal, bad timing": "bg-gold/10 text-gold",
  "Good time to buy": "bg-moss/10 text-moss",
};

export default function AffordPage() {
  const [form, setForm] = useState({
    item_name: "",
    price: "",
    category: "Shopping",
    need_or_want: "want",
    purchase_date: new Date().toISOString().slice(0, 10),
    product_url: "",
    notes: "",
  });
  const [result, setResult] = useState<AffordabilityCheck | null>(null);
  const [history, setHistory] = useState<AffordabilityCheck[]>([]);
  const [checking, setChecking] = useState(false);
  const [watching, setWatching] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getAffordabilityHistory().then(setHistory).catch(() => setHistory([]));
  }, []);

  const check = async () => {
    setChecking(true);
    setError(null);
    try {
      const response = await api.checkAffordability({
        item_name: form.item_name || "Purchase",
        price: Number(form.price) || 0,
        category: form.category,
        need_or_want: form.need_or_want,
        purchase_date: form.purchase_date,
        product_url: form.product_url || null,
        notes: form.notes || null,
      });
      setResult(response);
      setHistory((prev) => [response, ...prev]);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not check affordability");
    } finally {
      setChecking(false);
    }
  };

  const createWatch = async () => {
    if (!form.product_url) return;
    setWatching(true);
    try {
      await api.createPriceWatch(form.product_url, Number(form.price) || undefined);
    } finally {
      setWatching(false);
    }
  };

  return (
    <>
      <PageHeader title="Can I Afford This?" subtitle="Get a plain-English spending verdict before you buy" />
      <div className="px-8 py-6 max-w-6xl grid grid-cols-1 lg:grid-cols-[1fr_380px] gap-6">
        <div className="space-y-5">
          <Card>
            <CardLabel>Purchase details</CardLabel>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <Field label="Item name" value={form.item_name} onChange={(item_name) => setForm({ ...form, item_name })} />
              <Field label="Price" value={form.price} type="number" onChange={(price) => setForm({ ...form, price })} />
              <label className="text-sm">
                <span className="block text-slate mb-1">Category</span>
                <select value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })} className="w-full border border-line rounded-md px-3 py-2">
                  {CATEGORIES.map((cat) => <option key={cat}>{cat}</option>)}
                </select>
              </label>
              <label className="text-sm">
                <span className="block text-slate mb-1">Need or want</span>
                <select value={form.need_or_want} onChange={(e) => setForm({ ...form, need_or_want: e.target.value })} className="w-full border border-line rounded-md px-3 py-2">
                  <option value="want">Want</option>
                  <option value="need">Need</option>
                </select>
              </label>
              <Field label="Purchase date" value={form.purchase_date} type="date" onChange={(purchase_date) => setForm({ ...form, purchase_date })} />
              <Field label="Product URL (optional)" value={form.product_url} onChange={(product_url) => setForm({ ...form, product_url })} />
              <label className="text-sm md:col-span-2">
                <span className="block text-slate mb-1">Notes (optional)</span>
                <textarea value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} className="w-full border border-line rounded-md px-3 py-2 min-h-20" />
              </label>
            </div>
            <button onClick={check} disabled={checking || !form.price} className="mt-4 px-4 py-2 bg-moss text-paper rounded-md text-sm font-medium disabled:opacity-60">
              {checking ? "Checking..." : "Check affordability"}
            </button>
            {error && <p className="text-sm text-clay mt-3">{error}</p>}
          </Card>

          {result && (
            <Card className="space-y-5">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <CardLabel>Verdict</CardLabel>
                  <p className={cn("inline-flex px-2.5 py-1 rounded-full text-sm font-medium", VERDICT_STYLES[result.verdict] || "bg-line text-ink")}>{result.verdict}</p>
                </div>
                <Wallet className="text-moss" />
              </div>
              <p className="text-lg font-medium">{result.explanation}</p>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <Mini label="Safe before" value={formatCurrency(result.safe_to_spend_before)} />
                <Mini label="Safe after" value={formatCurrency(result.safe_to_spend_after)} />
                <Mini label="Remaining before" value={formatCurrency(result.remaining_before)} />
                <Mini label="Remaining after" value={formatCurrency(result.remaining_after)} />
              </div>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-sm">
                <Card>
                  <CardLabel>Category impact</CardLabel>
                  <p>{result.category_impact.category}: {formatCurrency(result.category_impact.remaining_after ?? 0)} left after purchase</p>
                </Card>
                <Card>
                  <CardLabel>Forecast impact</CardLabel>
                  <p>Month-end moves to {formatCurrency(result.forecast_impact.after ?? 0)}</p>
                </Card>
                <Card>
                  <CardLabel>Bills risk</CardLabel>
                  <p className="capitalize">{result.upcoming_bill_risk}</p>
                </Card>
              </div>
              <div className="flex flex-wrap gap-3">
                {result.suggested_actions.includes("Create price watch") && form.product_url && (
                  <button onClick={createWatch} disabled={watching} className="px-3 py-2 border border-line rounded-md text-sm hover:bg-line/40 flex items-center gap-1.5">
                    <Tag size={14} /> {watching ? "Creating..." : "Create price watch"}
                  </button>
                )}
                <Link href="/budget" className="px-3 py-2 border border-line rounded-md text-sm hover:bg-line/40">Rebalance budget</Link>
                <Link href="/" className="px-3 py-2 border border-line rounded-md text-sm hover:bg-line/40">View forecast</Link>
                <Link href="/chat" className="px-3 py-2 border border-line rounded-md text-sm hover:bg-line/40">Ask Nudge</Link>
              </div>
            </Card>
          )}
        </div>

        <Card>
          <CardLabel>Recent checks</CardLabel>
          {history.length === 0 ? <p className="text-sm text-slate">No affordability checks yet.</p> : (
            <div className="space-y-3">
              {history.slice(0, 8).map((item) => (
                <div key={item.id || `${item.item_name}-${item.created_at}`} className="border border-line rounded-md p-3">
                  <div className="flex justify-between gap-3 text-sm">
                    <span className="font-medium">{item.item_name}</span>
                    <span>{formatCurrency(item.price)}</span>
                  </div>
                  <p className="text-xs text-slate mt-1">{item.verdict} · {item.created_at ? formatDate(item.created_at) : item.purchase_date}</p>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>
    </>
  );
}

function Field({ label, value, type = "text", onChange }: { label: string; value: string; type?: string; onChange: (value: string) => void }) {
  return (
    <label className="text-sm">
      <span className="block text-slate mb-1">{label}</span>
      <input type={type} value={value} onChange={(e) => onChange(e.target.value)} className="w-full border border-line rounded-md px-3 py-2" />
    </label>
  );
}

function Mini({ label, value }: { label: string; value: string }) {
  return (
    <div className="border border-line rounded-md p-3">
      <p className="text-xs text-slate">{label}</p>
      <p className="font-display text-xl font-semibold">{value}</p>
    </div>
  );
}
