from pathlib import Path
import pandas as pd
import math

def dataframe_to_md_simple(df: pd.DataFrame) -> str:
    cols = list(df.columns)
    lines = []
    lines.append("| " + " | ".join(map(str, cols)) + " |")
    lines.append("| " + " | ".join(["---"] * len(cols)) + " |")
    for _, row in df.iterrows():
        vals = []
        for v in row.tolist():
            if v is None or (isinstance(v, float) and math.isnan(v)):
                vals.append("")
            else:
                s = str(v).replace("\n", " ").strip()
                vals.append(s)
        lines.append("| " + " | ".join(vals) + " |")
    return "\n".join(lines)

def to_csv(df: pd.DataFrame, out_csv: str) -> None:
    Path(out_csv).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_csv, index=False)

def to_markdown_report(df: pd.DataFrame, out_md: str, top_n: int = 20) -> None:
    Path(out_md).parent.mkdir(parents=True, exist_ok=True)
    cat_order = {"excellent": 0, "very_good": 1, "look_closer": 2, "avoid": 3}
    d2 = df.copy()
    d2["__rank"] = d2["category"].map(cat_order).fillna(9)
    top = d2.sort_values(["__rank", "price_per_acre"], na_position="last").drop(columns="__rank").head(top_n)
    cols = ["category", "price_per_acre"] + [c for c in top.columns if c not in ("category","price_per_acre")]

    lines = ["# Weekly Land Scout Report", "", "## Top Picks", ""]
    try:
        # use pandas markdown if tabulate is present
        lines.append(top[cols].to_markdown(index=False))
    except Exception:
        # fallback: minimal Markdown table, no external deps
        lines.append(dataframe_to_md_simple(top[cols]))

    Path(out_md).write_text("\n".join(lines), encoding="utf-8")
