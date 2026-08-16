# FORESIGHT — Executive Readout

## 1. Decision
Use FORESIGHT as a weekly planning aid for reorder and clearance triage.

## 2. What it does
- Forecasts SKU demand for 8 weeks.
- Compares performance with a seasonal-naive baseline.
- Scores stockout and overstock risk.
- Prioritises actions with rupee impact.
- Exposes results in Streamlit and a FastAPI scoring service.

## 3. Model result
The backtest uses rolling-origin evaluation and WAPE. The model is only considered trusted because it is evaluated against the seasonal-naive baseline on periods not used for training.

## 4. Inventory decision logic
- Reorder now: projected lead-time demand + safety stock exceeds current stock.
- Markdown / clear: stock materially exceeds the 8-week forecast.
- Watch / volatile: both stockout and overstock conditions are present.
- Healthy: neither condition is triggered.

## 5. Business impact
See `artifacts/impact_summary.json` after running the pipeline. The pipeline calculates sales-at-risk and locked capital from the supplied prices/costs rather than hard-coding business results.

## 6. Limitations
- The uploaded inventory extract has no lead-time/on-order fields; a 2-week proxy is used.
- The sales extract is smaller than the nominal size stated in its README.
- Stockout-suppressed transactions are inherently unobserved in POS data.
- This is a planning recommendation system, not an automated purchase-order system.

## 7. Recommended next step
Replace the lead-time proxy with supplier-specific lead times and add a historical inventory-snapshot table. Then monitor forecast WAPE and risk precision monthly.
