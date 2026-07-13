"use client";

import { useEffect, useMemo, useState } from "react";
import { AlertTriangle, CheckCircle2, FileUp, RefreshCw, Trash2 } from "lucide-react";
import { api } from "@/lib/api";
import { StatementTransaction, StatementUpload } from "@/types/api";
import { Card, CardLabel } from "@/components/card";
import { PageHeader } from "@/components/page-header";
import { formatCurrency, formatDate, cn } from "@/lib/format";

const CATEGORIES = [
  "Rent", "Utilities", "Groceries", "Dining", "Transportation", "Shopping", "Travel",
  "Entertainment", "Healthcare", "Education", "Subscriptions", "Transfers", "Income",
  "Savings", "Debt Payments", "Fees", "Other",
];

export default function StatementsPage() {
  const [statements, setStatements] = useState<StatementUpload[]>([]);
  const [selected, setSelected] = useState<StatementUpload | null>(null);
  const [transactions, setTransactions] = useState<StatementTransaction[]>([]);
  const [file, setFile] = useState<File | null>(null);
  const [bankName, setBankName] = useState("");
  const [statementMonth, setStatementMonth] = useState(new Date().toISOString().slice(0, 7));
  const [mappingNeeded, setMappingNeeded] = useState(false);
  const [columns, setColumns] = useState<string[]>([]);
  const [mapping, setMapping] = useState({ date: "", description: "", amount: "", debit: "", credit: "", merchant: "", category: "" });
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadStatements = () =>
    api
      .listStatements()
      .then((items) => {
        setStatements(items);
        if (!selected && items[0]) setSelected(items[0]);
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Could not load statements"))
      .finally(() => setLoading(false));

  useEffect(() => {
    loadStatements();
  }, []);

  useEffect(() => {
    if (!selected) {
      setTransactions([]);
      return;
    }
    api.listStatementTransactions(selected.id).then(setTransactions).catch(() => setTransactions([]));
  }, [selected?.id]);

  const totals = useMemo(() => {
    const income = transactions.filter((t) => !t.is_ignored && t.amount > 0).reduce((sum, t) => sum + t.amount, 0);
    const spending = transactions.filter((t) => !t.is_ignored && t.amount < 0).reduce((sum, t) => sum + Math.abs(t.amount), 0);
    const lowConfidence = transactions.filter((t) => (t.confidence_score ?? 1) < 0.65).length;
    const anomalies = transactions.filter((t) => t.is_anomaly).length;
    return { income, spending, lowConfidence, anomalies };
  }, [transactions]);

  const handleUpload = async () => {
    if (!file) return;
    setUploading(true);
    setError(null);
    setMessage(null);
    const form = new FormData();
    form.append("file", file);
    if (bankName) form.append("bank_name", bankName);
    form.append("statement_month", `${statementMonth}-01`);
    if (mappingNeeded) form.append("mapping", JSON.stringify(mapping));
    try {
      const result = await api.uploadStatement(form);
      setMessage(result.message);
      setMappingNeeded(result.needs_mapping);
      setSelected(result.statement);
      if (result.needs_mapping && file) {
        setColumns(await readHeaders(file));
      } else {
        setFile(null);
        await loadStatements();
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed");
      if (file) setColumns(await readHeaders(file));
    } finally {
      setUploading(false);
    }
  };

  const updateTxn = async (txn: StatementTransaction, patch: Partial<StatementTransaction> & { apply_to_similar?: boolean }) => {
    const updated = await api.updateStatementTransaction(txn.id, {
      ...patch,
      nudge_category: patch.category || undefined,
    });
    setTransactions((prev) => prev.map((item) => (item.id === txn.id ? updated : item)));
  };

  const handleDelete = async (statement: StatementUpload) => {
    await api.deleteStatement(statement.id);
    setSelected(null);
    await loadStatements();
  };

  const saveReview = async () => {
    setSaving(true);
    setMessage(null);
    try {
      const result = await api.saveReviewedStatements();
      setMessage(`Saved reviewed data for ${result.reviewed_statements} statement${result.reviewed_statements === 1 ? "" : "s"}.`);
      await loadStatements();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not save review");
    } finally {
      setSaving(false);
    }
  };

  return (
    <>
      <PageHeader title="AI Bank Statement Analyzer" subtitle="Upload statements, review transactions, and build a smarter budget" />
      <div className="px-8 py-6 max-w-6xl space-y-6">
        <Card className="bg-moss/5 border-moss/20">
          <div className="flex gap-3">
            <FileUp className="text-moss mt-0.5" size={22} />
            <div>
              <p className="font-medium">Upload your bank statement and we will analyze your spending, detect patterns, and create a smart budget.</p>
              <p className="text-sm text-slate mt-1">Your statement is used only to analyze your spending and build your budget. You can delete uploaded data anytime.</p>
            </div>
          </div>
        </Card>

        <Card>
          <CardLabel>Upload statement</CardLabel>
          <div className="grid grid-cols-1 md:grid-cols-[1fr_180px_180px_auto] gap-3 mt-2">
            <input type="file" accept=".csv,.txt,.xlsx,.pdf" onChange={(e) => setFile(e.target.files?.[0] || null)} className="text-sm" />
            <input value={bankName} onChange={(e) => setBankName(e.target.value)} placeholder="Bank name" className="border border-line rounded-md px-3 py-2 text-sm" />
            <input type="month" value={statementMonth} onChange={(e) => setStatementMonth(e.target.value)} className="border border-line rounded-md px-3 py-2 text-sm" />
            <button onClick={handleUpload} disabled={!file || uploading} className="px-4 py-2 bg-moss text-paper rounded-md text-sm font-medium disabled:opacity-60">
              {uploading ? "Uploading..." : "Upload"}
            </button>
          </div>
          <p className="text-xs text-slate mt-3">Supported now: CSV and TXT. XLSX is attempted when the server has spreadsheet support. PDF uploads are validated but require CSV export for parsing.</p>
          {mappingNeeded && (
            <div className="mt-4 border border-gold/30 bg-gold/5 rounded-md p-4">
              <p className="text-sm font-medium">Manual column mapping needed</p>
              <p className="text-xs text-slate mt-1">Tell Nudge which columns contain the required fields, then upload again.</p>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mt-3">
                <MappingSelect label="Transaction date" value={mapping.date} columns={columns} onChange={(date) => setMapping((prev) => ({ ...prev, date }))} />
                <MappingSelect label="Description" value={mapping.description} columns={columns} onChange={(description) => setMapping((prev) => ({ ...prev, description }))} />
                <MappingSelect label="Amount" value={mapping.amount} columns={columns} onChange={(amount) => setMapping((prev) => ({ ...prev, amount }))} />
                <MappingSelect label="Debit" value={mapping.debit} columns={columns} onChange={(debit) => setMapping((prev) => ({ ...prev, debit }))} />
                <MappingSelect label="Credit" value={mapping.credit} columns={columns} onChange={(credit) => setMapping((prev) => ({ ...prev, credit }))} />
                <MappingSelect label="Merchant" value={mapping.merchant} columns={columns} onChange={(merchant) => setMapping((prev) => ({ ...prev, merchant }))} />
              </div>
            </div>
          )}
          {message && <p className="text-sm text-moss mt-3 flex gap-1.5"><CheckCircle2 size={15} /> {message}</p>}
          {error && <p className="text-sm text-clay mt-3 flex gap-1.5"><AlertTriangle size={15} /> {error}</p>}
        </Card>

        <div className="grid grid-cols-1 lg:grid-cols-[280px_1fr] gap-5">
          <Card>
            <CardLabel>Uploaded statements</CardLabel>
            {loading ? <p className="text-sm text-slate">Loading...</p> : statements.length === 0 ? (
              <p className="text-sm text-slate">No statements uploaded yet.</p>
            ) : (
              <div className="space-y-2">
                {statements.map((statement) => (
                  <button
                    key={statement.id}
                    onClick={() => setSelected(statement)}
                    className={cn("w-full text-left border border-line rounded-md p-3 text-sm hover:bg-line/40", selected?.id === statement.id && "border-moss bg-moss/5")}
                  >
                    <span className="block font-medium">{statement.bank_name || "Bank statement"}</span>
                    <span className="block text-xs text-slate">{formatDate(statement.statement_month)} · {statement.status}</span>
                  </button>
                ))}
              </div>
            )}
          </Card>

          <Card>
            <div className="flex items-start justify-between gap-4">
              <div>
                <CardLabel>Review parsed transactions</CardLabel>
                {selected ? (
                  <p className="text-sm text-slate">{selected.file_name} · {transactions.length} transactions</p>
                ) : (
                  <p className="text-sm text-slate">Select a statement to review transactions.</p>
                )}
              </div>
              {selected && (
                <button onClick={() => handleDelete(selected)} className="text-clay hover:bg-clay/10 rounded-md p-2" title="Delete statement">
                  <Trash2 size={16} />
                </button>
              )}
            </div>

            {selected?.status === "failed" && (
              <div className="mt-4 border border-clay/30 bg-clay/5 rounded-md p-3 text-sm text-clay">
                Parsing failed: {selected.error_message || "We could not parse this file."} Re-upload as CSV or TXT.
              </div>
            )}

            {transactions.length > 0 && (
              <>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3 my-5">
                  <Metric label="Income" value={formatCurrency(totals.income)} />
                  <Metric label="Expenses" value={formatCurrency(totals.spending)} />
                  <Metric label="Low confidence" value={totals.lowConfidence.toString()} />
                  <Metric label="Anomalies" value={totals.anomalies.toString()} />
                </div>
                <div className="overflow-auto border border-line rounded-md">
                  <table className="w-full text-sm">
                    <thead className="bg-line/30 text-xs text-slate">
                      <tr>
                        <th className="text-left p-2">Date</th>
                        <th className="text-left p-2">Merchant</th>
                        <th className="text-right p-2">Amount</th>
                        <th className="text-left p-2">Category</th>
                        <th className="text-left p-2">Flags</th>
                      </tr>
                    </thead>
                    <tbody>
                      {transactions.map((txn) => (
                        <tr key={txn.id} className={cn("border-t border-line/60", txn.is_ignored && "opacity-50")}>
                          <td className="p-2 whitespace-nowrap">{formatDate(txn.date)}</td>
                          <td className="p-2 min-w-52">
                            <input value={txn.merchant_name || txn.description} onChange={(e) => updateTxn(txn, { merchant_name: e.target.value })} className="w-full border border-line rounded px-2 py-1" />
                            <p className="text-xs text-slate truncate">{txn.raw_description}</p>
                          </td>
                          <td className={cn("p-2 text-right font-mono", txn.amount < 0 ? "text-clay" : "text-moss")}>{formatCurrency(txn.amount)}</td>
                          <td className="p-2">
                            <select
                              value={txn.category || "Other"}
                              onChange={(e) => updateTxn(txn, { category: e.target.value, apply_to_similar: true })}
                              className="border border-line rounded px-2 py-1"
                            >
                              {CATEGORIES.map((cat) => <option key={cat}>{cat}</option>)}
                            </select>
                            {(txn.confidence_score ?? 1) < 0.65 && <span className="block text-[10px] text-gold mt-1">low confidence</span>}
                          </td>
                          <td className="p-2">
                            <label className="block text-xs"><input type="checkbox" checked={txn.is_ignored} onChange={(e) => updateTxn(txn, { is_ignored: e.target.checked })} /> Ignore</label>
                            <label className="block text-xs"><input type="checkbox" checked={txn.is_recurring} onChange={(e) => updateTxn(txn, { is_recurring: e.target.checked })} /> Recurring</label>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <button onClick={saveReview} disabled={saving} className="mt-4 px-4 py-2 bg-moss text-paper rounded-md text-sm font-medium disabled:opacity-60 flex items-center gap-1.5">
                  <RefreshCw size={15} /> {saving ? "Saving..." : "Save reviewed data"}
                </button>
              </>
            )}
          </Card>
        </div>
      </div>
    </>
  );
}

async function readHeaders(file: File): Promise<string[]> {
  if (!file.name.toLowerCase().match(/\.(csv|txt)$/)) return [];
  const firstLine = (await file.text()).split(/\r?\n/)[0] || "";
  return firstLine.split(firstLine.includes("\t") ? "\t" : ",").map((h) => h.replace(/^"|"$/g, "").trim()).filter(Boolean);
}

function MappingSelect({ label, value, columns, onChange }: { label: string; value: string; columns: string[]; onChange: (value: string) => void }) {
  return (
    <label className="text-sm">
      <span className="block text-slate mb-1">{label}</span>
      <select value={value} onChange={(e) => onChange(e.target.value)} className="w-full border border-line rounded-md px-3 py-2 text-sm">
        <option value="">Select column</option>
        {columns.map((column) => <option key={column} value={column}>{column}</option>)}
      </select>
    </label>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="border border-line rounded-md p-3">
      <p className="text-xs text-slate">{label}</p>
      <p className="font-display text-xl font-semibold">{value}</p>
    </div>
  );
}
