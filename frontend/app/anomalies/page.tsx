"use client";

import { useEffect, useState } from "react";
import { AlertTriangle, Check, X, ScanSearch } from "lucide-react";
import { api } from "@/lib/api";
import { Anomaly, StatementAnomaly } from "@/types/api";
import { formatCurrency, formatDate } from "@/lib/format";
import { Card } from "@/components/card";
import { PageHeader } from "@/components/page-header";

export default function AnomaliesPage() {
  const [anomalies, setAnomalies] = useState<Anomaly[]>([]);
  const [statementAnomalies, setStatementAnomalies] = useState<StatementAnomaly[]>([]);
  const [loading, setLoading] = useState(true);
  const [scanning, setScanning] = useState(false);

  const load = () => {
    Promise.all([api.listAnomalies(), api.getStatementAnomalies()])
      .then(([scanItems, statementItems]) => {
        setAnomalies(scanItems);
        setStatementAnomalies(statementItems);
      })
      .finally(() => setLoading(false));
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

  const handleStatementStatus = async (id: string, status: string) => {
    const updated = await api.updateStatementAnomaly(id, status);
    setStatementAnomalies((prev) => prev.map((a) => (a.id === id ? updated : a)));
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
        ) : anomalies.length === 0 && statementAnomalies.length === 0 ? (
          <Card>
            <p className="text-sm text-slate">No anomalies detected. Upload statements or run a scan after syncing transactions.</p>
          </Card>
        ) : (
          <div className="space-y-3">
            {statementAnomalies.map((a, i) => (
              <Card key={a.id || `${a.anomaly_type}-${i}`} className="flex items-start gap-3">
                <div className="w-8 h-8 rounded-full bg-gold/10 flex items-center justify-center shrink-0 mt-0.5">
                  <AlertTriangle size={15} className="text-gold" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex justify-between gap-3">
                    <p className="text-sm font-medium">
                      {a.anomaly_type === "possible_travel" ? "Possible travel spending detected" : a.merchant_name || "Unusual transaction"}
                    </p>
                    {a.amount !== null && <span className="font-mono text-sm">{formatCurrency(a.amount)}</span>}
                  </div>
                  <p className="text-sm text-ink mt-2 leading-relaxed">{a.explanation}</p>
                  {a.user_status === "pending" && a.id ? (
                    <div className="flex flex-wrap gap-2 mt-3">
                      <button onClick={() => handleStatementStatus(a.id!, "confirmed")} className="flex items-center gap-1 px-3 py-1.5 text-xs border border-line rounded-md hover:bg-moss/10">
                        <Check size={13} /> {a.anomaly_type === "possible_travel" ? "Yes, mark as travel" : "Confirm"}
                      </button>
                      <button onClick={() => handleStatementStatus(a.id!, "dismissed")} className="flex items-center gap-1 px-3 py-1.5 text-xs border border-line rounded-md hover:bg-line/40">
                        <X size={13} /> Dismiss
                      </button>
                      <button onClick={() => handleStatementStatus(a.id!, "ignored")} className="px-3 py-1.5 text-xs border border-line rounded-md hover:bg-line/40">
                        Ignore suggestion
                      </button>
                    </div>
                  ) : (
                    <p className="text-xs text-slate mt-2">Marked as {a.user_status}</p>
                  )}
                </div>
              </Card>
            ))}
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
                  <p className="text-xs text-slate mt-0.5">
                    {a.transaction_date ? formatDate(a.transaction_date) : "Date unknown"}
                  </p>
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
