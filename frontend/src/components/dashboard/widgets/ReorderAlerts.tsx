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

  // Build combined list with fallback prediction calculation
  const items: ReorderItem[] = inventory.map((inv) => {
    const pred = predMap.get(inv.ingredient_id);
    let days_until_stockout = pred?.days_until_stockout ?? null;
    
    // Fallback calculation if API prediction is null
    if (days_until_stockout === null) {
      const usage = (inv as any).avg_daily_usage_7d ?? (inv as any).avg_daily_usage_28d ?? 0;
      const available = inv.inventory_end + ((inv as any).on_order_qty ?? 0);
      if (usage > 0) {
        days_until_stockout = Math.round(available / usage);
      }
    }
    
    return {
      ingredient_id: inv.ingredient_id,
      ingredient_name: inv.ingredient_name,
      unit: inv.unit,
      inventory_end: inv.inventory_end,
      days_until_stockout,
    };
  });

  // Filter based on timeframe - include items that are out, or within timeframe + buffer
  const filtered = items.filter((item) => {
    const isOut = item.inventory_end <= 0;
    const days = item.days_until_stockout;
    const buffer = Math.max(2, Math.floor(timeframe * 0.2)); // 20% buffer, minimum 2 days
    
    return isOut || (days !== null && days <= timeframe + buffer);
  });

  // Sort by urgency level (most urgent first)
  const getUrgencyPriority = (item: ReorderItem) => {
    const isOut = item.inventory_end <= 0;
    const daysUntilStockout = item.days_until_stockout;
    const days = daysUntilStockout !== null ? timeframe - daysUntilStockout : null;
    
    if (isOut || (daysUntilStockout !== null && daysUntilStockout <= 0)) return 1; // OUT OF STOCK
    if (days !== null && days >= 4) return 2; // URGENT  
    if (days !== null && days >= 2) return 3; // NEEDS REORDER
    if (days !== null && days > 0) return 4; // PLAN REORDER
    return 5; // MONITOR STOCK
  };

  const sortedFiltered = [...filtered].sort((a, b) => {
    const priorityA = getUrgencyPriority(a);
    const priorityB = getUrgencyPriority(b);
    return priorityA - priorityB; // Sort by priority (lower number = higher priority)
  });

  return (
    <div style={{ 
      padding: "1.5rem", 
      height: "100%", 
      display: "flex", 
      flexDirection: "column" 
    }}>
      {/* Time buttons */}
      <div style={{ display: "flex", gap: "0.5rem", marginBottom: "1.5rem" }}>
        {TIMEFRAMES.map((tf) => (
          <button
            key={tf}
            onClick={() => setTimeframe(tf)}
            style={{
              flex: 1,
              padding: "0.5rem 1rem",
              borderRadius: "8px",
              border: timeframe === tf ? "1px solid rgba(255, 255, 255, 0.3)" : "1px solid rgba(255, 255, 255, 0.15)",
              background: timeframe === tf 
                ? "rgba(255, 255, 255, 0.15)" 
                : "rgba(255, 255, 255, 0.05)",
              color: "rgba(255, 255, 255, 0.95)",
              cursor: "pointer",
              fontSize: "0.875rem",
              fontWeight: timeframe === tf ? "700" : "600",
              transition: "all 0.2s ease",
              boxShadow: timeframe === tf 
                ? "0 2px 8px rgba(255, 255, 255, 0.1), inset -1px -1px 3px rgba(255,255,255,0.05)" 
                : "0 1px 3px rgba(0, 0, 0, 0.1)",
              transform: timeframe === tf ? "translateY(-1px)" : "none",
              textShadow: timeframe === tf ? "0 1px 2px rgba(0,0,0,0.3)" : "0 1px 1px rgba(0,0,0,0.2)",
              backdropFilter: "blur(10px)",
              WebkitBackdropFilter: "blur(10px)",
            }}
            onMouseEnter={(e) => {
              if (timeframe !== tf) {
                e.currentTarget.style.background = "rgba(255, 255, 255, 0.1)";
                e.currentTarget.style.transform = "translateY(-1px)";
              }
            }}
            onMouseLeave={(e) => {
              if (timeframe !== tf) {
                e.currentTarget.style.background = "rgba(255, 255, 255, 0.05)";
                e.currentTarget.style.transform = "none";
              }
            }}
          >
            {tf}d
          </button>
        ))}
      </div>

      {/* Alert list with scrolling */}
      {sortedFiltered.length === 0 ? (
        <div style={{ 
          color: "rgba(255, 255, 255, 0.9)", 
          fontSize: "0.9rem", 
          padding: "1.5rem", 
          background: "rgba(255, 255, 255, 0.05)", 
          backdropFilter: "url(#squircleFilter)",
          WebkitBackdropFilter: "url(#squircleFilter)",
          borderRadius: "12px",
          border: "1px solid rgba(255, 255, 255, 0.15)",
          textAlign: "center",
          boxShadow: "0 2px 8px rgba(0, 0, 0, 0.2)"
        }}>
          All ingredients are stocked for the next {timeframe} days
        </div>
      ) : (
        <div style={{ 
          display: "flex", 
          flexDirection: "column", 
          gap: "0.75rem",
          flex: 1,
          minHeight: 0,
          overflowY: "auto",
          paddingRight: "0.5rem"
        }}>
          {sortedFiltered.map((item) => (
            <ReorderRow key={item.ingredient_id} item={item} timeframe={timeframe} />
          ))}
        </div>
      )}
    </div>
  );
}

function ReorderRow({ item, timeframe }: { item: ReorderItem; timeframe: number }) {
  const isOut = item.inventory_end <= 0;
  const daysUntilStockout = item.days_until_stockout;
  const days = daysUntilStockout !== null ? timeframe - daysUntilStockout : null;

  let urgencyColor = "rgba(255, 255, 255, 0.7)";
  let urgencyLabel = "OK";
  let borderColor = "1px solid rgba(255, 255, 255, 0.15)";
  
  if (isOut || (daysUntilStockout !== null && daysUntilStockout <= 0)) {
    urgencyColor = "#ff6b6b";
    urgencyLabel = "OUT OF STOCK";
    borderColor = "1px solid rgba(255, 107, 107, 0.3)";
  } else if (days !== null && days >= 4) {
    urgencyColor = "#ff6b6b";
    urgencyLabel = "URGENT";
    borderColor = "1px solid rgba(255, 107, 107, 0.3)";
  } else if (days !== null && days >= 2) {
    urgencyColor = "#ffd93d";
    urgencyLabel = "NEEDS REORDER";
    borderColor = "1px solid rgba(255, 217, 61, 0.3)";
  } else if (days !== null && days > 0) {
    urgencyColor = "#ffd93d";
    urgencyLabel = "PLAN REORDER";
    borderColor = "1px solid rgba(255, 217, 61, 0.3)";
  } else if (days !== null && days <= 0) {
    urgencyColor = "#51cf66";
    urgencyLabel = "MONITOR STOCK";
    borderColor = "1px solid rgba(81, 207, 102, 0.3)";
  }

  return (
    <div style={{ 
      padding: "1rem", 
      border: borderColor, 
      borderRadius: "12px",
      background: "rgba(255, 255, 255, 0.05)",
      backdropFilter: "blur(10px)",
      WebkitBackdropFilter: "blur(10px)",
      boxShadow: "0 2px 8px rgba(0, 0, 0, 0.2), inset -1px -1px 3px rgba(255,255,255,0.05)",
      transition: "transform 0.2s ease, box-shadow 0.2s ease",
      color: "rgba(255, 255, 255, 0.95)"
    }}
    onMouseEnter={(e) => {
      e.currentTarget.style.transform = "translateY(-2px)";
      e.currentTarget.style.boxShadow = "0 4px 16px rgba(0, 0, 0, 0.3), inset -1px -1px 3px rgba(255,255,255,0.05)";
      e.currentTarget.style.background = "rgba(255, 255, 255, 0.08)";
    }}
    onMouseLeave={(e) => {
      e.currentTarget.style.transform = "translateY(0)";
      e.currentTarget.style.boxShadow = "0 2px 8px rgba(0, 0, 0, 0.2), inset -1px -1px 3px rgba(255,255,255,0.05)";
      e.currentTarget.style.background = "rgba(255, 255, 255, 0.05)";
    }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <div style={{ 
            fontWeight: "700", 
            fontSize: "1rem", 
            color: "rgba(255, 255, 255, 0.95)",
            marginBottom: "0.25rem",
            textShadow: "0 1px 2px rgba(0,0,0,0.3)"
          }}>
            {item.ingredient_name}
          </div>
          <div style={{ fontSize: "0.875rem", color: "rgba(255, 255, 255, 0.7)", textShadow: "0 1px 2px rgba(0,0,0,0.2)" }}>
            Current: <span style={{ fontWeight: "600" }}>{item.inventory_end} {item.unit}</span>
          </div>
        </div>
        <div style={{ textAlign: "right" }}>
          <div style={{ 
            color: urgencyColor, 
            fontWeight: "900", 
            fontSize: "0.875rem",
            marginBottom: "0.25rem",
            padding: "0.25rem 0.5rem",
            borderRadius: "6px",
            background: "transparent",
            textShadow: "0 1px 2px rgba(0,0,0,0.3)"
          }}>
            {urgencyLabel}
          </div>
          <div style={{ fontSize: "0.8rem", color: "rgba(255, 255, 255, 0.7)", fontWeight: "500", textShadow: "0 1px 2px rgba(0,0,0,0.2)" }}>
            {daysUntilStockout !== null ? `${daysUntilStockout} days left` : "No prediction"}
            {days !== null && (
              <div style={{ fontSize: "0.75rem", color: "rgba(255, 255, 255, 0.6)", marginTop: "0.125rem", fontWeight: "400" }}>
                ({days > 0 ? `${days} days short` : `${Math.abs(days)} days extra`})
              </div>
            )}
          </div>
        </div>
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
