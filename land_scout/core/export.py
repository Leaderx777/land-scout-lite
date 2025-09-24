from pathlib import Path

import pandas as pd


def to_csv(df: pd.DataFrame, out_csv: str) -> None:
    Path(out_csv).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_csv, index=False)


def to_markdown_report(df: pd.DataFrame, out_md: str, top_n: int = 20) -> None:
    Path(out_md).parent.mkdir(parents=True, exist_ok=True)
    cat_order = {"excellent": 0, "very_good": 1, "look_closer": 2, "avoid": 3}
    df2 = df.copy()
    df2["__cat_rank"] = df2["category"].map(cat_order).fillna(9)
    ranked = (
        df2.sort_values(["__cat_rank", "price_per_acre"], na_position="last")
        .drop(columns="__cat_rank")
        .head(top_n)
    )
    cols = ["county", "category", "price_per_acre", "price", "acre", "title", "link"]
    cols = [c for c in cols if c in ranked.columns]
    lines = ["# Weekly Land Scout Report", "", "## Top Picks", ""]
    lines.append(ranked[cols].to_markdown(index=False))
    Path(out_md).write_text("\n".join(lines), encoding="utf-8")
