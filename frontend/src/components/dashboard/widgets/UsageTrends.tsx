"use client";

import { useEffect, useState } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  Legend,
} from "recharts";
import { fetchTrends } from "@/lib/dashboard-api";
import type { TrendDay, WidgetProps } from "@/lib/types/dashboard";

export default function UsageTrends({ restaurantId }: WidgetProps) {
  const [data, setData] = useState<TrendDay[] | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    fetchTrends(restaurantId, 30)
      .then(setData)
      .catch(() => setError(true));
  }, [restaurantId]);

  if (error) return <p style={{ color: "var(--color-danger)" }}>Failed to load trends</p>;
  if (!data) return <Skeleton />;
  if (data.length === 0) return <p style={{ color: "var(--chart-text)" }}>No trend data</p>;

  const chartData = data.map((d) => ({
    date: d.log_date.slice(5), // MM-DD
    usage: d.total_used,
    inventory: d.total_inventory,
  }));

  return (
    <ResponsiveContainer width="100%" height={260}>
      <LineChart data={chartData} margin={{ left: 0, right: 10, top: 5, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid)" />
        <XAxis dataKey="date" tick={{ fill: "var(--chart-text)", fontSize: 11 }} />
        <YAxis tick={{ fill: "var(--chart-text)", fontSize: 12 }} />
        <Tooltip />
        <Legend />
        <Line type="monotone" dataKey="usage" stroke="var(--chart-primary)" strokeWidth={2} dot={false} name="Usage" />
        <Line type="monotone" dataKey="inventory" stroke="var(--chart-tertiary)" strokeWidth={2} dot={false} name="Inventory" />
      </LineChart>
    </ResponsiveContainer>
  );
}

function Skeleton() {
  return <div style={{ height: 260, background: "var(--background)", borderRadius: "var(--card-radius)", animation: "pulse 1.5s ease-in-out infinite" }} />;
}
