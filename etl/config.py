from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
REPORTS = ROOT / "reports"

# Local development database from docker-compose.yml
DB_URL = "postgresql+psycopg2://olist:olist_pw@localhost:5432/olist"