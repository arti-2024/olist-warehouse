-- Olist star-schema warehouse
-- Safe to re-run: drops and recreates everything.
DROP TABLE IF EXISTS fact_payments, fact_order_items,
    dim_date, dim_product, dim_seller, dim_customer,
    quarantine, pipeline_runs CASCADE;

-- ---------- Dimensions ----------
CREATE TABLE dim_customer (
    customer_key       SERIAL PRIMARY KEY,
    customer_id        TEXT NOT NULL UNIQUE,   -- one per order in Olist
    customer_unique_id TEXT NOT NULL,          -- the real person (use for repeat customers)
    zip_code_prefix    TEXT,
    city               TEXT,
    state              TEXT
);

CREATE TABLE dim_seller (
    seller_key      SERIAL PRIMARY KEY,
    seller_id       TEXT NOT NULL UNIQUE,
    zip_code_prefix TEXT,
    city            TEXT,
    state           TEXT
);

CREATE TABLE dim_product (
    product_key      SERIAL PRIMARY KEY,
    product_id       TEXT NOT NULL UNIQUE,
    category_pt      TEXT,
    category_english TEXT,
    weight_g         INTEGER,
    photos_qty       INTEGER
);

CREATE TABLE dim_date (
    date_key     INTEGER PRIMARY KEY,          -- 20180131 style
    full_date    DATE NOT NULL UNIQUE,
    year         SMALLINT NOT NULL,
    quarter      SMALLINT NOT NULL,
    month        SMALLINT NOT NULL,
    month_name   TEXT NOT NULL,
    day_of_month SMALLINT NOT NULL,
    weekday_name TEXT NOT NULL
);

-- ---------- Facts ----------
CREATE TABLE fact_order_items (
    order_id              TEXT NOT NULL,
    order_item_id         INTEGER NOT NULL,
    customer_key          INTEGER NOT NULL REFERENCES dim_customer (customer_key),
    seller_key            INTEGER NOT NULL REFERENCES dim_seller (seller_key),
    product_key           INTEGER NOT NULL REFERENCES dim_product (product_key),
    purchase_date_key     INTEGER NOT NULL REFERENCES dim_date (date_key),
    order_status          TEXT,
    purchase_ts           TIMESTAMP,
    delivered_ts          TIMESTAMP,            -- NULL if not delivered
    estimated_delivery_ts TIMESTAMP,
    price                 NUMERIC(10,2) NOT NULL CHECK (price >= 0),
    freight_value         NUMERIC(10,2) CHECK (freight_value >= 0),
    delivery_days         INTEGER,              -- delivered minus purchase
    delay_days            INTEGER,              -- delivered minus estimated (positive = late)
    is_late               BOOLEAN,              -- NULL if not delivered
    review_score          SMALLINT CHECK (review_score BETWEEN 1 AND 5),
    PRIMARY KEY (order_id, order_item_id)
);

CREATE TABLE fact_payments (
    order_id             TEXT NOT NULL,
    payment_sequential   INTEGER NOT NULL,
    payment_type         TEXT,
    payment_installments INTEGER,
    payment_value        NUMERIC(10,2) CHECK (payment_value >= 0),
    PRIMARY KEY (order_id, payment_sequential)
);

-- ---------- Pipeline support ----------
CREATE TABLE quarantine (
    id             SERIAL PRIMARY KEY,
    source_table   TEXT NOT NULL,
    record         JSONB NOT NULL,              -- the rejected row
    reason         TEXT NOT NULL,               -- which rule failed
    quarantined_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE pipeline_runs (
    run_id      SERIAL PRIMARY KEY,
    started_at  TIMESTAMP NOT NULL DEFAULT now(),
    finished_at TIMESTAMP,
    status      TEXT,                           -- running, success, failed
    notes       TEXT
);