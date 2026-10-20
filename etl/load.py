import json
import logging

import pandas as pd
from sqlalchemy import create_engine, text

from etl.config import DB_URL
from etl.transform import build_dim_date

log = logging.getLogger(__name__)

FACT_COLUMNS = ["order_id", "order_item_id", "customer_key", "seller_key",
                "product_key", "purchase_date_key", "order_status", "purchase_ts",
                "delivered_ts", "estimated_delivery_ts", "price", "freight_value",
                "delivery_days", "delay_days", "is_late", "review_score"]


def get_engine():
    return create_engine(DB_URL)


def _insert(conn, table, df):
    df.to_sql(table, conn, if_exists="append", index=False, chunksize=5000)
    log.info("loaded %-18s %7d rows", table, len(df))


def _keys(conn, table, key_col, nat_col):
    return pd.read_sql(text(f"SELECT {key_col}, {nat_col} FROM {table}"), conn)


def load_warehouse(engine, good: dict, bad: dict):
    """Empty the warehouse and reload it in ONE transaction.
    Re-running gives the same result, and a failure leaves the old data untouched."""
    with engine.begin() as conn:
        conn.execute(text(
            "TRUNCATE fact_payments, fact_order_items, dim_date, dim_product, "
            "dim_seller, dim_customer, quarantine RESTART IDENTITY CASCADE"))

        # dimensions
        _insert(conn, "dim_customer", good["customers"])
        _insert(conn, "dim_seller", good["sellers"])
        _insert(conn, "dim_product", good["products"])
        _insert(conn, "dim_date", build_dim_date(good["orders"]["purchase_ts"]))

        customer_keys = _keys(conn, "dim_customer", "customer_key", "customer_id")
        seller_keys = _keys(conn, "dim_seller", "seller_key", "seller_id")
        product_keys = _keys(conn, "dim_product", "product_key", "product_id")

        # fact_order_items: items + order info + dimension keys + one review score
        orders = good["orders"]
        items = good["items"]
        f = (items.merge(orders, on="order_id", how="inner")
                  .merge(customer_keys, on="customer_id", how="inner")
                  .merge(seller_keys, on="seller_id", how="inner")
                  .merge(product_keys, on="product_id", how="inner"))
        f["purchase_date_key"] = f["purchase_ts"].dt.strftime("%Y%m%d").astype(int)

        latest_review = (good["reviews"].sort_values("review_creation_date")
                         .drop_duplicates("order_id", keep="last"))
        f = f.merge(latest_review[["order_id", "review_score"]], on="order_id", how="left")
        f["review_score"] = f["review_score"].round().astype("Int64")

        if len(f) != len(items):
            raise RuntimeError(f"Fact build changed row count: {len(items)} -> {len(f)}")
        _insert(conn, "fact_order_items", f[FACT_COLUMNS])

        _insert(conn, "fact_payments", good["payments"])

        # rejected rows go to the quarantine table with their reason
        rows = []
        for table, df in bad.items():
            if df.empty:
                continue
            records = json.loads(df.drop(columns="reason").to_json(
                orient="records", date_format="iso"))
            for rec, reason in zip(records, df["reason"]):
                rows.append({"source_table": table, "record": json.dumps(rec),
                             "reason": reason})
        if rows:
            conn.execute(text(
                "INSERT INTO quarantine (source_table, record, reason) "
                "VALUES (:source_table, CAST(:record AS JSONB), :reason)"), rows)
        log.info("quarantined %d rows", len(rows))