# FORESIGHT — AI-Powered Demand & Inventory Intelligence Platform

A complete end-to-end implementation aligned to the Zidio Project FORESIGHT brief: reproducible data pipeline, leakage-safe demand forecasting, rolling-origin backtesting, transparent inventory risk scoring, Streamlit planning dashboard, FastAPI scoring service, and executive reporting.

## Scope alignment
The original brief requires:
1. Data pipeline
2. Data-quality & EDA memo
3. Weekly SKU demand forecast + seasonal-naive baseline
4. Stockout/overstock risk scoring + recommended action
5. Planning dashboard
6. Deployed scoring service
7. Executive readout

This repository implements all seven locally.

## Data
The supplied relational dataset is used:
- sales_transactions.csv
- sku_master.csv
- store_master.csv
- inventory_snapshot.csv
- promotions.csv
- sku_inventory_flags.csv (validation ground truth)

The separate `retail_store_inventory(1).csv` file is not used because it is a different schema and is not part of the relational FORESIGHT implementation.

## Quick start

### 1. Create environment
```bash
python -m venv .venv
# Windows
.venv\Scriptsctivate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### 2. Run the full pipeline
```bash
python run_pipeline.py
```

This creates:
- `data/processed/weekly_panel.pkl`
- `artifacts/backtest_results.csv`
- `artifacts/forecast_latest.csv`
- `artifacts/risk_latest.csv`
- `artifacts/risk_ground_truth_evaluation.csv`
- `artifacts/impact_summary.json`
- `artifacts/forecast_model.joblib`

### 3. Launch dashboard
```bash
streamlit run app/streamlit_app.py
```

### 4. Launch scoring service
```bash
uvicorn service.api:app --reload --port 8000
```

Useful endpoints:
- `/health`
- `/risk/{sku_id}`
- `/forecast/{sku_id}`
- `/score`

## Modelling
- Weekly SKU grain
- Lags: 1, 2, 4, 13, 26, 52 weeks
- Rolling means/std: 4, 13, 52 weeks
- Calendar and promotion signals
- Global LightGBM regression model trained on log1p demand
- Seasonal-naive baseline = same week one year earlier
- Rolling-origin, 8-week holdout evaluation
- WAPE as primary metric

The project follows the brief's non-negotiable rule: do not hide a model that loses to the baseline.

## Risk logic
Because the supplied inventory snapshot lacks lead time and on-order units, the implementation uses a documented 2-week lead-time proxy.

Stockout:
`stock_on_hand < forecast_lead_time + safety_stock`

Overstock:
`stock_on_hand > 1.5 × forecast_8w`

Decision:
- High stockout + high overstock -> Watch / volatile
- Stockout -> Reorder now
- Overstock -> Markdown / clear
- Neither -> Healthy

## Reproducibility
The pipeline is coded end-to-end. No manual spreadsheet transformations are required.

## Important data note
The supplied sales file currently contains 1,048,575 rows. Its README describes a nominal 10-million-row synthetic dataset. This implementation reports and models the actual supplied file; it does not fabricate the missing transactions.

## Professional / submission note
The Zidio brief says the intern must understand and be able to explain every result and must not fabricate or hide poor backtests. Use the generated metrics from your own run in the final submission and demo.
