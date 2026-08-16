from pathlib import Path
import json
import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT/"artifacts"

st.set_page_config(page_title="FORESIGHT", page_icon="📦", layout="wide")
st.title("📦 FORESIGHT — Demand & Inventory Intelligence")
st.caption("AI-assisted weekly demand forecasting, stockout early warning and overstock decisioning")

risk = pd.read_csv(ART/"risk_latest.csv")
forecast = pd.read_csv(ART/"forecast_latest.csv", parse_dates=["week"])
backtest = pd.read_csv(ART/"backtest_results.csv")
impact = json.loads((ART/"impact_summary.json").read_text())

# Filters
categories = ["All"] + sorted(risk["category"].dropna().unique().tolist())
cat = st.sidebar.selectbox("Category", categories)
filtered = risk if cat=="All" else risk[risk.category==cat]

c1,c2,c3,c4 = st.columns(4)
c1.metric("Sales at risk", f"₹{impact['sales_at_risk_rupees']:,.0f}")
c2.metric("Capital locked", f"₹{impact['locked_capital_rupees']:,.0f}")
c3.metric("Reorder now", f"{impact['reorder_now_skus']:,}")
c4.metric("Markdown / clear", f"{impact['markdown_clear_skus']:,}")

st.subheader("Decision queue")
st.dataframe(
    filtered[["sku_id","sku_name","category","stock_on_hand","forecast_lead_time",
              "forecast_8w","risk_level","action","reorder_qty","sales_at_risk","locked_capital"]]
    .sort_values(["risk_level","sales_at_risk","locked_capital"], ascending=[True,False,False])
    .head(200),
    use_container_width=True, hide_index=True
)

st.subheader("Stockout vs overstock decisioning grid")
grid = filtered.copy()
fig = px.scatter(
    grid, x="forecast_lead_time", y="stock_on_hand", size="sales_at_risk",
    color="action", hover_name="sku_id",
    hover_data=["sku_name","category","forecast_8w","coverage_weeks"],
    labels={"forecast_lead_time":"Forecast demand over lead-time proxy",
            "stock_on_hand":"Current stock on hand"}
)
st.plotly_chart(fig, use_container_width=True)

st.subheader("Forecast explorer")
sku = st.selectbox("SKU", filtered["sku_id"].sort_values().tolist())
hist = pd.read_pickle(ROOT/"data/processed/weekly_panel.pkl")
h = hist[hist.sku_id==sku][["week","units_sold"]].tail(40).rename(columns={"units_sold":"actual"})
f = forecast[forecast.sku_id==sku][["week","forecast_units"]].rename(columns={"forecast_units":"forecast"})
chart = pd.concat([h.set_index("week"), f.set_index("week")], axis=1).reset_index()
fig2 = px.line(chart, x="week", y=["actual","forecast"], markers=True,
               labels={"value":"Units","week":"Week","variable":"Series"})
st.plotly_chart(fig2, use_container_width=True)

selected = filtered[filtered.sku_id==sku].iloc[0]
st.info(
    f"**{selected.sku_name}** — action: **{selected.action}** | "
    f"risk: **{selected.risk_level}** | reorder qty: **{int(selected.reorder_qty):,}**"
)

st.subheader("Model validation")
st.dataframe(backtest, use_container_width=True, hide_index=True)
st.caption("WAPE = total absolute forecast error / total actual demand. The seasonal-naive baseline uses the same week one year earlier.")
