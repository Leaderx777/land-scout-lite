import pandas as pd
import streamlit as st

from land_scout.core.land_comp_analysis import analyze_land_comps


st.set_page_config(page_title="Verified Land Comps", layout="wide")
st.title("Verified Land Sold Comps")
st.caption(
    "Use this page when you have actual closed-sale evidence from county records, MLS, or another verified source. "
    "Closed sales are stronger evidence than active or inactive listing asking prices."
)

st.info(
    "Enter only actual sale prices in the Sale price column. Do not enter an asking price there unless you have verified that it was the closed sale price."
)

c1, c2, c3 = st.columns(3)
with c1:
    subject_acres = st.number_input("Subject parcel acres", min_value=0.01, value=1.0, step=0.25)
with c2:
    asking_price = st.number_input("Subject asking price ($)", min_value=0.0, value=10000.0, step=1000.0)
with c3:
    subject_lot_size = subject_acres * 43560.0
    st.metric("Subject lot size", f"{subject_lot_size:,.0f} sq ft")

st.subheader("Sold comparable properties")
comp_template = pd.DataFrame(
    [
        {"address": "", "sale_price": 0.0, "lot_size": 0.0, "sale_date": "", "source": ""},
        {"address": "", "sale_price": 0.0, "lot_size": 0.0, "sale_date": "", "source": ""},
        {"address": "", "sale_price": 0.0, "lot_size": 0.0, "sale_date": "", "source": ""},
    ]
)

edited = st.data_editor(
    comp_template,
    num_rows="dynamic",
    use_container_width=True,
    hide_index=True,
    column_config={
        "address": st.column_config.TextColumn("Comp address"),
        "sale_price": st.column_config.NumberColumn("Closed sale price ($)", min_value=0.0, step=1000.0, format="$%.0f"),
        "lot_size": st.column_config.NumberColumn("Lot size (sq ft)", min_value=0.0, step=1000.0),
        "sale_date": st.column_config.TextColumn("Sale date"),
        "source": st.column_config.TextColumn("Verification source"),
    },
)

st.download_button(
    "Download sold-comp CSV template",
    comp_template.to_csv(index=False).encode("utf-8"),
    file_name="verified_land_sold_comps_template.csv",
    mime="text/csv",
)

uploaded = st.file_uploader("Or upload verified sold comps CSV", type=["csv"])
working = edited
if uploaded is not None:
    try:
        uploaded_frame = pd.read_csv(uploaded)
        if not {"sale_price", "lot_size"}.issubset(uploaded_frame.columns):
            st.error("CSV must include sale_price and lot_size columns.")
        else:
            working = uploaded_frame
            st.success(f"Loaded {len(uploaded_frame)} row(s) from CSV.")
    except Exception as exc:
        st.error(f"Unable to read CSV: {exc}")

if st.button("Analyze verified sold comps", type="primary"):
    result = analyze_land_comps(subject_lot_size, working)

    if result.estimated_value is None:
        st.warning(
            f"Need at least two usable verified sales with positive sale price and lot size. "
            f"Usable records: {result.usable_comp_count}."
        )
    else:
        spread = result.estimated_value - asking_price
        discount = spread / result.estimated_value * 100.0 if result.estimated_value else 0.0

        a, b, c, d = st.columns(4)
        a.metric("Sold-comp land value", f"${result.estimated_value:,.0f}")
        b.metric("Estimated range", f"${result.range_low:,.0f}–${result.range_high:,.0f}")
        c.metric("Discount to estimate", f"{discount:.1f}%")
        d.metric("Evidence confidence", result.confidence_label)

        st.success(
            f"Valuation uses {result.sold_comp_count} verified sale comp(s) with a median of "
            f"about ${result.median_price_per_acre:,.0f} per acre."
        )
        st.caption(
            "This is a screening estimate, not an appraisal. Confirm parcel identity, zoning, utilities, access, flood risk, taxes, title, and buildability before making an offer."
        )

        display_cols = [
            c for c in [
                "address",
                "sale_price",
                "sale_date",
                "source",
                "lot_size",
                "acres",
                "price_per_acre",
                "evidence_type",
            ] if c in result.comparables.columns
        ]
        st.dataframe(result.comparables[display_cols], use_container_width=True, hide_index=True)
        st.download_button(
            "Download analyzed sold comps",
            result.comparables.to_csv(index=False).encode("utf-8"),
            file_name="analyzed_verified_land_comps.csv",
            mime="text/csv",
        )
