"use client";

import { useEffect, useMemo, useState } from "react";
import { ExternalLink, Info, Plus, RefreshCw, Trash2 } from "lucide-react";
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "@/lib/api";
import { PriceWatch } from "@/types/api";
import { formatCurrency, formatDate, cn } from "@/lib/format";
import { Card, CardLabel } from "@/components/card";
import { PageHeader } from "@/components/page-header";

const VERDICT_STYLES: Record<string, string> = {
  buy_now: "bg-moss/10 text-moss",
  wait: "bg-gold/10 text-gold",
  overpriced: "bg-clay/10 text-clay",
};

const VERDICT_LABEL: Record<string, string> = {
  buy_now: "Good time to buy",
  wait: "Wait if not urgent",
  overpriced: "Price is higher than usual",
};

function isValidUrl(url?: string | null) {
  if (!url) return false;
  try {
    const parsed = new URL(url);
    return parsed.protocol === "http:" || parsed.protocol === "https:";
  } catch {
    return false;
  }
}

function statsFor(watch: PriceWatch) {
  const prices = watch.price_history.map((point) => point.price).filter((price) => Number.isFinite(price));
  if (watch.current_price !== null && prices.length === 0) prices.push(watch.current_price);
  if (prices.length === 0) return null;
  const lowest = Math.min(...prices);
  const highest = Math.max(...prices);
  const average = prices.reduce((sum, price) => sum + price, 0) / prices.length;
  return { lowest, highest, average, count: prices.length };
}

function recommendationFor(watch: PriceWatch) {
  const stats = statsFor(watch);
  if (!stats || watch.current_price === null) return { label: "Limited history available", detail: "Price prediction will appear after enough price history is collected.", verdict: null };
  if (stats.count < 3) return { label: "Limited history available", detail: "Price prediction will appear after enough price history is collected.", verdict: null };
  if (watch.current_price <= stats.lowest * 1.03) return { label: "Good time to buy", detail: "The current price is close to the lowest observed price.", verdict: "buy_now" };
  if (watch.current_price > stats.average * 1.1) return { label: "Price is higher than usual", detail: "The current price is above the observed average.", verdict: "overpriced" };
  return { label: "Wait if not urgent", detail: "The current price is near the observed average.", verdict: "wait" };
}

function PriceChart({ watch }: { watch: PriceWatch }) {
  if (watch.price_history.length < 2) {
    return <p className="text-xs text-slate mt-3">No price history available yet.</p>;
  }
  return (
    <div className="h-36 mt-3">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={watch.price_history}>
          <XAxis dataKey="date" tickFormatter={formatDate} tick={{ fontSize: 10 }} minTickGap={18} />
          <YAxis tick={{ fontSize: 10 }} width={42} tickFormatter={(value) => `$${value}`} />
          <Tooltip
            formatter={(value) => formatCurrency(Number(value))}
            labelFormatter={(label) => formatDate(String(label))}
            contentStyle={{ border: "1px solid #ddd6c8", borderRadius: 8, fontSize: 12 }}
          />
          <Line type="monotone" dataKey="price" stroke="#55715f" strokeWidth={2} dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

function DetailRow({ label, value }: { label: string; value?: string | number | null }) {
  if (value === null || value === undefined || value === "") return null;
  return (
    <div className="flex justify-between gap-4 text-sm">
      <span className="text-slate">{label}</span>
      <span className="text-right text-ink">{value}</span>
    </div>
  );
}

export default function PriceWatchPage() {
  const [watches, setWatches] = useState<PriceWatch[]>([]);
  const [url, setUrl] = useState("");
  const [target, setTarget] = useState("");
  const [adding, setAdding] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<PriceWatch | null>(null);

  const load = () =>
    api
      .listPriceWatches()
      .then(setWatches)
      .catch((e) => setError(e instanceof Error ? e.message : "Could not load price watches"))
      .finally(() => setLoading(false));

  useEffect(() => {
    load();
  }, []);

  const handleAdd = async () => {
    if (!url) return;
    setAdding(true);
    setError(null);
    try {
      const watch = await api.createPriceWatch(url, target ? parseFloat(target) : undefined);
      setWatches((prev) => [watch, ...prev]);
      setUrl("");
      setTarget("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not add product");
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

  const activeSelection = useMemo(
    () => (selected ? watches.find((watch) => watch.id === selected.id) || selected : null),
    [selected, watches]
  );

  return (
    <>
      <PageHeader title="Price Watch" subtitle="Track product prices and decide when to buy" />

      <div className="px-8 py-6 max-w-5xl space-y-6">
        <Card>
          <CardLabel>Watch a new product</CardLabel>
          <div className="grid grid-cols-1 md:grid-cols-[1fr_180px_auto] gap-2 mt-2">
            <input
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="Paste a product URL"
              className="border border-line rounded-md px-3 py-2 text-sm"
            />
            <input
              value={target}
              onChange={(e) => setTarget(e.target.value)}
              placeholder="Target price (optional)"
              className="border border-line rounded-md px-3 py-2 text-sm"
            />
            <button
              onClick={handleAdd}
              disabled={adding || !url}
              className="px-4 py-2 bg-moss text-paper rounded-md text-sm font-medium hover:bg-moss2 transition-colors disabled:opacity-60 flex items-center justify-center gap-1.5"
            >
              <Plus size={15} /> Track price
            </button>
          </div>
          <p className="text-xs text-slate mt-2">Connect an API to view live product prices. If history is limited, Nudge will say so instead of inventing a forecast.</p>
        </Card>

        {loading ? (
          <p className="text-sm text-slate">Loading products…</p>
        ) : error ? (
          <Card><p className="text-sm text-clay">{error}</p></Card>
        ) : watches.length === 0 ? (
          <Card>
            <p className="text-sm text-slate">No price watches yet. Paste a product link above to get started.</p>
          </Card>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {watches.map((w) => {
              const stats = statsFor(w);
              const recommendation = recommendationFor(w);
              const verdict = recommendation.verdict || w.verdict;
              const productLink = isValidUrl(w.product_url);
              return (
                <Card key={w.id} className="space-y-4">
                  <div className="flex gap-3">
                    {w.image_url ? (
                      <img src={w.image_url} alt="" className="w-20 h-20 rounded-md object-cover bg-line shrink-0" />
                    ) : (
                      <div className="w-20 h-20 rounded-md bg-line/50 shrink-0" />
                    )}
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium truncate">{w.product_name || "Tracked product"}</p>
                      <p className="text-xs text-slate truncate">{w.retailer || "Unknown store"}</p>
                      <div className="flex flex-wrap items-center gap-2 mt-2">
                        <span className="text-xl font-display font-semibold">
                          {w.current_price !== null ? formatCurrency(w.current_price) : "Unavailable"}
                        </span>
                        {verdict && (
                          <span className={cn("text-xs px-2 py-0.5 rounded-full font-medium", VERDICT_STYLES[verdict])}>
                            {VERDICT_LABEL[verdict] || recommendation.label}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>

                  <PriceChart watch={w} />

                  <div className="grid grid-cols-3 gap-2 text-xs">
                    <div><span className="block text-slate">Lowest</span><strong>{stats ? formatCurrency(stats.lowest) : "—"}</strong></div>
                    <div><span className="block text-slate">Highest</span><strong>{stats ? formatCurrency(stats.highest) : "—"}</strong></div>
                    <div><span className="block text-slate">Average</span><strong>{stats ? formatCurrency(stats.average) : "—"}</strong></div>
                  </div>

                  <p className="text-xs text-slate">{recommendation.detail}</p>

                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div className="flex flex-wrap gap-3">
                      {productLink ? (
                        <a href={w.product_url} target="_blank" rel="noopener noreferrer" className="text-xs text-moss flex items-center gap-1 hover:underline">
                          View product <ExternalLink size={11} />
                        </a>
                      ) : (
                        <span className="text-xs text-slate">No external link available.</span>
                      )}
                      <button onClick={() => setSelected(w)} className="text-xs text-moss flex items-center gap-1 hover:underline">
                        More info <Info size={11} />
                      </button>
                    </div>
                    <div className="flex items-center gap-1">
                      <button onClick={() => handleRefresh(w.id)} className="p-2 rounded-md hover:bg-line/40 transition-colors" title="Refresh price">
                        <RefreshCw size={15} />
                      </button>
                      <button onClick={() => handleDelete(w.id)} className="p-2 rounded-md hover:bg-clay/10 text-clay transition-colors" title="Stop watching">
                        <Trash2 size={15} />
                      </button>
                    </div>
                  </div>
                </Card>
              );
            })}
          </div>
        )}
      </div>

      {activeSelection && (
        <div className="fixed inset-0 bg-ink/30 flex items-center justify-center p-4 z-50" onClick={() => setSelected(null)}>
          <Card className="max-w-lg w-full bg-paper" onClick={(e) => e.stopPropagation()}>
            <div className="flex justify-between gap-4 mb-4">
              <div>
                <p className="text-xs uppercase tracking-wide text-slate">{activeSelection.retailer || "Unknown store"}</p>
                <h2 className="text-xl font-display font-semibold">{activeSelection.product_name || "Tracked product"}</h2>
              </div>
              <button onClick={() => setSelected(null)} className="text-sm text-slate hover:text-ink">Close</button>
            </div>
            <p className="text-sm text-slate mb-4">
              {recommendationFor(activeSelection).detail || "More details are not available from this source."}
            </p>
            <div className="space-y-2">
              <DetailRow label="Current price" value={activeSelection.current_price !== null ? formatCurrency(activeSelection.current_price) : "Unavailable"} />
              <DetailRow label="Target price" value={activeSelection.target_price ? formatCurrency(activeSelection.target_price) : null} />
              <DetailRow label="Lowest observed" value={statsFor(activeSelection) ? formatCurrency(statsFor(activeSelection)!.lowest) : null} />
              <DetailRow label="Highest observed" value={statsFor(activeSelection) ? formatCurrency(statsFor(activeSelection)!.highest) : null} />
              <DetailRow label="Average" value={statsFor(activeSelection) ? formatCurrency(statsFor(activeSelection)!.average) : null} />
              <DetailRow label="Source" value={activeSelection.retailer || "Product page"} />
              <DetailRow label="Last updated" value={activeSelection.price_history.at(-1)?.date ? formatDate(activeSelection.price_history.at(-1)!.date) : null} />
            </div>
            <div className="flex flex-wrap gap-3 mt-5">
              {isValidUrl(activeSelection.product_url) ? (
                <a href={activeSelection.product_url} target="_blank" rel="noopener noreferrer" className="text-sm text-moss hover:underline">
                  View product
                </a>
              ) : (
                <span className="text-sm text-slate">No external link available.</span>
              )}
              <button onClick={() => handleRefresh(activeSelection.id)} className="text-sm text-moss hover:underline">
                Track price
              </button>
            </div>
          </Card>
        </div>
      )}
    </>
  );
}
