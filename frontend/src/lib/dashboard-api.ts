import { apiUrl } from "./api";
import type {
  Restaurant,
  DashboardOverview,
  TrendDay,
  TopMover,
  InventoryItem,
  InventoryHistory,
  PredictionsResponse,
  ExpiringBatch,
  MenuItem,
  MenuItemDetail,
  IngredientCatalogItem,
  RestaurantIngredient,
} from "./types/dashboard";

async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${apiUrl}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json() as Promise<T>;
}

// Restaurants
export const fetchRestaurants = () =>
  fetchJson<Restaurant[]>("/api/restaurants");

export const fetchRestaurant = (id: number) =>
  fetchJson<Restaurant>(`/api/restaurants/${id}`);

// Dashboard
export const fetchOverview = (restaurantId: number) =>
  fetchJson<DashboardOverview>(
    `/api/restaurants/${restaurantId}/dashboard/overview`
  );

export const fetchTrends = (restaurantId: number, days = 30) =>
  fetchJson<TrendDay[]>(
    `/api/restaurants/${restaurantId}/dashboard/trends?days=${days}`
  );

export const fetchTopMovers = (restaurantId: number, limit = 10) =>
  fetchJson<TopMover[]>(
    `/api/restaurants/${restaurantId}/dashboard/top-movers?limit=${limit}`
  );

// Inventory
export const fetchInventory = (restaurantId: number) =>
  fetchJson<InventoryItem[]>(
    `/api/restaurants/${restaurantId}/inventory`
  );

export const fetchInventoryHistory = (
  restaurantId: number,
  ingredientId: number,
  days = 14
) =>
  fetchJson<InventoryHistory[]>(
    `/api/restaurants/${restaurantId}/inventory/${ingredientId}/history?days=${days}`
  );

export const fetchRestaurantIngredients = (restaurantId: number) =>
  fetchJson<RestaurantIngredient[]>(
    `/api/restaurants/${restaurantId}/ingredients`
  );

export const addRestaurantIngredient = (
  restaurantId: number,
  body: { ingredient_id: number; lead_time_days?: number; safety_stock_days?: number }
) =>
  fetchJson<{
    restaurant_id: number;
    ingredient_id: number;
    lead_time_days: number;
    safety_stock_days: number;
    is_active: boolean;
  }>(`/api/restaurants/${restaurantId}/ingredients`, {
    method: "POST",
    body: JSON.stringify(body),
  });

export const removeRestaurantIngredient = (
  restaurantId: number,
  ingredientId: number
) =>
  fetchJson<{ restaurant_id: number; ingredient_id: number; is_active: boolean }>(
    `/api/restaurants/${restaurantId}/ingredients/${ingredientId}`,
    { method: "DELETE" }
  );

export const restockInventoryIngredient = (
  restaurantId: number,
  ingredientId: number,
  body: { restock_qty: number }
) =>
  fetchJson<{
    id: number;
    log_date: string;
    inventory_start: number;
    qty_used: number;
    inventory_end: number;
    on_order_qty: number;
  }>(`/api/restaurants/${restaurantId}/inventory/${ingredientId}/restock`, {
    method: "POST",
    body: JSON.stringify(body),
  });

// Predictions
export const fetchPredictions = (restaurantId: number) =>
  fetchJson<PredictionsResponse>(
    `/api/restaurants/${restaurantId}/predictions`
  );

// Batches
export const fetchExpiringBatches = (restaurantId: number, days = 7) =>
  fetchJson<ExpiringBatch[]>(
    `/api/restaurants/${restaurantId}/batches/expiring-soon?days=${days}`
  );

// Menu
export const fetchMenu = (restaurantId: number) =>
  fetchJson<MenuItem[]>(`/api/restaurants/${restaurantId}/menu`);

export const fetchMenuItemDetail = (menuItemId: number) =>
  fetchJson<MenuItemDetail>(`/api/menu-items/${menuItemId}`);

export const createMenuItem = (restaurantId: number, body: { item_name: string; price: number }) =>
  fetchJson<MenuItem>(`/api/restaurants/${restaurantId}/menu`, {
    method: "POST",
    body: JSON.stringify(body),
  });

export const deleteMenuItem = (menuItemId: number) =>
  fetchJson<{ menu_item_id: number }>(`/api/menu-items/${menuItemId}`, {
    method: "DELETE",
  });

export const fetchIngredientCatalog = () =>
  fetchJson<IngredientCatalogItem[]>("/api/ingredients");

export const addMenuItemIngredient = (
  menuItemId: number,
  body: { ingredient_id: number; qty_per_item: number }
) =>
  fetchJson<{ menu_item_id: number; ingredient_id: number; qty_per_item: number }>(
    `/api/menu-items/${menuItemId}/ingredients`,
    {
      method: "POST",
      body: JSON.stringify(body),
    }
  );

export const deleteMenuItemIngredient = (menuItemId: number, ingredientId: number) =>
  fetchJson<{ menu_item_id: number; ingredient_id: number }>(
    `/api/menu-items/${menuItemId}/ingredients/${ingredientId}`,
    {
      method: "DELETE",
    }
  );
