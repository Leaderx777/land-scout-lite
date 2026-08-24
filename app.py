import pandas as pd
import streamlit as st

from land_scout.core.market import CENTRAL_ILLINOIS_COUNTIES, MARKET_CENTER
from land_scout.core.screen import screen_deals
from land_scout.core.value_predictor import estimate_land_value

st.set_page_config(page_title="Land Scout Lite", layout="wide")
st.title("Land Scout Lite — Central Illinois")
st.caption(f"Land investment screening centered on {MARKET_CENTER}")

api_url = st.text_input("Land Value API URL", value="http://127.0.0.1:8000")
st.write("Initial target counties:", ", ".join(CENTRAL_ILLINOIS_COUNTIES))

st.header("Batch deal screening")
uploaded = st.file_uploader("Upload Central Illinois deals CSV", type=["csv"])

if uploaded is not None:
    df = pd.read_csv(uploaded)
    st.subheader("Uploaded listings")
    st.dataframe(df, use_container_width=True)

    if st.button("Score and rank listings", type="primary"):
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

st.header("Single-property estimate")
col1, col2 = st.columns(2)

with col1:
    county = st.selectbox("County", CENTRAL_ILLINOIS_COUNTIES)
    acres = st.number_input("Acres", min_value=0.1, value=5.0, step=0.5)
    distance = st.number_input("Distance to city (miles)", min_value=0.0, value=12.0, step=1.0)
    frontage = st.number_input("Road frontage (ft)", min_value=0.0, value=250.0, step=25.0)

with col2:
    asking_price = st.number_input("Asking price ($)", min_value=0.0, value=50000.0, step=1000.0)
    zoning = st.slider("Zoning score", min_value=1, max_value=5, value=3)
    utilities = st.selectbox("Utilities available", [0, 1], format_func=lambda x: "Yes" if x else "No")

if st.button("Estimate and analyze"):
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
