"use client";

import { useEffect, useMemo, useState } from "react";
import { fetchInventory } from "@/lib/dashboard-api";
import type { InventoryItem } from "@/lib/types/dashboard";

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
  const [error, setError] = useState(false);
  const [page, setPage] = useState(1);

  useEffect(() => {
    let cancelled = false;

    fetchInventory(restaurantId)
      .then((data) => {
        if (cancelled) return;
        setInventory(data);
        setError(false);
      })
      .catch(() => {
        if (cancelled) return;
        setError(true);
      });

    return () => {
      cancelled = true;
    };
  }, [restaurantId]);

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
        <div style={{ display: "flex", gap: "0.5rem" }}>
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={currentPage === 1}
            style={pagerButtonStyle(currentPage === 1)}
          >
            Previous
          </button>
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
