"""Load the raw Telco CSV into SQLite and create the segmentation view."""
import sqlite3
import pandas as pd
from config import RAW_CSV, DB_PATH, SQL_DIR


def main() -> None:
    # dtype=str keeps TotalCharges' blank strings intact so the SQL view
    # demonstrates the cleaning step (as you would see in a real warehouse).
    df = pd.read_csv(RAW_CSV, dtype={"TotalCharges": str})
    print(f"Loaded {len(df):,} rows x {df.shape[1]} columns from {RAW_CSV.name}")

    with sqlite3.connect(DB_PATH) as con:
        df.to_sql("telco_customers", con, if_exists="replace", index=False)
        con.executescript((SQL_DIR / "01_create_views.sql").read_text())
        n = con.execute("SELECT COUNT(*) FROM vw_customer_segments").fetchone()[0]
    print(f"Created view vw_customer_segments ({n:,} rows) in {DB_PATH.name}")


if __name__ == "__main__":
    main()
