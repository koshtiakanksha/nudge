"use client";

import { useEffect, useState } from "react";
import { CalendarDays, ExternalLink, Info, MapPin, Navigation, Star } from "lucide-react";
import { api } from "@/lib/api";
import { Deal } from "@/types/api";
import { Card } from "@/components/card";
import { PageHeader } from "@/components/page-header";
import { formatCurrency, formatDate } from "@/lib/format";

function isValidUrl(url?: string | null) {
  if (!url) return false;
  try {
    const parsed = new URL(url);
    return parsed.protocol === "http:" || parsed.protocol === "https:";
  } catch {
    return false;
  }
}

function directionsUrl(deal: Deal) {
  if (isValidUrl(deal.directions_url)) return deal.directions_url;
  if (deal.address || deal.location) {
    return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent([deal.location, deal.address].filter(Boolean).join(" "))}`;
  }
  if (deal.latitude && deal.longitude) {
    return `https://www.google.com/maps/search/?api=1&query=${deal.latitude},${deal.longitude}`;
  }
  return null;
}

function primaryAction(deal: Deal) {
  if (deal.result_type === "event" && isValidUrl(deal.ticket_url)) return { label: "Buy tickets", url: deal.ticket_url };
  if (deal.result_type === "event" && isValidUrl(deal.external_url)) return { label: "View event", url: deal.external_url };
  if (deal.result_type === "place" && isValidUrl(deal.website_url)) return { label: "Open website", url: deal.website_url };
  if (isValidUrl(deal.external_url)) return { label: "View source", url: deal.external_url };
  if (isValidUrl(deal.url)) return { label: "View source", url: deal.url };
  return null;
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

export default function DealsPage() {
  const [deals, setDeals] = useState<Deal[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<Deal | null>(null);

  useEffect(() => {
    api
      .getDeals()
      .then(setDeals)
      .catch((e) => setError(e instanceof Error ? e.message : "Could not load deals"))
      .finally(() => setLoading(false));
  }, []);

  return (
    <>
      <PageHeader title="Local Deals" subtitle="Discounts, places, and events near you" />

      <div className="px-8 py-6 max-w-5xl">
        {loading ? (
          <p className="text-sm text-slate">Looking for local recommendations…</p>
        ) : error ? (
          <Card>
            <p className="text-sm text-clay">{error}</p>
          </Card>
        ) : deals.length === 0 ? (
          <Card>
            <p className="text-sm text-slate">No deals found. Connect an API or set your location to view live local results.</p>
          </Card>
        ) : (
          <>
            {deals.some((deal) => deal.is_sample) && (
              <Card className="mb-4 bg-gold/5 border-gold/20">
                <p className="text-sm text-ink">Sample data shown. Connect APIs to view live results.</p>
              </Card>
            )}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {deals.map((deal, i) => {
                const action = primaryAction(deal);
                const mapUrl = directionsUrl(deal);
                const CardBody = (
                  <Card className="h-full hover:border-moss/40 transition-colors">
                    <div className="flex justify-between items-start mb-2 gap-3">
                      <span className="text-[10px] uppercase tracking-wide text-slate">{deal.category}</span>
                      <span className="text-[10px] text-slate">{deal.source}</span>
                    </div>
                    {deal.image_url ? (
                      <img src={deal.image_url} alt="" className="w-full aspect-[16/9] object-cover rounded-md mb-3 bg-line" />
                    ) : null}
                    <p className="font-medium text-sm mb-1">{deal.title}</p>
                    <p className="text-sm text-slate leading-snug line-clamp-3">{deal.description || "More details are not available from this source."}</p>
                    <div className="flex flex-wrap items-center gap-3 mt-3 text-xs text-slate">
                      {(deal.location || deal.address) && (
                        <span className="flex items-center gap-1">
                          <MapPin size={12} />
                          {deal.location || deal.address}
                          {deal.distance_miles ? ` · ${deal.distance_miles} mi` : ""}
                        </span>
                      )}
                      {deal.rating && (
                        <span className="flex items-center gap-1">
                          <Star size={12} /> {deal.rating}
                        </span>
                      )}
                      {(deal.cost || deal.price !== null) && (
                        <span>{deal.cost || (deal.price !== null ? formatCurrency(deal.price) : null)}</span>
                      )}
                      {deal.starts_at && (
                        <span className="flex items-center gap-1">
                          <CalendarDays size={12} /> {formatDate(deal.starts_at)}
                        </span>
                      )}
                    </div>
                    <div className="flex flex-wrap items-center gap-3 mt-4">
                      {action ? (
                        <a
                          href={action.url || "#"}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-xs text-moss flex items-center gap-1 hover:underline"
                        >
                          {action.label} <ExternalLink size={11} />
                        </a>
                      ) : (
                        <span className="text-xs text-slate">No external link available.</span>
                      )}
                      {mapUrl && (
                        <a href={mapUrl} target="_blank" rel="noopener noreferrer" className="text-xs text-moss flex items-center gap-1 hover:underline">
                          Get directions <Navigation size={11} />
                        </a>
                      )}
                      <button onClick={() => setSelected(deal)} className="text-xs text-moss flex items-center gap-1 hover:underline">
                        More info <Info size={11} />
                      </button>
                    </div>
                  </Card>
                );
                return action ? (
                  <div key={`${deal.title}-${i}`} className="h-full">{CardBody}</div>
                ) : (
                  <div key={`${deal.title}-${i}`} className="h-full opacity-90">{CardBody}</div>
                );
              })}
            </div>
          </>
        )}
      </div>

      {selected && (
        <div className="fixed inset-0 bg-ink/30 flex items-center justify-center p-4 z-50" onClick={() => setSelected(null)}>
          <Card className="max-w-lg w-full bg-paper" onClick={(e) => e.stopPropagation()}>
            <div className="flex justify-between gap-4 mb-4">
              <div>
                <p className="text-xs uppercase tracking-wide text-slate">{selected.source}</p>
                <h2 className="text-xl font-display font-semibold">{selected.title}</h2>
              </div>
              <button onClick={() => setSelected(null)} className="text-sm text-slate hover:text-ink">Close</button>
            </div>
            <p className="text-sm text-slate leading-relaxed mb-4">
              {selected.description || "More details are not available from this source."}
            </p>
            <div className="space-y-2">
              <DetailRow label="Price" value={selected.cost || (selected.price !== null ? formatCurrency(selected.price) : null)} />
              <DetailRow label="Rating" value={selected.rating} />
              <DetailRow label="Location" value={[selected.location, selected.address].filter(Boolean).join(", ")} />
              <DetailRow label="Date" value={selected.starts_at ? formatDate(selected.starts_at) : selected.expires_at ? `Expires ${formatDate(selected.expires_at)}` : null} />
              <DetailRow label="Provider" value={selected.provider || selected.source} />
              <DetailRow label="Last updated" value={selected.last_updated ? formatDate(selected.last_updated) : null} />
            </div>
            <div className="flex flex-wrap gap-3 mt-5">
              {primaryAction(selected) ? (
                <a href={primaryAction(selected)?.url || "#"} target="_blank" rel="noopener noreferrer" className="text-sm text-moss hover:underline">
                  Open external link
                </a>
              ) : (
                <span className="text-sm text-slate">No external link available.</span>
              )}
              {directionsUrl(selected) && (
                <a href={directionsUrl(selected) || "#"} target="_blank" rel="noopener noreferrer" className="text-sm text-moss hover:underline">
                  Get directions
                </a>
              )}
            </div>
          </Card>
        </div>
      )}
    </>
  );
}
