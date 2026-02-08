"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  addRestaurantIngredient,
  fetchIngredientCatalog,
  fetchInventory,
  fetchRestaurantIngredients,
  restockInventoryIngredient,
} from "@/lib/dashboard-api";
import type {
  IngredientCatalogItem,
  InventoryItem,
  RestaurantIngredient,
} from "@/lib/types/dashboard";

interface InventoryTableViewProps {
  restaurantId: number;
}

const PAGE_SIZE = 10;

function formatDate(iso: string) {
  return iso.slice(0, 10);
}

function formatNumber(value: number | null | undefined, decimals: number) {
  if (value === null || value === undefined || Number.isNaN(value)) return "\u2014";
  return value.toFixed(decimals);
}

export default function InventoryTableView({ restaurantId }: InventoryTableViewProps) {
  const [inventory, setInventory] = useState<InventoryItem[] | null>(null);
  const [ingredients, setIngredients] = useState<IngredientCatalogItem[]>([]);
  const [restaurantIngredients, setRestaurantIngredients] = useState<RestaurantIngredient[]>([]);
  const [error, setError] = useState(false);
  const [page, setPage] = useState(1);
  const [showAddItem, setShowAddItem] = useState(false);
  const [newIngredientId, setNewIngredientId] = useState<number | null>(null);
  const [newInitialStock, setNewInitialStock] = useState("");
  const [newLeadTimeDays, setNewLeadTimeDays] = useState("2");
  const [newSafetyStockDays, setNewSafetyStockDays] = useState("2");
  const [savingItem, setSavingItem] = useState(false);

  const loadData = useCallback(async () => {
    const [inventoryRows, allIngredients, restaurantRows] = await Promise.all([
      fetchInventory(restaurantId),
      fetchIngredientCatalog(),
      fetchRestaurantIngredients(restaurantId),
    ]);
    setInventory(inventoryRows);
    setIngredients(allIngredients);
    setRestaurantIngredients(restaurantRows);
    setError(false);
  }, [restaurantId]);

  useEffect(() => {
    let cancelled = false;

    loadData()
      .then(() => {
        if (cancelled) return;
      })
      .catch(() => {
        if (cancelled) return;
        setError(true);
      });

    return () => {
      cancelled = true;
    };
  }, [loadData]);

  const selectableIngredients = useMemo(() => {
    const inRestaurant = new Set(restaurantIngredients.map((row) => row.ingredient_id));
    return ingredients.filter((item) => !inRestaurant.has(item.ingredient_id));
  }, [ingredients, restaurantIngredients]);

  const totalPages = useMemo(() => {
    if (!inventory || inventory.length === 0) return 1;
    return Math.ceil(inventory.length / PAGE_SIZE);
  }, [inventory]);

  const currentPage = Math.min(page, totalPages);

  const pagedRows = useMemo(() => {
    if (!inventory) return [];
    const start = (currentPage - 1) * PAGE_SIZE;
    return inventory.slice(start, start + PAGE_SIZE);
  }, [currentPage, inventory]);

  async function handleCreateInventoryItem() {
    if (!newIngredientId) {
      alert("Select an ingredient first.");
      return;
    }

    const initialStock = Number(newInitialStock);
    const leadTimeDays = Number(newLeadTimeDays);
    const safetyStockDays = Number(newSafetyStockDays);

    if (Number.isNaN(initialStock) || initialStock <= 0) {
      alert("Initial stock must be greater than zero.");
      return;
    }
    if (Number.isNaN(leadTimeDays) || leadTimeDays < 0) {
      alert("Lead time must be zero or greater.");
      return;
    }
    if (Number.isNaN(safetyStockDays) || safetyStockDays < 0) {
      alert("Safety stock must be zero or greater.");
      return;
    }

    setSavingItem(true);
    try {
      await addRestaurantIngredient(restaurantId, {
        ingredient_id: newIngredientId,
        lead_time_days: leadTimeDays,
        safety_stock_days: safetyStockDays,
      });
      await restockInventoryIngredient(restaurantId, newIngredientId, {
        restock_qty: initialStock,
      });
      await loadData();
      setPage(1);
      setShowAddItem(false);
      setNewIngredientId(null);
      setNewInitialStock("");
      setNewLeadTimeDays("2");
      setNewSafetyStockDays("2");
    } catch {
      alert("Failed to add inventory item.");
    } finally {
      setSavingItem(false);
    }
  }

  if (error) {
    return <p style={{ color: "var(--color-danger)" }}>Failed to load inventory data</p>;
  }

  if (!inventory) {
    return (
      <div
        style={{
          height: 240,
          background: "var(--background)",
          borderRadius: "var(--card-radius)",
          animation: "pulse 1.5s ease-in-out infinite",
        }}
      />
    );
  }

  if (inventory.length === 0) {
    return <p style={{ color: "var(--chart-text)" }}>No inventory data</p>;
  }

  return (
    <div
      style={{
        background: "var(--card-bg)",
        border: "var(--card-border)",
        borderRadius: "var(--card-radius)",
        boxShadow: "var(--card-shadow)",
        overflow: "hidden",
      }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          padding: "0.75rem 1rem",
          borderBottom: "1px solid rgba(0,0,0,0.08)",
        }}
      >
        <div style={{ color: "var(--chart-text)", fontSize: "0.85rem" }}>
          Track a new ingredient and seed its initial stock.
        </div>
        <button onClick={() => setShowAddItem((s) => !s)} style={actionButtonStyle}>
          Add Item
        </button>
      </div>

      {showAddItem && (
        <div
          style={{
            padding: "0.75rem 1rem",
            borderBottom: "1px solid rgba(0,0,0,0.08)",
            display: "flex",
            gap: "0.5rem",
            flexWrap: "wrap",
            alignItems: "center",
          }}
        >
          <select
            value={newIngredientId ?? ""}
            onChange={(e) => setNewIngredientId(e.target.value ? Number(e.target.value) : null)}
            style={{ ...inputStyle, minWidth: 220 }}
          >
            <option value="">Select ingredient</option>
            {selectableIngredients.map((ing) => (
              <option key={ing.ingredient_id} value={ing.ingredient_id}>
                {ing.ingredient_name} ({ing.unit})
              </option>
            ))}
          </select>
          <input
            value={newInitialStock}
            onChange={(e) => setNewInitialStock(e.target.value)}
            placeholder="Initial stock"
            type="number"
            min={0.001}
            step="0.001"
            style={{ ...inputStyle, width: 120 }}
          />
          <input
            value={newLeadTimeDays}
            onChange={(e) => setNewLeadTimeDays(e.target.value)}
            placeholder="Lead time (days)"
            type="number"
            min={0}
            step={1}
            style={{ ...inputStyle, width: 130 }}
          />
          <input
            value={newSafetyStockDays}
            onChange={(e) => setNewSafetyStockDays(e.target.value)}
            placeholder="Safety stock (days)"
            type="number"
            min={0}
            step={1}
            style={{ ...inputStyle, width: 150 }}
          />
          <button
            onClick={handleCreateInventoryItem}
            disabled={savingItem}
            style={actionButtonStyle}
          >
            {savingItem ? "Adding..." : "Save"}
          </button>
          <button onClick={() => setShowAddItem(false)} style={secondaryButtonStyle}>
            Cancel
          </button>
        </div>
      )}

      <div style={{ overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", minWidth: 860 }}>
          <thead>
            <tr style={{ background: "rgba(0,0,0,0.02)" }}>
              <th style={thStyle}>Ingredient</th>
              <th style={thStyle}>Category</th>
              <th style={thStyle}>Unit</th>
              <th style={thStyle}>In Stock</th>
              <th style={thStyle}>On Order</th>
              <th style={thStyle}>Avg Daily Usage (7d)</th>
              <th style={thStyle}>Last Log Date</th>
            </tr>
          </thead>
          <tbody>
            {pagedRows.map((row) => (
              <tr key={row.ingredient_id} style={{ borderTop: "1px solid rgba(0,0,0,0.06)" }}>
                <td style={tdStyle}>{row.ingredient_name}</td>
                <td style={tdStyle}>{row.category}</td>
                <td style={tdStyle}>{row.unit}</td>
                <td style={tdStyle}>{formatNumber(row.inventory_end, 1)}</td>
                <td style={tdStyle}>{formatNumber(row.on_order_qty, 1)}</td>
                <td style={tdStyle}>{formatNumber(row.avg_daily_usage_7d, 2)}</td>
                <td style={tdStyle}>{formatDate(row.log_date)}</td>
              </tr>
            ))}
            {pagedRows.length === 0 && (
              <tr>
                <td style={tdStyle} colSpan={7}>
                  <span style={{ color: "var(--chart-text)" }}>No inventory data yet.</span>
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          padding: "0.75rem 1rem",
          borderTop: "1px solid rgba(0,0,0,0.08)",
        }}
      >
        <span style={{ color: "var(--chart-text)", fontSize: "0.85rem" }}>
          Page {currentPage} of {totalPages}
        </span>
        <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={currentPage === 1}
            style={pagerButtonStyle(currentPage === 1)}
          >
            Previous
          </button>
          <label style={{ display: "flex", alignItems: "center", gap: "0.3rem", fontSize: "0.8rem", color: "var(--chart-text)" }}>
            Go to
            <input
              type="number"
              min={1}
              max={totalPages}
              value={currentPage}
              onChange={(e) => {
                const value = Number(e.target.value);
                if (Number.isNaN(value)) return;
                const clamped = Math.max(1, Math.min(totalPages, Math.trunc(value)));
                setPage(clamped);
              }}
              style={{
                width: 64,
                border: "var(--card-border)",
                borderRadius: 6,
                padding: "0.25rem 0.4rem",
                fontSize: "0.8rem",
                background: "var(--background)",
                color: "var(--foreground)",
              }}
            />
          </label>
          <button
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={currentPage === totalPages}
            style={pagerButtonStyle(currentPage === totalPages)}
          >
            Next
          </button>
        </div>
      </div>
    </div>
  );
}

const thStyle: React.CSSProperties = {
  textAlign: "left",
  padding: "0.75rem 1rem",
  fontSize: "0.78rem",
  color: "var(--chart-text)",
  fontWeight: 600,
  whiteSpace: "nowrap",
};

const tdStyle: React.CSSProperties = {
  padding: "0.75rem 1rem",
  fontSize: "0.85rem",
  whiteSpace: "nowrap",
};

const inputStyle: React.CSSProperties = {
  border: "var(--card-border)",
  borderRadius: 6,
  padding: "0.35rem 0.5rem",
  fontSize: "0.85rem",
  background: "var(--background)",
  color: "var(--foreground)",
};

const actionButtonStyle: React.CSSProperties = {
  border: "none",
  background: "var(--btn-bg)",
  color: "var(--btn-color)",
  borderRadius: "var(--btn-radius)",
  padding: "0.35rem 0.7rem",
  fontSize: "0.8rem",
  cursor: "pointer",
};

const secondaryButtonStyle: React.CSSProperties = {
  border: "var(--card-border)",
  background: "transparent",
  color: "var(--foreground)",
  borderRadius: "var(--btn-radius)",
  padding: "0.35rem 0.7rem",
  fontSize: "0.8rem",
  cursor: "pointer",
};

function pagerButtonStyle(disabled: boolean): React.CSSProperties {
  return {
    border: "var(--card-border)",
    background: disabled ? "rgba(0,0,0,0.06)" : "var(--btn-bg)",
    color: disabled ? "var(--chart-text)" : "var(--btn-color)",
    borderRadius: "var(--btn-radius)",
    padding: "0.35rem 0.7rem",
    fontSize: "0.8rem",
    cursor: disabled ? "not-allowed" : "pointer",
  };
}
