from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT/"artifacts"

def score_risk(forecast, inventory, sku_master, lead_time_weeks=2, overstock_multiplier=1.5):
    f2 = forecast[forecast.week <= forecast.week.min() + pd.Timedelta(weeks=lead_time_weeks-1)]
    f2 = f2.groupby("sku_id", as_index=False)["forecast_units"].sum().rename(columns={"forecast_units":"forecast_lead_time"})
    f8 = forecast.groupby("sku_id", as_index=False)["forecast_units"].sum().rename(columns={"forecast_units":"forecast_8w"})

    inv = inventory.groupby("sku_id", as_index=False).agg(
        stock_on_hand=("stock_on_hand","sum"),
        reorder_point=("reorder_point","sum"),
        safety_stock=("safety_stock","sum")
    )

    r = sku_master[["sku_id","sku_name","category","unit_price","cost_price"]].merge(inv,on="sku_id",how="left")
    r = r.merge(f2,on="sku_id",how="left").merge(f8,on="sku_id",how="left").fillna(0)

    r["stockout_gap"] = r["stock_on_hand"] - (r["forecast_lead_time"] + r["safety_stock"])
    r["overstock_units"] = r["stock_on_hand"] - overstock_multiplier*r["forecast_8w"]
    r["coverage_weeks"] = np.where(r["forecast_8w"]>0, r["stock_on_hand"]/r["forecast_8w"], np.inf)

    stockout = r["stockout_gap"] < 0
    overstock = (r["overstock_units"] > 0) & (r["coverage_weeks"] > overstock_multiplier)

    r["action"] = np.select(
        [stockout & overstock, stockout, overstock],
        ["Watch / volatile","Reorder now","Markdown / clear"],
        default="Healthy"
    )
    r["risk_level"] = np.select(
        [r["action"].eq("Watch / volatile"), r["action"].ne("Healthy")],
        ["High","Medium"], default="Low"
    )
    r["sales_at_risk"] = np.maximum(0, -r["stockout_gap"]) * r["unit_price"]
    r["locked_capital"] = np.maximum(0, r["overstock_units"]) * r["cost_price"]
    r["reorder_qty"] = np.maximum(0, r["forecast_lead_time"] + r["safety_stock"] - r["stock_on_hand"]).round().astype(int)

    return r.sort_values(["risk_level","sales_at_risk","locked_capital"], ascending=[True,False,False])

def evaluate_against_flags(risk, flags):
    if flags is None or len(flags)==0:
        return pd.DataFrame()
    truth = flags.groupby("sku_id")["flag"].agg(lambda x:"|".join(sorted(set(x)))).reset_index()
    x = risk.merge(truth,on="sku_id",how="left")
    x["flag"] = x["flag"].fillna("NONE")
    rows=[]
    for truth_label, action in [("STOCKOUT_RISK","Reorder now"),("SLOW_MOVER","Markdown / clear")]:
        subset = x[x.flag.eq(truth_label)]
        rows.append({
            "ground_truth": truth_label,
            "n_flagged_skus": int(len(subset)),
            "detected_action_or_watch": int((subset.action.isin([action,"Watch / volatile"])).sum()),
            "recall": float((subset.action.isin([action,"Watch / volatile"])).mean()) if len(subset) else 0
        })
    return pd.DataFrame(rows)
