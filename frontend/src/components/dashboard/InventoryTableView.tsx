"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  addRestaurantIngredient,
  createIngredient,
  fetchIngredientCatalog,
  fetchInventory,
  fetchRestaurantIngredients,
  removeRestaurantIngredient,
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

const CATEGORIES = [
  "protein",
  "dairy",
  "produce",
  "bakery",
  "condiment",
  "dry_goods",
  "oil",
  "beverage",
];

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

  // Add existing ingredient state
  const [showAddItem, setShowAddItem] = useState(false);
  const [addMode, setAddMode] = useState<"existing" | "new">("existing");
  const [newIngredientId, setNewIngredientId] = useState<number | null>(null);
  const [newInitialStock, setNewInitialStock] = useState("");
  const [newLeadTimeDays, setNewLeadTimeDays] = useState("2");
  const [newSafetyStockDays, setNewSafetyStockDays] = useState("2");
  const [savingItem, setSavingItem] = useState(false);

  // Create new ingredient state
  const [newIngName, setNewIngName] = useState("");
  const [newIngUnit, setNewIngUnit] = useState("");
  const [newIngCategory, setNewIngCategory] = useState("");
  const [newIngUnitCost, setNewIngUnitCost] = useState("");
  const [newIngShelfLife, setNewIngShelfLife] = useState("");

  // Restock state
  const [restockId, setRestockId] = useState<number | null>(null);
  const [restockQty, setRestockQty] = useState("");
  const [restocking, setRestocking] = useState(false);

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

  function resetAddForm() {
    setShowAddItem(false);
    setAddMode("existing");
    setNewIngredientId(null);
    setNewInitialStock("");
    setNewLeadTimeDays("2");
    setNewSafetyStockDays("2");
    setNewIngName("");
    setNewIngUnit("");
    setNewIngCategory("");
    setNewIngUnitCost("");
    setNewIngShelfLife("");
  }

  async function handleAddExistingIngredient() {
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
      resetAddForm();
    } catch {
      alert("Failed to add inventory item.");
    } finally {
      setSavingItem(false);
    }
  }

  async function handleCreateNewIngredient() {
    const name = newIngName.trim();
    const unit = newIngUnit.trim();
    if (!name) { alert("Ingredient name is required."); return; }
    if (!unit) { alert("Unit is required."); return; }

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

    const unitCost = newIngUnitCost ? Number(newIngUnitCost) : 0;
    const shelfLife = newIngShelfLife ? Number(newIngShelfLife) : null;

    setSavingItem(true);
    try {
      const created = await createIngredient({
        ingredient_name: name,
        unit,
        unit_cost: unitCost,
        category: newIngCategory || undefined,
        shelf_life_days: shelfLife,
      });
      await addRestaurantIngredient(restaurantId, {
        ingredient_id: created.ingredient_id,
        lead_time_days: leadTimeDays,
        safety_stock_days: safetyStockDays,
      });
      await restockInventoryIngredient(restaurantId, created.ingredient_id, {
        restock_qty: initialStock,
      });
      await loadData();
      setPage(1);
      resetAddForm();
    } catch {
      alert("Failed to create ingredient.");
    } finally {
      setSavingItem(false);
    }
  }

  async function handleRestock(ingredientId: number) {
    const qty = Number(restockQty);
    if (Number.isNaN(qty) || qty <= 0) {
      alert("Restock quantity must be greater than zero.");
      return;
    }
    setRestocking(true);
    try {
      await restockInventoryIngredient(restaurantId, ingredientId, { restock_qty: qty });
      await loadData();
      setRestockId(null);
      setRestockQty("");
    } catch {
      alert("Failed to restock ingredient.");
    } finally {
      setRestocking(false);
    }
  }

  async function handleRemoveIngredient(ingredientId: number) {
    if (!confirm("Remove this ingredient from inventory tracking?")) return;
    try {
      await removeRestaurantIngredient(restaurantId, ingredientId);
      await loadData();
    } catch {
      alert("Failed to remove ingredient.");
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

  return (
    <div
      style={{
        overflow: "hidden",
        background: "rgba(255, 255, 255, 0.05)",
        border: "1px solid rgba(255, 255, 255, 0.15)",
        borderRadius: "24px",
        backdropFilter: "url(#liquidFilter)",
        WebkitBackdropFilter: "url(#liquidFilter)",
        boxShadow: "15px 20px 30px rgba(0,0,0,0.3), inset -2px -2px 6px rgba(255,255,255,0.05)",
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
        <div style={{ color: "var(--chart-text)", fontSize: "0.85rem", textShadow: "0 1px 2px rgba(0,0,0,0.4)" }}>
          Track a new ingredient and seed its initial stock.
        </div>
        <button onClick={() => { showAddItem ? resetAddForm() : setShowAddItem(true); }} style={actionButtonStyle}>
          {showAddItem ? "Cancel" : "Add Item"}
        </button>
      </div>

      {/* Add item panel */}
      {showAddItem && (
        <div
          style={{
            padding: "0.75rem 1rem",
            borderBottom: "1px solid rgba(0,0,0,0.08)",
            display: "flex",
            flexDirection: "column",
            gap: "0.5rem",
          }}
        >
          {/* Mode toggle */}
          <div style={{ display: "flex", gap: "0.5rem" }}>
            <button
              onClick={() => setAddMode("existing")}
              style={addMode === "existing" ? actionButtonStyle : secondaryButtonStyle}
            >
              From Catalog
            </button>
            <button
              onClick={() => setAddMode("new")}
              style={addMode === "new" ? actionButtonStyle : secondaryButtonStyle}
            >
              Create New
            </button>
          </div>

          {addMode === "existing" ? (
            <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap", alignItems: "center" }}>
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
              <input value={newInitialStock} onChange={(e) => setNewInitialStock(e.target.value)} placeholder="Initial stock" type="number" min={0.001} step="0.001" style={{ ...inputStyle, width: 120 }} />
              <input value={newLeadTimeDays} onChange={(e) => setNewLeadTimeDays(e.target.value)} placeholder="Lead time (days)" type="number" min={0} step={1} style={{ ...inputStyle, width: 130 }} />
              <input value={newSafetyStockDays} onChange={(e) => setNewSafetyStockDays(e.target.value)} placeholder="Safety stock (days)" type="number" min={0} step={1} style={{ ...inputStyle, width: 150 }} />
              <button onClick={handleAddExistingIngredient} disabled={savingItem} style={actionButtonStyle}>
                {savingItem ? "Adding..." : "Save"}
              </button>
            </div>
          ) : (
            <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap", alignItems: "center" }}>
              <input value={newIngName} onChange={(e) => setNewIngName(e.target.value)} placeholder="Ingredient name" style={{ ...inputStyle, minWidth: 180 }} />
              <input value={newIngUnit} onChange={(e) => setNewIngUnit(e.target.value)} placeholder="Unit (e.g. g, ml, piece)" style={{ ...inputStyle, width: 140 }} />
              <select value={newIngCategory} onChange={(e) => setNewIngCategory(e.target.value)} style={{ ...inputStyle, minWidth: 130 }}>
                <option value="">Category (optional)</option>
                {CATEGORIES.map((cat) => (
                  <option key={cat} value={cat}>{cat}</option>
                ))}
              </select>
              <input value={newIngUnitCost} onChange={(e) => setNewIngUnitCost(e.target.value)} placeholder="Unit cost" type="number" min={0} step="0.01" style={{ ...inputStyle, width: 100 }} />
              <input value={newIngShelfLife} onChange={(e) => setNewIngShelfLife(e.target.value)} placeholder="Shelf life (days)" type="number" min={0} step={1} style={{ ...inputStyle, width: 130 }} />
              <input value={newInitialStock} onChange={(e) => setNewInitialStock(e.target.value)} placeholder="Initial stock" type="number" min={0.001} step="0.001" style={{ ...inputStyle, width: 120 }} />
              <input value={newLeadTimeDays} onChange={(e) => setNewLeadTimeDays(e.target.value)} placeholder="Lead time (days)" type="number" min={0} step={1} style={{ ...inputStyle, width: 130 }} />
              <input value={newSafetyStockDays} onChange={(e) => setNewSafetyStockDays(e.target.value)} placeholder="Safety stock (days)" type="number" min={0} step={1} style={{ ...inputStyle, width: 150 }} />
              <button onClick={handleCreateNewIngredient} disabled={savingItem} style={actionButtonStyle}>
                {savingItem ? "Creating..." : "Create & Add"}
              </button>
            </div>
          )}
        </div>
      )}

      <div style={{ overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", minWidth: 960 }}>
          <thead>
            <tr style={{ background: "rgba(0,0,0,0.02)" }}>
              <th style={thStyle}>Ingredient</th>
              <th style={thStyle}>Category</th>
              <th style={thStyle}>Unit</th>
              <th style={thStyle}>In Stock</th>
              <th style={thStyle}>On Order</th>
              <th style={thStyle}>Avg Daily Usage (7d)</th>
              <th style={thStyle}>Last Log Date</th>
              <th style={thStyle}>Actions</th>
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
                <td style={tdStyle}>
                  <div style={{ display: "flex", gap: "0.35rem", alignItems: "center" }}>
                    {restockId === row.ingredient_id ? (
                      <>
                        <input
                          value={restockQty}
                          onChange={(e) => setRestockQty(e.target.value)}
                          placeholder="Qty"
                          type="number"
                          min={0.001}
                          step="0.001"
                          autoFocus
                          onKeyDown={(e) => e.key === "Enter" && handleRestock(row.ingredient_id)}
                          style={{ ...inputStyle, width: 80 }}
                        />
                        <button
                          onClick={() => void handleRestock(row.ingredient_id)}
                          disabled={restocking}
                          style={actionButtonStyle}
                        >
                          {restocking ? "..." : "OK"}
                        </button>
                        <button
                          onClick={() => { setRestockId(null); setRestockQty(""); }}
                          style={secondaryButtonStyle}
                        >
                          X
                        </button>
                      </>
                    ) : (
                      <>
                        <button
                          onClick={() => { setRestockId(row.ingredient_id); setRestockQty(""); }}
                          style={actionButtonStyle}
                        >
                          Restock
                        </button>
                        <button
                          onClick={() => void handleRemoveIngredient(row.ingredient_id)}
                          style={dangerButtonStyle}
                        >
                          Remove
                        </button>
                      </>
                    )}
                  </div>
                </td>
              </tr>
            ))}
            {pagedRows.length === 0 && (
              <tr>
                <td style={tdStyle} colSpan={8}>
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

const dangerButtonStyle: React.CSSProperties = {
  border: "none",
  background: "var(--color-danger)",
  color: "#fff",
  borderRadius: "var(--btn-radius)",
  padding: "0.3rem 0.6rem",
  fontSize: "0.75rem",
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
