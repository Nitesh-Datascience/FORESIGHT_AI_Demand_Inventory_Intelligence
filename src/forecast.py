from pathlib import Path
import json
import joblib
import numpy as np
import pandas as pd
from lightgbm import LGBMRegressor

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT/"artifacts"
PROCESSED = ROOT/"data"/"processed"

FEATURES = [
    "lag_1","lag_2","lag_4","lag_13","lag_26","lag_52",
    "roll_mean_4","roll_std_4","roll_mean_13","roll_std_13",
    "roll_mean_52","roll_std_52","week_num","month","year","t",
    "unit_price","cost_price","promo_rate",
    "category_code","subcategory_code","brand_code","sku_id_code"
]

def wape(y, pred):
    return float(np.abs(np.asarray(y)-np.asarray(pred)).sum() / max(np.asarray(y).sum(), 1e-9))

def make_model(seed=42):
    return LGBMRegressor(
        n_estimators=180, learning_rate=0.06, num_leaves=31,
        subsample=0.8, colsample_bytree=0.8,
        random_state=seed, n_jobs=-1, verbosity=-1
    )

def rolling_backtest(panel, origins=None, horizon=8):
    if origins is None:
        max_week = panel["week"].max()
        origins = [max_week - pd.Timedelta(weeks=30),
                   max_week - pd.Timedelta(weeks=22),
                   max_week - pd.Timedelta(weeks=14)]
    rows = []
    for origin in origins:
        train = panel[panel.week < origin]
        test = panel[(panel.week >= origin) & (panel.week < origin + pd.Timedelta(weeks=horizon))]
        model = make_model()
        model.fit(train[FEATURES], np.log1p(train.units_sold))
        pred = np.expm1(model.predict(test[FEATURES])).clip(0)
        rows.append({
            "origin": str(origin.date()),
            "horizon_weeks": horizon,
            "rows_tested": len(test),
            "baseline_wape": wape(test.units_sold, test.lag_52),
            "model_wape": wape(test.units_sold, pred),
            "improvement_pct": 100*(wape(test.units_sold, test.lag_52)-wape(test.units_sold, pred))/wape(test.units_sold, test.lag_52)
        })
    return pd.DataFrame(rows)

def train_final(panel):
    ART.mkdir(parents=True, exist_ok=True)
    model = make_model()
    model.fit(panel[FEATURES], np.log1p(panel.units_sold))
    joblib.dump(model, ART/"forecast_model.joblib")
    # Save the category-code mapping used by the training panel.
    meta = {"features": FEATURES}
    for c in ["category","subcategory","brand","sku_id"]:
        meta[c] = panel[[c,f"{c}_code"]].drop_duplicates().set_index(c)[f"{c}_code"].to_dict()
    meta["last_week"] = str(panel.week.max().date())
    meta["first_week"] = str(panel.week.min().date())
    (ART/"feature_meta.json").write_text(json.dumps(meta))
    return model

def recursive_forecast(panel, sku_master, horizon=8):
    model = joblib.load(ART/"forecast_model.joblib")
    meta = json.loads((ART/"feature_meta.json").read_text())
    hist = panel[["sku_id","week","units_sold","category","subcategory","unit_price","cost_price","brand"]].copy()
    last_week = pd.Timestamp(meta["last_week"])
    skus = sku_master.copy().sort_values("sku_id")
    static = skus.set_index("sku_id")
    outputs = []

    for step in range(1, horizon+1):
        fw = last_week + pd.Timedelta(weeks=step)
        piv = hist.pivot(index="sku_id", columns="week", values="units_sold").reindex(skus.sku_id)
        X = pd.DataFrame(index=skus.sku_id)

        for lag in [1,2,4,13,26,52]:
            w = fw - pd.Timedelta(weeks=lag)
            X[f"lag_{lag}"] = piv[w] if w in piv.columns else 0

        cutoff = fw - pd.Timedelta(weeks=1)
        for w in [4,13,52]:
            vals_mean, vals_std = [], []
            for sku_id in skus.sku_id:
                arr = piv.loc[sku_id].loc[:cutoff].tail(w).dropna().values
                vals_mean.append(float(np.mean(arr)) if len(arr) else 0.0)
                vals_std.append(float(np.std(arr)) if len(arr) > 1 else 0.0)
            X[f"roll_mean_{w}"] = vals_mean
            X[f"roll_std_{w}"] = vals_std

        X["week_num"] = int(fw.isocalendar().week)
        X["month"] = fw.month
        X["year"] = fw.year
        X["t"] = int((fw - pd.Timestamp(meta["first_week"])).days // 7)
        X["unit_price"] = static.loc[skus.sku_id, "unit_price"].values
        X["cost_price"] = static.loc[skus.sku_id, "cost_price"].values
        X["promo_rate"] = 0.0

        for c in ["category","subcategory","brand","sku_id"]:
            mapping = meta[c]
            if c == "sku_id":
                source_values = skus["sku_id"]
            else:
                source_values = static.loc[skus.sku_id, c]
            X[f"{c}_code"] = source_values.map(mapping).fillna(-1).values

        pred = np.expm1(model.predict(X[FEATURES])).clip(0)
        out = pd.DataFrame({"sku_id": skus.sku_id, "week": fw, "forecast_units": pred})
        outputs.append(out)

        hist = pd.concat([
            hist,
            pd.DataFrame({
                "sku_id": skus.sku_id, "week": fw, "units_sold": pred,
                "category": static.loc[skus.sku_id,"category"].values,
                "subcategory": static.loc[skus.sku_id,"subcategory"].values,
                "unit_price": static.loc[skus.sku_id,"unit_price"].values,
                "cost_price": static.loc[skus.sku_id,"cost_price"].values,
                "brand": static.loc[skus.sku_id,"brand"].values
            })
        ], ignore_index=True)
    return pd.concat(outputs, ignore_index=True)
