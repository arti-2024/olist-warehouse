import pandas as pd

RULE_COUNT = {}  # table name -> number of rules checked (used in the report)


def apply_rules(table, df, rules):
    """rules = list of (reason, boolean Series where True means the row FAILS).
    Returns (valid_rows, rejected_rows). A rejected row keeps its first failing reason."""
    RULE_COUNT[table] = len(rules)
    reason = pd.Series("", index=df.index, dtype="object")
    for name, fail in rules:
        fail = fail.fillna(False).astype(bool)
        reason = reason.mask(fail & (reason == ""), name)
    rejected = df[reason != ""].copy()
    rejected["reason"] = reason[reason != ""]
    valid = df[reason == ""].copy()
    return valid, rejected


def validate(data: dict):
    good, bad = {}, {}

    c = data["customers"]
    good["customers"], bad["customers"] = apply_rules("customers", c, [
        ("customer_id missing", c["customer_id"].isna()),
        ("customer_unique_id missing", c["customer_unique_id"].isna()),
        ("duplicate customer_id", c.duplicated("customer_id")),
    ])

    s = data["sellers"]
    good["sellers"], bad["sellers"] = apply_rules("sellers", s, [
        ("seller_id missing", s["seller_id"].isna()),
        ("duplicate seller_id", s.duplicated("seller_id")),
    ])

    p = data["products"]
    good["products"], bad["products"] = apply_rules("products", p, [
        ("product_id missing", p["product_id"].isna()),
        ("duplicate product_id", p.duplicated("product_id")),
        ("negative weight", p["weight_g"] < 0),
    ])

    o = data["orders"]
    good["orders"], bad["orders"] = apply_rules("orders", o, [
        ("order_id missing", o["order_id"].isna()),
        ("duplicate order_id", o.duplicated("order_id")),
        ("purchase timestamp missing or invalid", o["purchase_ts"].isna()),
        ("customer not found", ~o["customer_id"].isin(good["customers"]["customer_id"])),
        ("delivered before purchase", o["delivered_ts"] < o["purchase_ts"]),
    ])

    i = data["items"]
    good["items"], bad["items"] = apply_rules("items", i, [
        ("order_id, product_id or seller_id missing",
         i[["order_id", "product_id", "seller_id"]].isna().any(axis=1)),
        ("order_item_id missing", i["order_item_id"].isna()),
        ("duplicate (order_id, order_item_id)", i.duplicated(["order_id", "order_item_id"])),
        ("price missing or not positive", ~(i["price"] > 0)),
        ("negative freight", i["freight_value"] < 0),
        ("order not found", ~i["order_id"].isin(good["orders"]["order_id"])),
        ("product not found", ~i["product_id"].isin(good["products"]["product_id"])),
        ("seller not found", ~i["seller_id"].isin(good["sellers"]["seller_id"])),
    ])

    pay = data["payments"]
    good["payments"], bad["payments"] = apply_rules("payments", pay, [
        ("order_id or payment_sequential missing",
         pay[["order_id", "payment_sequential"]].isna().any(axis=1)),
        ("duplicate (order_id, payment_sequential)",
         pay.duplicated(["order_id", "payment_sequential"])),
        ("payment value missing or negative", ~(pay["payment_value"] >= 0)),
        ("order not found", ~pay["order_id"].isin(good["orders"]["order_id"])),
    ])

    r = data["reviews"]
    good["reviews"], bad["reviews"] = apply_rules("reviews", r, [
        ("review_id or order_id missing", r[["review_id", "order_id"]].isna().any(axis=1)),
        ("duplicate (review_id, order_id)", r.duplicated(["review_id", "order_id"])),
        ("review score not in 1-5", ~r["review_score"].isin([1, 2, 3, 4, 5])),
        ("order not found", ~r["order_id"].isin(good["orders"]["order_id"])),
    ])

    return good, bad


def quality_report(data: dict, good: dict, bad: dict) -> str:
    lines = ["DATA QUALITY REPORT", "=" * 60]
    for name in good:
        lines.append(f"{name}: {len(data[name])} rows in, "
                     f"{len(good[name])} valid, {len(bad[name])} rejected")
        if len(bad[name]):
            for reason, n in bad[name]["reason"].value_counts().items():
                lines.append(f"    - {reason}: {n}")
    lines.append("=" * 60)
    lines.append(f"Rules checked: {sum(RULE_COUNT.values())}")
    lines.append(f"Rows quarantined: {sum(len(b) for b in bad.values())}")
    return "\n".join(lines)