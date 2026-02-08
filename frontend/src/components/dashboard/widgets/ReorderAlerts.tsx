"use client";

import { useEffect, useState } from "react";
import { fetchInventory, fetchPredictions } from "@/lib/dashboard-api";
import type {
  InventoryItem,
  Prediction,
  PredictionsResponse,
  WidgetProps,
} from "@/lib/types/dashboard";

const TIMEFRAMES = [1, 3, 7, 14, 30] as const;

interface ReorderItem {
  ingredient_id: number;
  ingredient_name: string;
  unit: string;
  inventory_end: number;
  days_until_stockout: number | null;
}

export default function ReorderAlerts({ restaurantId }: WidgetProps) {
  const [inventory, setInventory] = useState<InventoryItem[] | null>(null);
  const [predictions, setPredictions] = useState<PredictionsResponse | null>(null);
  const [error, setError] = useState(false);
  const [timeframe, setTimeframe] = useState<number>(7);

  useEffect(() => {
    Promise.all([fetchInventory(restaurantId), fetchPredictions(restaurantId)])
      .then(([inv, pred]) => {
        setInventory(inv);
        setPredictions(pred);
      })
      .catch(() => setError(true));
  }, [restaurantId]);

  if (error) return <p style={{ color: "var(--color-danger)" }}>Failed to load reorder data</p>;
  if (!inventory) return <Skeleton />;

  const predMap = new Map<number, Prediction>();
  if (predictions) {
    for (const p of predictions.all) predMap.set(p.ingredient_id, p);
  }

  // Build combined list
  const items: ReorderItem[] = inventory.map((inv) => {
    const pred = predMap.get(inv.ingredient_id);
    return {
      ingredient_id: inv.ingredient_id,
      ingredient_name: inv.ingredient_name,
      unit: inv.unit,
      inventory_end: inv.inventory_end,
      days_until_stockout: pred?.days_until_stockout ?? null,
    };
  });

  // Filter: already out of stock OR days_until_stockout within timeframe
  const filtered = items
    .filter((it) => {
      if (it.inventory_end <= 0) return true;
      if (it.days_until_stockout !== null && it.days_until_stockout <= timeframe) return true;
      return false;
    })
    .sort((a, b) => {
      // Already out of stock first (treat as -1), then ascending by days
      const da = a.inventory_end <= 0 ? -1 : (a.days_until_stockout ?? Infinity);
      const db = b.inventory_end <= 0 ? -1 : (b.days_until_stockout ?? Infinity);
      return da - db;
    });

  return (
    <div>
      {/* Timeframe selector pills */}
      <div style={{ display: "flex", gap: "0.35rem", marginBottom: "0.75rem", flexWrap: "wrap" }}>
        {TIMEFRAMES.map((tf) => (
          <button
            key={tf}
            onClick={() => setTimeframe(tf)}
            style={{
              padding: "0.25rem 0.6rem",
              borderRadius: "var(--btn-radius)",
              border: "1px solid",
              borderColor: timeframe === tf ? "var(--btn-bg)" : "var(--chart-grid)",
              background: timeframe === tf ? "var(--btn-bg)" : "transparent",
              color: timeframe === tf ? "var(--btn-color)" : "var(--foreground)",
              cursor: "pointer",
              fontSize: "0.8rem",
              fontWeight: 500,
              transition: "all 0.15s",
            }}
          >
            {tf}d
          </button>
        ))}
      </div>

      {/* Alert list */}
      {filtered.length === 0 ? (
        <p style={{ color: "var(--color-success)", fontSize: "0.9rem" }}>
          All ingredients are stocked for the next {timeframe} days
        </p>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "0.4rem" }}>
          {filtered.map((item) => (
            <ReorderRow key={item.ingredient_id} item={item} />
          ))}
        </div>
      )}
    </div>
  );
}

function ReorderRow({ item }: { item: ReorderItem }) {
  const isOut = item.inventory_end <= 0;
  const days = item.days_until_stockout;

  let daysColor = "var(--foreground)";
  if (isOut || (days !== null && days <= 1)) {
    daysColor = "var(--color-danger)";
  } else if (days !== null && days <= 3) {
    daysColor = "var(--color-warning)";
  }

  const daysLabel = isOut ? "OUT" : days !== null ? `${days}d` : "—";

  return (
    <div
      style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        padding: "0.5rem 0.65rem",
        borderRadius: "var(--card-radius)",
        border: `1px solid ${isOut ? "#fca5a5" : "var(--chart-grid)"}`,
        background: isOut ? "#fef2f2" : "var(--card-bg)",
      }}
    >
      <span style={{ fontWeight: 500, fontSize: "0.9rem" }}>{item.ingredient_name}</span>
      <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", fontSize: "0.8rem" }}>
        <span style={{ color: "var(--chart-text)" }}>
          {item.inventory_end.toFixed(1)} {item.unit}
        </span>
        <span style={{ fontWeight: 700, color: daysColor, minWidth: "2.5rem", textAlign: "right" }}>
          {daysLabel}
        </span>
      </div>
    </div>
  );
}

function Skeleton() {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
      {Array.from({ length: 4 }).map((_, i) => (
        <div
          key={i}
          style={{
            height: 40,
            background: "var(--background)",
            borderRadius: "var(--card-radius)",
            animation: "pulse 1.5s ease-in-out infinite",
          }}
        />
      ))}
    </div>
  );
}
