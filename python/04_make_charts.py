"""Static charts + a Power BI-style dashboard preview image."""
import sqlite3
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from config import DB_PATH, IMAGES_DIR

IMAGES_DIR.mkdir(exist_ok=True)
RED, BLUE, GREY, DARK = "#E4572E", "#2E86AB", "#B8C0C8", "#1F2D3D"
plt.rcParams.update({"font.family": "DejaVu Sans", "axes.spines.top": False,
                     "axes.spines.right": False, "axes.edgecolor": GREY,
                     "axes.labelcolor": DARK, "xtick.color": DARK, "ytick.color": DARK})


def rate(df, col):
    g = df.groupby(col).churned.agg(["mean", "count", "sum"]).reset_index()
    g["pct"] = g["mean"] * 100
    return g


def bar(ax, g, col, title, highlight=None, rot=0):
    labels = [f"{l}\n(n={n:,})" for l, n in zip(g[col].str.replace(r"^\d\. ", "", regex=True), g["count"])]
    colors = [RED if (highlight and highlight in str(l)) else BLUE for l in g[col]]
    bars = ax.bar(labels, g.pct, color=colors, width=0.62)
    for b, p, n in zip(bars, g.pct, g["count"]):
        ax.text(b.get_x() + b.get_width() / 2, p + 1, f"{p:.1f}%", ha="center",
                fontweight="bold", color=DARK, fontsize=10)
    ax.set_title(title, loc="left", fontweight="bold", color=DARK, fontsize=12)
    ax.set_ylabel("Churn rate (%)")
    ax.set_ylim(0, g.pct.max() * 1.18)
    plt.setp(ax.get_xticklabels(), rotation=rot, ha="right" if rot else "center", fontsize=9)


def main() -> None:
    df = pd.read_sql("SELECT * FROM vw_customer_segments", sqlite3.connect(DB_PATH))
    overall = df.churned.mean() * 100
    mtm = df[df.contract_group == "Month-to-month"]
    ann = df[df.contract_group != "Month-to-month"]
    mtm_r, ann_r = mtm.churned.mean() * 100, ann.churned.mean() * 100
    one_r = df[df.contract_type == "One year"].churned.mean() * 100

    contract = rate(df, "contract_type").sort_values("pct", ascending=False)
    tenure = rate(df, "tenure_band").sort_values("tenure_band")
    usage = rate(df, "service_usage_band").sort_values("service_usage_band")

    # ---------- individual charts ------------------------------------------
    for name, g, col, title, hi, rot in [
        ("churn_by_contract", contract, "contract_type", "Churn rate by contract type", "Month", 0),
        ("churn_by_tenure", tenure, "tenure_band", "Churn rate by tenure band", "0-12", 0),
        ("churn_by_service_usage", usage, "service_usage_band", "Churn rate by service usage", "Internet only", 20),
    ]:
        fig, ax = plt.subplots(figsize=(7, 4.4))
        bar(ax, g, col, title, hi, rot)
        ax.axhline(overall, ls="--", color=GREY, lw=1)
        ax.text(len(g) - 0.5, overall + 0.8, f"overall {overall:.1f}%", ha="right", color="#6b7785", fontsize=8)
        fig.tight_layout(); fig.savefig(IMAGES_DIR / f"{name}.png", dpi=160); plt.close(fig)

    # heatmap contract x tenure
    piv = (df.pivot_table(index="contract_type", columns="tenure_band", values="churned", aggfunc="mean") * 100)
    piv = piv.loc[["Month-to-month", "One year", "Two year"]]
    fig, ax = plt.subplots(figsize=(7.5, 3.6))
    im = ax.imshow(piv.values, cmap="Reds", vmin=0, vmax=60, aspect="auto")
    ax.set_xticks(range(piv.shape[1]), [c[3:] for c in piv.columns])
    ax.set_yticks(range(piv.shape[0]), piv.index)
    for i in range(piv.shape[0]):
        for j in range(piv.shape[1]):
            v = piv.values[i, j]
            ax.text(j, i, f"{v:.1f}%", ha="center", va="center",
                    color="white" if v > 30 else DARK, fontweight="bold")
    ax.set_title("Churn rate: contract type x tenure", loc="left", fontweight="bold", color=DARK)
    for s in ax.spines.values(): s.set_visible(False)
    fig.tight_layout(); fig.savefig(IMAGES_DIR / "heatmap_contract_tenure.png", dpi=160); plt.close(fig)

    # ---------- dashboard preview -------------------------------------------
    fig = plt.figure(figsize=(16, 9), facecolor="#F4F6F8")
    gs = GridSpec(3, 4, figure=fig, height_ratios=[0.5, 1.5, 1.5], hspace=0.55, wspace=0.35,
                  left=0.04, right=0.97, top=0.88, bottom=0.07)
    fig.text(0.04, 0.94, "Telco Customer Churn - Retention Risk Dashboard", fontsize=20,
             fontweight="bold", color=DARK)
    fig.text(0.04, 0.905, "Preview of the Power BI report (matplotlib render of the same SQL outputs)",
             fontsize=10, color="#6b7785")

    kpis = [("Customers", f"{len(df):,}", DARK),
            ("Overall churn", f"{overall:.1f}%", DARK),
            ("Month-to-month churn", f"{mtm_r:.1f}%", RED),
            ("Risk vs one-year / annual+", f"{mtm_r/one_r:.1f}x  /  {mtm_r/ann_r:.1f}x", RED)]
    for i, (lab, val, c) in enumerate(kpis):
        ax = fig.add_subplot(gs[0, i]); ax.axis("off")
        ax.add_patch(plt.Rectangle((0, 0), 1, 1, transform=ax.transAxes, color="white", ec=GREY))
        ax.text(0.05, 0.68, lab, transform=ax.transAxes, fontsize=10, color="#6b7785")
        ax.text(0.05, 0.2, val, transform=ax.transAxes, fontsize=21, fontweight="bold", color=c)

    ax1 = fig.add_subplot(gs[1, 0:2]); bar(ax1, contract, "contract_type", "Churn % by contract type", "Month")
    ax2 = fig.add_subplot(gs[1, 2:4]); bar(ax2, tenure, "tenure_band", "Churn % by tenure band", "0-12")
    ax3 = fig.add_subplot(gs[2, 0:2]); bar(ax3, usage, "service_usage_band", "Churn % by service usage", "Internet only", rot=15)
    ax4 = fig.add_subplot(gs[2, 2:4])
    im = ax4.imshow(piv.values, cmap="Reds", vmin=0, vmax=60, aspect="auto")
    ax4.set_xticks(range(piv.shape[1]), [c[3:] for c in piv.columns], fontsize=9)
    ax4.set_yticks(range(piv.shape[0]), piv.index, fontsize=9)
    for i in range(piv.shape[0]):
        for j in range(piv.shape[1]):
            v = piv.values[i, j]
            ax4.text(j, i, f"{v:.1f}%", ha="center", va="center", color="white" if v > 30 else DARK, fontweight="bold")
    ax4.set_title("Contract x tenure heatmap", loc="left", fontweight="bold", color=DARK, fontsize=12)
    for s in ax4.spines.values(): s.set_visible(False)
    fig.savefig(IMAGES_DIR / "dashboard_preview.png", dpi=130, facecolor=fig.get_facecolor()); plt.close(fig)
    print("Saved charts to", IMAGES_DIR)


if __name__ == "__main__":
    main()
