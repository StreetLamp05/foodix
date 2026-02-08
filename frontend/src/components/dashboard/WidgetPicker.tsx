"use client";

import type { WidgetId } from "@/lib/types/dashboard";
import { WIDGET_REGISTRY } from "@/lib/constants/widget-registry";

interface WidgetPickerProps {
  visibleWidgetIds: WidgetId[];
  onToggle: (id: WidgetId) => void;
  onReset: () => void;
}

export default function WidgetPicker({
  visibleWidgetIds,
  onToggle,
  onReset,
}: WidgetPickerProps) {
  return (
    <aside
      style={{
        background: "var(--card-bg)",
        border: "var(--card-border)",
        borderRadius: "var(--card-radius)",
        padding: "var(--card-padding)",
        boxShadow: "var(--card-shadow)",
        minWidth: 220,
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.75rem" }}>
        <h3 style={{ fontSize: "var(--card-header-size)", fontWeight: "var(--card-header-weight)" as never, color: "var(--card-header-color)", margin: 0 }}>
          Widgets
        </h3>
        <button
          onClick={onReset}
          style={{
            fontSize: "0.75rem",
            color: "var(--chart-text)",
            background: "none",
            border: "none",
            cursor: "pointer",
            textDecoration: "underline",
          }}
        >
          Reset
        </button>
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
        {WIDGET_REGISTRY.map((w) => (
          <label
            key={w.id}
            style={{
              display: "flex",
              alignItems: "flex-start",
              gap: "0.5rem",
              cursor: "pointer",
              fontSize: "0.85rem",
            }}
          >
            <input
              type="checkbox"
              checked={visibleWidgetIds.includes(w.id)}
              onChange={() => onToggle(w.id)}
              style={{ marginTop: "0.2rem" }}
            />
            <div>
              <div style={{ fontWeight: 500 }}>{w.label}</div>
              <div style={{ fontSize: "0.75rem", color: "var(--chart-text)" }}>
                {w.description}
              </div>
            </div>
          </label>
        ))}
      </div>
    </aside>
  );
}
