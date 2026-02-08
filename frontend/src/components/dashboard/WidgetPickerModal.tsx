"use client";

import type { WidgetId } from "@/lib/types/dashboard";
import { WIDGET_REGISTRY } from "@/lib/constants/widget-registry";

interface WidgetPickerModalProps {
  visibleWidgetIds: WidgetId[];
  onToggle: (id: WidgetId) => void;
  onReset: () => void;
  onClose: () => void;
}

export default function WidgetPickerModal({
  visibleWidgetIds,
  onToggle,
  onReset,
  onClose,
}: WidgetPickerModalProps) {
  return (
    <div
      onClick={onClose}
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 1000,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "rgba(0, 0, 0, 0.5)",
        backdropFilter: "blur(4px)",
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          background: "var(--card-bg)",
          border: "var(--card-border)",
          borderRadius: "var(--card-radius)",
          boxShadow: "0 16px 48px rgba(0, 0, 0, 0.2)",
          padding: "1.5rem",
          width: "100%",
          maxWidth: 420,
          maxHeight: "80vh",
          overflowY: "auto",
          margin: "1rem",
        }}
      >
        {/* Header */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            marginBottom: "1rem",
          }}
        >
          <h2
            style={{
              fontSize: "1.1rem",
              fontWeight: 700,
              margin: 0,
              color: "var(--card-header-color)",
            }}
          >
            Widgets
          </h2>
          <div style={{ display: "flex", gap: "0.75rem", alignItems: "center" }}>
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
            <button
              onClick={onClose}
              aria-label="Close"
              style={{
                background: "none",
                border: "none",
                cursor: "pointer",
                padding: "4px",
                display: "flex",
                alignItems: "center",
                color: "var(--chart-text)",
              }}
            >
              <svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                <path d="M4 4l10 10M14 4L4 14" />
              </svg>
            </button>
          </div>
        </div>

        {/* Widget list */}
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
                padding: "0.5rem",
                borderRadius: 8,
                background: visibleWidgetIds.includes(w.id)
                  ? "rgba(128, 128, 128, 0.08)"
                  : "transparent",
              }}
            >
              <input
                type="checkbox"
                checked={visibleWidgetIds.includes(w.id)}
                onChange={() => onToggle(w.id)}
                style={{ marginTop: "0.2rem" }}
              />
              <div>
                <div style={{ fontWeight: 500 }}>
                  {w.label}{" "}
                  <span
                    style={{
                      fontWeight: 400,
                      color: "var(--chart-text)",
                      fontSize: "0.75rem",
                    }}
                  >
                    ({w.defaultSize})
                  </span>
                </div>
                <div style={{ fontSize: "0.75rem", color: "var(--chart-text)" }}>
                  {w.description}
                </div>
              </div>
            </label>
          ))}
        </div>
      </div>
    </div>
  );
}
