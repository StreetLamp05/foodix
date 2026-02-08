"use client";

import type { ReactNode } from "react";

interface DashboardCardProps {
  title: string;
  children: ReactNode;
  isDragMode?: boolean;
  isBeingDragged?: boolean;
  isDropTarget?: boolean;
}

export default function DashboardCard({
  title,
  children,
  isDragMode = false,
  isBeingDragged = false,
  isDropTarget = false,
}: DashboardCardProps) {
  return (
    <div
      style={{
        background: "var(--card-bg)",
        borderRadius: "var(--card-radius)",
        border: isDropTarget
          ? "2px dashed var(--color-success)"
          : "var(--card-border)",
        padding: "var(--card-padding)",
        boxShadow: isDropTarget
          ? "0 0 0 4px rgba(52, 199, 89, 0.15)"
          : "var(--card-shadow)",
        height: "100%",
        overflow: "hidden",
        display: "flex",
        flexDirection: "column",
        position: "relative",
        cursor: isDragMode ? "grab" : undefined,
        opacity: isBeingDragged ? 0.3 : isDragMode ? 0.6 : 1,
        transition: "opacity 150ms, border 150ms, box-shadow 150ms",
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          marginBottom: "0.75rem",
          flexShrink: 0,
        }}
      >
        <h3
          style={{
            fontSize: "var(--card-header-size)",
            fontWeight: "var(--card-header-weight)" as never,
            color: "var(--card-header-color)",
            margin: 0,
          }}
        >
          {title}
        </h3>
      </div>
      <div style={{ flex: 1, overflowY: isDragMode ? "hidden" : "auto", minHeight: 0 }}>
        {children}
      </div>

      {/* Drag-mode overlay blocks all interaction with widget content */}
      {isDragMode && (
        <div
          style={{
            position: "absolute",
            inset: 0,
            borderRadius: "var(--card-radius)",
          }}
        />
      )}
    </div>
  );
}
