"use client";

import { useEffect, useState } from "react";
import { fetchOverview } from "@/lib/dashboard-api";
import type { DashboardOverview, WidgetProps } from "@/lib/types/dashboard";

export default function TopStatsBar({ restaurantId }: WidgetProps) {
  const [data, setData] = useState<DashboardOverview | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    fetchOverview(restaurantId)
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, [restaurantId]);

  const stats = data ? [
    { label: "Total Ingredients", value: data.total_ingredients },
    { label: "Stockouts", value: data.stockout_count, color: "#ff6b6b" },
    { label: "Low Stock", value: data.low_stock_count, color: "#ffd93d" },
    { label: "Avg Inventory", value: data.avg_inventory.toFixed(1) },
    { label: "Avg Daily Usage", value: data.avg_daily_usage.toFixed(1) },
  ] : [];

  return (
    <div style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap", justifyContent: "flex-start" }}>
      {loading ? (
        Array.from({ length: 5 }).map((_, i) => (
          <div
            key={i}
            style={{
              background: "rgba(255, 255, 255, 0.08)",
              backdropFilter: "url(#squircleFilter)",
              WebkitBackdropFilter: "url(#squircleFilter)",
              border: "1px solid rgba(255, 255, 255, 0.2)",
              borderRadius: "50px",
              padding: "0.5rem 1rem",
              minWidth: "100px",
              height: "40px",
              animation: "pulse 1.5s ease-in-out infinite",
            }}
          />
        ))
      ) : stats.length > 0 ? (
        stats.map((s) => (
          <div
            key={s.label}
            style={{
              background: "rgba(255, 255, 255, 0.08)",
              backdropFilter: "url(#squircleFilter)",
              WebkitBackdropFilter: "url(#squircleFilter)",
              border: "1px solid rgba(255, 255, 255, 0.2)",
              borderRadius: "50px",
              padding: "0.5rem 1rem",
              display: "flex",
              alignItems: "center",
              gap: "0.5rem",
              transition: "all 0.2s cubic-bezier(0.2, 0, 0.2, 1)",
              cursor: "default",
              whiteSpace: "nowrap",
              boxShadow: "0 2px 8px rgba(0, 0, 0, 0.15), inset -1px -1px 2px rgba(255,255,255,0.05)",
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = "rgba(255, 255, 255, 0.15)";
              e.currentTarget.style.transform = "translateY(-2px)";
              e.currentTarget.style.boxShadow = "0 4px 16px rgba(0, 0, 0, 0.25), inset -1px -1px 2px rgba(255,255,255,0.08)";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = "rgba(255, 255, 255, 0.08)";
              e.currentTarget.style.transform = "translateY(0)";
              e.currentTarget.style.boxShadow = "0 2px 8px rgba(0, 0, 0, 0.15), inset -1px -1px 2px rgba(255,255,255,0.05)";
            }}
          >
            <div style={{ fontSize: "0.9rem", fontWeight: 800, color: s.color ?? "rgba(255, 255, 255, 0.95)", textShadow: "0 1px 2px rgba(0,0,0,0.3)" }}>
              {s.value}
            </div>
            <div style={{ fontSize: "0.65rem", color: "rgba(255, 255, 255, 0.7)", fontWeight: 500, textShadow: "0 1px 1px rgba(0,0,0,0.2)" }}>
              {s.label}
            </div>
          </div>
        ))
      ) : null}
    </div>
  );
}
