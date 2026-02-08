// --- Backend response shapes ---

export interface Restaurant {
  restaurant_id: number;
  restaurant_name: string;
  timezone: string;
  is_active: boolean;
  created_at: string;
}

export interface DashboardOverview {
  total_ingredients: number;
  stockout_count: number;
  low_stock_count: number;
  avg_inventory: number;
  avg_daily_usage: number;
}

export interface TrendDay {
  log_date: string;
  total_used: number;
  total_inventory: number;
  total_on_order: number;
  total_covers: number;
}

export interface TopMover {
  ingredient_id: number;
  ingredient_name: string;
  unit: string;
  category: string;
  total_used_7d: number;
  avg_daily_used: number;
}

export interface InventoryItem {
  ingredient_id: number;
  ingredient_name: string;
  unit: string;
  category: string;
  shelf_life_days: number;
  log_date: string;
  inventory_start: number;
  qty_used: number;
  inventory_end: number;
  on_order_qty: number;
  avg_daily_usage_7d: number;
  avg_daily_usage_28d: number;
}

export interface PredictionXgboost {
  ingredient_id: number;
  ingredient_name: string;
  unit: string;
  prediction_date: string;
  model_type: string;
  projected_demand_leadtime: number;
  reorder_point: number;
  target_stock_level: number;
  stockout_probability: number;
  days_until_stockout: number;
  restock_today: boolean;
  suggested_order_qty: number;
  suggested_order_date: string;
  confidence: "high";
}

export interface PredictionSimple {
  ingredient_id: number;
  ingredient_name: string;
  lead_time_days: number;
  days_of_history: number;
  current_inventory: number;
  on_order_qty: number;
  avg_daily_usage: number;
  days_until_stockout: number | null;
  confidence: "low";
}

export type Prediction = PredictionXgboost | PredictionSimple;

export interface PredictionsResponse {
  xgboost: PredictionXgboost[];
  simple: PredictionSimple[];
  all: Prediction[];
}

export interface ExpiringBatch {
  batch_id: number;
  ingredient_id: number;
  ingredient_name: string;
  unit: string;
  qty_remaining: number;
  expiration_date: string;
  supplier_name: string;
}

export interface MenuItem {
  menu_item_id: number;
  item_name: string;
  price: number;
  is_active: boolean;
}

export interface MenuItemIngredient {
  ingredient_id: number;
  ingredient_name: string;
  unit: string;
  qty_per_item: number | null;
  unit_cost: number | null;
}

export interface MenuItemDetail extends MenuItem {
  restaurant_id: number;
  ingredients: MenuItemIngredient[];
}

export interface IngredientCatalogItem {
  ingredient_id: number;
  ingredient_name: string;
  unit: string;
  unit_cost: number | null;
  category: string | null;
  shelf_life_days: number | null;
  is_active: boolean;
}

export interface RestaurantIngredient {
  ingredient_id: number;
  ingredient_name: string;
  unit: string;
  unit_cost: number | null;
  category: string | null;
  shelf_life_days: number | null;
  lead_time_days: number;
  safety_stock_days: number;
  first_stocked_date: string;
}

export interface InventoryHistory {
  log_date: string;
  inventory_start: number;
  qty_used: number;
  stockout_qty: number;
  inventory_end: number;
  on_order_qty: number;
  avg_daily_usage_7d: number;
  avg_daily_usage_28d: number;
  covers: number;
  seasonality_factor: number;
}

// --- Widget layout types ---

export type WidgetSize = "2x1" | "2x2" | "2x3" | "1x2" | "1x3";

export type WidgetId =
  | "stock-forecast"
  | "overview-stats"
  | "inventory-levels"
  | "usage-trends"
  | "top-movers"
  | "predictions-chart"
  | "expiring-batches"
  | "ingredient-inventory"
  | "reorder-alerts"
  | "menu-overview";

export interface WidgetConfig {
  id: WidgetId;
  label: string;
  description: string;
  defaultSize: WidgetSize;
}

export interface LayoutState {
  visibleWidgetIds: WidgetId[];
}

export interface WidgetProps {
  restaurantId: number;
}
