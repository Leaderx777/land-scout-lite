import pandas as pd, yaml

def load_csv(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    return df

def load_cfg(path: str) -> dict:
    with open(path, "r") as f:
        return yaml.safe_load(f) or {}
