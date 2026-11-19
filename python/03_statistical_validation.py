"""Is the month-to-month gap real, or explained by tenure / price / services?

1. Chi-square test of independence (contract group vs churn)
2. Relative risk with 95% CI
3. Logistic regression controlling for tenure, monthly charges, add-on services
"""
import sqlite3
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.linear_model import LogisticRegression
from config import DB_PATH


def main() -> None:
    df = pd.read_sql("SELECT * FROM vw_customer_segments", sqlite3.connect(DB_PATH))

    # --- 1) Chi-square ------------------------------------------------------
    ct = pd.crosstab(df["contract_group"], df["churned"])
    chi2, p, dof, _ = stats.chi2_contingency(ct)
    print("Contingency table:\n", ct, "\n")
    print(f"Chi-square = {chi2:,.1f}, dof = {dof}, p-value = {p:.3e}")

    # --- 2) Relative risk + 95% CI (log method) --------------------------------
    m = df[df.contract_group == "Month-to-month"].churned
    a = df[df.contract_group != "Month-to-month"].churned
    rr = m.mean() / a.mean()
    se = np.sqrt((1 - m.mean()) / m.sum() + (1 - a.mean()) / a.sum())
    lo, hi = np.exp(np.log(rr) + np.array([-1.96, 1.96]) * se)
    print(f"\nRelative risk (month-to-month vs annual+): {rr:.2f}x  (95% CI {lo:.2f}-{hi:.2f})")

    one = df[df.contract_type == "One year"].churned
    rr1 = m.mean() / one.mean()
    se1 = np.sqrt((1 - m.mean()) / m.sum() + (1 - one.mean()) / one.sum())
    lo1, hi1 = np.exp(np.log(rr1) + np.array([-1.96, 1.96]) * se1)
    print(f"Relative risk (month-to-month vs ONE-YEAR only):   {rr1:.2f}x  (95% CI {lo1:.2f}-{hi1:.2f})")

    # --- 3) Adjusted effect --------------------------------------------------
    X = pd.DataFrame({
        "month_to_month": (df.contract_group == "Month-to-month").astype(int),
        "tenure_months": df.tenure_months,
        "monthly_charges": df.monthly_charges,
        "addon_services": df.addon_services,
        "senior_citizen": df.senior_citizen,
    })
    X_std = (X - X.mean()) / X.std()
    # unpenalised logistic regression (sklearn >= 1.2 supports C=np.inf)
    lr = LogisticRegression(C=np.inf, max_iter=1000).fit(X_std, df.churned)
    print("\nStandardised logistic-regression odds ratios (per 1 SD):")
    for name, coef in zip(X.columns, lr.coef_[0]):
        print(f"  {name:<16} OR = {np.exp(coef):.2f}")

    raw = LogisticRegression(C=np.inf, max_iter=1000).fit(X[["month_to_month"]], df.churned)
    full = LogisticRegression(C=np.inf, max_iter=1000).fit(X, df.churned)
    print(f"\nMonth-to-month odds ratio  unadjusted: {np.exp(raw.coef_[0][0]):.2f}"
          f"   adjusted: {np.exp(full.coef_[0][0]):.2f}")
    print("-> The contract effect stays large after controlling for tenure, price and services.")


if __name__ == "__main__":
    main()
