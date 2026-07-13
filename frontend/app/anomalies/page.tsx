"use client";

import { useEffect, useState } from "react";
import { AlertTriangle, Check, X, ScanSearch } from "lucide-react";
import { api } from "@/lib/api";
import { Anomaly } from "@/types/api";
import { formatCurrency, formatDate } from "@/lib/format";
import { Card } from "@/components/card";
import { PageHeader } from "@/components/page-header";

export default function AnomaliesPage() {
  const [anomalies, setAnomalies] = useState<Anomaly[]>([]);
  const [loading, setLoading] = useState(true);
  const [scanning, setScanning] = useState(false);

  const load = () => {
    api.listAnomalies().then(setAnomalies).finally(() => setLoading(false));
  };
  useEffect(() => {
    load();
  }, []);

  const handleScan = async () => {
    setScanning(true);
    await api.scanAnomalies();
    await load();
    setScanning(false);
  };

  const handleFeedback = async (id: string, intentional: boolean) => {
    const updated = await api.submitAnomalyFeedback(id, intentional);
    setAnomalies((prev) => prev.map((a) => (a.id === id ? updated : a)));
  };

  return (
    <>
      <PageHeader title="Unusual Activity" subtitle="Charges that stand out from your normal pattern" />

      <div className="px-8 py-6 max-w-3xl space-y-5">
        <button
          onClick={handleScan}
          disabled={scanning}
          className="flex items-center gap-2 px-4 py-2 border border-line rounded-md text-sm hover:bg-line/40 transition-colors disabled:opacity-60"
        >
          <ScanSearch size={15} className={scanning ? "animate-pulse" : ""} />
          {scanning ? "Scanning…" : "Scan for new anomalies"}
        </button>

        {loading ? (
          <p className="text-sm text-slate">Loading…</p>
        ) : anomalies.length === 0 ? (
          <Card>
            <p className="text-sm text-slate">No unusual activity flagged. Run a scan after syncing transactions.</p>
          </Card>
        ) : (
          <div className="space-y-3">
            {anomalies.map((a) => (
              <Card key={a.id} className="flex items-start gap-3">
                <div className="w-8 h-8 rounded-full bg-clay/10 flex items-center justify-center shrink-0 mt-0.5">
                  <AlertTriangle size={15} className="text-clay" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex justify-between items-baseline">
                    <p className="text-sm font-medium">{a.merchant_name}</p>
                    <span className="font-mono text-sm">{formatCurrency(a.amount)}</span>
                  </div>
                  <p className="text-xs text-slate mt-0.5">{formatDate(a.created_at)}</p>
                  {a.ai_context && <p className="text-sm text-ink mt-2 leading-relaxed">{a.ai_context}</p>}

                  {a.user_marked_intentional === null ? (
                    <div className="flex gap-2 mt-3">
                      <button
                        onClick={() => handleFeedback(a.id, true)}
                        className="flex items-center gap-1 px-3 py-1.5 text-xs border border-line rounded-md hover:bg-moss/10 hover:border-moss/40 transition-colors"
                      >
                        <Check size={13} /> That was me
                      </button>
                      <button
                        onClick={() => handleFeedback(a.id, false)}
                        className="flex items-center gap-1 px-3 py-1.5 text-xs border border-line rounded-md hover:bg-clay/10 hover:border-clay/40 transition-colors"
                      >
                        <X size={13} /> Not sure
                      </button>
                    </div>
                  ) : (
                    <p className="text-xs text-slate mt-2">
                      Marked as {a.user_marked_intentional ? "intentional" : "flagged for review"}
                    </p>
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
