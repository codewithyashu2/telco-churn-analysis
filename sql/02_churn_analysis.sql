-- =====================================================================
-- 02_churn_analysis.sql
-- Churn rate % per segment. Every query returns:
--   customers, churned, churn_rate_pct, avg_monthly_charges
-- Run after 01_create_views.sql.
-- =====================================================================

-- Q1. Overall baseline ------------------------------------------------
SELECT
    COUNT(*)                                   AS customers,
    SUM(churned)                               AS churned,
    ROUND(100.0 * AVG(churned), 2)             AS churn_rate_pct,
    ROUND(AVG(monthly_charges), 2)             AS avg_monthly_charges
FROM vw_customer_segments;

-- Q2. Churn by contract type -------------------------------------------
SELECT
    contract_type,
    COUNT(*)                                   AS customers,
    SUM(churned)                               AS churned,
    ROUND(100.0 * AVG(churned), 2)             AS churn_rate_pct,
    ROUND(AVG(monthly_charges), 2)             AS avg_monthly_charges
FROM vw_customer_segments
GROUP BY contract_type
ORDER BY churn_rate_pct DESC;

-- Q3. Headline finding: month-to-month vs annual holders ----------------
--     relative_risk = segment churn rate / annual+ churn rate
WITH grp AS (
    SELECT contract_group,
           COUNT(*)           AS customers,
           SUM(churned)       AS churned,
           1.0 * AVG(churned) AS churn_rate
    FROM vw_customer_segments
    GROUP BY contract_group
)
SELECT
    g.contract_group,
    g.customers,
    g.churned,
    ROUND(100 * g.churn_rate, 2)                                   AS churn_rate_pct,
    ROUND(g.churn_rate / b.churn_rate, 2)                          AS relative_risk_vs_annual
FROM grp g
CROSS JOIN (SELECT churn_rate FROM grp WHERE contract_group LIKE 'Annual%') b
ORDER BY churn_rate_pct DESC;

-- Q4. Churn by tenure band ---------------------------------------------
SELECT
    tenure_band,
    COUNT(*)                                   AS customers,
    SUM(churned)                               AS churned,
    ROUND(100.0 * AVG(churned), 2)             AS churn_rate_pct,
    ROUND(AVG(monthly_charges), 2)             AS avg_monthly_charges
FROM vw_customer_segments
GROUP BY tenure_band
ORDER BY tenure_band;

-- Q5. Churn by service usage (add-on depth) ------------------------------
SELECT
    service_usage_band,
    COUNT(*)                                   AS customers,
    SUM(churned)                               AS churned,
    ROUND(100.0 * AVG(churned), 2)             AS churn_rate_pct,
    ROUND(AVG(monthly_charges), 2)             AS avg_monthly_charges
FROM vw_customer_segments
GROUP BY service_usage_band
ORDER BY service_usage_band;

-- Q6. Churn by internet service type -------------------------------------
SELECT
    internet_service,
    COUNT(*)                                   AS customers,
    ROUND(100.0 * AVG(churned), 2)             AS churn_rate_pct
FROM vw_customer_segments
GROUP BY internet_service
ORDER BY churn_rate_pct DESC;

-- Q7. Contract x tenure matrix (where exactly is the risk?) --------------
SELECT
    contract_type,
    tenure_band,
    COUNT(*)                                   AS customers,
    SUM(churned)                               AS churned,
    ROUND(100.0 * AVG(churned), 2)             AS churn_rate_pct
FROM vw_customer_segments
GROUP BY contract_type, tenure_band
ORDER BY contract_type, tenure_band;

-- Q8. Contract x service usage -------------------------------------------
SELECT
    contract_type,
    service_usage_band,
    COUNT(*)                                   AS customers,
    ROUND(100.0 * AVG(churned), 2)             AS churn_rate_pct
FROM vw_customer_segments
GROUP BY contract_type, service_usage_band
ORDER BY contract_type, service_usage_band;

-- Q9. Ranked risk segments (contract x tenure x usage) --------------------
--     min 100 customers so tiny cells don't dominate; window functions rank
--     segments and show each one's share of ALL churners.
WITH seg AS (
    SELECT
        contract_type, tenure_band, service_usage_band,
        COUNT(*)           AS customers,
        SUM(churned)       AS churned,
        1.0 * AVG(churned) AS churn_rate
    FROM vw_customer_segments
    GROUP BY contract_type, tenure_band, service_usage_band
    HAVING COUNT(*) >= 100
)
SELECT
    RANK() OVER (ORDER BY churn_rate DESC)                          AS risk_rank,
    contract_type, tenure_band, service_usage_band,
    customers, churned,
    ROUND(100 * churn_rate, 2)                                      AS churn_rate_pct,
    ROUND(100.0 * churned / SUM(churned) OVER (), 2)                AS pct_of_all_churners
FROM seg
ORDER BY risk_rank
LIMIT 10;

-- Q10. Revenue at risk: monthly recurring revenue lost to churn -----------
SELECT
    contract_type,
    ROUND(SUM(CASE WHEN churned = 1 THEN monthly_charges END), 2)   AS mrr_lost,
    ROUND(100.0 * SUM(CASE WHEN churned = 1 THEN monthly_charges END)
          / SUM(SUM(CASE WHEN churned = 1 THEN monthly_charges END)) OVER (), 2) AS pct_of_mrr_lost
FROM vw_customer_segments
GROUP BY contract_type
ORDER BY mrr_lost DESC;
