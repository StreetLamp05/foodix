"use client";

import { useEffect, useState, useCallback } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  Cell,
  LineChart,
  Line,
  ReferenceLine,
  Legend,
} from "recharts";
import {
  fetchInventory,
  fetchPredictions,
  fetchInventoryHistory,
} from "@/lib/dashboard-api";
import type {
  InventoryItem,
  InventoryHistory,
  Prediction,
  PredictionsResponse,
  WidgetProps,
} from "@/lib/types/dashboard";

// --- helpers ---

function stockColor(item: InventoryItem) {
  if (item.inventory_end <= 0) return "var(--color-danger)";
  if (item.avg_daily_usage_7d > 0 && item.inventory_end < item.avg_daily_usage_7d * 3)
    return "var(--color-warning)";
  return "var(--chart-primary)";
}

/** Build projected depletion points from current stock to 0. */
function buildProjection(
  currentStock: number,
  daysUntilStockout: number | null,
  startDate: Date
) {
  const days = daysUntilStockout ?? 30; // fallback to 30 if unknown
  const pts: { date: string; projected: number }[] = [];
  const dailyBurn = days > 0 ? currentStock / days : 0;
  const count = Math.min(days, 60); // cap projection length

  for (let d = 0; d <= count; d++) {
    const dt = new Date(startDate);
    dt.setDate(dt.getDate() + d);
    const label = `${String(dt.getMonth() + 1).padStart(2, "0")}-${String(dt.getDate()).padStart(2, "0")}`;
    pts.push({ date: label, projected: Math.max(0, +(currentStock - dailyBurn * d).toFixed(1)) });
  }
  return pts;
}

function formatDate(iso: string) {
  return iso.slice(5); // MM-DD
}

// --- sub-components ---

function ForecastDetail({
  item,
  prediction,
  restaurantId,
  onClose,
}: {
  item: InventoryItem;
  prediction: Prediction | undefined;
  restaurantId: number;
  onClose: () => void;
}) {
  const [history, setHistory] = useState<InventoryHistory[] | null>(null);

  useEffect(() => {
    fetchInventoryHistory(restaurantId, item.ingredient_id, 14).then(setHistory).catch(() => setHistory([]));
  }, [restaurantId, item.ingredient_id]);

  if (!history) {
    return (
      <div style={{ height: 260, display: "flex", alignItems: "center", justifyContent: "center", color: "var(--chart-text)" }}>
        Loading history...
      </div>
    );
  }

  // Build the merged dataset: actual history + projected future
  const actual = history.map((h) => ({
    date: formatDate(h.log_date),
    actual: h.inventory_end,
    projected: undefined as number | undefined,
  }));

  const daysUntil = prediction?.days_until_stockout ?? null;
  const lastStock = item.inventory_end;
  const today = new Date();
  const projectionPts = buildProjection(lastStock, daysUntil, today);

  // The first projection point overlaps with "today", connect the lines
  const projected = projectionPts.map((p) => ({
    date: p.date,
    actual: undefined as number | undefined,
    projected: p.projected,
  }));

  // Merge: history then projection. The bridge point has both values so lines connect.
  const todayLabel = `${String(today.getMonth() + 1).padStart(2, "0")}-${String(today.getDate()).padStart(2, "0")}`;
  const bridge = { date: todayLabel, actual: lastStock, projected: lastStock };
  const chartData = [...actual.filter((a) => a.date !== todayLabel), bridge, ...projected.slice(1)];

  const confidence = prediction ? prediction.confidence : null;
  const stockoutDays = daysUntil !== null ? `${daysUntil} days` : "unknown";

  return (
    <div
      style={{
        marginTop: "1rem",
        padding: "1rem",
        background: "var(--background)",
        borderRadius: "var(--card-radius)",
        border: "var(--card-border)",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.75rem" }}>
        <div>
          <span style={{ fontWeight: 600, fontSize: "1rem" }}>{item.ingredient_name}</span>
          <span style={{ color: "var(--chart-text)", fontSize: "0.8rem", marginLeft: "0.5rem" }}>
            ({item.unit}) &middot; Stockout in {stockoutDays}
            {confidence && (
              <span
                style={{
                  marginLeft: "0.4rem",
                  padding: "0.1rem 0.4rem",
                  borderRadius: 4,
                  fontSize: "0.7rem",
                  fontWeight: 600,
                  background: confidence === "high" ? "var(--color-success)" : "var(--color-warning)",
                  color: "#fff",
                }}
              >
                {confidence}
              </span>
            )}
          </span>
        </div>
        <button
          onClick={onClose}
          style={{
            background: "none",
            border: "none",
            cursor: "pointer",
            fontSize: "1.1rem",
            color: "var(--chart-text)",
            lineHeight: 1,
          }}
          aria-label="Close detail"
        >
          &times;
        </button>
      </div>

      <ResponsiveContainer width="100%" height={260}>
        <LineChart data={chartData} margin={{ left: 0, right: 10, top: 5, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid)" />
          <XAxis dataKey="date" tick={{ fill: "var(--chart-text)", fontSize: 11 }} />
          <YAxis tick={{ fill: "var(--chart-text)", fontSize: 12 }} />
          <Tooltip />
          <Legend />
          <ReferenceLine x={todayLabel} stroke="var(--chart-text)" strokeDasharray="4 4" label={{ value: "Today", fill: "var(--chart-text)", fontSize: 11 }} />
          <Line
            type="monotone"
            dataKey="actual"
            stroke="var(--chart-primary)"
            strokeWidth={2}
            dot={{ r: 3, fill: "var(--chart-primary)" }}
            connectNulls={false}
            name="Actual Stock"
          />
          <Line
            type="monotone"
            dataKey="projected"
            stroke="var(--color-danger)"
            strokeWidth={2}
            strokeDasharray="6 3"
            dot={false}
            connectNulls={false}
            name="Predicted Depletion"
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

// --- main widget ---

export default function StockForecast({ restaurantId }: WidgetProps) {
  const [inventory, setInventory] = useState<InventoryItem[] | null>(null);
  const [predictions, setPredictions] = useState<PredictionsResponse | null>(null);
  const [error, setError] = useState(false);
  const [selectedId, setSelectedId] = useState<number | null>(null);

  useEffect(() => {
    Promise.all([fetchInventory(restaurantId), fetchPredictions(restaurantId)])
      .then(([inv, pred]) => {
        setInventory(inv);
        setPredictions(pred);
      })
      .catch(() => setError(true));
  }, [restaurantId]);

  const handleBarClick = useCallback((ingredientId: number) => {
    setSelectedId((prev) => (prev === ingredientId ? null : ingredientId));
  }, []);

  if (error) return <p style={{ color: "var(--color-danger)" }}>Failed to load stock data</p>;
  if (!inventory) return <Skeleton />;
  if (inventory.length === 0) return <p style={{ color: "var(--chart-text)" }}>No inventory data</p>;

  const predMap = new Map<number, Prediction>();
  if (predictions) {
    for (const p of predictions.all) predMap.set(p.ingredient_id, p);
  }

  const chartData = inventory.map((d) => ({
    id: d.ingredient_id,
    name: d.ingredient_name.length > 18 ? d.ingredient_name.slice(0, 17) + "\u2026" : d.ingredient_name,
    qty: d.inventory_end,
    _item: d,
  }));

  const selectedItem = selectedId !== null ? inventory.find((i) => i.ingredient_id === selectedId) : null;

  return (
    <div>
      <p style={{ fontSize: "0.8rem", color: "var(--chart-text)", margin: "0 0 0.5rem" }}>
        Click a bar to see its depletion forecast
      </p>

      <ResponsiveContainer width="100%" height={Math.max(220, chartData.length * 30)}>
        <BarChart
          data={chartData}
          layout="vertical"
          margin={{ left: 10, right: 20, top: 5, bottom: 5 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid)" />
          <XAxis type="number" tick={{ fill: "var(--chart-text)", fontSize: 12 }} />
          <YAxis dataKey="name" type="category" width={120} tick={{ fill: "var(--chart-text)", fontSize: 12 }} />
          <Tooltip
            formatter={(value?: number) => [value?.toFixed(1) ?? "—", "Stock"]}
            cursor={{ fill: "rgba(0,0,0,0.05)" }}
          />
          <Bar
            dataKey="qty"
            name="Current Stock"
            radius={[0, 4, 4, 0]}
            cursor="pointer"
            onClick={(_data: unknown, index: number) => {
              handleBarClick(chartData[index].id);
            }}
          >
            {chartData.map((entry) => (
              <Cell
                key={entry.id}
                fill={
                  selectedId === entry.id
                    ? "var(--chart-secondary)"
                    : stockColor(entry._item)
                }
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>

      {selectedItem && (
        <ForecastDetail
          item={selectedItem}
          prediction={predMap.get(selectedItem.ingredient_id)}
          restaurantId={restaurantId}
          onClose={() => setSelectedId(null)}
        />
      )}
    </div>
  );
}

function Skeleton() {
  return (
    <div
      style={{
        height: 260,
        background: "var(--background)",
        borderRadius: "var(--card-radius)",
        animation: "pulse 1.5s ease-in-out infinite",
      }}
    />
  );
}
