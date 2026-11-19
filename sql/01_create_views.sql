-- =====================================================================
-- 01_create_views.sql
-- Cleans the raw Telco table and derives the segmentation columns used
-- by every downstream query and by the Power BI dashboard.
-- Dialect: SQLite (portable to PostgreSQL / SQL Server with minor edits,
-- see README "Porting notes").
-- =====================================================================

DROP VIEW IF EXISTS vw_customer_segments;

CREATE VIEW vw_customer_segments AS
WITH cleaned AS (
    SELECT
        customerID                                           AS customer_id,
        gender,
        SeniorCitizen                                        AS senior_citizen,
        Partner                                              AS has_partner,
        Dependents                                           AS has_dependents,
        tenure                                               AS tenure_months,
        PhoneService                                         AS phone_service,
        InternetService                                      AS internet_service,
        Contract                                             AS contract_type,
        PaperlessBilling                                     AS paperless_billing,
        PaymentMethod                                        AS payment_method,
        MonthlyCharges                                       AS monthly_charges,
        -- 11 new customers (tenure = 0) have a blank TotalCharges string.
        CASE WHEN TRIM(TotalCharges) = '' THEN 0.0
             ELSE CAST(TotalCharges AS REAL) END             AS total_charges,
        CASE WHEN Churn = 'Yes' THEN 1 ELSE 0 END            AS churned,
        -- Add-on service flags (internet-dependent services only count when 'Yes')
        (OnlineSecurity   = 'Yes') + (OnlineBackup     = 'Yes')
      + (DeviceProtection = 'Yes') + (TechSupport      = 'Yes')
      + (StreamingTV      = 'Yes') + (StreamingMovies  = 'Yes') AS addon_services
    FROM telco_customers
)
SELECT
    *,
    -- Tenure bands
    CASE
        WHEN tenure_months <= 12 THEN '1. 0-12 months'
        WHEN tenure_months <= 24 THEN '2. 13-24 months'
        WHEN tenure_months <= 48 THEN '3. 25-48 months'
        ELSE                          '4. 49-72 months'
    END AS tenure_band,
    -- Service-usage bands (number of add-on services subscribed)
    CASE
        WHEN internet_service = 'No' THEN '0. No internet'
        WHEN addon_services   = 0    THEN '1. Internet only (0 add-ons)'
        WHEN addon_services <= 2     THEN '2. Light (1-2 add-ons)'
        WHEN addon_services <= 4     THEN '3. Moderate (3-4 add-ons)'
        ELSE                              '4. Heavy (5-6 add-ons)'
    END AS service_usage_band,
    -- Contract grouping used for the headline comparison
    CASE WHEN contract_type = 'Month-to-month' THEN 'Month-to-month'
         ELSE 'Annual+ (1 or 2 year)' END AS contract_group
FROM cleaned;
