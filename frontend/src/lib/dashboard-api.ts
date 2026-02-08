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
} from "./types/dashboard";

async function fetchJson<T>(path: string): Promise<T> {
  const res = await fetch(`${apiUrl}${path}`);
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
