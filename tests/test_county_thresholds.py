import pandas as pd

from land_scout.core.score import apply


def test_county_specific_thresholds():
    df = pd.DataFrame(
        {
            "price": [4000, 4000, 4000],
            "acre": [1, 1, 1],
            "county": ["Peoria", "Knox", "Chicago"],
        }
    )
    out = apply(df)  # uses built-in COUNTY_THRESHOLDS
    got = dict(zip(out["county"].str.lower(), out["category"]))
    assert got["peoria"] == "very_good"
    assert got["knox"] == "very_good"
    assert got["chicago"] == "excellent"
