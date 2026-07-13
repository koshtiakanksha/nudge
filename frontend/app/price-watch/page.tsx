"use client";

import { useEffect, useState } from "react";
import { Trash2, RefreshCw, Plus } from "lucide-react";
import { api } from "@/lib/api";
import { PriceWatch } from "@/types/api";
import { formatCurrency, cn } from "@/lib/format";
import { Card, CardLabel } from "@/components/card";
import { PageHeader } from "@/components/page-header";

const VERDICT_STYLES: Record<string, string> = {
  buy_now: "bg-moss/10 text-moss",
  wait: "bg-gold/10 text-gold",
  overpriced: "bg-clay/10 text-clay",
};

const VERDICT_LABEL: Record<string, string> = {
  buy_now: "Buy now",
  wait: "Wait",
  overpriced: "Overpriced",
};

export default function PriceWatchPage() {
  const [watches, setWatches] = useState<PriceWatch[]>([]);
  const [url, setUrl] = useState("");
  const [target, setTarget] = useState("");
  const [adding, setAdding] = useState(false);
  const [loading, setLoading] = useState(true);

  const load = () => api.listPriceWatches().then(setWatches).finally(() => setLoading(false));
  useEffect(() => {
    load();
  }, []);

  const handleAdd = async () => {
    if (!url) return;
    setAdding(true);
    try {
      const watch = await api.createPriceWatch(url, target ? parseFloat(target) : undefined);
      setWatches((prev) => [watch, ...prev]);
      setUrl("");
      setTarget("");
    } finally {
      setAdding(false);
    }
  };

  const handleRefresh = async (id: string) => {
    const updated = await api.refreshPriceWatch(id);
    setWatches((prev) => prev.map((w) => (w.id === id ? updated : w)));
  };

  const handleDelete = async (id: string) => {
    await api.deletePriceWatch(id);
    setWatches((prev) => prev.filter((w) => w.id !== id));
  };

  return (
    <>
      <PageHeader title="Price Watch" subtitle="Track products and let Nudge tell you when to buy" />

      <div className="px-8 py-6 max-w-3xl space-y-6">
        <Card>
          <CardLabel>Watch a new product</CardLabel>
          <div className="flex gap-2 mt-2">
            <input
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="Paste a product URL"
              className="flex-1 border border-line rounded-md px-3 py-2 text-sm"
            />
            <input
              value={target}
              onChange={(e) => setTarget(e.target.value)}
              placeholder="Target price (optional)"
              className="w-44 border border-line rounded-md px-3 py-2 text-sm"
            />
            <button
              onClick={handleAdd}
              disabled={adding || !url}
              className="px-4 py-2 bg-moss text-paper rounded-md text-sm font-medium hover:bg-moss2 transition-colors disabled:opacity-60 flex items-center gap-1.5"
            >
              <Plus size={15} /> Watch
            </button>
          </div>
        </Card>

        {loading ? (
          <p className="text-sm text-slate">Loading…</p>
        ) : watches.length === 0 ? (
          <p className="text-sm text-slate">No price watches yet. Paste a product link above to get started.</p>
        ) : (
          <div className="space-y-3">
            {watches.map((w) => (
              <Card key={w.id} className="flex items-center justify-between gap-4">
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium truncate">{w.product_name}</p>
                  <p className="text-xs text-slate truncate">{w.retailer} · {w.product_url}</p>
                  <div className="flex items-center gap-3 mt-2">
                    <span className="text-lg font-display font-semibold">
                      {w.current_price !== null ? formatCurrency(w.current_price) : "—"}
                    </span>
                    {w.target_price && (
                      <span className="text-xs text-slate">target {formatCurrency(w.target_price)}</span>
                    )}
                    {w.verdict && (
                      <span
                        className={cn("text-xs px-2 py-0.5 rounded-full font-medium", VERDICT_STYLES[w.verdict])}
                      >
                        {VERDICT_LABEL[w.verdict]} {w.confidence ? `· ${Math.round(w.confidence)}%` : ""}
                      </span>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <button
                    onClick={() => handleRefresh(w.id)}
                    className="p-2 rounded-md hover:bg-line/40 transition-colors"
                    title="Refresh price"
                  >
                    <RefreshCw size={15} />
                  </button>
                  <button
                    onClick={() => handleDelete(w.id)}
                    className="p-2 rounded-md hover:bg-clay/10 text-clay transition-colors"
                    title="Stop watching"
                  >
                    <Trash2 size={15} />
                  </button>
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>
    </>
  );
}
