"use client";

import { useEffect, useState } from "react";
import { Repeat } from "lucide-react";
import { api } from "@/lib/api";
import { RecurringExpense } from "@/types/api";
import { Card, CardLabel } from "@/components/card";
import { PageHeader } from "@/components/page-header";
import { formatCurrency, formatDate } from "@/lib/format";

export default function RecurringPage() {
  const [items, setItems] = useState<RecurringExpense[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .getRecurringExpenses()
      .then(setItems)
      .catch((e) => setError(e instanceof Error ? e.message : "Could not load recurring expenses"))
      .finally(() => setLoading(false));
  }, []);

  return (
    <>
      <PageHeader title="Recurring Expenses" subtitle="Subscriptions and bills detected from statement history" />
      <div className="px-8 py-6 max-w-4xl">
        {loading ? (
          <p className="text-sm text-slate">Looking for recurring expenses...</p>
        ) : error ? (
          <Card><p className="text-sm text-clay">{error}</p></Card>
        ) : items.length === 0 ? (
          <Card className="text-center py-10">
            <Repeat className="mx-auto text-slate mb-3" size={24} />
            <p className="text-sm text-slate">No recurring expenses detected yet. Upload at least 2 to 3 months of statements for better detection.</p>
          </Card>
        ) : (
          <Card padded={false}>
            <div className="grid grid-cols-[1fr_120px_120px_150px] gap-3 p-3 text-xs uppercase tracking-wide text-slate border-b border-line/60">
              <span>Merchant</span><span>Amount</span><span>Frequency</span><span>Next expected</span>
            </div>
            {items.map((item, i) => (
              <div key={item.id || `${item.merchant_name}-${i}`} className="grid grid-cols-[1fr_120px_120px_150px] gap-3 p-3 border-b border-line/60 last:border-b-0 text-sm">
                <div>
                  <p className="font-medium">{item.merchant_name}</p>
                  <p className="text-xs text-slate">{item.category || "Uncategorized"} · {Math.round(item.confidence_score * 100)}% confidence</p>
                </div>
                <span>{formatCurrency(item.amount)}</span>
                <span>{item.frequency}</span>
                <span>{item.next_expected_date ? formatDate(item.next_expected_date) : "Not enough history"}</span>
              </div>
            ))}
          </Card>
        )}
      </div>
    </>
  );
}
