-- INGREDIENT BATCHES — batch-level tracking with FIFO support

CREATE TABLE ingredient_batches (
    batch_id            BIGSERIAL PRIMARY KEY,
    restaurant_id       INT NOT NULL REFERENCES restaurants(restaurant_id),
    ingredient_id       INT NOT NULL REFERENCES ingredients(ingredient_id),

    -- Source / supplier
    supplier_name       TEXT,
    supplier_contact    TEXT,

    -- Cost (batch-specific, may differ from catalog unit_cost)
    purchase_cost_per_unit  NUMERIC(10,4),

    -- Quantities
    qty_received        NUMERIC(12,4) NOT NULL,
    qty_remaining       NUMERIC(12,4) NOT NULL,

    -- Dates
    received_date       DATE NOT NULL DEFAULT CURRENT_DATE,
    expiration_date     DATE,

    -- Status: active (on shelf), depleted (used up), expired (past date)
    status              TEXT NOT NULL DEFAULT 'active'
                        CHECK (status IN ('active', 'depleted', 'expired')),

    created_at          TIMESTAMPTZ DEFAULT now()
);

-- FIFO lookups: only active batches, ordered by oldest expiration first
CREATE INDEX idx_batch_fifo
    ON ingredient_batches (restaurant_id, ingredient_id, expiration_date ASC NULLS LAST)
    WHERE status = 'active';

-- Find batches expiring soon (for alerts)
CREATE INDEX idx_batch_expiration
    ON ingredient_batches (restaurant_id, expiration_date)
    WHERE status = 'active';
