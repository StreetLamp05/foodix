"use client";

import { useEffect, useState } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  Cell,
} from "recharts";
import { fetchPredictions } from "@/lib/dashboard-api";
import type { PredictionsResponse, WidgetProps } from "@/lib/types/dashboard";

function riskColor(days: number | null) {
  if (days === null) return "var(--chart-text)";
  if (days <= 3) return "var(--color-danger)";
  if (days <= 7) return "var(--color-warning)";
  return "var(--color-success)";
}

export default function PredictionsChart({ restaurantId }: WidgetProps) {
  const [data, setData] = useState<PredictionsResponse | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    fetchPredictions(restaurantId)
      .then(setData)
      .catch(() => setError(true));
  }, [restaurantId]);

  if (error) return <p style={{ color: "var(--color-danger)" }}>Failed to load predictions</p>;
  if (!data) return <Skeleton />;
  if (data.all.length === 0) return <p style={{ color: "var(--chart-text)" }}>No predictions yet</p>;

  const chartData = data.all
    .filter((p) => p.days_until_stockout !== null)
    .map((p) => ({
      name: p.ingredient_name.length > 15 ? p.ingredient_name.slice(0, 14) + "..." : p.ingredient_name,
      days: p.days_until_stockout as number,
    }))
    .sort((a, b) => a.days - b.days);

  if (chartData.length === 0) return <p style={{ color: "var(--chart-text)" }}>No stockout estimates</p>;

  return (
    <ResponsiveContainer width="100%" height={Math.max(200, chartData.length * 32)}>
      <BarChart data={chartData} layout="vertical" margin={{ left: 10, right: 20, top: 5, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid)" />
        <XAxis type="number" tick={{ fill: "var(--chart-text)", fontSize: 12 }} label={{ value: "Days", position: "insideBottomRight", offset: -5, fill: "var(--chart-text)" }} />
        <YAxis dataKey="name" type="category" width={110} tick={{ fill: "var(--chart-text)", fontSize: 12 }} />
        <Tooltip />
        <Bar dataKey="days" name="Days Until Stockout" radius={[0, 4, 4, 0]}>
          {chartData.map((entry, i) => (
            <Cell key={i} fill={riskColor(entry.days)} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

function Skeleton() {
  return <div style={{ height: 200, background: "var(--background)", borderRadius: "var(--card-radius)", animation: "pulse 1.5s ease-in-out infinite" }} />;
}
