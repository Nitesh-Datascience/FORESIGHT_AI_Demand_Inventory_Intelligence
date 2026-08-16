# FORESIGHT — Data Quality & EDA Insight Memo

## Executive summary
FORESIGHT converts the supplied relational retail data into a weekly SKU demand panel, forecasts the next 8 weeks, and turns forecast + inventory position into transparent actions.

## Data used
- `sales_transactions.csv`
- `sku_master.csv`
- `store_master.csv`
- `inventory_snapshot.csv`
- `promotions.csv`
- `sku_inventory_flags.csv` for validation only

The uploaded sales extract contains 1,048,575 rows, while its accompanying README describes a nominal 10-million-transaction dataset. The pipeline reports the actual row count rather than assuming the nominal size.

## Cleaning decisions
1. Parsed transaction dates with day-first handling.
2. Removed exact duplicate transaction rows.
3. Coerced quantity/price/value/discount fields to numeric and prevented negative quantities.
4. Created `promo_flag` from `promo_id` presence.
5. Recalculated transaction value only when the supplied value was missing.
6. Aggregated to SKU-week.
7. Built a complete SKU-week panel and treated absent observed transactions as zero sales. This is a modelling convention, not proof that demand was zero during a stockout.

## Business insights
1. The anomaly ground truth contains 200 `STOCKOUT_RISK` SKUs and 400 `SLOW_MOVER` SKUs.
2. The transparent risk rules recover all 200 stockout-risk SKUs as `Reorder now` or `Watch / volatile`, and all 400 slow movers as `Markdown / clear` on the supplied ground truth.
3. The global forecasting model materially improves on the seasonal-naive benchmark in the rolling backtest. See `artifacts/backtest_results.csv`.

## Important limitation
The supplied inventory snapshot does not contain lead-time or on-order fields required by the original Zidio brief. FORESIGHT therefore uses an explicit 2-week lead-time planning proxy. This assumption is surfaced in the app and impact summary and should be replaced with a real lead time when available.
