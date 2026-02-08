"use client";

import { useEffect, useState } from "react";
import { fetchExpiringBatches } from "@/lib/dashboard-api";
import type { ExpiringBatch, WidgetProps } from "@/lib/types/dashboard";

function daysLeft(expDate: string) {
  const diff = (new Date(expDate).getTime() - Date.now()) / 86_400_000;
  return Math.ceil(diff);
}

function daysColor(days: number) {
  if (days <= 1) return "var(--color-danger)";
  if (days <= 3) return "var(--color-warning)";
  return "var(--chart-text)";
}

export default function ExpiringBatches({ restaurantId }: WidgetProps) {
  const [data, setData] = useState<ExpiringBatch[] | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    fetchExpiringBatches(restaurantId, 7)
      .then(setData)
      .catch(() => setError(true));
  }, [restaurantId]);

  if (error) return <p style={{ color: "var(--color-danger)" }}>Failed to load batches</p>;
  if (!data) return <Skeleton />;
  if (data.length === 0) return <p style={{ color: "var(--color-success)" }}>No batches expiring soon</p>;

  return (
    <div style={{ overflowX: "auto" }}>
      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.85rem" }}>
        <thead>
          <tr style={{ borderBottom: "var(--card-border)", textAlign: "left" }}>
            <th style={{ padding: "0.5rem 0.75rem", color: "var(--chart-text)", fontWeight: 600 }}>Ingredient</th>
            <th style={{ padding: "0.5rem 0.75rem", color: "var(--chart-text)", fontWeight: 600 }}>Qty</th>
            <th style={{ padding: "0.5rem 0.75rem", color: "var(--chart-text)", fontWeight: 600 }}>Supplier</th>
            <th style={{ padding: "0.5rem 0.75rem", color: "var(--chart-text)", fontWeight: 600 }}>Expires</th>
            <th style={{ padding: "0.5rem 0.75rem", color: "var(--chart-text)", fontWeight: 600 }}>Days Left</th>
          </tr>
        </thead>
        <tbody>
          {data.map((b) => {
            const dl = daysLeft(b.expiration_date);
            return (
              <tr key={b.batch_id} style={{ borderBottom: "var(--card-border)" }}>
                <td style={{ padding: "0.5rem 0.75rem" }}>{b.ingredient_name}</td>
                <td style={{ padding: "0.5rem 0.75rem" }}>{b.qty_remaining} {b.unit}</td>
                <td style={{ padding: "0.5rem 0.75rem" }}>{b.supplier_name || "—"}</td>
                <td style={{ padding: "0.5rem 0.75rem" }}>{b.expiration_date}</td>
                <td style={{ padding: "0.5rem 0.75rem", fontWeight: 700, color: daysColor(dl) }}>
                  {dl}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function Skeleton() {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
      {Array.from({ length: 3 }).map((_, i) => (
        <div key={i} style={{ height: 32, background: "var(--background)", borderRadius: 6, animation: "pulse 1.5s ease-in-out infinite" }} />
      ))}
    </div>
  );
}
