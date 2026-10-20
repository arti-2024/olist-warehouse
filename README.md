<h1 align="center">Olist E-commerce Data Warehouse</h1>

<p align="center">
  A Python ETL pipeline that turns 8 messy marketplace files into a validated PostgreSQL star schema,<br/>
  then uses it to answer one question: <b>do late deliveries hurt customer reviews?</b>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3776AB?logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/pandas-150458?logo=pandas&logoColor=white" alt="pandas">
  <img src="https://img.shields.io/badge/PostgreSQL-4169E1?logo=postgresql&logoColor=white" alt="PostgreSQL">
  <img src="https://img.shields.io/badge/Docker-2496ED?logo=docker&logoColor=white" alt="Docker">
  <img src="https://img.shields.io/badge/SQL-336791" alt="SQL">
</p>

## 🎯 The problem
An online retailer keeps orders, payments, customers, sellers and reviews in separate files, and some of the data is wrong.
Nobody can answer "why are our ratings dropping?" until the data is joined, cleaned and trusted.
This project builds that trusted layer and then uses it to find out where deliveries go wrong.

## 📊 At a glance
| | |
|---|---|
| Order items loaded | **112,650** |
| Payments loaded | **103,886** |
| Orders / customers | **99,441** each |
| Warehouse tables | **6** (4 dimensions, 2 facts) |
| Data-quality rules | **29** |
| Reconciliation checks | **4**, all passing |
| Full pipeline run | **about 58 seconds** |

## 🔄 How the pipeline works
```mermaid
flowchart LR
    A[8 source CSV files] --> B[Extract<br/>pandas]
    B --> C[Transform<br/>types, dates, delivery metrics]
    C --> D{Validate<br/>29 rules}
    D -- valid rows --> E[(PostgreSQL<br/>star schema)]
    D -- rejected rows --> Q[(quarantine table)]
    E --> R[Reconcile<br/>counts and totals]
    E --> S[SQL analysis<br/>and charts]
```

1. **Extract**: read every file as text so zip codes keep leading zeros
2. **Transform**: fix types and dates, add English category names, calculate `delivery_days`, `delay_days` and `is_late`
3. **Validate**: 29 rules (missing keys, duplicates, impossible dates, orphan records); failing rows go to a `quarantine` table with the reason. No row broke a rule on this dataset.
4. **Load**: truncate and reload everything in one transaction, so a re-run gives the same result and a failure leaves the old data untouched
5. **Reconcile**: source row counts and totals must equal warehouse plus quarantine, or the run fails

## 🗂️ Warehouse design
```mermaid
erDiagram
    dim_customer ||--o{ fact_order_items : customer_key
    dim_seller   ||--o{ fact_order_items : seller_key
    dim_product  ||--o{ fact_order_items : product_key
    dim_date     ||--o{ fact_order_items : purchase_date_key
    fact_order_items {
        text order_id
        int order_item_id
        numeric price
        int delivery_days
        bool is_late
        smallint review_score
    }
    fact_payments {
        text order_id
        int payment_sequential
        numeric payment_value
    }
```

## 🔎 Findings (96,476 delivered orders)
- **8.11%** of delivered orders arrived after the estimated date.
- Late orders average **2.57** stars against **4.29** for on-time orders, a gap of 1.72 points.
- Late rates range from **23.9% in Alagoas** and **19.7% in Maranhão** down to **5.9% in São Paulo** and **2.9% in Rondônia**.
- Review scores fall as delays grow: **4.29** on time, **3.59** up to 3 days late, **2.10** for 4-7 days late and **1.70** for more than 7 days late.
- These are associations in the data, not proof that lateness alone causes low scores.

![Late rate by state](reports/late_rate_by_state.png)

![Review score by delay](reports/review_by_delay.png)

## 📁 Project structure
```
etl/                extract, transform, validate, load, reconcile, run_pipeline
sql/                schema.sql, analytics.sql
analysis/           charts.py
reports/            quality report and charts
docker-compose.yml  PostgreSQL service
```

## ▶️ Run it
<details>
<summary>Show commands</summary>

```
docker compose up -d
pip install pandas sqlalchemy psycopg2-binary matplotlib
docker cp sql/schema.sql olist_db:/schema.sql
docker exec olist_db psql -U olist -d olist -f /schema.sql
python -m etl.run_pipeline
python analysis/charts.py
```
Download the dataset from Kaggle ("Brazilian E-Commerce Public Dataset by Olist") and place the CSV files in `data/raw/`.
</details>

## 🛣️ Roadmap
- [x] Star-schema design and Python ETL
- [x] Validation rules and reconciliation checks
- [x] SQL analysis and charts
- [ ] Index benchmarks (before and after timings)
- [ ] Scheduling with Airflow
- [ ] Larger-scale processing with Spark

## 🙏 Data
[Brazilian E-Commerce Public Dataset by Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) on Kaggle.