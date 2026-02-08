"use client";

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
import type { WidgetId } from "@/lib/types/dashboard";
import DashboardCard from "./DashboardCard";
import DragHandle from "./DragHandle";
import WidgetPicker from "./WidgetPicker";

interface DashboardShellProps {
  restaurantId: number;
  restaurantName: string;
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

  const style: React.CSSProperties = {
    transform: CSS.Transform.toString(transform),
    transition,
    gridColumn: `span ${entry.defaultColSpan}`,
    opacity: isDragging ? 0.5 : 1,
  };

  return (
    <div ref={setNodeRef} style={style}>
      <DashboardCard
        title={entry.label}
        colSpan={entry.defaultColSpan}
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
  const {
    visibleWidgetIds,
    isEditing,
    setIsEditing,
    toggleWidget,
    reorderWidgets,
    resetLayout,
  } = useDashboardLayout(restaurantId);

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
    <div style={{ padding: "1.5rem", maxWidth: 1200, margin: "0 auto" }}>
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
      </div>

      {/* Body */}
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
                  gridTemplateColumns: "repeat(2, 1fr)",
                  gap: "1.25rem",
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
    </div>
  );
}
