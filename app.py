import pandas as pd
import streamlit as st

from land_scout.core.flip import analyze_flip
from land_scout.core.market import CENTRAL_ILLINOIS_COUNTIES, MARKET_CENTER
from land_scout.core.screen import screen_deals
from land_scout.core.value_predictor import estimate_land_value

st.set_page_config(page_title="Land Scout Lite", layout="wide")
st.title("Land Scout Lite — Central Illinois")
st.caption(f"Land and flip investment screening centered on {MARKET_CENTER}")

st.header("House flip analysis")
flip_col1, flip_col2 = st.columns(2)

with flip_col1:
    purchase_price = st.number_input(
        "Purchase / asking price ($)", min_value=0.0, value=40000.0, step=1000.0
    )
    rehab_cost = st.number_input(
        "Estimated rehab ($)", min_value=0.0, value=15000.0, step=1000.0
    )
    holding_cost = st.number_input(
        "Holding costs ($)", min_value=0.0, value=4000.0, step=500.0
    )

with flip_col2:
    selling_cost = st.number_input(
        "Selling / closing costs ($)", min_value=0.0, value=9000.0, step=500.0
    )
    arv = st.number_input(
        "After-repair value (ARV) ($)", min_value=0.0, value=110000.0, step=1000.0
    )
    target_profit = st.number_input(
        "Target profit ($)", min_value=0.0, value=25000.0, step=1000.0
    )

if st.button("Analyze flip", type="primary"):
    flip = analyze_flip(
        purchase_price=purchase_price,
        rehab_cost=rehab_cost,
        holding_cost=holding_cost,
        selling_cost=selling_cost,
        arv=arv,
        target_profit=target_profit,
    )

    a, b, c, d = st.columns(4)
    a.metric("Total project cost", f"${flip.total_cost:,.0f}")
    b.metric("Projected profit", f"${flip.projected_profit:,.0f}")
    c.metric("ROI", f"{flip.roi_percent:.1f}%")
    d.metric("Maximum offer", f"${flip.max_offer:,.0f}")

    if flip.decision == "BUY":
        st.success("Decision: BUY")
    elif flip.decision == "REVIEW":
        st.warning("Decision: REVIEW")
    else:
        st.error("Decision: PASS")

    st.caption(
        "Current buy-box rules: purchase ≤ $50,000, rehab ≤ $20,000, "
        "and projected profit ≥ target profit."
    )

st.divider()

api_url = st.text_input("Land Value API URL", value="http://127.0.0.1:8000")
st.write("Initial target counties:", ", ".join(CENTRAL_ILLINOIS_COUNTIES))

st.header("Batch land deal screening")
uploaded = st.file_uploader("Upload Central Illinois deals CSV", type=["csv"])

if uploaded is not None:
    df = pd.read_csv(uploaded)
    st.subheader("Uploaded listings")
    st.dataframe(df, use_container_width=True)

    if st.button("Score and rank listings"):
        try:
            ranked = screen_deals(df, api_url=api_url)
            if ranked.empty:
                st.warning("No listings matched the current Central Illinois target counties.")
            else:
                st.subheader("Ranked opportunities")
                st.dataframe(ranked, use_container_width=True)
                st.download_button(
                    "Download ranked CSV",
                    ranked.to_csv(index=False).encode("utf-8"),
                    file_name="central_illinois_ranked_land.csv",
                    mime="text/csv",
                )
        except Exception as exc:
            st.error(f"Unable to score listings: {exc}")

st.header("Single-property land estimate")
col1, col2 = st.columns(2)

with col1:
    county = st.selectbox("County", CENTRAL_ILLINOIS_COUNTIES)
    acres = st.number_input("Acres", min_value=0.1, value=5.0, step=0.5)
    distance = st.number_input("Distance to city (miles)", min_value=0.0, value=12.0, step=1.0)
    frontage = st.number_input("Road frontage (ft)", min_value=0.0, value=250.0, step=25.0)

with col2:
    asking_price = st.number_input("Land asking price ($)", min_value=0.0, value=50000.0, step=1000.0)
    zoning = st.slider("Zoning score", min_value=1, max_value=5, value=3)
    utilities = st.selectbox("Utilities available", [0, 1], format_func=lambda x: "Yes" if x else "No")

if st.button("Estimate and analyze land"):
    try:
        result = estimate_land_value(
            acres=acres,
            distance_to_city_miles=distance,
            road_frontage_ft=frontage,
            zoning_score=zoning,
            utilities=utilities,
            api_url=api_url,
        )
        value = float(result["estimated_value"])
        spread = value - asking_price
        discount = (spread / value * 100) if value else 0.0
        a, b, c = st.columns(3)
        a.metric("Estimated value", f"${value:,.0f}")
        b.metric("Value spread", f"${spread:,.0f}")
        c.metric("Discount to estimate", f"{discount:.1f}%")
        st.caption(f"Market: {county} County, Central Illinois")
        st.info(result.get("data_note", "Demo estimate"))
    except Exception as exc:
        st.error(f"Predictor API unavailable: {exc}")
        st.code("cd land-value-predictor\npython train.py\nuvicorn api:app --reload --port 8000")
