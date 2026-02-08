import { apiUrl } from "./api";

// Full schema + business logic context derived from migrations/001–003 and backend services
const DB_CONTEXT = `
DATABASE: Restaurant inventory system for "The Corner Bistro" (restaurant_id = 1)

=== TABLES ===

TABLE restaurants (
  restaurant_id SERIAL PK, restaurant_name TEXT, timezone TEXT, is_active BOOLEAN, created_at TIMESTAMPTZ
);
-- Only one restaurant: "The Corner Bistro" (restaurant_id = 1)

TABLE ingredients (
  ingredient_id SERIAL PK, ingredient_name TEXT, unit TEXT, unit_cost NUMERIC(10,4),
  is_active BOOLEAN, created_at TIMESTAMPTZ, category TEXT, shelf_life_days SMALLINT
);
-- 46 ingredients. Categories: protein (shelf 3d), dairy (7-14d), produce (5-10d), bakery (3d),
-- condiment (14-30d), dry_goods (365d), oil (180d), beverage (7-30d)
-- Cost column is "unit_cost" (NOT "cost_per_unit")

TABLE restaurant_ingredients (
  restaurant_id INT, ingredient_id INT, lead_time_days SMALLINT DEFAULT 2,
  safety_stock_days SMALLINT DEFAULT 2, is_active BOOLEAN, first_stocked_date DATE,
  PRIMARY KEY (restaurant_id, ingredient_id)
);
-- Links ingredients to restaurant. lead_time_days = supplier delivery time.
-- first_stocked_date used for 90-day training split (XGBoost vs simple prediction)

TABLE menu_items (
  menu_item_id SERIAL PK, restaurant_id INT, item_name TEXT, price NUMERIC(8,2), is_active BOOLEAN
);
-- 12 items: Caesar Salad ($14.50), Chicken Sandwich ($15.95), Chocolate Cake ($10.50),
-- Classic Burger ($16.95), Craft Soda ($4.50), Fish Tacos 3 ($17.50), French Fries ($7.95),
-- Iced Latte ($6.50), Kids Pasta ($9.95), Margherita Pizza ($18.50), Steak Frites ($28.95), Tomato Soup ($9.50)

TABLE menu_item_ingredients (
  menu_item_id INT, ingredient_id INT, qty_per_item NUMERIC(10,4),
  PRIMARY KEY (menu_item_id, ingredient_id)
);
-- Bill of materials / recipes: which ingredients and how much go into each dish

TABLE daily_inventory_log (
  id BIGSERIAL PK, restaurant_id INT, ingredient_id INT, log_date DATE,
  covers INT,                     -- customers served that day
  seasonality_factor NUMERIC,
  inventory_start NUMERIC,        -- opening stock for the day
  qty_used NUMERIC,               -- amount consumed that day
  stockout_qty NUMERIC,           -- unmet demand (ran out)
  inventory_end NUMERIC,          -- closing stock (= start - used + restocked)
  on_order_qty NUMERIC,           -- pending supplier deliveries
  avg_daily_usage_7d NUMERIC,     -- 7-day rolling average usage
  avg_daily_usage_28d NUMERIC,    -- 28-day rolling average usage
  avg_daily_usage_56d NUMERIC,    -- 56-day rolling average usage
  units_sold_items_using INT,     -- menu items sold containing this ingredient
  revenue_items_using NUMERIC,    -- revenue from those menu items
  UNIQUE (restaurant_id, ingredient_id, log_date)
);
-- Core fact table. One row per restaurant × ingredient × day.
-- inventory_end is the CURRENT STOCK LEVEL for the most recent log_date.

TABLE predictions (
  id BIGSERIAL PK, restaurant_id INT, ingredient_id INT,
  prediction_date DATE,           -- date the prediction was made
  model_type TEXT,                -- 'xgboost' or 'simple_avg'
  projected_demand_leadtime NUMERIC, -- predicted demand over the supplier lead time window
  reorder_point NUMERIC,          -- stock level at which to reorder
  target_stock_level NUMERIC,     -- ideal stock level to order up to
  stockout_probability NUMERIC,   -- 0.0 to 1.0, probability of running out
  days_until_stockout SMALLINT,   -- PREDICTED DAYS UNTIL THIS INGREDIENT RUNS OUT
  restock_today BOOLEAN,          -- TRUE if we should order this ingredient TODAY
  suggested_order_qty NUMERIC,    -- how much to order
  suggested_order_date DATE,      -- when to place the order
  created_at TIMESTAMPTZ,
  UNIQUE (restaurant_id, ingredient_id, prediction_date)
);
-- ML-generated demand forecasts. Generated daily by XGBoost model.

TABLE ingredient_batches (
  batch_id BIGSERIAL PK, restaurant_id INT, ingredient_id INT,
  supplier_name TEXT, supplier_contact TEXT, purchase_cost_per_unit NUMERIC,
  qty_received NUMERIC, qty_remaining NUMERIC,
  received_date DATE, expiration_date DATE,
  status TEXT CHECK (status IN ('active','depleted','expired')),
  created_at TIMESTAMPTZ
);
-- Physical batch tracking with FIFO. "active" = on shelf, "depleted" = used up, "expired" = past date.
-- qty_remaining shows how much is left in each batch.

TABLE holidays (holiday_date DATE, holiday_name TEXT, region TEXT, PK (holiday_date, region));
TABLE model_runs (run_id SERIAL PK, model_type TEXT, trained_at TIMESTAMPTZ, training_rows INT, feature_set JSONB, hyperparams JSONB, metrics JSONB, model_artifact TEXT, notes TEXT);

=== HOW TO ANSWER COMMON QUESTIONS ===

"What will run out?" / "What do I need to restock?" / "Low stock alerts":
  → Use the predictions table. Get latest predictions per ingredient:
    SELECT DISTINCT ON (p.ingredient_id) i.ingredient_name, p.days_until_stockout, p.stockout_probability,
           p.restock_today, p.suggested_order_qty
    FROM predictions p
    JOIN ingredients i ON i.ingredient_id = p.ingredient_id
    WHERE p.restaurant_id = 1
    ORDER BY p.ingredient_id, p.prediction_date DESC
  → Filter: days_until_stockout <= N for "next N days", or restock_today = TRUE for urgent items,
    or stockout_probability > 0.5 for risky items
  → Sort by days_until_stockout ASC or stockout_probability DESC for urgency

"Current stock levels" / "How much X do we have?":
  → Use daily_inventory_log, get latest row per ingredient:
    SELECT DISTINCT ON (d.ingredient_id) i.ingredient_name, d.inventory_end AS current_stock,
           d.avg_daily_usage_7d, d.on_order_qty, d.log_date
    FROM daily_inventory_log d
    JOIN ingredients i ON i.ingredient_id = d.ingredient_id
    WHERE d.restaurant_id = 1
    ORDER BY d.ingredient_id, d.log_date DESC
  → inventory_end is the current stock level
  → "Low stock" = inventory_end / avg_daily_usage_7d <= 3 (3 days supply or less)

"Usage trends" / "What are we using the most?":
  → Aggregate daily_inventory_log over a date range:
    SUM(qty_used) for total usage, AVG(qty_used) for average
  → covers column = customer count per day

"Batch/expiration" / "What's expiring soon?":
  → Use ingredient_batches WHERE status = 'active' AND expiration_date <= CURRENT_DATE + INTERVAL 'N days'

"Cost" / "Value" / "How much is our inventory worth?":
  → Join latest daily_inventory_log.inventory_end × ingredients.unit_cost (NOT cost_per_unit)

"Menu analysis" / "Which dishes use X?":
  → Join menu_items ↔ menu_item_ingredients ↔ ingredients

=== KEY QUERY PATTERNS ===

- ALWAYS filter restaurant_id = 1
- For latest row per ingredient from daily_inventory_log:
    DISTINCT ON (d.ingredient_id) ... ORDER BY d.ingredient_id, d.log_date DESC
- For latest predictions per ingredient:
    DISTINCT ON (p.ingredient_id) ... ORDER BY p.ingredient_id, p.prediction_date DESC
- Cost column is "unit_cost" in ingredients (NOT "cost_per_unit")
- ROUND numeric results to 2 decimal places
- End with LIMIT 100 unless a specific count is requested
`.trim();

const OPTIMIZER_PROMPT = `You are a query optimizer for a restaurant inventory PostgreSQL database. Your job is to rewrite vague user questions into precise, unambiguous questions that a code-generation model (Qwen-2.5-coder) can easily convert to correct SQL.

${DB_CONTEXT}

Rules for rewriting:
- Map the user's intent to the correct table(s) and column(s) using the "HOW TO ANSWER" section above
- Reference exact table and column names
- Be specific about which tables to join, which columns to select and filter on
- Specify date ranges, aggregation methods, and sort orders explicitly
- Mention "restaurant_id = 1" if the user forgot
- Mention DISTINCT ON patterns when asking for "latest" or "current" data
- Keep it as a natural language question (NOT SQL)
- Output ONLY the rewritten question, nothing else
- If the user's question is already precise enough, return it unchanged

User question: "{question}"

Optimized question:`;

const QWEN_CONTEXT_PREFIX = `[Schema context for correct SQL generation:
- ingredients: ingredient_id, ingredient_name, unit, unit_cost (NOT cost_per_unit), category, shelf_life_days
- daily_inventory_log: restaurant_id, ingredient_id, log_date, inventory_start, qty_used, stockout_qty, inventory_end (=current stock), on_order_qty, avg_daily_usage_7d/28d/56d, covers, units_sold_items_using, revenue_items_using. Use DISTINCT ON (ingredient_id) ORDER BY ingredient_id, log_date DESC for latest.
- predictions: restaurant_id, ingredient_id, prediction_date, model_type, projected_demand_leadtime, reorder_point, target_stock_level, stockout_probability (0-1), days_until_stockout, restock_today (bool), suggested_order_qty, suggested_order_date. Use DISTINCT ON (ingredient_id) ORDER BY ingredient_id, prediction_date DESC for latest.
- ingredient_batches: batch_id, restaurant_id, ingredient_id, supplier_name, qty_received, qty_remaining, received_date, expiration_date, status IN ('active','depleted','expired')
- restaurant_ingredients: restaurant_id, ingredient_id, lead_time_days, safety_stock_days, is_active
- menu_items: menu_item_id, restaurant_id, item_name, price
- menu_item_ingredients: menu_item_id, ingredient_id, qty_per_item
- holidays: holiday_date, holiday_name
- model_runs: run_id, model_type, metrics (JSONB), trained_at
Key: "run out" / "restock" → use predictions table (days_until_stockout, restock_today, stockout_probability). "current stock" → daily_inventory_log.inventory_end (latest row). "expiring" → ingredient_batches. Always filter restaurant_id = 1.]

Question: `;

export const DEFAULT_PROMPT_TEMPLATE = `You are an AI assistant for "The Corner Bistro" restaurant inventory system. The user asked a question and the database returned real data.

The user asked: "{question}"

The database returned this data:
{results}

IMPORTANT: This is REAL data from the restaurant's database — do NOT say you don't have data. Analyze what was returned and give a clear, actionable answer. Summarize key insights, flag anything urgent (items about to run out, low stock, expiring batches), and suggest next steps if relevant.

If the SQL results have NULL values for days_until_stockout, refer to the SUPPLEMENTARY DATA section below (if present) which contains simple predictions computed as (current_stock + on_order) / avg_daily_usage_7d for all ingredients. Use these to answer questions about what will run out or needs restocking.`;

// ---------- Simple prediction fallback (frontend-computed) ----------

export type SimplePrediction = {
  ingredient_id: number;
  ingredient_name: string;
  category: string;
  unit: string;
  inventory_end: number;
  on_order_qty: number;
  avg_daily_usage_7d: number | null;
  days_left: number | null; // null if avg usage is 0 or unknown
};

/**
 * Fetches current inventory from the REST API and computes a simple
 * days-left prediction for every ingredient:
 *   days_left = (inventory_end + on_order_qty) / avg_daily_usage_7d
 *
 * This covers ingredients that don't have XGBoost predictions (< 90 days history)
 * as well as ingredients whose days_until_stockout is null in the predictions table.
 */
export async function fetchSimplePredictions(): Promise<SimplePrediction[]> {
  const res = await fetch(`${apiUrl}/api/restaurants/1/inventory`);
  if (!res.ok) return []; // non-critical — don't block the pipeline

  const items: Record<string, unknown>[] = await res.json();

  return items.map((item) => {
    const inventoryEnd = Number(item.inventory_end) || 0;
    const onOrder = Number(item.on_order_qty) || 0;
    const avgUsage = item.avg_daily_usage_7d != null ? Number(item.avg_daily_usage_7d) : null;

    let daysLeft: number | null = null;
    if (avgUsage && avgUsage > 0) {
      daysLeft = Math.round(((inventoryEnd + onOrder) / avgUsage) * 100) / 100;
    }

    return {
      ingredient_id: Number(item.ingredient_id),
      ingredient_name: String(item.ingredient_name),
      category: String(item.category),
      unit: String(item.unit),
      inventory_end: inventoryEnd,
      on_order_qty: onOrder,
      avg_daily_usage_7d: avgUsage,
      days_left: daysLeft,
    };
  });
}

export async function askClaude(prompt: string): Promise<string> {
  const res = await fetch("/api/claude", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ prompt }),
  });

  if (!res.ok) {
    const data = await res.json().catch(() => null);
    throw new Error(data?.error ?? `Claude API error (${res.status})`);
  }

  const data = await res.json();
  return data.text ?? "No response from Claude.";
}

export function buildOptimizerPrompt(question: string): string {
  return OPTIMIZER_PROMPT.replace("{question}", question);
}

export function addQwenContext(optimizedQuestion: string): string {
  return QWEN_CONTEXT_PREFIX + optimizedQuestion;
}

export function buildExplainPrompt(
  template: string,
  question: string,
  results: unknown,
  simplePredictions?: SimplePrediction[]
): string {
  let prompt = template
    .replace("{question}", question)
    .replace("{results}", JSON.stringify(results, null, 2));

  if (simplePredictions && simplePredictions.length > 0) {
    // Build a compact summary sorted by urgency (lowest days_left first)
    const sorted = [...simplePredictions]
      .filter((p) => p.days_left !== null)
      .sort((a, b) => (a.days_left ?? Infinity) - (b.days_left ?? Infinity));

    const summary = sorted
      .map(
        (p) =>
          `${p.ingredient_name}: ${p.days_left} days left (stock: ${p.inventory_end} ${p.unit}, on order: ${p.on_order_qty}, avg usage/day: ${p.avg_daily_usage_7d})`
      )
      .join("\n");

    prompt += `\n\nSUPPLEMENTARY DATA — Simple stock-level predictions computed as (current_stock + on_order) / avg_daily_usage_7d for ALL ingredients. Use this to fill in any gaps where the SQL results have NULL days_until_stockout or when the user asks about restocking/running out:\n${summary}`;
  }

  return prompt;
}
