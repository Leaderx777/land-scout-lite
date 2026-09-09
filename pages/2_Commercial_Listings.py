import pandas as pd
import streamlit as st

from land_scout.core.rentcast_source import RentCastError, RentCastSearch, fetch_rentcast_sale_listings
from land_scout.core.trellistate_source import (
    TrellistateError,
    TrellistateSearch,
    fetch_trellistate_commercial_listings,
)


st.set_page_config(page_title="Commercial Listings", layout="wide")
st.title("Commercial Listings")
st.caption(
    "Search commercial opportunities using two sources: RentCast for apartment/multifamily inventory and "
    "Trellistate for public commercial, office, retail, industrial, mixed-use, and investment listings."
)

if "commercial_results" not in st.session_state:
    st.session_state.commercial_results = pd.DataFrame()
if "commercial_errors" not in st.session_state:
    st.session_state.commercial_errors = []

api_key = st.text_input(
    "RentCast API key",
    type="password",
    help="Only RentCast needs a key. Trellistate public reads do not require one.",
)

col1, col2, col3 = st.columns(3)
with col1:
    area = st.selectbox("Search area", ["Galesburg", "Canton", "Brimfield", "Kickapoo", "Custom city", "ZIP code"])
with col2:
    state = st.text_input("State", value="IL", max_chars=2)
with col3:
    max_price = st.number_input("Maximum asking price ($)", min_value=1000.0, value=500000.0, step=10000.0)

city = ""
zip_code = ""
if area == "Custom city":
    city = st.text_input("City")
elif area == "ZIP code":
    zip_code = st.text_input("ZIP code", max_chars=5)
else:
    city = area

limit = st.number_input("Maximum listings per source", min_value=1, max_value=100, value=100, step=10)

if st.button("Search commercial listings", type="primary"):
    frames = []
    errors = []

    try:
        trelli = fetch_trellistate_commercial_listings(
            TrellistateSearch(
                city=city,
                state=state,
                postal_code=zip_code,
                max_price=max_price,
                limit=int(limit),
            )
        )
        if not trelli.empty:
            frames.append(trelli)
    except (ValueError, TrellistateError) as exc:
        errors.append(str(exc))

    if api_key.strip():
        try:
            rentcast = fetch_rentcast_sale_listings(
                api_key,
                RentCastSearch(
                    city=city,
                    state=state,
                    zip_code=zip_code,
                    max_price=max_price,
                    limit=int(limit),
                    property_types=("Apartment",),
                ),
            )
            if not rentcast.empty:
                frames.append(rentcast)
        except (ValueError, RentCastError) as exc:
            errors.append(str(exc))

    if frames:
        combined = pd.concat(frames, ignore_index=True, sort=False)
        if "asking_price" in combined.columns:
            combined["asking_price"] = pd.to_numeric(combined["asking_price"], errors="coerce")
            combined = combined.loc[
                combined["asking_price"].isna() | (combined["asking_price"] <= float(max_price))
            ]
        dedupe_cols = [column for column in ("address", "asking_price") if column in combined.columns]
        if dedupe_cols:
            combined = combined.drop_duplicates(subset=dedupe_cols, keep="first")
        if "asking_price" in combined.columns:
            combined = combined.sort_values("asking_price", na_position="last")
        st.session_state.commercial_results = combined.reset_index(drop=True)
    else:
        st.session_state.commercial_results = pd.DataFrame()

    st.session_state.commercial_errors = errors

results = st.session_state.commercial_results
errors = st.session_state.commercial_errors

if errors:
    with st.expander("Source messages"):
        for error in errors:
            st.write(error)

if results.empty:
    st.info(
        "No commercial listings were returned for this search. That can mean the public sources currently have no inventory "
        "for the selected city/price range. Try a larger nearby city or a higher price ceiling."
    )
else:
    st.success(f"Found {len(results)} commercial candidate(s).")

    if "square_feet" in results.columns:
        sqft = pd.to_numeric(results["square_feet"], errors="coerce")
        price = pd.to_numeric(results.get("asking_price"), errors="coerce")
        results = results.copy()
        results["price_per_sqft"] = (price / sqft.where(sqft > 0)).round(2)

    columns = [
        "source",
        "title",
        "address",
        "city",
        "asking_price",
        "property_type",
        "square_feet",
        "price_per_sqft",
        "lot_size",
        "year_built",
        "listing_url",
    ]
    available = [column for column in columns if column in results.columns]
    st.dataframe(results[available], width="stretch", hide_index=True)

    st.download_button(
        "Download commercial candidates CSV",
        results.to_csv(index=False).encode("utf-8"),
        file_name="commercial_candidates.csv",
        mime="text/csv",
    )

st.divider()
st.caption(
    "Trellistate is an open public listing exchange rather than an MLS, so verify every listing independently. "
    "RentCast commercial coverage is limited to Apartment properties."
)
