import logging
import pandas as pd
from etl.config import RAW

log = logging.getLogger(__name__)

FILES = {
    "customers": "olist_customers_dataset.csv",
    "sellers": "olist_sellers_dataset.csv",
    "products": "olist_products_dataset.csv",
    "translation": "product_category_name_translation.csv",
    "orders": "olist_orders_dataset.csv",
    "items": "olist_order_items_dataset.csv",
    "payments": "olist_order_payments_dataset.csv",
    "reviews": "olist_order_reviews_dataset.csv",
}


def extract() -> dict:
    """Read every source file as text. Types are fixed later in transform."""
    data = {}
    for name, filename in FILES.items():
        # utf-8-sig removes a hidden BOM character if the file has one
        df = pd.read_csv(RAW / filename, dtype=str, encoding="utf-8-sig")
        log.info("extracted %-12s %7d rows", name, len(df))
        data[name] = df
    return data