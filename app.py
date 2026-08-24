import pandas as pd
import streamlit as st

from land_scout.core.value_predictor import estimate_land_value

st.set_page_config(page_title="Land Scout Lite", layout="wide")
st.title("Land Scout Lite")
st.caption("Deal screening + optional Land Value Predictor integration")

uploaded = st.file_uploader("Upload deals CSV", type=["csv"])

if uploaded is not None:
    df = pd.read_csv(uploaded)
    st.subheader("Deals")
    st.dataframe(df, use_container_width=True)

st.subheader("Estimate land value")
col1, col2 = st.columns(2)

with col1:
    acres = st.number_input("Acres", min_value=0.1, value=5.0, step=0.5)
    distance = st.number_input("Distance to city (miles)", min_value=0.0, value=12.0, step=1.0)
    frontage = st.number_input("Road frontage (ft)", min_value=0.0, value=250.0, step=25.0)

with col2:
    zoning = st.slider("Zoning score", min_value=1, max_value=5, value=3)
    utilities = st.selectbox("Utilities available", [0, 1], format_func=lambda x: "Yes" if x else "No")
    api_url = st.text_input("Land Value API URL", value="http://127.0.0.1:8000")

if st.button("Estimate with Land Value Predictor", type="primary"):
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
        st.metric("Estimated value", f"${value:,.0f}")
        st.info(result.get("data_note", "Demo estimate"))
    except Exception as exc:
        st.error(f"Predictor API unavailable: {exc}")
        st.code("cd land-value-predictor\npython train.py\nuvicorn api:app --reload --port 8000")
