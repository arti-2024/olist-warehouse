# Olist E-commerce Data Warehouse

A PostgreSQL star-schema warehouse built with a Python ETL pipeline on the public
Olist Brazilian e-commerce dataset. Goal: answer one business question, **do late
deliveries hurt customer reviews, and where?**

## What the pipeline does
1. **Extract** 8 source CSV files with pandas
2. **Transform** types and dates, add English category names, calculate `delivery_days`, `delay_days` and `is_late`
3. **Validate** with 29 data-quality rules; rejected rows go to a `quarantine` table with the reason
4. **Load** a star schema into PostgreSQL in one transaction (safe to re-run)
5. **Reconcile** row counts and totals between source files and warehouse

## Results of the latest run
- 112,650 order items, 103,886 payments, 99,441 orders loaded
- 6 warehouse tables (4 dimensions, 2 facts) plus quarantine and run-log tables
- 29 validation rules and 4 reconciliation checks, all passing
- Full pipeline runtime: about 58 seconds

## Run it
```
docker compose up -d
pip install pandas sqlalchemy psycopg2-binary
docker cp sql/schema.sql olist_db:/schema.sql
docker exec olist_db psql -U olist -d olist -f /schema.sql
python -m etl.run_pipeline
```
Download the dataset from Kaggle ("Brazilian E-Commerce Public Dataset by Olist")
and place the CSV files in `data/raw/`.

## Next steps
Analytics queries, indexing benchmarks, charts, scheduling with Airflow.