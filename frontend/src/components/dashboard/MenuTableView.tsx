"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  addMenuItemIngredient,
  createMenuItem,
  deleteMenuItem,
  deleteMenuItemIngredient,
  fetchIngredientCatalog,
  fetchMenu,
  fetchMenuItemDetail,
} from "@/lib/dashboard-api";
import type { IngredientCatalogItem, MenuItem, MenuItemDetail } from "@/lib/types/dashboard";

interface MenuTableViewProps {
  restaurantId: number;
}

const PAGE_SIZE = 10;

function formatCurrency(value: number | null | undefined) {
  if (value === null || value === undefined || Number.isNaN(value)) return "\u2014";
  return `$${value.toFixed(2)}`;
}

function formatNumber(value: number | null | undefined, decimals: number) {
  if (value === null || value === undefined || Number.isNaN(value)) return "\u2014";
  return value.toFixed(decimals);
}

export default function MenuTableView({ restaurantId }: MenuTableViewProps) {
  const [menu, setMenu] = useState<MenuItem[] | null>(null);
  const [error, setError] = useState(false);
  const [page, setPage] = useState(1);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [detail, setDetail] = useState<MenuItemDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState(false);
  const [ingredients, setIngredients] = useState<IngredientCatalogItem[]>([]);

  const [showAddMenu, setShowAddMenu] = useState(false);
  const [newMenuName, setNewMenuName] = useState("");
  const [newMenuPrice, setNewMenuPrice] = useState("");
  const [savingMenu, setSavingMenu] = useState(false);

  const [showAddIngredient, setShowAddIngredient] = useState(false);
  const [newIngredientId, setNewIngredientId] = useState<number | null>(null);
  const [newQtyPerItem, setNewQtyPerItem] = useState("");
  const [savingIngredient, setSavingIngredient] = useState(false);

  const loadMenu = useCallback(async () => {
    try {
      const rows = await fetchMenu(restaurantId);
      setMenu(rows);
      setError(false);
      return rows;
    } catch {
      setError(true);
      return null;
    }
  }, [restaurantId]);

  const loadDetail = useCallback(async (menuItemId: number) => {
    setDetailLoading(true);
    setDetailError(false);
    try {
      const data = await fetchMenuItemDetail(menuItemId);
      setDetail(data);
      setDetailError(false);
    } catch {
      setDetailError(true);
      setDetail(null);
    } finally {
      setDetailLoading(false);
    }
  }, []);

  useEffect(() => {
    setMenu(null);
    setError(false);
    setPage(1);
    setSelectedId(null);
    setDetail(null);
    setShowAddIngredient(false);
    setShowAddMenu(false);
    setNewMenuName("");
    setNewMenuPrice("");
    setNewIngredientId(null);
    setNewQtyPerItem("");
    void loadMenu();
  }, [loadMenu]);

  useEffect(() => {
    let cancelled = false;
    fetchIngredientCatalog()
      .then((rows) => {
        if (cancelled) return;
        setIngredients(rows);
      })
      .catch(() => {
        if (cancelled) return;
        setIngredients([]);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const totalPages = useMemo(() => {
    if (!menu || menu.length === 0) return 1;
    return Math.ceil(menu.length / PAGE_SIZE);
  }, [menu]);

  const currentPage = Math.min(page, totalPages);

  const pagedRows = useMemo(() => {
    if (!menu) return [];
    const start = (currentPage - 1) * PAGE_SIZE;
    return menu.slice(start, start + PAGE_SIZE);
  }, [currentPage, menu]);

  const selectableIngredients = useMemo(() => {
    if (!detail) return ingredients;
    const inBom = new Set(detail.ingredients.map((i) => i.ingredient_id));
    return ingredients.filter((i) => !inBom.has(i.ingredient_id));
  }, [detail, ingredients]);

  async function handleSelectMenuItem(menuItemId: number) {
    if (selectedId === menuItemId) {
      setSelectedId(null);
      setDetail(null);
      setDetailError(false);
      setDetailLoading(false);
      setShowAddIngredient(false);
      return;
    }
    setSelectedId(menuItemId);
    setShowAddIngredient(false);
    await loadDetail(menuItemId);
  }

  async function handleCreateMenuItem() {
    const itemName = newMenuName.trim();
    const price = Number(newMenuPrice);
    if (!itemName) {
      alert("Menu item name is required.");
      return;
    }
    if (Number.isNaN(price) || price < 0) {
      alert("Price must be a valid non-negative number.");
      return;
    }

    setSavingMenu(true);
    try {
      const created = await createMenuItem(restaurantId, { item_name: itemName, price });
      const rows = await loadMenu();
      if (rows) {
        const index = rows.findIndex((r) => r.menu_item_id === created.menu_item_id);
        if (index >= 0) {
          setPage(Math.floor(index / PAGE_SIZE) + 1);
        }
      }
      setSelectedId(created.menu_item_id);
      await loadDetail(created.menu_item_id);
      setShowAddMenu(false);
      setNewMenuName("");
      setNewMenuPrice("");
    } catch {
      alert("Failed to add menu item.");
    } finally {
      setSavingMenu(false);
    }
  }

  async function handleAddIngredientToBom() {
    if (!selectedId || !newIngredientId) {
      alert("Select an ingredient first.");
      return;
    }
    const qty = Number(newQtyPerItem);
    if (Number.isNaN(qty) || qty <= 0) {
      alert("Quantity per item must be greater than zero.");
      return;
    }

    setSavingIngredient(true);
    try {
      await addMenuItemIngredient(selectedId, {
        ingredient_id: newIngredientId,
        qty_per_item: qty,
      });
      await loadDetail(selectedId);
      setShowAddIngredient(false);
      setNewIngredientId(null);
      setNewQtyPerItem("");
    } catch {
      alert("Failed to add ingredient.");
    } finally {
      setSavingIngredient(false);
    }
  }

  async function handleDeleteMenuItem(menuItemId: number) {
    if (!confirm("Delete this menu item?")) return;
    try {
      await deleteMenuItem(menuItemId);
      if (selectedId === menuItemId) {
        setSelectedId(null);
        setDetail(null);
      }
      await loadMenu();
    } catch {
      alert("Failed to delete menu item.");
    }
  }

  async function handleDeleteIngredientFromBom(ingredientId: number) {
    if (!selectedId) return;
    if (!confirm("Delete this ingredient from the BOM?")) return;
    try {
      await deleteMenuItemIngredient(selectedId, ingredientId);
      await loadDetail(selectedId);
    } catch {
      alert("Failed to delete ingredient.");
    }
  }

  if (error) {
    return <p style={{ color: "var(--color-danger)" }}>Failed to load menu items</p>;
  }

  if (!menu) {
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
    <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
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
          <div style={{ color: "var(--chart-text)", fontSize: "0.85rem" }}>
            Click a row to open ingredient BOM details.
          </div>
          <button
            onClick={() => setShowAddMenu((s) => !s)}
            style={actionButtonStyle}
          >
            Add Item
          </button>
        </div>

        {showAddMenu && (
          <div style={{ padding: "0.75rem 1rem", borderBottom: "1px solid rgba(0,0,0,0.08)", display: "flex", gap: "0.5rem", flexWrap: "wrap", alignItems: "center" }}>
            <input
              value={newMenuName}
              onChange={(e) => setNewMenuName(e.target.value)}
              placeholder="Item name"
              style={inputStyle}
            />
            <input
              value={newMenuPrice}
              onChange={(e) => setNewMenuPrice(e.target.value)}
              placeholder="Price"
              type="number"
              min={0}
              step="0.01"
              style={{ ...inputStyle, width: 120 }}
            />
            <button onClick={handleCreateMenuItem} disabled={savingMenu} style={actionButtonStyle}>
              {savingMenu ? "Adding..." : "Save"}
            </button>
            <button onClick={() => setShowAddMenu(false)} style={secondaryButtonStyle}>
              Cancel
            </button>
          </div>
        )}

        <div style={{ overflowX: "auto", marginRight: "2px" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", minWidth: 760 }}>
            <thead>
              <tr style={{ background: "rgba(0,0,0,0.02)" }}>
                <th style={thStyle}>Item Name</th>
                <th style={thStyle}>Price</th>
                <th style={thStyle}>Active</th>
                <th style={thStyle}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {pagedRows.map((row) => (
                <tr
                  key={row.menu_item_id}
                  onClick={() => handleSelectMenuItem(row.menu_item_id)}
                  style={{
                    borderTop: "1px solid rgba(0,0,0,0.06)",
                    cursor: "pointer",
                    background: selectedId === row.menu_item_id ? "rgba(37,99,235,0.10)" : "transparent",
                  }}
                >
                  <td style={tdStyle}>{row.item_name}</td>
                  <td style={tdStyle}>{formatCurrency(row.price)}</td>
                  <td style={tdStyle}>{row.is_active ? "Yes" : "No"}</td>
                  <td style={tdStyle}>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        void handleDeleteMenuItem(row.menu_item_id);
                      }}
                      style={dangerButtonStyle}
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
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

      <div
        style={{
          padding: "1rem",
          background: "rgba(255, 255, 255, 0.05)",
          border: "1px solid rgba(255, 255, 255, 0.15)",
          borderRadius: "24px",
          backdropFilter: "url(#liquidFilter)",
          WebkitBackdropFilter: "url(#liquidFilter)",
          boxShadow: "15px 20px 30px rgba(0,0,0,0.3), inset -2px -2px 6px rgba(255,255,255,0.05)",
        }}
      >
        {!selectedId && (
          <p style={{ margin: 0, color: "var(--chart-text)", textShadow: "0 1px 2px rgba(0,0,0,0.4)" }}>
            Select a menu item to manage ingredients.
          </p>
        )}

        {selectedId && detailLoading && (
          <p style={{ margin: 0, color: "var(--chart-text)" }}>Loading menu item detail...</p>
        )}

        {selectedId && detailError && (
          <p style={{ margin: 0, color: "var(--color-danger)" }}>
            Failed to load menu item detail
          </p>
        )}

        {detail && (
          <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "1rem" }}>
              <div>
                <h3 style={{ margin: 0, fontSize: "1rem" }}>{detail.item_name}</h3>
                <p style={{ margin: "0.25rem 0 0", color: "var(--chart-text)", fontSize: "0.85rem" }}>
                  Price: {formatCurrency(detail.price)} | Ingredients: {detail.ingredients.length}
                </p>
              </div>
              <button onClick={() => setShowAddIngredient((s) => !s)} style={actionButtonStyle}>
                Add Item
              </button>
            </div>

            {showAddIngredient && (
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
                <input
                  value={newQtyPerItem}
                  onChange={(e) => setNewQtyPerItem(e.target.value)}
                  placeholder="Qty per item"
                  type="number"
                  min={0}
                  step="0.001"
                  style={{ ...inputStyle, width: 130 }}
                />
                <button onClick={handleAddIngredientToBom} disabled={savingIngredient} style={actionButtonStyle}>
                  {savingIngredient ? "Adding..." : "Save"}
                </button>
                <button onClick={() => setShowAddIngredient(false)} style={secondaryButtonStyle}>
                  Cancel
                </button>
              </div>
            )}

            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", minWidth: 780 }}>
                <thead>
                  <tr style={{ background: "rgba(0,0,0,0.02)" }}>
                    <th style={thStyle}>Ingredient</th>
                    <th style={thStyle}>Unit</th>
                    <th style={thStyle}>Qty Per Item</th>
                    <th style={thStyle}>Unit Cost</th>
                    <th style={thStyle}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {detail.ingredients.map((ing) => (
                    <tr key={ing.ingredient_id} style={{ borderTop: "1px solid rgba(0,0,0,0.06)" }}>
                      <td style={tdStyle}>{ing.ingredient_name}</td>
                      <td style={tdStyle}>{ing.unit}</td>
                      <td style={tdStyle}>{formatNumber(ing.qty_per_item, 3)}</td>
                      <td style={tdStyle}>{formatCurrency(ing.unit_cost)}</td>
                      <td style={tdStyle}>
                        <button
                          onClick={() => void handleDeleteIngredientFromBom(ing.ingredient_id)}
                          style={dangerButtonStyle}
                        >
                          Delete Item
                        </button>
                      </td>
                    </tr>
                  ))}
                  {detail.ingredients.length === 0 && (
                    <tr>
                      <td style={tdStyle} colSpan={5}>
                        <span style={{ color: "var(--chart-text)" }}>No ingredients in this BOM yet.</span>
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}
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
