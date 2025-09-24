import pandas as pd
from land_scout.core.score import apply

def test_categories_default_thresholds():
    df = pd.DataFrame({"price":[1000, 4000, 12000], "acre":[1,1,1]})
    out = apply(df)  # default thresholds [1000, 3500, 8000]
    assert set(out["category"]) == {"excellent","very_good","avoid"}
