"use client";

import { useEffect, useState } from "react";
import { fetchOverview } from "@/lib/dashboard-api";
import type { DashboardOverview, WidgetProps } from "@/lib/types/dashboard";

export default function OverviewStats({ restaurantId }: WidgetProps) {
  const [data, setData] = useState<DashboardOverview | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    fetchOverview(restaurantId)
      .then(setData)
      .catch(() => setError(true));
  }, [restaurantId]);

  if (error) return <p style={{ color: "var(--color-danger)" }}>Failed to load overview</p>;
  if (!data) return <LoadingSkeleton />;

  const stats = [
    { label: "Total Ingredients", value: data.total_ingredients },
    { label: "Stockouts", value: data.stockout_count, color: "var(--color-danger)" },
    { label: "Low Stock", value: data.low_stock_count, color: "var(--color-warning)" },
    { label: "Avg Inventory", value: data.avg_inventory.toFixed(1) },
    { label: "Avg Daily Usage", value: data.avg_daily_usage.toFixed(1) },
  ];

  return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(130px, 1fr))", gap: "0.75rem" }}>
      {stats.map((s) => (
        <div
          key={s.label}
          style={{
            background: "var(--background)",
            borderRadius: "var(--card-radius)",
            padding: "0.75rem 1rem",
            border: "var(--card-border)",
            textAlign: "center",
          }}
        >
          <div style={{ fontSize: "1.5rem", fontWeight: 700, color: s.color ?? "var(--foreground)" }}>
            {s.value}
          </div>
          <div style={{ fontSize: "0.75rem", color: "var(--chart-text)", marginTop: "0.25rem" }}>
            {s.label}
          </div>
        </div>
      ))}
    </div>
  );
}

function LoadingSkeleton() {
  return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(130px, 1fr))", gap: "0.75rem" }}>
      {Array.from({ length: 5 }).map((_, i) => (
        <div
          key={i}
          style={{
            background: "var(--background)",
            borderRadius: "var(--card-radius)",
            padding: "0.75rem 1rem",
            border: "var(--card-border)",
            height: 72,
            animation: "pulse 1.5s ease-in-out infinite",
          }}
        />
      ))}
    </div>
  );
}
