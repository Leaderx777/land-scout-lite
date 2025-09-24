import pandas as pd
DEFAULT_THRESHOLDS = [1000, 3500, 8000]  # tune per market

def apply(df: pd.DataFrame, thresholds=None) -> pd.DataFrame:
    df = df.copy()
    cols = [c.lower().strip().replace(" ", "_") for c in df.columns]
    df.columns = cols
    acre_col = "acre" if "acre" in cols else ("acres" if "acres" in cols else None)

    if "price" in cols and acre_col:
        df["price_per_acre"] = (df["price"].astype(float) / df[acre_col].astype(float)).round(2)
    else:
        df["price_per_acre"] = None

    thr = thresholds or DEFAULT_THRESHOLDS
    def cat(v):
        if v is None: return "look_closer"
        if v <= thr[0]: return "excellent"
        if v <= thr[1]: return "very_good"
        if v <= thr[2]: return "look_closer"
        return "avoid"

    df["category"] = df["price_per_acre"].apply(cat)
    return df
