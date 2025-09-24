from pathlib import Path
from typing import Optional, Sequence

import pandas as pd

CAT_ORDER = {"excellent": 0, "very_good": 1, "look_closer": 2, "avoid": 3}


def _rank(df: pd.DataFrame) -> pd.DataFrame:
    df2 = df.copy()
    df2["__cat_rank"] = df2["category"].map(CAT_ORDER).fillna(9)
    return df2.sort_values(["__cat_rank", "price_per_acre"], na_position="last").drop(
        columns="__cat_rank"
    )


def to_csv(df: pd.DataFrame, out_csv: str) -> None:
    Path(out_csv).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_csv, index=False)


def to_markdown_report(
    df: pd.DataFrame,
    out_md: str,
    top_n: int = 20,
    group_by_county: bool = True,
    columns: Optional[Sequence[str]] = None,
) -> None:
    Path(out_md).parent.mkdir(parents=True, exist_ok=True)
    cols_default = [
        "county",
        "category",
        "price_per_acre",
        "price",
        "acre",
        "title",
        "link",
    ]
    cols = [c for c in (columns or cols_default) if c in df.columns]

    lines = ["# Weekly Land Scout Report", ""]
    ranked = _rank(df)

    if group_by_county and "county" in ranked.columns:
        for county, chunk in ranked.groupby(
            ranked["county"].fillna("Unknown"), sort=True
        ):
            lines += [f"## {county}", ""]
            top = chunk.head(top_n)

            # If link+title exist, render title as markdown link
            if "link" in cols and "title" in cols:
                top = top.copy()

                def _mk_title(r: pd.Series) -> str | float:
                    t = r.get("title")
                    L = r.get("link")
                    if pd.notna(t) and pd.notna(L):
                        return f"[{t}]({L})"
                    return t

                top["title"] = top.apply(_mk_title, axis=1)
                safe_cols = [c for c in cols if c != "link"]
            else:
                safe_cols = cols

            lines.append(top[safe_cols].to_markdown(index=False))
            lines.append("")
    else:
        lines += ["## Top Picks", ""]
        lines.append(ranked.head(top_n)[cols].to_markdown(index=False))
        lines.append("")

    Path(out_md).write_text("\n".join(lines), encoding="utf-8")
