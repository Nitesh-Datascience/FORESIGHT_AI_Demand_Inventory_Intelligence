from pathlib import Path
import sys, json
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from src.pipeline import clean_and_build_weekly
from src.forecast import rolling_backtest, train_final, recursive_forecast
from src.risk import score_risk, evaluate_against_flags

def main():
    panel, inventory, sku, flags, quality = clean_and_build_weekly()
    backtest = rolling_backtest(panel)
    backtest.to_csv(ROOT/"artifacts"/"backtest_results.csv", index=False)

    model = train_final(panel)
    forecast = recursive_forecast(panel, sku, horizon=8)
    forecast.to_csv(ROOT/"artifacts"/"forecast_latest.csv", index=False)

    risk = score_risk(forecast, inventory, sku, lead_time_weeks=2, overstock_multiplier=1.5)
    risk.to_csv(ROOT/"artifacts"/"risk_latest.csv", index=False)

    flag_eval = evaluate_against_flags(risk, flags)
    flag_eval.to_csv(ROOT/"artifacts"/"risk_ground_truth_evaluation.csv", index=False)

    impact = {
        "sales_at_risk_rupees": float(risk["sales_at_risk"].sum()),
        "locked_capital_rupees": float(risk["locked_capital"].sum()),
        "reorder_now_skus": int((risk.action=="Reorder now").sum()),
        "markdown_clear_skus": int((risk.action=="Markdown / clear").sum()),
        "watch_volatile_skus": int((risk.action=="Watch / volatile").sum()),
        "healthy_skus": int((risk.action=="Healthy").sum()),
        "forecast_horizon_weeks": 8,
        "lead_time_proxy_weeks": 2
    }
    (ROOT/"artifacts"/"impact_summary.json").write_text(json.dumps(impact, indent=2))

    print("FORESIGHT pipeline completed.")
    print(json.dumps(quality, indent=2))
    print("\nBacktest:")
    print(backtest.to_string(index=False))
    print("\nImpact:")
    print(json.dumps(impact, indent=2))
    if not flag_eval.empty:
        print("\nGround-truth evaluation:")
        print(flag_eval.to_string(index=False))

if __name__ == "__main__":
    main()
