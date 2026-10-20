import logging
import pandas as pd

log = logging.getLogger(__name__)


def _num(s):
    return pd.to_numeric(s, errors="coerce")


def _ts(s):
    return pd.to_datetime(s, errors="coerce")


def transform(raw: dict) -> dict:
    """Fix types and build derived columns. No rows are dropped here."""
    out = {}

    # --- customers
    c = raw["customers"].rename(columns={
        "customer_zip_code_prefix": "zip_code_prefix",
        "customer_city": "city",
        "customer_state": "state"})
    c["city"] = c["city"].str.strip().str.lower()
    c["state"] = c["state"].str.strip().str.upper()
    out["customers"] = c[["customer_id", "customer_unique_id",
                          "zip_code_prefix", "city", "state"]]

    # --- sellers
    s = raw["sellers"].rename(columns={
        "seller_zip_code_prefix": "zip_code_prefix",
        "seller_city": "city",
        "seller_state": "state"})
    s["city"] = s["city"].str.strip().str.lower()
    s["state"] = s["state"].str.strip().str.upper()
    out["sellers"] = s[["seller_id", "zip_code_prefix", "city", "state"]]

    # --- products (+ English category names)
    t = raw["translation"].rename(columns={
        "product_category_name": "category_pt",
        "product_category_name_english": "category_english"})
    p = raw["products"].rename(columns={
        "product_category_name": "category_pt",
        "product_weight_g": "weight_g",
        "product_photos_qty": "photos_qty"})
    p = p.merge(t, on="category_pt", how="left")
    p["category_english"] = (p["category_english"]
                             .fillna(p["category_pt"]).fillna("unknown"))
    p["weight_g"] = _num(p["weight_g"]).round().astype("Int64")
    p["photos_qty"] = _num(p["photos_qty"]).round().astype("Int64")
    out["products"] = p[["product_id", "category_pt", "category_english",
                         "weight_g", "photos_qty"]]

    # --- orders (delivery metrics)
    o = raw["orders"].copy()
    o["purchase_ts"] = _ts(o["order_purchase_timestamp"])
    o["delivered_ts"] = _ts(o["order_delivered_customer_date"])
    o["estimated_delivery_ts"] = _ts(o["order_estimated_delivery_date"])
    o["delivery_days"] = (o["delivered_ts"] - o["purchase_ts"]).dt.days.astype("Int64")
    o["delay_days"] = (o["delivered_ts"] - o["estimated_delivery_ts"]).dt.days.astype("Int64")
    known = o["delivered_ts"].notna() & o["estimated_delivery_ts"].notna()
    o["is_late"] = pd.Series(pd.NA, index=o.index, dtype="boolean")
    o.loc[known, "is_late"] = (o.loc[known, "delivered_ts"]
                               > o.loc[known, "estimated_delivery_ts"])
    out["orders"] = o[["order_id", "customer_id", "order_status", "purchase_ts",
                       "delivered_ts", "estimated_delivery_ts",
                       "delivery_days", "delay_days", "is_late"]]

    # --- order items
    i = raw["items"].copy()
    i["order_item_id"] = _num(i["order_item_id"]).astype("Int64")
    i["price"] = _num(i["price"])
    i["freight_value"] = _num(i["freight_value"])
    out["items"] = i[["order_id", "order_item_id", "product_id", "seller_id",
                      "price", "freight_value"]]

    # --- payments
    pay = raw["payments"].copy()
    pay["payment_sequential"] = _num(pay["payment_sequential"]).astype("Int64")
    pay["payment_installments"] = _num(pay["payment_installments"]).astype("Int64")
    pay["payment_value"] = _num(pay["payment_value"])
    out["payments"] = pay[["order_id", "payment_sequential", "payment_type",
                           "payment_installments", "payment_value"]]

    # --- reviews
    r = raw["reviews"].copy()
    r["review_score"] = _num(r["review_score"])
    r["review_creation_date"] = _ts(r["review_creation_date"])
    out["reviews"] = r[["review_id", "order_id", "review_score",
                        "review_creation_date"]]

    return out


def build_dim_date(dates: pd.Series) -> pd.DataFrame:
    """One row per calendar day between the first and last purchase."""
    days = pd.date_range(dates.min().normalize(), dates.max().normalize(), freq="D")
    d = pd.DataFrame({"full_date": days})
    d["date_key"] = d["full_date"].dt.strftime("%Y%m%d").astype(int)
    d["year"] = d["full_date"].dt.year
    d["quarter"] = d["full_date"].dt.quarter
    d["month"] = d["full_date"].dt.month
    d["month_name"] = d["full_date"].dt.month_name()
    d["day_of_month"] = d["full_date"].dt.day
    d["weekday_name"] = d["full_date"].dt.day_name()
    d["full_date"] = d["full_date"].dt.date
    return d[["date_key", "full_date", "year", "quarter", "month",
              "month_name", "day_of_month", "weekday_name"]]


if __name__ == "__main__":
    # quick self-test: python -m etl.transform
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")
    from etl.extract import extract
    data = transform(extract())
    for name, df in data.items():
        print(f"{name:10s} {df.shape}")
    print(data["orders"].head(3).T)