"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { UserProfile } from "@/types/api";
import { Card, CardLabel } from "@/components/card";
import { PageHeader } from "@/components/page-header";

export default function SettingsPage() {
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [form, setForm] = useState({ monthly_income: "", spend_ceiling: "", buffer_pct: "10" });
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    api.getMe().then((p) => {
      setProfile(p);
      setForm({
        monthly_income: p.monthly_income?.toString() || "",
        spend_ceiling: p.spend_ceiling?.toString() || "",
        buffer_pct: ((p.buffer_pct ?? 0.1) * 100).toString(),
      });
    });
  }, []);

  const handleSave = async () => {
    setSaving(true);
    setSaved(false);
    try {
      const updated = await api.updateMe({
        monthly_income: parseFloat(form.monthly_income) || undefined,
        spend_ceiling: parseFloat(form.spend_ceiling) || undefined,
        buffer_pct: parseFloat(form.buffer_pct) / 100 || undefined,
      });
      setProfile(updated);
      setSaved(true);
    } finally {
      setSaving(false);
    }
  };

  const handleUseLocation = () => {
    navigator.geolocation?.getCurrentPosition(async (pos) => {
      const updated = await api.updateMe({
        location_lat: pos.coords.latitude,
        location_lng: pos.coords.longitude,
      });
      setProfile(updated);
    });
  };

  return (
    <>
      <PageHeader title="Settings" subtitle="Income, ceiling, and the basics Nudge plans around" />

      <div className="px-8 py-6 max-w-lg space-y-5">
        <Card>
          <CardLabel>Monthly income</CardLabel>
          <input
            type="number"
            value={form.monthly_income}
            onChange={(e) => setForm({ ...form, monthly_income: e.target.value })}
            placeholder="6000"
            className="w-full border border-line rounded-md px-3 py-2 text-sm mt-1"
          />
        </Card>

        <Card>
          <CardLabel>Spend ceiling (optional)</CardLabel>
          <p className="text-xs text-slate mb-2">
            The max you want to spend this month. If left blank, Nudge derives it from income minus your buffer.
          </p>
          <input
            type="number"
            value={form.spend_ceiling}
            onChange={(e) => setForm({ ...form, spend_ceiling: e.target.value })}
            placeholder="4200"
            className="w-full border border-line rounded-md px-3 py-2 text-sm"
          />
        </Card>

        <Card>
          <CardLabel>Savings buffer</CardLabel>
          <p className="text-xs text-slate mb-2">Percent of income reserved as a safety cushion each month.</p>
          <div className="flex items-center gap-2">
            <input
              type="number"
              value={form.buffer_pct}
              onChange={(e) => setForm({ ...form, buffer_pct: e.target.value })}
              className="w-24 border border-line rounded-md px-3 py-2 text-sm"
            />
            <span className="text-sm text-slate">%</span>
          </div>
        </Card>

        <Card>
          <CardLabel>Location</CardLabel>
          <p className="text-xs text-slate mb-2">Used to find nearby deals and events.</p>
          {profile?.location_lat ? (
            <p className="text-sm">
              {profile.location_lat.toFixed(3)}, {profile.location_lng?.toFixed(3)}
            </p>
          ) : (
            <button
              onClick={handleUseLocation}
              className="text-sm text-moss hover:underline"
            >
              Use my current location
            </button>
          )}
        </Card>

        <div className="flex items-center gap-3">
          <button
            onClick={handleSave}
            disabled={saving}
            className="px-5 py-2 bg-moss text-paper rounded-md text-sm font-medium hover:bg-moss2 transition-colors disabled:opacity-60"
          >
            {saving ? "Saving…" : "Save settings"}
          </button>
          {saved && <span className="text-sm text-moss">Saved.</span>}
        </div>
      </div>
    </>
  );
}
