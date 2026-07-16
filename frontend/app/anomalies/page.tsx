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

  const load = async () => {
    try {
      const items = await api.listAnomalies();
      setAnomalies(items);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const handleScan = async () => {
    setScanning(true);

    try {
      await api.scanAnomalies();
      await load();
    } finally {
      setScanning(false);
    }
  };

  const handleFeedback = async (
    id: string,
    intentional: boolean
  ) => {
    const updated = await api.submitAnomalyFeedback(
      id,
      intentional
    );

    setAnomalies((previous) =>
      previous.map((anomaly) =>
        anomaly.id === id ? updated : anomaly
      )
    );
  };

  return (
    <>
      <PageHeader
        title="Unusual Activity"
        subtitle="Charges that stand out from your normal pattern"
      />

      <div className="px-8 py-6 max-w-3xl space-y-5">
        <button
          onClick={handleScan}
          disabled={scanning}
          className="flex items-center gap-2 px-4 py-2 border border-line rounded-md text-sm hover:bg-line/40 transition-colors disabled:opacity-60"
        >
          <ScanSearch
            size={15}
            className={scanning ? "animate-pulse" : ""}
          />

          {scanning
            ? "Scanning…"
            : "Scan for new anomalies"}
        </button>

        {loading ? (
          <p className="text-sm text-slate">
            Loading…
          </p>
        ) : anomalies.length === 0 ? (
          <Card>
            <p className="text-sm text-slate">
              No anomalies detected. Run a scan after
              syncing transactions.
            </p>
          </Card>
        ) : (
          <div className="space-y-3">
            {anomalies.map((anomaly) => (
              <Card
                key={anomaly.id}
                className="flex items-start gap-3"
              >
                <div className="w-8 h-8 rounded-full bg-clay/10 flex items-center justify-center shrink-0 mt-0.5">
                  <AlertTriangle
                    size={15}
                    className="text-clay"
                  />
                </div>

                <div className="flex-1 min-w-0">
                  <div className="flex justify-between items-baseline gap-3">
                    <p className="text-sm font-medium">
                      {anomaly.merchant_name ||
                        "Unusual transaction"}
                    </p>

                    <span className="font-mono text-sm">
                      {formatCurrency(anomaly.amount)}
                    </span>
                  </div>

                  <p className="text-xs text-slate mt-0.5">
                    {anomaly.transaction_date
                      ? formatDate(
                          anomaly.transaction_date
                        )
                      : "Date unknown"}
                  </p>

                  {anomaly.ai_context && (
                    <p className="text-sm text-ink mt-2 leading-relaxed">
                      {anomaly.ai_context}
                    </p>
                  )}

                  {anomaly.user_marked_intentional ===
                  null ? (
                    <div className="flex gap-2 mt-3">
                      <button
                        onClick={() =>
                          handleFeedback(
                            anomaly.id,
                            true
                          )
                        }
                        className="flex items-center gap-1 px-3 py-1.5 text-xs border border-line rounded-md hover:bg-moss/10 hover:border-moss/40 transition-colors"
                      >
                        <Check size={13} />
                        That was me
                      </button>

                      <button
                        onClick={() =>
                          handleFeedback(
                            anomaly.id,
                            false
                          )
                        }
                        className="flex items-center gap-1 px-3 py-1.5 text-xs border border-line rounded-md hover:bg-clay/10 hover:border-clay/40 transition-colors"
                      >
                        <X size={13} />
                        Not sure
                      </button>
                    </div>
                  ) : (
                    <p className="text-xs text-slate mt-2">
                      Marked as{" "}
                      {anomaly.user_marked_intentional
                        ? "intentional"
                        : "flagged for review"}
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