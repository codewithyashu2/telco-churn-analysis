# Power BI Dashboard Build Guide

This guide rebuilds the **Telco Retention Risk** report from the SQL outputs in about 30 minutes.
`images/dashboard_preview.png` shows the target layout.

## 1. Load the data

`Home -> Get data -> Text/CSV`, load these three files from `powerbi/data/`
(generate them first with `python python/02_run_sql_analysis.py`):

| Table | Grain | Used for |
|---|---|---|
| `fact_customers` | 1 row per customer | KPI cards, slicers, drill-through |
| `segment_summary` | 1 row per segment | (optional) quick bar charts |
| `contract_tenure_matrix` | contract x tenure | (optional) heatmap |

> **Alternative:** connect Power BI straight to your own SQL Server / PostgreSQL instance
> and load `vw_customer_segments` (see README "Porting notes"). Everything below works the same.

**Power Query checks:** set `churned`, `senior_citizen`, `tenure_months`, `addon_services` to *Whole number*;
`monthly_charges`, `total_charges` to *Decimal number*. Remove nothing, the SQL view already cleaned the data.

## 2. Sort order for the band columns

The band labels start with a number (`1. 0-12 months`) so they sort correctly.
For a cleaner axis label, add calculated columns:

```DAX
Tenure Band Label = MID ( fact_customers[tenure_band], 4, 50 )
Usage Band Label  = MID ( fact_customers[service_usage_band], 4, 50 )
```

Then select each label column -> *Column tools -> Sort by column* -> the original band column.

## 3. DAX measures

Create a `_Measures` table (*Home -> Enter data*, empty) and add:

```DAX
Customers = COUNTROWS ( fact_customers )

Churned Customers = SUM ( fact_customers[churned] )

Churn Rate % =
DIVIDE ( [Churned Customers], [Customers] )          -- format as 0.0%

Overall Churn Rate % =
CALCULATE ( [Churn Rate %], ALL ( fact_customers ) )  -- baseline, ignores filters

Churn vs Overall (pp) =
( [Churn Rate %] - [Overall Churn Rate %] ) * 100

Avg Monthly Charges = AVERAGE ( fact_customers[monthly_charges] )

MRR Lost =
CALCULATE (
    SUM ( fact_customers[monthly_charges] ),
    fact_customers[churned] = 1
)

Share of All Churners % =
DIVIDE (
    [Churned Customers],
    CALCULATE ( [Churned Customers], ALL ( fact_customers ) )
)

-- Headline measures --------------------------------------------------------
Month-to-Month Churn % =
CALCULATE ( [Churn Rate %], fact_customers[contract_type] = "Month-to-month" )

Annual Plus Churn % =
CALCULATE (
    [Churn Rate %],
    fact_customers[contract_type] IN { "One year", "Two year" }
)

One Year Churn % =
CALCULATE ( [Churn Rate %], fact_customers[contract_type] = "One year" )

Risk Multiple vs Annual+ =
DIVIDE ( [Month-to-Month Churn %], [Annual Plus Churn %] )     -- format 0.0"x"

Risk Multiple vs One-Year =
DIVIDE ( [Month-to-Month Churn %], [One Year Churn %] )        -- format 0.0"x"

Risk Flag =
IF ( [Churn Rate %] >= 1.5 * [Overall Churn Rate %], "High risk", "Normal" )
```

Expected values with no filters: Customers **7,043**, Churn Rate **26.5%**,
Month-to-Month **42.7%**, vs Annual+ **6.3x**, vs One-Year **3.8x**.
If your cards match, the model is wired correctly.

## 4. Report page layout (16:9)

| Zone | Visual | Fields |
|---|---|---|
| Top row | 4 x **Card** | `Customers`, `Overall Churn Rate %`, `Month-to-Month Churn %`, `Risk Multiple vs One-Year` |
| Left-middle | **Clustered column** | X: `contract_type` / Y: `Churn Rate %` / Tooltip: `Customers`, `MRR Lost` |
| Right-middle | **Clustered column** | X: `Tenure Band Label` / Y: `Churn Rate %` |
| Left-bottom | **Clustered column** | X: `Usage Band Label` / Y: `Churn Rate %` |
| Right-bottom | **Matrix** | Rows: `contract_type`, Columns: `Tenure Band Label`, Values: `Churn Rate %` with *conditional formatting -> background colour -> gradient* (white -> red) |
| Right rail | **Slicers** | `internet_service`, `payment_method`, `senior_citizen`, `paperless_billing` |

**Formatting tips**
- Use *Conditional formatting -> Rules* on the contract column chart: colour red where `Risk Flag = "High risk"`, otherwise blue.
- Add a constant line at `Overall Churn Rate %` (*Analytics pane -> Constant line -> fx*) so every bar is read against the baseline.
- Import `powerbi/telco_theme.json` via *View -> Themes -> Browse for themes*.

## 5. Drill-through page ("Customer Detail")

1. Add a new page, name it **Customer Detail**.
2. Drag `contract_type`, `tenure_band`, `service_usage_band` into **Drill through -> Add drill-through fields here**
   (turn *Keep all filters* **on**).
3. Add visuals: a **Table** with `customer_id`, `tenure_months`, `monthly_charges`, `internet_service`,
   `payment_method`, `churned`, sorted by `monthly_charges` descending; cards for `Customers`,
   `Churn Rate %`, `MRR Lost`; a column chart of customer count by `tenure_months`.
4. Power BI adds a back button automatically.
5. On the main page, **right-click any bar -> Drill through -> Customer Detail** to see the exact customers behind a segment.

Optional: add a **Drill-down hierarchy** `contract_type -> tenure_band -> service_usage_band` on the contract chart
so users can click the down-arrow to go from "Month-to-month" to "Month-to-month, 0-12 months", etc.

## 6. Key insight callout (text box)

> Month-to-month customers churn at **42.7%**, **3.8x** the one-year rate and **6.3x** the
> annual+ rate, and account for **89%** of all churners and **87%** of lost MRR.
> Highest-risk cell: month-to-month, 0-12 months tenure, no add-ons, **60% churn**.

## 7. Publish / share

Save as `powerbi/telco_churn_dashboard.pbix`, export a PNG/PDF of the report, and drop screenshots
into `images/` so the README can show the real dashboard instead of the preview.
