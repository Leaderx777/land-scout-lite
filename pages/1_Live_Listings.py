import os

import streamlit as st

from land_scout.core.rentcast_source import (
    RentCastError,
    RentCastSearch,
    fetch_rentcast_sale_listings,
)
from land_scout.core.residential_listings import ingest_residential_listings


st.set_page_config(page_title="Live Listings", layout="wide")
st.title("Live Residential Listings")
st.caption(
    "Search active for-sale listings from RentCast, then pass the results through Property Scout's broad residential buy box."
)

saved_key = os.getenv("RENTCAST_API_KEY", "")
api_key = st.text_input(
    "RentCast API key",
    value=saved_key,
    type="password",
    help="Set RENTCAST_API_KEY in your environment to avoid retyping the key.",
)

search_col1, search_col2, search_col3 = st.columns(3)
with search_col1:
    city_choice = st.selectbox(
        "Search area",
        ["Galesburg", "Canton", "Brimfield", "Kickapoo", "Custom city", "ZIP code"],
    )
with search_col2:
    state = st.text_input("State", value="IL", max_chars=2)
with search_col3:
    max_price = st.number_input(
        "Maximum asking price ($)",
        min_value=1000.0,
        value=50000.0,
        step=1000.0,
    )

city = ""
zip_code = ""
if city_choice == "Custom city":
    city = st.text_input("City")
elif city_choice == "ZIP code":
    zip_code = st.text_input("ZIP code", max_chars=5)
else:
    city = city_choice

option_col1, option_col2 = st.columns(2)
with option_col1:
    limit = st.number_input("Maximum listings to retrieve", min_value=1, max_value=500, value=100, step=25)
with option_col2:
    days_old = st.number_input(
        "Listed within last N days (0 = any)",
        min_value=0,
        value=0,
        step=7,
    )

if st.button("Search live listings", type="primary"):
    try:
        source_df = fetch_rentcast_sale_listings(
            api_key,
            RentCastSearch(
                city=city,
                state=state,
                zip_code=zip_code,
                max_price=max_price,
                limit=int(limit),
                days_old=int(days_old) if days_old else None,
            ),
        )
        intake = ingest_residential_listings(source_df, max_purchase_price=max_price)

        metric_a, metric_b, metric_c = st.columns(3)
        metric_a.metric("Live listings returned", len(source_df))
        metric_b.metric("In buy box", len(intake.listings))
        metric_c.metric("Filtered / invalid", len(intake.rejected))

        if intake.listings.empty:
            st.warning("No active listings matched this search and the current price screen.")
        else:
            st.subheader("Live flip candidates")
            display_columns = [
                "address",
                "city",
                "asking_price",
                "bedrooms",
                "bathrooms",
                "square_feet",
                "year_built",
                "property_type",
                "screening_status",
            ]
            st.dataframe(
                intake.listings[display_columns],
                use_container_width=True,
                hide_index=True,
            )
            st.info(
                "Live listings start as NEEDS_ARV because the feed does not tell us the after-repair value or repair budget. "
                "That is intentional: Property Scout will not invent deal economics."
            )
            st.download_button(
                "Download live candidates CSV",
                intake.listings.to_csv(index=False).encode("utf-8"),
                file_name="live_residential_candidates.csv",
                mime="text/csv",
            )

        if not intake.rejected.empty:
            with st.expander("Show filtered / invalid listings"):
                st.dataframe(intake.rejected, use_container_width=True, hide_index=True)
    except ValueError as exc:
        st.warning(str(exc))
    except RentCastError as exc:
        st.error(str(exc))
    except Exception as exc:
        st.error(f"Unable to search live listings: {exc}")

st.divider()
st.caption(
    "Data source: RentCast sale listings API. API credentials are supplied locally and are not stored in this repository."
)
