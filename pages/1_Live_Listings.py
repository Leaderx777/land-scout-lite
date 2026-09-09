import os

import pandas as pd
import streamlit as st

from land_scout.core.land_scoring import score_land_candidates
from land_scout.core.rentcast_avm import RentCastAvmRequest, fetch_rentcast_value_estimate
from land_scout.core.rentcast_source import RentCastError, RentCastSearch, fetch_rentcast_sale_listings
from land_scout.core.residential_listings import ingest_property_listings

PROPERTY_MODES = {
    "Residential": ("Single Family", "Condo", "Townhouse", "Manufactured", "Multi-Family"),
    "Commercial": ("Apartment",),
    "Land": ("Land",),
}
MODE_HELP = {
    "Residential": "Houses, condos, townhomes, manufactured homes, and 2-4 unit multi-family properties.",
    "Commercial": "RentCast commercial coverage is limited to 5+ unit apartment properties.",
    "Land": "Vacant land. Search results get a preliminary rank; valuation evidence upgrades the score to a value-aware deal score.",
}


def _add_mode_metrics(frame: pd.DataFrame, mode: str) -> pd.DataFrame:
    enriched = frame.copy()
    if enriched.empty:
        return enriched
    if "square_feet" in enriched.columns:
        sqft = pd.to_numeric(enriched["square_feet"], errors="coerce")
        enriched["price_per_sqft"] = (pd.to_numeric(enriched["asking_price"], errors="coerce") / sqft.where(sqft > 0)).round(2)
    if mode == "Land" and "lot_size" in enriched.columns:
        lot = pd.to_numeric(enriched["lot_size"], errors="coerce")
        enriched["acres"] = (lot.where(lot > 0) / 43560.0).round(3)
        enriched["price_per_acre"] = (pd.to_numeric(enriched["asking_price"], errors="coerce") / enriched["acres"].where(enriched["acres"] > 0)).round(0)
        enriched = score_land_candidates(enriched)
    return enriched


def _address(row: pd.Series) -> str:
    return str(row.get("address", "") or "").strip()


st.set_page_config(page_title="Property Scout", layout="wide")
st.title("Property Scout")
st.caption("Search live for-sale listings and screen Residential, Commercial Multifamily, and Land separately.")
property_mode = st.radio("Property category", list(PROPERTY_MODES), horizontal=True)
st.caption(MODE_HELP[property_mode])

for key, default in {
    "live_intake_listings": pd.DataFrame(), "live_rejected_listings": pd.DataFrame(),
    "live_source_count": 0, "live_result_mode": "", "live_search_completed": False,
    "land_valuations": {},
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

saved_key = os.getenv("RENTCAST_API_KEY", "")
api_key = st.text_input("RentCast API key", value=saved_key, type="password", help="Set RENTCAST_API_KEY in Streamlit secrets or your environment to avoid retyping the key.")

c1, c2, c3 = st.columns(3)
with c1:
    city_choice = st.selectbox("Search area", ["Galesburg", "Canton", "Brimfield", "Kickapoo", "Peoria", "Custom city", "ZIP code"])
with c2:
    state = st.text_input("State", value="IL", max_chars=2)
with c3:
    max_price = st.number_input("Maximum asking price ($)", min_value=1000.0, value=50000.0, step=1000.0)
city, zip_code = "", ""
if city_choice == "Custom city": city = st.text_input("City")
elif city_choice == "ZIP code": zip_code = st.text_input("ZIP code", max_chars=5)
else: city = city_choice
c1, c2 = st.columns(2)
with c1: limit = st.number_input("Maximum listings to retrieve", min_value=1, max_value=500, value=100, step=25)
with c2: days_old = st.number_input("Listed within last N days (0 = any)", min_value=0, value=0, step=7)

if property_mode == "Land":
    st.info("Preliminary scores use listing facts only. Run valuation on the strongest candidates before treating any parcel as a deal. Zoning, access, utilities, flood risk, taxes, title, and buildability still require due diligence.")

if st.button(f"Search {property_mode.lower()} listings", type="primary"):
    st.session_state.live_search_completed = False
    try:
        selected_types = PROPERTY_MODES[property_mode]
        source_df = fetch_rentcast_sale_listings(api_key, RentCastSearch(city=city, state=state, zip_code=zip_code, max_price=max_price, limit=int(limit), days_old=int(days_old) if days_old else None, property_types=selected_types))
        intake = ingest_property_listings(source_df, max_purchase_price=max_price, allowed_property_types=selected_types)
        st.session_state.live_source_count = len(source_df)
        st.session_state.live_intake_listings = intake.listings
        st.session_state.live_rejected_listings = intake.rejected
        st.session_state.live_result_mode = property_mode
        st.session_state.live_search_completed = True
        if property_mode == "Land": st.session_state.land_valuations = {}
    except ValueError as exc: st.warning(str(exc))
    except RentCastError as exc: st.error(str(exc))
    except Exception as exc: st.error(f"Unable to search live listings: {exc}")

if st.session_state.live_result_mode and st.session_state.live_result_mode != property_mode:
    st.info(f"Select Search to load {property_mode.lower()} results for this area.")
    intake_listings, rejected_listings = pd.DataFrame(), pd.DataFrame()
else:
    base = st.session_state.live_intake_listings.copy()
    if property_mode == "Land" and not base.empty and st.session_state.land_valuations:
        for col in ("estimated_value", "value_range_low", "value_range_high", "value_comp_count"):
            base[col] = pd.NA
        for idx, row in base.iterrows():
            data = st.session_state.land_valuations.get(_address(row))
            if data:
                for col, value in data.items(): base.at[idx, col] = value
    intake_listings = _add_mode_metrics(base, property_mode)
    rejected_listings = st.session_state.live_rejected_listings

if st.session_state.live_search_completed and st.session_state.live_result_mode == property_mode:
    a, b, c = st.columns(3)
    a.metric("Live listings returned", st.session_state.live_source_count); b.metric("In buy box", len(intake_listings)); c.metric("Filtered / invalid", len(rejected_listings))
    if st.session_state.live_source_count == 0: st.warning(f"No active {property_mode.lower()} listings matched this search. Try a higher maximum price or another nearby city/ZIP.")
    elif intake_listings.empty: st.warning("Listings were returned, but none passed the current type/price screen.")

if not intake_listings.empty:
    if property_mode == "Residential":
        st.subheader("Residential candidates"); display_columns = ["address","city","asking_price","bedrooms","bathrooms","square_feet","price_per_sqft","year_built","property_type","days_on_market"]; download_name = "live_residential_candidates.csv"
    elif property_mode == "Commercial":
        st.subheader("Commercial multi-family candidates"); display_columns = ["address","city","asking_price","square_feet","price_per_sqft","lot_size","year_built","days_on_market"]; download_name = "live_commercial_candidates.csv"
    else:
        valued = pd.to_numeric(intake_listings.get("estimated_value"), errors="coerce").notna().sum() if "estimated_value" in intake_listings else 0
        st.subheader("Land candidates — strongest screen first")
        st.caption(f"{valued} of {len(intake_listings)} candidates have valuation evidence. 'Best Deal' is reserved for valued candidates.")
        display_columns = ["deal_rating","land_deal_score","address","asking_price","estimated_value","discount_to_value_pct","estimated_equity","acres","price_per_acre","days_on_market"]
        download_name = "live_land_candidates.csv"
    available = [c for c in display_columns if c in intake_listings.columns]
    st.dataframe(intake_listings[available], width="stretch", hide_index=True)
    st.download_button("Download candidates CSV", intake_listings.to_csv(index=False).encode(), file_name=download_name, mime="text/csv")

    st.divider()
    st.header("Land value + comparable review" if property_mode == "Land" else ("ARV + comparable review" if property_mode == "Residential" else "Commercial value + comparable review"))
    labels, indexes = [], []
    for idx, row in intake_listings.iterrows():
        asking = row.get("asking_price"); label = f"{_address(row)} — ${float(asking):,.0f}" if pd.notna(asking) else _address(row)
        labels.append(label); indexes.append(idx)
    selected_label = st.selectbox("Candidate property", labels)
    selected = intake_listings.loc[indexes[labels.index(selected_label)]]
    a, b, c = st.columns(3)
    with a: comp_radius = st.number_input("Maximum comp radius (miles)", min_value=0.1, value=5.0, step=0.5)
    with b: comp_days = st.number_input("Comparable lookback (days)", min_value=1, value=270, step=30)
    with c: comp_count = st.number_input("Comparable count", min_value=5, max_value=25, value=15, step=1)

    if st.button("Get value estimate + comps"):
        try:
            avm = fetch_rentcast_value_estimate(api_key, RentCastAvmRequest(address=_address(selected), property_type=str(selected.get("property_type", "") or "").strip(), bedrooms=float(selected["bedrooms"]) if pd.notna(selected.get("bedrooms")) else None, bathrooms=float(selected["bathrooms"]) if pd.notna(selected.get("bathrooms")) else None, square_feet=float(selected["square_feet"]) if pd.notna(selected.get("square_feet")) else None, max_radius=float(comp_radius), days_old=int(comp_days), comp_count=int(comp_count)))
            if property_mode == "Land":
                st.session_state.land_valuations[_address(selected)] = {"estimated_value": avm.estimated_value, "value_range_low": avm.range_low, "value_range_high": avm.range_high, "value_comp_count": avm.comp_count}
                asking = float(selected.get("asking_price") or 0)
                discount = ((avm.estimated_value - asking) / avm.estimated_value * 100) if avm.estimated_value else 0
                st.success(f"Valuation saved for reranking: estimated value ${avm.estimated_value:,.0f}, asking ${asking:,.0f}, estimated discount {discount:.1f}%. The table will rerank on the next Streamlit rerun.")
            a, b, c, d = st.columns(4)
            a.metric("RentCast value estimate", f"${avm.estimated_value:,.0f}"); b.metric("Range low", f"${avm.range_low:,.0f}"); c.metric("Range high", f"${avm.range_high:,.0f}"); d.metric("Scout confidence", avm.confidence_label)
            st.caption(f"{avm.comp_count} comparable listing(s); estimate-range width: {avm.range_width_percent:.1f}%.")
            if not avm.comparables.empty:
                cols = [x for x in ["address","price","status","property_type","lot_size","distance_miles","days_old","correlation","days_on_market"] if x in avm.comparables.columns]
                st.dataframe(avm.comparables[cols], width="stretch", hide_index=True)
        except ValueError as exc: st.warning(str(exc))
        except RentCastError as exc: st.error(str(exc))
        except Exception as exc: st.error(f"Unable to retrieve value estimate/comps: {exc}")

if not rejected_listings.empty:
    with st.expander("Show filtered / invalid listings"): st.dataframe(rejected_listings, width="stretch", hide_index=True)
st.divider()
st.caption("Data source: RentCast sale-listing and value-estimate APIs. API credentials are supplied locally and are not stored in this repository.")
