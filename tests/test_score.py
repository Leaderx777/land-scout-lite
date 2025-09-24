import pandas as pd

from land_scout.core.score import apply


def test_categories():
    df = pd.DataFrame({"price": [1000, 4000, 12000], "acre": [1, 1, 1]})
    out = apply(df)
    assert set(out["category"]) == {"excellent", "very_good", "avoid"}
