import os

import pandas as pd
import streamlit as st

from land_scout.core.rentcast_avm import RentCastAvmRequest, fetch_rentcast_value_estimate
from land_scout.core.rentcast_source import (
    RentCastError,
    RentCastSearch,
    fetch_rentcast_sale_listings,
)
from land_scout.core.residential_listings import ingest_property_listings


PROPERTY_MODES = {
    "Residential": (
        "Single Family",
        "Condo",
        "Townhouse",
        "Manufactured",
        "Multi-Family",
    ),
    "Commercial": ("Apartment",),
    "Land": ("Land",),
}

MODE_HELP = {
    "Residential": "Houses, condos, townhomes, manufactured homes, and 2-4 unit multi-family properties.",
    "Commercial": (
        "Current RentCast coverage is commercial multi-family only: apartment buildings and complexes with 5+ units. "
        "Office, retail, industrial, agricultural, and other non-residential commercial properties will require another data source."
    ),
    "Land": "Vacant land and undeveloped parcels. RentCast coverage is strongest for smaller residential and urban lots.",
}


def _add_mode_metrics(frame: pd.DataFrame, mode: str) -> pd.DataFrame:
    enriched = frame.copy()
    if enriched.empty:
        return enriched

    if "square_feet" in enriched.columns:
        valid_sqft = enriched["square_feet"].notna() & (enriched["square_feet"] > 0)
        enriched["price_per_sqft"] = pd.NA
        enriched.loc[valid_sqft, "price_per_sqft"] = (
            enriched.loc[valid_sqft, "asking_price"] / enriched.loc[valid_sqft, "square_feet"]
        ).round(2)

    if mode == "Land" and "lot_size" in enriched.columns:
        valid_lot = enriched["lot_size"].notna() & (enriched["lot_size"] > 0)
        enriched["acres"] = pd.NA
        enriched["price_per_acre"] = pd.NA
        enriched.loc[valid_lot, "acres"] = (enriched.loc[valid_lot, "lot_size"] / 43560.0).round(3)
        valid_acres = enriched["acres"].notna() & (enriched["acres"] > 0)
        enriched.loc[valid_acres, "price_per_acre"] = (
            enriched.loc[valid_acres, "asking_price"] / enriched.loc[valid_acres, "acres"]
        ).round(0)

    return enriched


st.set_page_config(page_title="Property Scout", layout="wide")
st.title("Property Scout")
st.caption("Search live for-sale listings, separate them by investment type, and review market-value comps.")

property_mode = st.radio(
    "Property category",
    list(PROPERTY_MODES),
    horizontal=True,
)
st.caption(MODE_HELP[property_mode])

if "live_intake_listings" not in st.session_state:
    st.session_state.live_intake_listings = pd.DataFrame()
if "live_rejected_listings" not in st.session_state:
    st.session_state.live_rejected_listings = pd.DataFrame()
if "live_source_count" not in st.session_state:
    st.session_state.live_source_count = 0
if "live_result_mode" not in st.session_state:
    st.session_state.live_result_mode = ""

saved_key = os.getenv("RENTCAST_API_KEY", "")
api_key = st.text_input(
    "RentCast API key",
    value=saved_key,
    type="password",
    help="Set RENTCAST_API_KEY in Streamlit secrets or your environment to avoid retyping the key.",
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

if st.button(f"Search {property_mode.lower()} listings", type="primary"):
    try:
        selected_types = PROPERTY_MODES[property_mode]
        source_df = fetch_rentcast_sale_listings(
            api_key,
            RentCastSearch(
                city=city,
                state=state,
                zip_code=zip_code,
                max_price=max_price,
                limit=int(limit),
                days_old=int(days_old) if days_old else None,
                property_types=selected_types,
            ),
        )
        intake = ingest_property_listings(
            source_df,
            max_purchase_price=max_price,
            allowed_property_types=selected_types,
        )
        st.session_state.live_source_count = len(source_df)
        st.session_state.live_intake_listings = intake.listings
        st.session_state.live_rejected_listings = intake.rejected
        st.session_state.live_result_mode = property_mode
    except ValueError as exc:
        st.warning(str(exc))
    except RentCastError as exc:
        st.error(str(exc))
    except Exception as exc:
        st.error(f"Unable to search live listings: {exc}")

if st.session_state.live_result_mode and st.session_state.live_result_mode != property_mode:
    st.info(f"Select Search to load {property_mode.lower()} results for this area.")
    intake_listings = pd.DataFrame()
    rejected_listings = pd.DataFrame()
else:
    intake_listings = _add_mode_metrics(st.session_state.live_intake_listings, property_mode)
    rejected_listings = st.session_state.live_rejected_listings

if st.session_state.live_result_mode == property_mode and (
    st.session_state.live_source_count or not intake_listings.empty
):
    metric_a, metric_b, metric_c = st.columns(3)
    metric_a.metric("Live listings returned", st.session_state.live_source_count)
    metric_b.metric("In buy box", len(intake_listings))
    metric_c.metric("Filtered / invalid", len(rejected_listings))

if not intake_listings.empty:
    if property_mode == "Residential":
        st.subheader("Residential candidates")
        display_columns = [
            "address",
            "city",
            "asking_price",
            "bedrooms",
            "bathrooms",
            "square_feet",
            "price_per_sqft",
            "year_built",
            "property_type",
            "days_on_market",
        ]
        download_name = "live_residential_candidates.csv"
    elif property_mode == "Commercial":
        st.subheader("Commercial multi-family candidates")
        display_columns = [
            "address",
            "city",
            "asking_price",
            "bedrooms",
            "bathrooms",
            "square_feet",
            "price_per_sqft",
            "lot_size",
            "year_built",
            "property_type",
            "days_on_market",
        ]
        download_name = "live_commercial_candidates.csv"
    else:
        st.subheader("Land candidates")
        display_columns = [
            "address",
            "city",
            "asking_price",
            "lot_size",
            "acres",
            "price_per_acre",
            "property_type",
            "days_on_market",
        ]
        download_name = "live_land_candidates.csv"

    available_display_columns = [column for column in display_columns if column in intake_listings.columns]
    st.dataframe(
        intake_listings[available_display_columns],
        width="stretch",
        hide_index=True,
    )

    st.download_button(
        "Download candidates CSV",
        intake_listings.to_csv(index=False).encode("utf-8"),
        file_name=download_name,
        mime="text/csv",
    )

    st.divider()
    if property_mode == "Residential":
        st.header("ARV + comparable review")
        st.caption(
            "Use RentCast's current value estimate and comparable sale listings as an ARV aid. "
            "Condition and repair scope still need to be verified before making an offer."
        )
    elif property_mode == "Commercial":
        st.header("Commercial value + comparable review")
        st.caption(
            "For Apartment properties, RentCast's value estimate represents the entire building. "
            "Income, expenses, occupancy, cap rate, and unit-level due diligence still need separate review."
        )
    else:
        st.header("Land value + comparable review")
        st.caption(
            "Use the value estimate and nearby land comps as an initial screen. Zoning, access, utilities, flood risk, "
            "survey/title issues, and buildability must be checked separately."
        )

    candidate_labels = []
    candidate_indexes = []
    for idx, row in intake_listings.iterrows():
        address = str(row.get("address", "") or "").strip()
        city_name = str(row.get("city", "") or "").strip()
        asking = row.get("asking_price")
        label = f"{address}, {city_name} — ${float(asking):,.0f}" if pd.notna(asking) else f"{address}, {city_name}"
        candidate_labels.append(label)
        candidate_indexes.append(idx)

    selected_label = st.selectbox("Candidate property", candidate_labels)
    selected_position = candidate_labels.index(selected_label)
    selected = intake_listings.loc[candidate_indexes[selected_position]]

    avm_col1, avm_col2, avm_col3 = st.columns(3)
    with avm_col1:
        comp_radius = st.number_input("Maximum comp radius (miles)", min_value=0.1, value=5.0, step=0.5)
    with avm_col2:
        comp_days = st.number_input("Comparable lookback (days)", min_value=1, value=270, step=30)
    with avm_col3:
        comp_count = st.number_input("Comparable count", min_value=5, max_value=25, value=15, step=1)

    if st.button("Get value estimate + comps"):
        try:
            avm = fetch_rentcast_value_estimate(
                api_key,
                RentCastAvmRequest(
                    address=str(selected.get("address", "") or "").strip(),
                    property_type=str(selected.get("property_type", "") or "").strip(),
                    bedrooms=float(selected["bedrooms"]) if pd.notna(selected.get("bedrooms")) else None,
                    bathrooms=float(selected["bathrooms"]) if pd.notna(selected.get("bathrooms")) else None,
                    square_feet=float(selected["square_feet"]) if pd.notna(selected.get("square_feet")) else None,
                    max_radius=float(comp_radius),
                    days_old=int(comp_days),
                    comp_count=int(comp_count),
                ),
            )

            arv_a, arv_b, arv_c, arv_d = st.columns(4)
            value_label = "RentCast value / ARV estimate" if property_mode == "Residential" else "RentCast value estimate"
            arv_a.metric(value_label, f"${avm.estimated_value:,.0f}")
            arv_b.metric("Range low", f"${avm.range_low:,.0f}")
            arv_c.metric("Range high", f"${avm.range_high:,.0f}")
            arv_d.metric("Scout confidence", avm.confidence_label)
            st.caption(
                f"{avm.comp_count} comparable listing(s); estimate-range width: {avm.range_width_percent:.1f}%. "
                "Scout confidence is an app-side label based on comp count and range width."
            )

            if not avm.comparables.empty:
                st.subheader("Comparable sale listings")
                comp_columns = [
                    "address",
                    "price",
                    "status",
                    "property_type",
                    "bedrooms",
                    "bathrooms",
                    "square_feet",
                    "lot_size",
                    "year_built",
                    "distance_miles",
                    "days_old",
                    "correlation",
                    "days_on_market",
                ]
                available_columns = [column for column in comp_columns if column in avm.comparables.columns]
                st.dataframe(
                    avm.comparables[available_columns],
                    width="stretch",
                    hide_index=True,
                )
                st.download_button(
                    "Download comps CSV",
                    avm.comparables.to_csv(index=False).encode("utf-8"),
                    file_name="rentcast_comparables.csv",
                    mime="text/csv",
                )
            else:
                st.warning("RentCast returned a value estimate but no comparable listings.")
        except ValueError as exc:
            st.warning(str(exc))
        except RentCastError as exc:
            st.error(str(exc))
        except Exception as exc:
            st.error(f"Unable to retrieve value estimate/comps: {exc}")

if not rejected_listings.empty:
    with st.expander("Show filtered / invalid listings"):
        st.dataframe(rejected_listings, width="stretch", hide_index=True)

st.divider()
st.caption(
    "Data source: RentCast sale-listing and value-estimate APIs. API credentials are supplied locally and are not stored in this repository."
)
