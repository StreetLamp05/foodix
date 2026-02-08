"use client";

import { useState } from "react";
import {
  DndContext,
  DragOverlay,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  type DragStartEvent,
  type DragOverEvent,
  type DragEndEvent,
} from "@dnd-kit/core";
import {
  SortableContext,
  sortableKeyboardCoordinates,
  rectSortingStrategy,
  useSortable,
} from "@dnd-kit/sortable";
import { useDashboardLayout } from "@/lib/hooks/useDashboardLayout";
import { WIDGET_MAP } from "@/lib/constants/widget-registry";
import type { WidgetId, WidgetSize } from "@/lib/types/dashboard";
import DashboardCard from "./DashboardCard";

import InventoryTableView from "./InventoryTableView";
import MenuTableView from "./MenuTableView";
import TrafficCalendarView from "./TrafficCalendarView";

import WidgetPickerModal from "./WidgetPickerModal";


interface DashboardShellProps {
  restaurantId: number;
  restaurantName: string;
}

type DashboardTab = "dashboard" | "inventory" | "menu" | "calendar";

function sizeToSpans(size: WidgetSize): { colSpan: number; rowSpan: number } {
  const [c, r] = size.split("x").map(Number);
  return { colSpan: c, rowSpan: r };
}

function SortableWidget({
  widgetId,
  restaurantId,
  isDragMode,
  isBeingDragged,
  isDropTarget,
}: {
  widgetId: WidgetId;
  restaurantId: number;
  isDragMode: boolean;
  isBeingDragged: boolean;
  isDropTarget: boolean;
}) {
  const entry = WIDGET_MAP.get(widgetId);
  const {
    attributes,
    listeners,
    setNodeRef,
  } = useSortable({ id: widgetId, disabled: !isDragMode });

  if (!entry) return null;

  const Widget = entry.component;
  const { colSpan, rowSpan } = sizeToSpans(entry.defaultSize);

  const style: React.CSSProperties = {
    gridColumn: `span ${colSpan}`,
    gridRow: `span ${rowSpan}`,
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...(isDragMode ? { ...attributes, ...listeners } : {})}
    >
      <DashboardCard
        title={entry.label}
        isDragMode={isDragMode}
        isBeingDragged={isBeingDragged}
        isDropTarget={isDropTarget}
      >
        <Widget restaurantId={restaurantId} />
      </DashboardCard>
    </div>
  );
}

/* ── Overlay card shown while dragging ── */

function DragOverlayCard({
  widgetId,
  restaurantId,
}: {
  widgetId: WidgetId;
  restaurantId: number;
}) {
  const entry = WIDGET_MAP.get(widgetId);
  if (!entry) return null;
  const Widget = entry.component;

  return (
    <DashboardCard title={entry.label}>
      <Widget restaurantId={restaurantId} />
    </DashboardCard>
  );
}

/* ── Icon components ── */

function GridIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" fill="currentColor">
      <rect x="1" y="1" width="7" height="7" rx="1.5" />
      <rect x="10" y="1" width="7" height="7" rx="1.5" />
      <rect x="1" y="10" width="7" height="7" rx="1.5" />
      <rect x="10" y="10" width="7" height="7" rx="1.5" />
    </svg>
  );
}

function MoveIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M9 1v16M1 9h16M9 1l-3 3M9 1l3 3M9 17l-3-3M9 17l3-3M1 9l3-3M1 9l3 3M17 9l-3-3M17 9l-3 3" />
    </svg>
  );
}

export default function DashboardShell({
  restaurantId,
  restaurantName,
}: DashboardShellProps) {
  const [activeTab, setActiveTab] = useState<DashboardTab>("dashboard");
  const {
    visibleWidgetIds,
    toggleWidget,
    reorderWidgets,
    resetLayout,
  } = useDashboardLayout(restaurantId);

  useEffect(() => {
    if (activeTab !== "dashboard" && isEditing) setIsEditing(false);
  }, [activeTab, isEditing, setIsEditing]);
  
  
  const [isPickerOpen, setIsPickerOpen] = useState(false);
  const [isDragMode, setIsDragMode] = useState(false);
  const [activeId, setActiveId] = useState<WidgetId | null>(null);
  const [overId, setOverId] = useState<WidgetId | null>(null);

  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  function handleDragStart(event: DragStartEvent) {
    setActiveId(event.active.id as WidgetId);
  }

  function handleDragOver(event: DragOverEvent) {
    setOverId((event.over?.id as WidgetId) ?? null);
  }

  function handleDragEnd(event: DragEndEvent) {
    const { active, over } = event;
    setActiveId(null);
    setOverId(null);

    if (!over || active.id === over.id) return;

    const oldIdx = visibleWidgetIds.indexOf(active.id as WidgetId);
    const newIdx = visibleWidgetIds.indexOf(over.id as WidgetId);
    if (oldIdx === -1 || newIdx === -1) return;

    const updated = [...visibleWidgetIds];
    updated.splice(oldIdx, 1);
    updated.splice(newIdx, 0, active.id as WidgetId);
    reorderWidgets(updated);
  }

  function handleDragCancel() {
    setActiveId(null);
    setOverId(null);
  }

  const iconBtnStyle: React.CSSProperties = {
    background: "var(--btn-bg)",
    color: "var(--btn-color)",
    border: "none",
    borderRadius: "var(--btn-radius)",
    padding: "0.5rem",
    cursor: "pointer",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
  };

  return (
    <>
      <div style={{ padding: "1rem", paddingBottom: "6rem", maxWidth: 1400, margin: "0 auto" }}>
        {/* Header */}
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginBottom: "1.5rem",
          }}
        >
          <div>
            <h1 style={{ fontSize: "1.75rem", fontWeight: 700, margin: 0 }}>
              {restaurantName}
            </h1>
            <p style={{ color: "var(--chart-text)", margin: "0.25rem 0 0", fontSize: "0.85rem" }}>
              Dashboard
            </p>
          </div>

          <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
            {/* Widget picker */}
            <button
              onClick={() => setIsPickerOpen(true)}
              aria-label="Choose widgets"
              title="Choose widgets"
              style={iconBtnStyle}
            >
              <GridIcon />
            </button>

            {/* Drag mode toggle */}
            <button
              onClick={() => setIsDragMode((d) => !d)}
              aria-label={isDragMode ? "Done rearranging" : "Rearrange widgets"}
              title={isDragMode ? "Done rearranging" : "Rearrange widgets"}
              style={{
                ...iconBtnStyle,
                background: isDragMode ? "var(--color-success)" : "var(--btn-bg)",
              }}
            >
              <MoveIcon />
            </button>
            <button onClick={() => setActiveTab("menu")} style={sideTabStyle(activeTab === "menu")}>
              Menu
            </button>
            <button onClick={() => setActiveTab("calendar")} style={sideTabStyle(activeTab === "calendar")}>
              Calendar
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
                {activeTab === "dashboard"
                  ? "Dashboard"
                  : activeTab === "inventory"
                    ? "Inventory"
                    : activeTab === "menu"
                      ? "Menu"
                      : "Traffic Calendar"}
              </h1>
              <p style={{ color: "var(--chart-text)", margin: "0.25rem 0 0", fontSize: "0.85rem" }}>
                {activeTab === "dashboard"
                  ? "Drag and configure widgets for this restaurant"
                  : activeTab === "inventory"
                    ? "Browse inventory records with pagination"
                    : activeTab === "menu"
                      ? "Browse menu items and open ingredient BOM details"
                      : "Predicted heavy-traffic days and holidays by month"}
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
          ) : activeTab === "menu" ? (
            <MenuTableView key={restaurantId} restaurantId={restaurantId} />
          ) : activeTab === "calendar" ? (
            <TrafficCalendarView key={restaurantId} restaurantId={restaurantId} />
          ) : (
            <div style={{ display: "flex", gap: "1.5rem" }}>
              {/* Widget picker sidebar (edit mode only) */}
              {isEditing && (
                <WidgetPicker
                  visibleWidgetIds={visibleWidgetIds}
                  onToggle={toggleWidget}
                  onReset={resetLayout}
        </div>

        {/* Grid */}
        <DndContext
          sensors={sensors}
          collisionDetection={closestCenter}
          onDragStart={handleDragStart}
          onDragOver={handleDragOver}
          onDragEnd={handleDragEnd}
          onDragCancel={handleDragCancel}
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
                  isDragMode={isDragMode}
                  isBeingDragged={id === activeId}
                  isDropTarget={id === overId && overId !== activeId}
                />
              ))}
            </div>
          </SortableContext>

          <DragOverlay dropAnimation={null}>
            {activeId ? (
              <DragOverlayCard
                widgetId={activeId}
                restaurantId={restaurantId}
              />
            ) : null}
          </DragOverlay>
        </DndContext>
      </div>

      {/* Widget picker modal */}
      {isPickerOpen && (
        <WidgetPickerModal
          visibleWidgetIds={visibleWidgetIds}
          onToggle={toggleWidget}
          onReset={resetLayout}
          onClose={() => setIsPickerOpen(false)}
        />
      )}
    </>
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
