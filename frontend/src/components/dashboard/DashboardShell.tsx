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
import LiquidGlassDashboardCard from "./LiquidGlassDashboardCard";
import WidgetPickerModal from "./WidgetPickerModal";
import InventoryTableView from "./InventoryTableView";
import MenuTableView from "./MenuTableView";
import TrafficCalendarView from "./TrafficCalendarView";
import TopStatsBar from "./TopStatsBar";

interface DashboardShellProps {
  restaurantId: number;
  restaurantName: string;
}

type DashboardTab = "dashboard" | "inventory" | "menu" | "calendar";

const NAV_ITEMS: { key: DashboardTab; label: string; icon: () => React.JSX.Element }[] = [
  { key: "dashboard", label: "Dashboard", icon: DashboardIcon },
  { key: "inventory", label: "Inventory", icon: InventoryIcon },
  { key: "menu", label: "Menu", icon: MenuIcon },
  { key: "calendar", label: "Calendar", icon: CalendarIcon },
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
      <LiquidGlassDashboardCard
        title={entry.label}
        glassVariant="squircle"
      >
        <Widget restaurantId={restaurantId} />
      </LiquidGlassDashboardCard>
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
    <LiquidGlassDashboardCard title={entry.label} glassVariant="squircle">
      <Widget restaurantId={restaurantId} />
    </LiquidGlassDashboardCard>
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

/* ── Navigation Icons ── */

function DashboardIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect width="7" height="9" x="3" y="3" rx="1"/>
      <rect width="7" height="5" x="14" y="3" rx="1"/>
      <rect width="7" height="9" x="14" y="12" rx="1"/>
      <rect width="7" height="5" x="3" y="16" rx="1"/>
    </svg>
  );
}

function InventoryIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect width="18" height="18" x="3" y="3" rx="2"/>
      <path d="M9 3v18"/>
      <path d="m16 15-3-3 3-3"/>
    </svg>
  );
}

function MenuIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="4" x2="20" y1="6" y2="6"/>
      <line x1="4" x2="20" y1="12" y2="12"/>
      <line x1="4" x2="20" y1="18" y2="18"/>
    </svg>
  );
}

function CalendarIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M8 2v4"/>
      <path d="M16 2v4"/>
      <rect width="18" height="18" x="3" y="4" rx="2"/>
      <path d="M3 10h18"/>
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
                gap: "1.5rem",
              }}
            >
              <div style={{ flex: 0 }}>
                <h1 style={{ fontSize: "1.75rem", fontWeight: 700, margin: 0 }}>
                  {restaurantName}
                </h1>
                <p style={{ color: "var(--chart-text)", margin: "0.25rem 0 0", fontSize: "0.85rem" }}>
                  Dashboard
                </p>
              </div>

              {/* Top stats bar - centered */}
              <div style={{ flex: 1, display: "flex", justifyContent: "center" }}>
                <TopStatsBar restaurantId={restaurantId} />
              </div>

              <div style={{ display: "flex", gap: "0.5rem", alignItems: "center", flex: 0 }}>
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
    <>
      <style>{`
        .dashboard-layout {
          display: flex;
          min-height: 0;
        }
        .dashboard-sidebar {
          position: sticky;
          top: 0;
          width: 64px;
          min-width: 64px;
          height: 100vh;
          padding: 1rem 0;
          display: flex;
          flex-direction: column;
          gap: 0.5rem;
          background: var(--card-bg);
          border-right: var(--card-border);
          align-items: center;
        }
        .dashboard-topnav {
          display: none;
        }
        .dashboard-main {
          flex: 1;
          min-width: 0;
          padding: 1rem;
          padding-bottom: 6rem;
          max-width: 1400px;
          margin: 0 auto;
          width: 100%;
        }
        @media (max-width: 768px) {
          .dashboard-layout {
            flex-direction: column;
          }
          .dashboard-sidebar {
            display: none;
          }
          .dashboard-topnav {
            display: flex;
            gap: 0.25rem;
            padding: 0.5rem 0.75rem;
            background: var(--card-bg);
            border-bottom: var(--card-border);
            overflow-x: auto;
            position: sticky;
            top: 0;
            z-index: 10;
          }
        }
      `}</style>

      <div className="dashboard-layout">
        {/* Sidebar – desktop */}
        <nav className="dashboard-sidebar">
          {NAV_ITEMS.map((item) => {
            const IconComponent = item.icon;
            return (
              <button
                key={item.key}
                onClick={() => setActiveTab(item.key)}
                style={iconSidebarStyle(activeTab === item.key)}
                title={item.label}
              >
                <IconComponent />
              </button>
            );
          })}
        </nav>

        {/* Top nav – mobile */}
        <nav className="dashboard-topnav">
          {NAV_ITEMS.map((item) => (
            <button
              key={item.key}
              onClick={() => setActiveTab(item.key)}
              style={mobileTabStyle(activeTab === item.key)}
            >
              {item.label}
            </button>
          ))}
        </nav>

        {/* Main content */}
        <div className="dashboard-main">
          {renderContent()}
        </div>
      </div>
    </>
  );
}

function iconSidebarStyle(active: boolean): React.CSSProperties {
  return {
    width: "48px",
    height: "48px",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    border: "none",
    borderRadius: 12,
    background: active ? "var(--btn-bg)" : "transparent",
    color: active ? "var(--btn-color)" : "var(--foreground)",
    cursor: "pointer",
    transition: "all 0.2s ease",
  };
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