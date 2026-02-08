"use client";

import type { DraggableAttributes } from "@dnd-kit/core";
import type { SyntheticListenerMap } from "@dnd-kit/core/dist/hooks/utilities";

interface DragHandleProps {
  listeners?: SyntheticListenerMap;
  attributes?: DraggableAttributes;
}

export default function DragHandle({ listeners, attributes }: DragHandleProps) {
  return (
    <button
      {...attributes}
      {...listeners}
      aria-label="Drag to reorder"
      style={{
        cursor: "grab",
        background: "none",
        border: "none",
        padding: "4px",
        display: "flex",
        alignItems: "center",
        color: "var(--chart-text)",
      }}
    >
      <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
        <circle cx="5" cy="3" r="1.5" />
        <circle cx="11" cy="3" r="1.5" />
        <circle cx="5" cy="8" r="1.5" />
        <circle cx="11" cy="8" r="1.5" />
        <circle cx="5" cy="13" r="1.5" />
        <circle cx="11" cy="13" r="1.5" />
      </svg>
    </button>
  );
}
