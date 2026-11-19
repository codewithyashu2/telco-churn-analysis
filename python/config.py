from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW_CSV = ROOT / "data" / "Telco-Customer-Churn.csv"
DB_PATH = ROOT / "data" / "telco_churn.db"
SQL_DIR = ROOT / "sql"
POWERBI_DIR = ROOT / "powerbi" / "data"
IMAGES_DIR = ROOT / "images"
