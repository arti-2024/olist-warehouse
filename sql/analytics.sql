\echo '--- Q2. Overall late-delivery rate'
SELECT COUNT(DISTINCT order_id) FILTER (WHERE is_late) AS late_orders,
       COUNT(DISTINCT order_id) FILTER (WHERE is_late IS NOT NULL) AS delivered_orders,
       ROUND(100.0 * COUNT(DISTINCT order_id) FILTER (WHERE is_late)
             / COUNT(DISTINCT order_id) FILTER (WHERE is_late IS NOT NULL), 2) AS late_pct
FROM fact_order_items;

\echo '--- Q3. KEY QUESTION: average review score, on time vs late'
WITH o AS (
    SELECT DISTINCT order_id, is_late, review_score
    FROM fact_order_items
    WHERE is_late IS NOT NULL AND review_score IS NOT NULL
)
SELECT CASE WHEN is_late THEN 'Late' ELSE 'On time' END AS delivery,
       COUNT(*) AS orders,
       ROUND(AVG(review_score), 2) AS avg_review
FROM o
GROUP BY is_late
ORDER BY is_late;

\echo '--- Q4. Late rate by customer state (states with 100+ delivered orders)'
WITH o AS (
    SELECT DISTINCT f.order_id, c.state, f.is_late
    FROM fact_order_items f
    JOIN dim_customer c ON c.customer_key = f.customer_key
    WHERE f.is_late IS NOT NULL
)
SELECT state, COUNT(*) AS delivered_orders,
       ROUND(100.0 * AVG(is_late::int), 2) AS late_pct
FROM o
GROUP BY state
HAVING COUNT(*) >= 100
ORDER BY late_pct DESC;

\echo '--- Q5. Review score by how late the order was'
WITH o AS (
    SELECT DISTINCT order_id, delay_days, review_score
    FROM fact_order_items
    WHERE delay_days IS NOT NULL AND review_score IS NOT NULL
)
SELECT CASE WHEN delay_days <= 0 THEN '1. On time or early'
            WHEN delay_days <= 3 THEN '2. 1-3 days late'
            WHEN delay_days <= 7 THEN '3. 4-7 days late'
            ELSE '4. More than 7 days late' END AS bucket,
       COUNT(*) AS orders,
       ROUND(AVG(review_score), 2) AS avg_review
FROM o
GROUP BY 1
ORDER BY 1;