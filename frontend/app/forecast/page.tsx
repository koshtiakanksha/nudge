"use client";

import { useEffect, useState } from "react";
import { Area, AreaChart, CartesianGrid, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "@/lib/api";
import { ForecastResponse } from "@/types/api";
import { formatCurrency, formatDate } from "@/lib/format";
import { Card, CardLabel } from "@/components/card";
import { PageHeader } from "@/components/page-header";
import { cn } from "@/lib/format";

export default function ForecastPage() {
  const [forecast, setForecast] = useState<ForecastResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .getForecast()
      .then(setForecast)
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <>
        <PageHeader title="Forecast" subtitle="Where your spending is headed this month" />
        <div className="px-8 py-12 text-sm text-slate">Crunching the numbers…</div>
      </>
    );
  }

  if (!forecast || forecast.points.length === 0) {
    return (
      <>
        <PageHeader title="Forecast" subtitle="Where your spending is headed this month" />
        <div className="px-8 py-12">
          <Card>
            <p className="text-sm text-slate">
              Not enough transaction history yet to forecast. Link and sync an account to get started.
            </p>
          </Card>
        </div>
      </>
    );
  }

  const chartData = forecast.points.map((p) => ({
    date: formatDate(p.date),
    predicted: p.predicted_spend,
    range: [p.lower_bound, p.upper_bound],
  }));

  return (
    <>
      <PageHeader title="Forecast" subtitle="Where your spending is headed this month" />

      <div className="px-8 py-6 max-w-4xl space-y-5">
        <div className="grid grid-cols-3 gap-5">
          <Card>
            <CardLabel>Projected month-end</CardLabel>
            <p className="text-2xl font-display font-semibold">{formatCurrency(forecast.month_end_projection)}</p>
          </Card>
          <Card>
            <CardLabel>Spend ceiling</CardLabel>
            <p className="text-2xl font-display font-semibold">
              {forecast.ceiling ? formatCurrency(forecast.ceiling) : "Not set"}
            </p>
          </Card>
          <Card className={cn(forecast.on_track ? "bg-moss/5 border-moss/20" : "bg-clay/5 border-clay/20")}>
            <CardLabel>Status</CardLabel>
            <p className={cn("text-2xl font-display font-semibold", forecast.on_track ? "text-moss" : "text-clay")}>
              {forecast.on_track ? "On track" : "Over ceiling"}
            </p>
          </Card>
        </div>

        <Card>
          <CardLabel>Next {forecast.days_remaining} days, projected daily spend</CardLabel>
          <div className="h-64 mt-3">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData} margin={{ top: 5, right: 10, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="fillPredicted" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#2F5D50" stopOpacity={0.35} />
                    <stop offset="95%" stopColor="#2F5D50" stopOpacity={0.02} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#DDD6C5" vertical={false} />
                <XAxis dataKey="date" tick={{ fontSize: 11, fill: "#5B6760" }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fontSize: 11, fill: "#5B6760" }} axisLine={false} tickLine={false} width={50} />
                <Tooltip
                  contentStyle={{ borderRadius: 8, borderColor: "#DDD6C5", fontSize: 12 }}
                  formatter={(value: number) => formatCurrency(value)}
                />
                <Area type="monotone" dataKey="predicted" stroke="#2F5D50" strokeWidth={2} fill="url(#fillPredicted)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>
    </>
  );
}
