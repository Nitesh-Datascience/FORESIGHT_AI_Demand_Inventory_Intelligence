from pathlib import Path
import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT/"artifacts"
app = FastAPI(title="FORESIGHT Scoring Service", version="1.0.0")

risk = pd.read_csv(ART/"risk_latest.csv")
forecast = pd.read_csv(ART/"forecast_latest.csv", parse_dates=["week"])

class SKURequest(BaseModel):
    sku_id: str = Field(..., min_length=3)

@app.get("/health")
def health():
    return {"status":"ok","service":"foresight","skus":int(risk.sku_id.nunique())}

@app.get("/risk/{sku_id}")
def get_risk(sku_id: str):
    row = risk[risk.sku_id.eq(sku_id)]
    if row.empty:
        raise HTTPException(status_code=404, detail="Unknown SKU")
    return row.iloc[0].to_dict()

@app.get("/forecast/{sku_id}")
def get_forecast(sku_id: str):
    rows = forecast[forecast.sku_id.eq(sku_id)].copy()
    if rows.empty:
        raise HTTPException(status_code=404, detail="Unknown SKU")
    rows["week"] = rows["week"].dt.strftime("%Y-%m-%d")
    return {"sku_id":sku_id,"horizon_weeks":len(rows),"forecast":rows.to_dict("records")}

@app.post("/score")
def score(req: SKURequest):
    return {"sku_id": req.sku_id, "risk": get_risk(req.sku_id), "forecast": get_forecast(req.sku_id)}
