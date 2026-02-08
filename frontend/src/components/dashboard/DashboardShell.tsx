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
import WidgetPickerModal from "./WidgetPickerModal";
import InventoryTableView from "./InventoryTableView";
import MenuTableView from "./MenuTableView";
import TrafficCalendarView from "./TrafficCalendarView";

interface DashboardShellProps {
  restaurantId: number;
  restaurantName: string;
}

type DashboardTab = "dashboard" | "inventory" | "menu" | "calendar";

const NAV_ITEMS: { key: DashboardTab; label: string }[] = [
  { key: "dashboard", label: "Dashboard" },
  { key: "inventory", label: "Inventory" },
  { key: "menu", label: "Menu" },
  { key: "calendar", label: "Calendar" },
];

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

  const renderContent = () => {
    switch (activeTab) {
      case "inventory":
        return <InventoryTableView restaurantId={restaurantId} />;
      case "menu":
        return <MenuTableView restaurantId={restaurantId} />;
      case "calendar":
        return <TrafficCalendarView restaurantId={restaurantId} />;
      default:
        return (
          <>
            {/* Dashboard header controls */}
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
                <button
                  onClick={() => setIsPickerOpen(true)}
                  aria-label="Choose widgets"
                  title="Choose widgets"
                  style={iconBtnStyle}
                >
                  <GridIcon />
                </button>
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
              </div>
            </div>

            {/* Widget grid */}
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
  };

  return (
    <div style={{ padding: "1rem 2rem 6rem 1rem", minHeight: "100vh" }}>
      <div style={{ display: "flex", gap: "1rem" }}>
        <aside    
          style={{
            width: 64,
            flexShrink: 0,
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
          <div style={{ display: "flex", flexDirection: "column", gap: "0.35rem" }}>
            <button onClick={() => setActiveTab("dashboard")} style={sideTabStyle(activeTab === "dashboard")}>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <rect x="3" y="11" width="4" height="10" rx="1" fill="currentColor"/>
                <rect x="10" y="7" width="4" height="14" rx="1" fill="currentColor"/>
                <rect x="17" y="3" width="4" height="18" rx="1" fill="currentColor"/>
              </svg>
            </button>
            <button onClick={() => setActiveTab("inventory")} style={sideTabStyle(activeTab === "inventory")}>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <rect x="3" y="3" width="18" height="18" rx="2" stroke="currentColor" strokeWidth="2" fill="none"/>
                <path d="M9 9h6v6H9V9z" fill="currentColor"/>
                <path d="M3 9h18" stroke="currentColor" strokeWidth="2"/>
                <path d="M9 3v18" stroke="currentColor" strokeWidth="2"/>
              </svg>
            </button>
            <button onClick={() => setActiveTab("menu")} style={sideTabStyle(activeTab === "menu")}>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
              </svg>
            </button>
            <button onClick={() => setActiveTab("calendar")} style={sideTabStyle(activeTab === "calendar")}>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <rect x="3" y="4" width="18" height="18" rx="2" ry="2" stroke="currentColor" strokeWidth="2" fill="none"/>
                <line x1="16" y1="2" x2="16" y2="6" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
                <line x1="8" y1="2" x2="8" y2="6" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
                <line x1="3" y1="10" x2="21" y2="10" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
              </svg>
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
                {activeTab === "dashboard" ? "Dashboard" : 
                 activeTab === "inventory" ? "Inventory" :
                 activeTab === "menu" ? "Menu" : "Calendar"}
              </h1>
              <p style={{ color: "var(--chart-text)", margin: "0.25rem 0 0", fontSize: "0.85rem" }}>
                {activeTab === "dashboard" ? "Drag and configure widgets for this restaurant" :
                 activeTab === "inventory" ? "Browse inventory records with pagination" :
                 activeTab === "menu" ? "Manage menu items and pricing" : "Schedule and events"}
              </p>
            </div>
            {activeTab === "dashboard" && (
              <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
                <button
                  onClick={() => setIsPickerOpen(true)}
                  aria-label="Choose widgets"
                  title="Choose widgets"
                  style={iconBtnStyle}
                >
                  <GridIcon />
                </button>
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
              </div>
            )}
          </div>

          {activeTab === "dashboard" ? (
            <>
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
                        "repeat(auto-fill, minmax(280px, 1fr))",
                      gridAutoRows: "minmax(200px, auto)",
                      gap: "1.5rem",
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
            </>
          ) : (
            <div style={{ padding: "2rem", textAlign: "center", color: "var(--chart-text)" }}>
              {activeTab === "inventory" && "Inventory management coming soon..."}
              {activeTab === "menu" && "Menu management coming soon..."}
              {activeTab === "calendar" && "Calendar feature coming soon..."}
            </div>
          )}
        </div>
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
    </div>
  );
}

function sideTabStyle(active: boolean): React.CSSProperties {
  return {
    width: "100%",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    border: "none",
    borderRadius: 8,
    padding: "0.5rem",
    fontSize: "0.85rem",
    fontWeight: active ? 600 : 500,
    background: active ? "var(--btn-bg)" : "transparent",
    color: active ? "var(--btn-color)" : "var(--foreground)",
    cursor: "pointer",
    transition: "all 0.2s ease",
  };
}

function mobileTabStyle(active: boolean): React.CSSProperties {
  return {
    border: "none",
    borderRadius: 8,
    padding: "0.4rem 0.75rem",
    fontSize: "0.8rem",
    fontWeight: active ? 600 : 500,
    background: active ? "var(--btn-bg)" : "transparent",
    color: active ? "var(--btn-color)" : "var(--foreground)",
    cursor: "pointer",
    whiteSpace: "nowrap",
  };
}
