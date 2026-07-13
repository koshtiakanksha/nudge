"use client";

import { useEffect, useState } from "react";
import { MapPin, ExternalLink } from "lucide-react";
import { api } from "@/lib/api";
import { Deal } from "@/types/api";
import { Card } from "@/components/card";
import { PageHeader } from "@/components/page-header";

export default function DealsPage() {
  const [deals, setDeals] = useState<Deal[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .getDeals()
      .then(setDeals)
      .finally(() => setLoading(false));
  }, []);

  return (
    <>
      <PageHeader title="Local Deals" subtitle="Discounts and free things to do near you" />

      <div className="px-8 py-6 max-w-3xl">
        {loading ? (
          <p className="text-sm text-slate">Looking for deals nearby…</p>
        ) : deals.length === 0 ? (
          <Card>
            <p className="text-sm text-slate">
              No deals found nearby. Set your location under Settings so Nudge can find local discounts and events.
            </p>
          </Card>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {deals.map((d, i) => (
              <Card key={i}>
                <div className="flex justify-between items-start mb-2">
                  <span className="text-[10px] uppercase tracking-wide text-slate">{d.category}</span>
                  <span className="text-[10px] text-slate">{d.source}</span>
                </div>
                <p className="font-medium text-sm mb-1">{d.title}</p>
                <p className="text-sm text-slate leading-snug">{d.description}</p>
                <div className="flex items-center justify-between mt-3">
                  <span className="text-xs text-slate flex items-center gap-1">
                    <MapPin size={12} />
                    {d.location}
                    {d.distance_miles && ` · ${d.distance_miles} mi`}
                  </span>
                  {d.url && (
                    <a
                      href={d.url}
                      target="_blank"
                      rel="noreferrer"
                      className="text-xs text-moss flex items-center gap-1 hover:underline"
                    >
                      View <ExternalLink size={11} />
                    </a>
                  )}
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>
    </>
  );
}
