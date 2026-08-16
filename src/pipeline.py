from pathlib import Path
import pandas as pd
import numpy as np
import json

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"

def load_raw():
    sales = pd.read_csv(RAW/"sales_transactions.csv", parse_dates=["date"], dayfirst=True)
    sku = pd.read_csv(RAW/"sku_master.csv")
    store = pd.read_csv(RAW/"store_master.csv")
    inv = pd.read_csv(RAW/"inventory_snapshot.csv")
    promos = pd.read_csv(RAW/"promotions.csv", parse_dates=["start_date","end_date"])
    flags_path = RAW/"sku_inventory_flags.csv"
    flags = pd.read_csv(flags_path) if flags_path.exists() else None
    return sales, sku, store, inv, promos, flags

def clean_and_build_weekly():
    sales, sku, store, inv, promos, flags = load_raw()

    # Type and integrity fixes.
    sales["date"] = pd.to_datetime(sales["date"], errors="coerce", dayfirst=True)
    sales["quantity"] = pd.to_numeric(sales["quantity"], errors="coerce").fillna(0).clip(lower=0)
    sales["unit_price"] = pd.to_numeric(sales["unit_price"], errors="coerce")
    sales["total_value"] = pd.to_numeric(sales["total_value"], errors="coerce")
    sales["discount_pct"] = pd.to_numeric(sales["discount_pct"], errors="coerce").fillna(0)
    sales["promo_flag"] = sales["promo_id"].notna().astype(int)
    sales = sales.dropna(subset=["date","sku_id","store_id"]).drop_duplicates()

    # Recalculate value only when the supplied value is missing.
    calc_value = sales["quantity"] * sales["unit_price"] * (1 - sales["discount_pct"]/100)
    sales["total_value"] = sales["total_value"].fillna(calc_value)

    # Weekly SKU grain for FORESIGHT.
    sales["week"] = sales["date"].dt.to_period("W-SUN").dt.start_time
    weekly = sales.groupby(["sku_id","week"], as_index=False).agg(
        units_sold=("quantity","sum"),
        revenue=("total_value","sum"),
        avg_price=("unit_price","mean"),
        promo_rate=("promo_flag","mean"),
    )

    # Full SKU-week panel: absent transactions are treated as zero observed sales.
    # This is documented because stockout-suppressed transactions are not observable in POS data.
    weeks = pd.date_range(weekly["week"].min(), weekly["week"].max(), freq="W-MON")
    panel = pd.MultiIndex.from_product(
        [sku["sku_id"].sort_values(), weeks], names=["sku_id","week"]
    ).to_frame(index=False)
    panel = panel.merge(weekly, on=["sku_id","week"], how="left")
    panel["units_sold"] = panel["units_sold"].fillna(0)
    panel["revenue"] = panel["revenue"].fillna(0)
    panel["promo_rate"] = panel["promo_rate"].fillna(0)
    panel["avg_price"] = panel.groupby("sku_id")["avg_price"].transform(lambda s: s.ffill().bfill())
    panel = panel.merge(
        sku[["sku_id","category","subcategory","unit_price","cost_price","brand"]],
        on="sku_id", how="left"
    )

    # Calendar features.
    panel["week_num"] = panel["week"].dt.isocalendar().week.astype(int)
    panel["month"] = panel["week"].dt.month
    panel["year"] = panel["week"].dt.year
    panel["t"] = ((panel["week"] - panel["week"].min()).dt.days // 7).astype(int)

    # Leakage-safe lag and rolling features.
    g = panel.groupby("sku_id")["units_sold"]
    for lag in [1,2,4,13,26,52]:
        panel[f"lag_{lag}"] = g.shift(lag)
    for w in [4,13,52]:
        shifted = g.shift(1)
        panel[f"roll_mean_{w}"] = shifted.rolling(w).mean().reset_index(level=0, drop=True)
        panel[f"roll_std_{w}"] = shifted.rolling(w).std().reset_index(level=0, drop=True)

    panel = panel.dropna(subset=["lag_52"]).copy()

    # Stable category codes for the global model.
    for c in ["category","subcategory","brand","sku_id"]:
        panel[f"{c}_code"] = panel[c].astype("category").cat.codes

    PROCESSED.mkdir(parents=True, exist_ok=True)
    panel.to_pickle(PROCESSED/"weekly_panel.pkl")
    inv.to_pickle(PROCESSED/"inventory_snapshot.pkl")
    sku.to_pickle(PROCESSED/"sku_master.pkl")
    store.to_pickle(PROCESSED/"store_master.pkl")
    if flags is not None:
        flags.to_pickle(PROCESSED/"sku_inventory_flags.pkl")

    quality = {
        "sales_rows_after_cleaning": int(len(sales)),
        "sales_min_date": str(sales["date"].min().date()),
        "sales_max_date": str(sales["date"].max().date()),
        "unique_skus": int(sales["sku_id"].nunique()),
        "unique_stores": int(sales["store_id"].nunique()),
        "duplicate_rows_removed": int(len(pd.read_csv(RAW/"sales_transactions.csv")) - len(sales)),
        "missing_promo_id_rows": int(sales["promo_id"].isna().sum()),
        "weekly_panel_rows": int(len(panel)),
        "inventory_rows": int(len(inv)),
        "flag_rows": int(len(flags)) if flags is not None else 0,
    }
    pd.DataFrame([quality]).to_json(PROCESSED/"quality_summary.json", orient="records", indent=2)
    return panel, inv, sku, flags, quality

if __name__ == "__main__":
    panel, inv, sku, flags, quality = clean_and_build_weekly()
    print(json.dumps(quality, indent=2))
