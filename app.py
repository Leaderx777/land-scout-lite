import pandas as pd
import streamlit as st

from land_scout.core.comps import ComparableSale, estimate_arv_from_comps
from land_scout.core.flip import analyze_flip
from land_scout.core.flip_storage import clear_saved_flips, load_saved_flips, save_saved_flips
from land_scout.core.market import CENTRAL_ILLINOIS_COUNTIES, MARKET_CENTER
from land_scout.core.property_details import PropertyDetails
from land_scout.core.residential_listings import (
    analyze_ready_residential_listings,
    ingest_residential_listings,
)
from land_scout.core.screen import screen_deals
from land_scout.core.value_predictor import estimate_land_value

st.set_page_config(page_title="Land Scout Lite", layout="wide")
st.title("Land Scout Lite — Central Illinois")
st.caption(f"Land and flip investment screening centered on {MARKET_CENTER}")

if "saved_flip_deals" not in st.session_state:
    st.session_state.saved_flip_deals = load_saved_flips()

st.header("Residential listing intake")
st.caption(
    "Upload residential listings from a CSV export or other permitted data source. "
    "The intake keeps all residential property types and bedroom counts, then filters by price."
)
listing_col1, listing_col2 = st.columns([1, 1])
with listing_col1:
    residential_upload = st.file_uploader(
        "Upload residential listings CSV",
        type=["csv"],
        key="residential_listing_upload",
    )
with listing_col2:
    residential_max_price = st.number_input(
        "Maximum purchase / asking price ($)",
        min_value=0.0,
        value=50000.0,
        step=1000.0,
        key="residential_max_price",
    )

if residential_upload is not None:
    try:
        source_listings = pd.read_csv(residential_upload)
        intake = ingest_residential_listings(
            source_listings,
            max_purchase_price=residential_max_price,
        )

        intake_a, intake_b, intake_c = st.columns(3)
        intake_a.metric("Uploaded", len(source_listings))
        intake_b.metric("In buy box", len(intake.listings))
        intake_c.metric("Filtered / invalid", len(intake.rejected))

        if intake.listings.empty:
            st.warning("No uploaded listings passed the current price/address screen.")
        else:
            st.subheader("Residential candidates")
            listing_display_columns = [
                "address",
                "city",
                "asking_price",
                "bedrooms",
                "bathrooms",
                "square_feet",
                "year_built",
                "property_type",
                "screening_status",
                "rehab_estimate",
                "arv_estimate",
                "listing_url",
            ]
            st.dataframe(
                intake.listings[listing_display_columns],
                use_container_width=True,
                hide_index=True,
            )

            st.download_button(
                "Download screened residential listings",
                intake.listings.to_csv(index=False).encode("utf-8"),
                file_name="screened_residential_listings.csv",
                mime="text/csv",
            )

            ranked_residential = analyze_ready_residential_listings(intake.listings)
            if ranked_residential.empty:
                st.info(
                    "These listings are in the price buy box, but none have both rehab and ARV estimates yet. "
                    "Add those estimates before treating any listing as a BUY/REVIEW/PASS candidate."
                )
            else:
                st.subheader("Ready listings ranked by flip economics")
                ranked_columns = [
                    "address",
                    "decision",
                    "asking_price",
                    "rehab_estimate",
                    "arv_estimate",
                    "projected_profit",
                    "roi_percent",
                    "max_offer",
                    "bedrooms",
                    "bathrooms",
                    "square_feet",
                    "property_type",
                    "listing_url",
                ]
                st.dataframe(
                    ranked_residential[ranked_columns],
                    use_container_width=True,
                    hide_index=True,
                )
                st.download_button(
                    "Download ranked residential opportunities",
                    ranked_residential.to_csv(index=False).encode("utf-8"),
                    file_name="ranked_residential_opportunities.csv",
                    mime="text/csv",
                )
    except Exception as exc:
        st.error(f"Unable to read residential listings: {exc}")

st.divider()
st.header("House flip analysis")
st.subheader("Property details")
property_col1, property_col2 = st.columns(2)

with property_col1:
    property_address = st.text_input("Property address")
    bedrooms = st.number_input("Bedrooms", min_value=0, value=3, step=1)
    bathrooms = st.number_input("Bathrooms", min_value=0.0, value=1.0, step=0.5)
    square_feet = st.number_input("Square feet", min_value=0, value=1200, step=50)

with property_col2:
    year_built = st.number_input("Year built", min_value=0, value=1950, step=1)
    listing_url = st.text_input("Listing URL")
    notes = st.text_area(
        "Property notes",
        placeholder="Condition, layout, neighborhood, known repairs, seller motivation, etc.",
    )

st.subheader("Comparable sales / ARV")
st.caption(
    "Enter sold comparable properties. The estimator uses the median sale price per square foot. "
    "Closer, similar properties are better comps."
)

comp_template = pd.DataFrame(
    [
        {"address": "", "sale_price": 0.0, "square_feet": 0, "bedrooms": 0, "bathrooms": 0.0, "distance_miles": 0.0},
        {"address": "", "sale_price": 0.0, "square_feet": 0, "bedrooms": 0, "bathrooms": 0.0, "distance_miles": 0.0},
        {"address": "", "sale_price": 0.0, "square_feet": 0, "bedrooms": 0, "bathrooms": 0.0, "distance_miles": 0.0},
    ]
)

edited_comps = st.data_editor(
    comp_template,
    num_rows="dynamic",
    use_container_width=True,
    hide_index=True,
    key="flip_comps_editor",
    column_config={
        "address": st.column_config.TextColumn("Comp address"),
        "sale_price": st.column_config.NumberColumn("Sold price ($)", min_value=0.0, step=1000.0, format="$%.0f"),
        "square_feet": st.column_config.NumberColumn("Sq ft", min_value=0, step=50),
        "bedrooms": st.column_config.NumberColumn("Beds", min_value=0, step=1),
        "bathrooms": st.column_config.NumberColumn("Baths", min_value=0.0, step=0.5),
        "distance_miles": st.column_config.NumberColumn("Miles away", min_value=0.0, step=0.1, format="%.1f"),
    },
)

comps = []
for _, row in edited_comps.iterrows():
    sale_price = float(row.get("sale_price", 0) or 0)
    comp_sqft = int(row.get("square_feet", 0) or 0)
    if sale_price > 0 and comp_sqft > 0:
        comps.append(
            ComparableSale(
                address=str(row.get("address", "") or "").strip(),
                sale_price=sale_price,
                square_feet=comp_sqft,
                bedrooms=int(row.get("bedrooms", 0) or 0),
                bathrooms=float(row.get("bathrooms", 0) or 0),
                distance_miles=float(row.get("distance_miles", 0) or 0),
            )
        )

comp_arv = None
if comps and square_feet > 0:
    try:
        comp_arv = estimate_arv_from_comps(int(square_feet), comps)
        comp_a, comp_b, comp_c, comp_d = st.columns(4)
        comp_a.metric("Comp-based ARV", f"${comp_arv.estimated_arv:,.0f}")
        comp_b.metric("Median $ / sq ft", f"${comp_arv.median_price_per_sqft:,.0f}")
        comp_c.metric("ARV range", f"${comp_arv.low_arv:,.0f}–${comp_arv.high_arv:,.0f}")
        comp_d.metric("Confidence", comp_arv.confidence)
        st.caption(
            f"Based on {comp_arv.comp_count} valid comp(s); price-per-square-foot spread: "
            f"{comp_arv.spread_percent:.1f}%."
        )
    except ValueError as exc:
        st.warning(str(exc))
else:
    st.info("Add at least one sold comp with a sale price and square footage to calculate a comp-based ARV.")

st.subheader("Deal numbers")
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
    manual_arv = st.number_input(
        "Manual ARV ($)", min_value=0.0, value=110000.0, step=1000.0
    )
    target_profit = st.number_input(
        "Target profit ($)", min_value=0.0, value=25000.0, step=1000.0
    )

arv_source_options = ["Manual ARV"]
if comp_arv is not None:
    arv_source_options.append("Comparable sales")
arv_source = st.radio("ARV used for analysis", arv_source_options, horizontal=True)
analysis_arv = comp_arv.estimated_arv if arv_source == "Comparable sales" and comp_arv else manual_arv
st.caption(f"ARV currently used in flip math: ${analysis_arv:,.0f}")


def current_property_details() -> PropertyDetails:
    return PropertyDetails(
        address=property_address.strip(),
        bedrooms=int(bedrooms),
        bathrooms=float(bathrooms),
        square_feet=int(square_feet),
        year_built=int(year_built),
        listing_url=listing_url.strip(),
        notes=notes.strip(),
    )


def current_flip_analysis():
    return analyze_flip(
        purchase_price=purchase_price,
        rehab_cost=rehab_cost,
        holding_cost=holding_cost,
        selling_cost=selling_cost,
        arv=analysis_arv,
        target_profit=target_profit,
    )


def render_flip_result(property_details: PropertyDetails, flip) -> None:
    st.subheader(property_details.address or "Unnamed property")
    detail_a, detail_b, detail_c, detail_d = st.columns(4)
    detail_a.metric("Beds", property_details.bedrooms)
    detail_b.metric("Baths", f"{property_details.bathrooms:g}")
    detail_c.metric("Sq ft", f"{property_details.square_feet:,}")
    detail_d.metric("Year built", property_details.year_built or "Unknown")

    if property_details.listing_url:
        st.write("Listing:", property_details.listing_url)
    if property_details.notes:
        st.info(property_details.notes)

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


button_col1, button_col2 = st.columns([1, 1])
analyze_clicked = button_col1.button("Analyze flip", type="primary")
save_clicked = button_col2.button("Save property")

if analyze_clicked:
    render_flip_result(current_property_details(), current_flip_analysis())

if save_clicked:
    property_details = current_property_details()
    flip = current_flip_analysis()

    st.session_state.saved_flip_deals.append(
        {
            "address": property_details.address or "Unnamed property",
            "bedrooms": property_details.bedrooms,
            "bathrooms": property_details.bathrooms,
            "square_feet": property_details.square_feet,
            "year_built": property_details.year_built,
            "listing_url": property_details.listing_url,
            "notes": property_details.notes,
            "purchase_price": flip.purchase_price,
            "rehab_cost": flip.rehab_cost,
            "holding_cost": flip.holding_cost,
            "selling_cost": flip.selling_cost,
            "arv": flip.arv,
            "arv_source": arv_source,
            "comp_count": comp_arv.comp_count if comp_arv else 0,
            "arv_confidence": comp_arv.confidence if comp_arv else "MANUAL",
            "total_cost": flip.total_cost,
            "projected_profit": flip.projected_profit,
            "roi_percent": flip.roi_percent,
            "max_offer": flip.max_offer,
            "decision": flip.decision,
        }
    )
    save_saved_flips(st.session_state.saved_flip_deals)
    st.success(f"Saved: {property_details.address or 'Unnamed property'}")
    render_flip_result(property_details, flip)

st.caption(
    "Current buy-box rules: purchase ≤ $50,000, rehab ≤ $20,000, "
    "and projected profit ≥ target profit."
)

if st.session_state.saved_flip_deals:
    st.subheader("Saved flip opportunities")
    saved_df = pd.DataFrame(st.session_state.saved_flip_deals)
    decision_rank = {"BUY": 0, "REVIEW": 1, "PASS": 2}
    saved_df["decision_rank"] = saved_df["decision"].map(decision_rank).fillna(3)
    ranked_flips = saved_df.sort_values(
        by=["decision_rank", "projected_profit", "roi_percent"],
        ascending=[True, False, False],
    ).drop(columns=["decision_rank"])

    display_columns = [
        "address",
        "decision",
        "purchase_price",
        "rehab_cost",
        "arv",
        "projected_profit",
        "roi_percent",
        "max_offer",
        "bedrooms",
        "bathrooms",
        "square_feet",
    ]
    optional_columns = ["arv_source", "comp_count", "arv_confidence"]
    display_columns.extend(column for column in optional_columns if column in ranked_flips.columns)
    st.dataframe(ranked_flips[display_columns], use_container_width=True)

    export_col1, export_col2 = st.columns([1, 1])
    export_col1.download_button(
        "Download saved flips CSV",
        ranked_flips.to_csv(index=False).encode("utf-8"),
        file_name="ranked_flip_opportunities.csv",
        mime="text/csv",
    )
    if export_col2.button("Clear saved flips"):
        st.session_state.saved_flip_deals = []
        clear_saved_flips()
        st.rerun()

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
    asking_price = st.number_input(
        "Land asking price ($)", min_value=0.0, value=50000.0, step=1000.0
    )
    zoning = st.slider("Zoning score", min_value=1, max_value=5, value=3)
    utilities = st.selectbox(
        "Utilities available", [0, 1], format_func=lambda x: "Yes" if x else "No"
    )

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
