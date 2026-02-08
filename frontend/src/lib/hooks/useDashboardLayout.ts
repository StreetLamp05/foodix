"use client";

import { useState, useCallback, useEffect } from "react";
import type { WidgetId, LayoutState } from "@/lib/types/dashboard";
import { DEFAULT_LAYOUT, WIDGET_MAP } from "@/lib/constants/widget-registry";

function storageKey(restaurantId: number) {
  return `dashboard-layout-${restaurantId}`;
}

function loadLayout(restaurantId: number): WidgetId[] {
  if (typeof window === "undefined") return DEFAULT_LAYOUT;
  try {
    const raw = localStorage.getItem(storageKey(restaurantId));
    if (!raw) return DEFAULT_LAYOUT;
    const parsed: LayoutState = JSON.parse(raw);
    // Filter out any widget IDs that no longer exist in registry
    const valid = parsed.visibleWidgetIds.filter((id) => WIDGET_MAP.has(id));
    return valid.length > 0 ? valid : DEFAULT_LAYOUT;
  } catch {
    return DEFAULT_LAYOUT;
  }
}

function saveLayout(restaurantId: number, ids: WidgetId[]) {
  const state: LayoutState = { visibleWidgetIds: ids };
  localStorage.setItem(storageKey(restaurantId), JSON.stringify(state));
}

export function useDashboardLayout(restaurantId: number) {
  const [visibleWidgetIds, setVisibleWidgetIds] = useState<WidgetId[]>(() =>
    loadLayout(restaurantId)
  );
  // Re-load when restaurantId changes
  useEffect(() => {
    setVisibleWidgetIds(loadLayout(restaurantId));
  }, [restaurantId]);

  // Persist on change
  useEffect(() => {
    saveLayout(restaurantId, visibleWidgetIds);
  }, [restaurantId, visibleWidgetIds]);

  const toggleWidget = useCallback((id: WidgetId) => {
    setVisibleWidgetIds((prev) =>
      prev.includes(id) ? prev.filter((w) => w !== id) : [...prev, id]
    );
  }, []);

  const reorderWidgets = useCallback((ids: WidgetId[]) => {
    setVisibleWidgetIds(ids);
  }, []);

  const resetLayout = useCallback(() => {
    setVisibleWidgetIds(DEFAULT_LAYOUT);
  }, []);

  return {
    visibleWidgetIds,
    toggleWidget,
    reorderWidgets,
    resetLayout,
  };
}
