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

const RANGE_OPTIONS = [
  { value: "", label: "All time" },
  { value: "this_month", label: "This month" },
  { value: "last_3_months", label: "Last 3 months" },
  { value: "ytd", label: "Year to date" },
  { value: "last_year", label: "Last year" },
];

export default function TransactionsPage() {
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [items, setItems] = useState<PlaidItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [linking, setLinking] = useState(false);
  const [linkError, setLinkError] = useState<string | null>(null);
  const [rangePreset, setRangePreset] = useState("");
  const [exporting, setExporting] = useState(false);

  const load = (range = rangePreset) => {
    setLoading(true);
    Promise.all([api.listTransactions(1, 200, undefined, range || undefined), api.listPlaidItems()])
      .then(([txnRes, itemsRes]) => {
        setTransactions(txnRes.items);
        setItems(itemsRes);
      })
      .catch((err) => {
        console.error("Failed to load transactions/items:", err);
        setLinkError(err instanceof Error ? err.message : "Failed to load your data. Check the console for details.");
      })
      .finally(() => setLoading(false));
  };

  const handleRangeChange = (value: string) => {
    setRangePreset(value);
    load(value);
  };

  const handleExport = async () => {
    setExporting(true);
    try {
      await api.downloadTransactionsCsv(undefined, rangePreset || undefined);
    } catch (err) {
      console.error("Failed to export:", err);
      setLinkError(err instanceof Error ? err.message : "Export failed. Check the console for details.");
    } finally {
      setExporting(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const handleLink = async () => {
    setLinking(true);
    setLinkError(null);
    try {
      const { mock_mode } = await api.createLinkToken();
      // In production this opens Plaid Link UI; in local sample mode we simulate the
      // exchange directly since there's no real bank to connect to.
      const item = await api.exchangeToken("mock-public-token", mock_mode ? "Sample Bank" : undefined);
      setItems((prev) => [...prev, item]);
    } catch (err) {
      console.error("Failed to link bank account:", err);
      setLinkError(err instanceof Error ? err.message : "Failed to link account. Check the console for details.");
    } finally {
      setLinking(false);
    }
  };

  const handleSync = async (itemId: string) => {
    setSyncing(true);
    setLinkError(null);
    try {
      await api.syncItem(itemId);
      load();
    } catch (err) {
      console.error("Failed to sync:", err);
      setLinkError(err instanceof Error ? err.message : "Sync failed. Check the console for details.");
    } finally {
      setSyncing(false);
    }
  };

  const handleDisconnect = async (itemId: string, institutionName: string) => {
    if (!confirm(`Disconnect ${institutionName}? Your synced transaction history will be kept, but this account will stop syncing new activity.`)) {
      return;
    }
    setLinkError(null);
    try {
      await api.disconnectItem(itemId);
      setItems((prev) => prev.filter((i) => i.id !== itemId));
    } catch (err) {
      console.error("Failed to disconnect:", err);
      setLinkError(err instanceof Error ? err.message : "Failed to disconnect. Check the console for details.");
    }
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
              disabled={linking}
              className="px-4 py-2 bg-moss text-paper rounded-md text-sm font-medium hover:bg-moss2 transition-colors disabled:opacity-60"
            >
              {linking ? "Linking…" : "Link a bank account"}
            </button>
          ) : (
            <button
              onClick={handleLink}
              disabled={linking}
              className="px-3 py-1.5 border border-line rounded-md text-sm hover:bg-line/40 transition-colors disabled:opacity-50"
            >
              {linking ? "Linking…" : "+ Link another account"}
            </button>
          )}
        </div>

        {linkError && (
          <p className="mb-5 text-sm text-clay bg-clay/10 border border-clay/30 rounded-md px-3 py-2">
            {linkError}
          </p>
        )}

        {items.length > 0 && (
          <div className="space-y-3 mb-6">
            {items.map((item) => (
              <Card key={item.id} className="flex items-center justify-between">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-medium">{item.institution_name}</span>
                    <span className="inline-flex items-center gap-1 text-xs text-moss">
                      <Check size={12} /> Connected
                    </span>
                  </div>
                  <p className="text-xs text-slate mt-1">
                    {item.accounts.map((a) => `${a.name} ••${a.mask}`).join(" · ") || "No accounts"}
                  </p>
                  <p className="text-xs text-slate mt-0.5">
                    {item.last_synced_at ? `Last synced ${formatDate(item.last_synced_at)}` : "Never synced"}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => handleSync(item.id)}
                    disabled={syncing}
                    className="flex items-center gap-2 px-3 py-1.5 border border-line rounded-md text-sm hover:bg-line/40 transition-colors disabled:opacity-50"
                  >
                    <RefreshCw size={14} className={syncing ? "animate-spin" : ""} />
                    Sync
                  </button>
                  <button
                    onClick={() => handleDisconnect(item.id, item.institution_name)}
                    className="px-3 py-1.5 text-sm text-clay hover:bg-clay/10 rounded-md transition-colors"
                  >
                    Disconnect
                  </button>
                </div>
              </Card>
            ))}
          </div>
        )}

        <div className="flex items-center justify-between mb-3">
          <select
            value={rangePreset}
            onChange={(e) => handleRangeChange(e.target.value)}
            className="border border-line rounded-md px-3 py-1.5 text-sm bg-white/60"
          >
            {RANGE_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
          <button
            onClick={handleExport}
            disabled={exporting || transactions.length === 0}
            className="px-3 py-1.5 border border-line rounded-md text-sm hover:bg-line/40 transition-colors disabled:opacity-50"
          >
            {exporting ? "Exporting…" : "Download CSV"}
          </button>
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
