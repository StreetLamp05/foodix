import type { ComponentType } from "react";
import type { WidgetConfig, WidgetId, WidgetProps } from "@/lib/types/dashboard";
import StockForecast from "@/components/dashboard/widgets/StockForecast";
import OverviewStats from "@/components/dashboard/widgets/OverviewStats";
import InventoryLevels from "@/components/dashboard/widgets/InventoryLevels";
import UsageTrends from "@/components/dashboard/widgets/UsageTrends";
import TopMovers from "@/components/dashboard/widgets/TopMovers";
import PredictionsChart from "@/components/dashboard/widgets/PredictionsChart";
import ExpiringBatches from "@/components/dashboard/widgets/ExpiringBatches";
import IngredientInventory from "@/components/dashboard/widgets/IngredientInventory";
import ReorderAlerts from "@/components/dashboard/widgets/ReorderAlerts";
import MenuOverview from "@/components/dashboard/widgets/MenuOverview";

export interface WidgetRegistryEntry extends WidgetConfig {
  component: ComponentType<WidgetProps>;
}

export const WIDGET_REGISTRY: WidgetRegistryEntry[] = [
  {
    id: "stock-forecast",
    label: "Stock Forecast",
    description: "Current stock levels — click any ingredient to see its predicted depletion",
    defaultColSpan: 2,
    component: StockForecast,
  },
  {
    id: "overview-stats",
    label: "Overview Stats",
    description: "Key inventory metrics at a glance",
    defaultColSpan: 2,
    component: OverviewStats,
  },
  {
    id: "inventory-levels",
    label: "Inventory Levels",
    description: "Current quantity per ingredient",
    defaultColSpan: 1,
    component: InventoryLevels,
  },
  {
    id: "usage-trends",
    label: "Usage Trends",
    description: "Usage and inventory over the last 30 days",
    defaultColSpan: 1,
    component: UsageTrends,
  },
  {
    id: "top-movers",
    label: "Top Movers",
    description: "Highest-usage ingredients (7-day)",
    defaultColSpan: 1,
    component: TopMovers,
  },
  {
    id: "predictions-chart",
    label: "Stockout Predictions",
    description: "Days until stockout, color-coded by risk",
    defaultColSpan: 1,
    component: PredictionsChart,
  },
  {
    id: "expiring-batches",
    label: "Expiring Batches",
    description: "Batches expiring within 7 days",
    defaultColSpan: 2,
    component: ExpiringBatches,
  },
  {
    id: "ingredient-inventory",
    label: "Ingredient Inventory",
    description: "Ingredient quantities — click a bar to see its predicted depletion",
    defaultColSpan: 2,
    component: IngredientInventory,
  },
  {
    id: "reorder-alerts",
    label: "Reorder Alerts",
    description: "Ingredients needing reorder by timeframe",
    defaultColSpan: 1,
    component: ReorderAlerts,
  },
  {
    id: "menu-overview",
    label: "Menu Overview",
    description: "Menu items with prices",
    defaultColSpan: 1,
    component: MenuOverview,
  },
];

export const WIDGET_MAP = new Map<WidgetId, WidgetRegistryEntry>(
  WIDGET_REGISTRY.map((w) => [w.id, w])
);

export const DEFAULT_LAYOUT: WidgetId[] = WIDGET_REGISTRY.map((w) => w.id);
