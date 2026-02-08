"use client";

import { useEffect, useState } from "react";
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
} from "@dnd-kit/core";
import {
  SortableContext,
  sortableKeyboardCoordinates,
  rectSortingStrategy,
  useSortable,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { useDashboardLayout } from "@/lib/hooks/useDashboardLayout";
import { WIDGET_MAP } from "@/lib/constants/widget-registry";
import type { WidgetId, WidgetSize } from "@/lib/types/dashboard";
import DashboardCard from "./DashboardCard";
import DragHandle from "./DragHandle";
import WidgetPicker from "./WidgetPicker";
import InventoryTableView from "./InventoryTableView";

interface DashboardShellProps {
  restaurantId: number;
  restaurantName: string;
}

type DashboardTab = "dashboard" | "inventory";

function sizeToSpans(size: WidgetSize): { colSpan: number; rowSpan: number } {
  const [c, r] = size.split("x").map(Number);
  return { colSpan: c, rowSpan: r };
}

function SortableWidget({
  widgetId,
  restaurantId,
  isEditing,
}: {
  widgetId: WidgetId;
  restaurantId: number;
  isEditing: boolean;
}) {
  const entry = WIDGET_MAP.get(widgetId);
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: widgetId });

  if (!entry) return null;

  const Widget = entry.component;
  const { colSpan, rowSpan } = sizeToSpans(entry.defaultSize);

  const style: React.CSSProperties = {
    transform: CSS.Transform.toString(transform),
    transition,
    gridColumn: `span ${colSpan}`,
    gridRow: `span ${rowSpan}`,
    opacity: isDragging ? 0.5 : 1,
  };

  return (
    <div ref={setNodeRef} style={style}>
      <DashboardCard
        title={entry.label}
        isEditing={isEditing}
        dragHandleSlot={
          isEditing ? (
            <DragHandle listeners={listeners} attributes={attributes} />
          ) : undefined
        }
      >
        <Widget restaurantId={restaurantId} />
      </DashboardCard>
    </div>
  );
}

export default function DashboardShell({
  restaurantId,
  restaurantName,
}: DashboardShellProps) {
  const [activeTab, setActiveTab] = useState<DashboardTab>("dashboard");
  const {
    visibleWidgetIds,
    isEditing,
    setIsEditing,
    toggleWidget,
    reorderWidgets,
    resetLayout,
  } = useDashboardLayout(restaurantId);

  useEffect(() => {
    if (activeTab === "inventory" && isEditing) setIsEditing(false);
  }, [activeTab, isEditing, setIsEditing]);

  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  function handleDragEnd(event: DragEndEvent) {
    const { active, over } = event;
    if (!over || active.id === over.id) return;

    const oldIdx = visibleWidgetIds.indexOf(active.id as WidgetId);
    const newIdx = visibleWidgetIds.indexOf(over.id as WidgetId);
    if (oldIdx === -1 || newIdx === -1) return;

    const updated = [...visibleWidgetIds];
    updated.splice(oldIdx, 1);
    updated.splice(newIdx, 0, active.id as WidgetId);
    reorderWidgets(updated);
  }

  return (
    <div style={{ padding: "1rem", paddingBottom: "6rem", maxWidth: 1400, margin: "0 auto" }}>
      <div style={{ display: "flex", gap: "1rem" }}>
        <aside
          style={{
            width: 190,
            alignSelf: "flex-start",
            position: "sticky",
            top: "1rem",
            background: "var(--card-bg)",
            border: "var(--card-border)",
            borderRadius: "var(--card-radius)",
            boxShadow: "var(--card-shadow)",
            padding: "0.75rem",
          }}
        >
          <div style={{ marginBottom: "0.75rem" }}>
            <h2 style={{ fontSize: "0.95rem", margin: 0, fontWeight: 700 }}>
              {restaurantName}
            </h2>
            <p style={{ margin: "0.25rem 0 0", color: "var(--chart-text)", fontSize: "0.75rem" }}>
              Workspace
            </p>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: "0.35rem" }}>
            <button onClick={() => setActiveTab("dashboard")} style={sideTabStyle(activeTab === "dashboard")}>
              Dashboard
            </button>
            <button onClick={() => setActiveTab("inventory")} style={sideTabStyle(activeTab === "inventory")}>
              Inventory
            </button>
          </div>
        </aside>

        <div style={{ flex: 1, minWidth: 0 }}>
          {/* Header */}
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              marginBottom: "1.25rem",
            }}
          >
            <div>
              <h1 style={{ fontSize: "1.75rem", fontWeight: 700, margin: 0 }}>
                {activeTab === "dashboard" ? "Dashboard" : "Inventory"}
              </h1>
              <p style={{ color: "var(--chart-text)", margin: "0.25rem 0 0", fontSize: "0.85rem" }}>
                {activeTab === "dashboard"
                  ? "Drag and configure widgets for this restaurant"
                  : "Browse inventory records with pagination"}
              </p>
            </div>
            {activeTab === "dashboard" && (
              <button
                onClick={() => setIsEditing(!isEditing)}
                style={{
                  background: isEditing ? "var(--color-success)" : "var(--btn-bg)",
                  color: "var(--btn-color)",
                  border: "none",
                  borderRadius: "var(--btn-radius)",
                  padding: "0.5rem 1rem",
                  fontWeight: 600,
                  fontSize: "0.85rem",
                  cursor: "pointer",
                }}
              >
                {isEditing ? "Done" : "Edit Layout"}
              </button>
            )}
          </div>

          {activeTab === "inventory" ? (
            <InventoryTableView key={restaurantId} restaurantId={restaurantId} />
          ) : (
            <div style={{ display: "flex", gap: "1.5rem" }}>
              {/* Widget picker sidebar (edit mode only) */}
              {isEditing && (
                <WidgetPicker
                  visibleWidgetIds={visibleWidgetIds}
                  onToggle={toggleWidget}
                  onReset={resetLayout}
                />
              )}

              {/* Grid */}
              <div style={{ flex: 1 }}>
                <DndContext
                  sensors={sensors}
                  collisionDetection={closestCenter}
                  onDragEnd={handleDragEnd}
                >
                  <SortableContext
                    items={visibleWidgetIds}
                    strategy={rectSortingStrategy}
                  >
                    <div
                      style={{
                        display: "grid",
                        gridTemplateColumns:
                          "repeat(auto-fill, minmax(max(160px, calc(20% - 1rem)), 1fr))",
                        gridAutoRows: 180,
                        gap: "1rem",
                      }}
                    >
                      {visibleWidgetIds.map((id) => (
                        <SortableWidget
                          key={id}
                          widgetId={id}
                          restaurantId={restaurantId}
                          isEditing={isEditing}
                        />
                      ))}
                    </div>
                  </SortableContext>
                </DndContext>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function sideTabStyle(active: boolean): React.CSSProperties {
  return {
    width: "100%",
    textAlign: "left",
    border: "none",
    borderRadius: 8,
    padding: "0.5rem 0.6rem",
    fontSize: "0.85rem",
    fontWeight: active ? 600 : 500,
    background: active ? "var(--btn-bg)" : "transparent",
    color: active ? "var(--btn-color)" : "var(--foreground)",
    cursor: "pointer",
  };
}
