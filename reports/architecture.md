# FORESIGHT Architecture

```text
Raw CSVs
   |
   v
src/pipeline.py
   |  clean + relational joins + SKU-week panel + leakage-safe features
   v
weekly_panel.parquet
   |
   +----------------------+
   |                      |
   v                      v
src/forecast.py       src/risk.py
   |                      |
   | rolling CV            | forecast + inventory
   v                      v
backtest_results.csv   risk_latest.csv
   |                      |
   +----------+-----------+
              |
       +------+------+
       |             |
       v             v
 Streamlit       FastAPI
 dashboard       scoring service
```

The original Zidio brief explicitly separates raw ingestion, modelling, risk scoring, dashboard, and service layers. This project follows that separation.
