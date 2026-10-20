from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from sqlalchemy import create_engine

OUT = Path(__file__).resolve().parent.parent / "reports"
OUT.mkdir(exist_ok=True)
engine = create_engine("postgresql+psycopg2://olist:olist_pw@localhost:5432/olist")

# ---- Chart 1: late-delivery rate by customer state
q1 = """
WITH o AS (
    SELECT DISTINCT f.order_id, c.state, f.is_late
    FROM fact_order_items f
    JOIN dim_customer c ON c.customer_key = f.customer_key
    WHERE f.is_late IS NOT NULL
)
SELECT state, COUNT(*) AS delivered_orders, 100.0 * AVG(is_late::int) AS late_pct
FROM o GROUP BY state HAVING COUNT(*) >= 100
ORDER BY late_pct DESC
"""
d1 = pd.read_sql(q1, engine).sort_values("late_pct")
fig, ax = plt.subplots(figsize=(8, 8))
bars = ax.barh(d1["state"], d1["late_pct"], color="#1a6f8a")
for b, v in zip(bars, d1["late_pct"]):
    ax.text(v + 0.3, b.get_y() + b.get_height() / 2, f"{v:.1f}%", va="center", fontsize=8)
ax.set_xlabel("Late deliveries (% of delivered orders)")
ax.set_title("Late-delivery rate by customer state\n(states with 100+ delivered orders)")
ax.spines[["top", "right"]].set_visible(False)
fig.savefig(OUT / "late_rate_by_state.png", dpi=150, bbox_inches="tight")
plt.close(fig)

# ---- Chart 2: average review score by lateness
q2 = """
WITH o AS (
    SELECT DISTINCT order_id, is_late, delay_days, review_score
    FROM fact_order_items
    WHERE is_late IS NOT NULL AND review_score IS NOT NULL
)
SELECT CASE WHEN NOT is_late THEN '1. On time or early'
            WHEN delay_days <= 3 THEN '2. Late, up to 3 days'
            WHEN delay_days <= 7 THEN '3. Late, 4-7 days'
            ELSE '4. Late, more than 7 days' END AS bucket,
       COUNT(*) AS orders, AVG(review_score) AS avg_review
FROM o GROUP BY 1 ORDER BY 1
"""
d2 = pd.read_sql(q2, engine)
print(d2)
fig, ax = plt.subplots(figsize=(8, 4.5))
bars = ax.bar(d2["bucket"].str[3:], d2["avg_review"], color="#1a6f8a")
for b, v, n in zip(bars, d2["avg_review"], d2["orders"]):
    ax.text(b.get_x() + b.get_width() / 2, v + 0.05, f"{v:.2f}\n({n:,} orders)",
            ha="center", fontsize=9)
ax.set_ylim(0, 5.2)
ax.set_ylabel("Average review score (1-5)")
ax.set_title("Review score falls as deliveries get later")
ax.spines[["top", "right"]].set_visible(False)
plt.setp(ax.get_xticklabels(), rotation=12, ha="right")
fig.savefig(OUT / "review_by_delay.png", dpi=150, bbox_inches="tight")
plt.close(fig)
print("charts saved in", OUT)