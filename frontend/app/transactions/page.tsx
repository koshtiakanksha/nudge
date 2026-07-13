"use client";

import { useEffect, useState } from "react";
import { Check, RefreshCw } from "lucide-react";
import { api } from "@/lib/api";
import { Transaction, PlaidItem } from "@/types/api";
import { formatCurrency, formatDate, cn } from "@/lib/format";
import { Card } from "@/components/card";
import { PageHeader } from "@/components/page-header";

const CATEGORIES = [
  "Groceries", "Dining", "Transportation", "Entertainment", "Health & Fitness",
  "Shopping", "Travel", "Utilities & Bills", "Subscriptions", "Other",
];

export default function TransactionsPage() {
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [items, setItems] = useState<PlaidItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);

  const load = () => {
    setLoading(true);
    Promise.all([api.listTransactions(1, 100), api.listPlaidItems()])
      .then(([txnRes, itemsRes]) => {
        setTransactions(txnRes.items);
        setItems(itemsRes);
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, []);

  const handleLink = async () => {
    const { mock_mode } = await api.createLinkToken();
    // In production this opens Plaid Link UI; in local sample mode we simulate the
    // exchange directly since there's no real bank to connect to.
    const item = await api.exchangeToken("mock-public-token", mock_mode ? "Sample Bank" : undefined);
    setItems((prev) => [...prev, item]);
  };

  const handleSync = async (itemId: string) => {
    setSyncing(true);
    await api.syncItem(itemId);
    load();
    setSyncing(false);
  };

  const handleCategoryChange = async (txnId: string, category: string) => {
    const updated = await api.updateTransaction(txnId, { nudge_category: category });
    setTransactions((prev) => prev.map((t) => (t.id === txnId ? updated : t)));
    setEditingId(null);
  };

  return (
    <>
      <PageHeader title="Transactions" subtitle="Everything synced from your linked accounts" />

      <div className="px-8 py-6">
        <div className="flex items-center gap-3 mb-5">
          {items.length === 0 ? (
            <button
              onClick={handleLink}
              className="px-4 py-2 bg-moss text-paper rounded-md text-sm font-medium hover:bg-moss2 transition-colors"
            >
              Link a bank account
            </button>
          ) : (
            items.map((item) => (
              <button
                key={item.id}
                onClick={() => handleSync(item.id)}
                disabled={syncing}
                className="flex items-center gap-2 px-3 py-1.5 border border-line rounded-md text-sm hover:bg-line/40 transition-colors disabled:opacity-50"
              >
                <RefreshCw size={14} className={syncing ? "animate-spin" : ""} />
                Sync {item.institution_name}
              </button>
            ))
          )}
        </div>

        <Card padded={false} className="overflow-hidden">
          {loading ? (
            <p className="p-5 text-sm text-slate">Loading transactions…</p>
          ) : transactions.length === 0 ? (
            <p className="p-5 text-sm text-slate">
              No transactions yet. Link an account above, then sync to pull in your spending.
            </p>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-line text-left text-xs uppercase tracking-wide text-slate">
                  <th className="px-5 py-3 font-medium">Date</th>
                  <th className="px-5 py-3 font-medium">Merchant</th>
                  <th className="px-5 py-3 font-medium">Category</th>
                  <th className="px-5 py-3 font-medium text-right">Amount</th>
                </tr>
              </thead>
              <tbody>
                {transactions.map((t) => (
                  <tr key={t.id} className="border-b border-line/60 hover:bg-line/20">
                    <td className="px-5 py-3 text-slate whitespace-nowrap">{formatDate(t.date)}</td>
                    <td className="px-5 py-3">{t.merchant_name || "Unknown"}</td>
                    <td className="px-5 py-3">
                      {editingId === t.id ? (
                        <select
                          autoFocus
                          defaultValue={t.nudge_category || "Other"}
                          onChange={(e) => handleCategoryChange(t.id, e.target.value)}
                          onBlur={() => setEditingId(null)}
                          className="border border-line rounded-sm px-2 py-1 text-sm"
                        >
                          {CATEGORIES.map((c) => (
                            <option key={c} value={c}>
                              {c}
                            </option>
                          ))}
                        </select>
                      ) : (
                        <button
                          onClick={() => setEditingId(t.id)}
                          className="px-2 py-0.5 rounded-full bg-line/50 text-xs hover:bg-line transition-colors"
                        >
                          {t.nudge_category || "Other"}
                        </button>
                      )}
                    </td>
                    <td
                      className={cn(
                        "px-5 py-3 text-right font-mono whitespace-nowrap",
                        t.amount < 0 ? "text-ink" : "text-moss"
                      )}
                    >
                      {formatCurrency(t.amount)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Card>
      </div>
    </>
  );
}
