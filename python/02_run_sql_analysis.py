"""Run the analysis queries and export the tables that feed Power BI."""
import sqlite3
import pandas as pd
from config import DB_PATH, POWERBI_DIR

POWERBI_DIR.mkdir(parents=True, exist_ok=True)

# One tidy segment table (long format) -> single visual-friendly source for Power BI
SEGMENT_DIMS = {
    "Contract type": "contract_type",
    "Tenure band": "tenure_band",
    "Service usage": "service_usage_band",
    "Internet service": "internet_service",
}


def main() -> None:
    con = sqlite3.connect(DB_PATH)

    # 1) Customer-level fact table (drill-through target)
    fact = pd.read_sql("SELECT * FROM vw_customer_segments", con)
    fact.to_csv(POWERBI_DIR / "fact_customers.csv", index=False)

    # 2) Pre-aggregated segment table (churn rate % per segment)
    frames = []
    for label, col in SEGMENT_DIMS.items():
        q = f"""
            SELECT '{label}' AS segment_type, {col} AS segment,
                   COUNT(*) AS customers, SUM(churned) AS churned,
                   ROUND(100.0 * AVG(churned), 2) AS churn_rate_pct,
                   ROUND(AVG(monthly_charges), 2) AS avg_monthly_charges
            FROM vw_customer_segments GROUP BY {col}"""
        frames.append(pd.read_sql(q, con))
    seg = pd.concat(frames, ignore_index=True)
    seg.to_csv(POWERBI_DIR / "segment_summary.csv", index=False)

    # 3) Contract x tenure heatmap table
    heat = pd.read_sql(
        """SELECT contract_type, tenure_band, COUNT(*) AS customers,
                  SUM(churned) AS churned,
                  ROUND(100.0 * AVG(churned), 2) AS churn_rate_pct
           FROM vw_customer_segments GROUP BY contract_type, tenure_band""", con)
    heat.to_csv(POWERBI_DIR / "contract_tenure_matrix.csv", index=False)

    # 4) Print the headline results
    pd.set_option("display.width", 160)
    print("\n=== Churn by contract type ===")
    print(pd.read_sql("""SELECT contract_type, COUNT(*) customers, SUM(churned) churned,
          ROUND(100.0*AVG(churned),2) churn_rate_pct FROM vw_customer_segments
          GROUP BY contract_type ORDER BY churn_rate_pct DESC""", con).to_string(index=False))

    print("\n=== Headline: month-to-month vs annual+ ===")
    print(pd.read_sql("""
        WITH grp AS (SELECT contract_group, COUNT(*) customers, SUM(churned) churned,
                            1.0*AVG(churned) r FROM vw_customer_segments GROUP BY contract_group)
        SELECT g.contract_group, g.customers, g.churned, ROUND(100*g.r,2) churn_rate_pct,
               ROUND(g.r/b.r,2) relative_risk
        FROM grp g CROSS JOIN (SELECT r FROM grp WHERE contract_group LIKE 'Annual%') b
        ORDER BY churn_rate_pct DESC""", con).to_string(index=False))

    print("\n=== Top 10 risk segments (min 100 customers) ===")
    print(pd.read_sql("""
        WITH seg AS (SELECT contract_type, tenure_band, service_usage_band,
                COUNT(*) customers, SUM(churned) churned, 1.0*AVG(churned) r
             FROM vw_customer_segments GROUP BY 1,2,3 HAVING COUNT(*)>=100)
        SELECT RANK() OVER (ORDER BY r DESC) rnk, contract_type, tenure_band,
               service_usage_band, customers, ROUND(100*r,2) churn_rate_pct,
               ROUND(100.0*churned/SUM(churned) OVER (),2) pct_of_all_churners
        FROM seg ORDER BY rnk LIMIT 10""", con).to_string(index=False))

    print(f"\nExported Power BI tables to {POWERBI_DIR}")
    con.close()


if __name__ == "__main__":
    main()
