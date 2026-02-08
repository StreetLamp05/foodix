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
} from "recharts";
import { fetchInventory } from "@/lib/dashboard-api";
import type { InventoryItem, WidgetProps } from "@/lib/types/dashboard";

export default function InventoryLevels({ restaurantId }: WidgetProps) {
  const [data, setData] = useState<InventoryItem[] | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    fetchInventory(restaurantId)
      .then(setData)
      .catch(() => setError(true));
  }, [restaurantId]);

  if (error) return <p style={{ color: "var(--color-danger)" }}>Failed to load inventory</p>;
  if (!data) return <Skeleton />;
  if (data.length === 0) return <p style={{ color: "var(--chart-text)" }}>No inventory data</p>;

  const chartData = data.map((d) => ({
    name: d.ingredient_name.length > 15 ? d.ingredient_name.slice(0, 14) + "..." : d.ingredient_name,
    qty: d.inventory_end,
  }));

  return (
    <ResponsiveContainer width="100%" height={Math.max(200, chartData.length * 32)}>
      <BarChart data={chartData} layout="vertical" margin={{ left: 10, right: 20, top: 5, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid)" />
        <XAxis type="number" tick={{ fill: "var(--chart-text)", fontSize: 12 }} />
        <YAxis dataKey="name" type="category" width={110} tick={{ fill: "var(--chart-text)", fontSize: 12 }} />
        <Tooltip />
        <Bar dataKey="qty" fill="var(--chart-primary)" radius={[0, 4, 4, 0]} name="Current Qty" />
      </BarChart>
    </ResponsiveContainer>
  );
}

function Skeleton() {
  return <div style={{ height: 200, background: "var(--background)", borderRadius: "var(--card-radius)", animation: "pulse 1.5s ease-in-out infinite" }} />;
}
