import logging
from sqlalchemy import text

log = logging.getLogger(__name__)


def reconcile(engine, data: dict, bad: dict):
    """Source totals must equal warehouse totals plus quarantined totals."""
    with engine.connect() as conn:
        n_fact, sum_fact = conn.execute(text(
            "SELECT count(*), coalesce(sum(price), 0) FROM fact_order_items")).one()
        n_pay, sum_pay = conn.execute(text(
            "SELECT count(*), coalesce(sum(payment_value), 0) FROM fact_payments")).one()

    items, pays = data["items"], data["payments"]
    checks = [
        ("order items: row count", len(items), n_fact + len(bad["items"])),
        ("order items: total price", float(items["price"].sum()),
         float(sum_fact) + float(bad["items"]["price"].sum())),
        ("payments: row count", len(pays), n_pay + len(bad["payments"])),
        ("payments: total value", float(pays["payment_value"].sum()),
         float(sum_pay) + float(bad["payments"]["payment_value"].sum())),
    ]

    failed = False
    for name, source, warehouse in checks:
        ok = abs(source - warehouse) < 0.01
        failed = failed or not ok
        log.info("reconcile %-26s source=%14.2f warehouse+quarantine=%14.2f %s",
                 name, source, warehouse, "OK" if ok else "MISMATCH")
    if failed:
        raise RuntimeError("Reconciliation failed: source and warehouse totals differ")
    return checks