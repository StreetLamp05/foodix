"use client";

import { useEffect, useState } from "react";
import { fetchMenu } from "@/lib/dashboard-api";
import type { MenuItem, WidgetProps } from "@/lib/types/dashboard";

export default function MenuOverview({ restaurantId }: WidgetProps) {
  const [data, setData] = useState<MenuItem[] | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    fetchMenu(restaurantId)
      .then(setData)
      .catch(() => setError(true));
  }, [restaurantId]);

  if (error) return <p style={{ color: "var(--color-danger)" }}>Failed to load menu</p>;
  if (!data) return <Skeleton />;
  if (data.length === 0) return <p style={{ color: "var(--chart-text)" }}>No menu items</p>;

  return (
    <div style={{ maxHeight: 320, overflowY: "auto", scrollbarWidth: "none", msOverflowStyle: "none" }}>
      {data.map((item) => (
        <div
          key={item.menu_item_id}
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            padding: "0.5rem 0",
            borderBottom: "var(--card-border)",
          }}
        >
          <span style={{ fontWeight: 500 }}>{item.item_name}</span>
          <span style={{ fontWeight: 600, color: "var(--chart-primary)" }}>
            ${item.price.toFixed(2)}
          </span>
        </div>
      ))}
    </div>
  );
}

function Skeleton() {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
      {Array.from({ length: 5 }).map((_, i) => (
        <div key={i} style={{ height: 36, background: "var(--background)", borderRadius: 6, animation: "pulse 1.5s ease-in-out infinite" }} />
      ))}
    </div>
  );
}
