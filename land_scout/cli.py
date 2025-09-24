import argparse
import pathlib

import pandas as pd
import yaml

from land_scout.core.export import to_csv, to_markdown_report
from land_scout.core.score import apply


def main():
    p = argparse.ArgumentParser(description="Land Scout Lite")
    p.add_argument(
        "--input", required=True, help="CSV with columns incl. price, acre(s), county"
    )
    p.add_argument(
        "--config", default="examples/config.example.yaml", help="YAML with thresholds"
    )
    p.add_argument("--out", default="out/weekly.csv")
    p.add_argument("--report", default="out/week.md", help="Markdown report output")
    p.add_argument(
        "--counties",
        default="",
        help="Comma-separated county filter (e.g., 'Peoria,Knox')",
    )
    p.add_argument("--top", type=int, default=20, help="Top N rows in the MD report")
    args = p.parse_args()

    df = pd.read_csv(args.input)

    thresholds = None
    thresholds_by_county = None
    try:
        with open(args.config, "r") as f:
            cfg = yaml.safe_load(f) or {}
        sc = cfg.get("scoring") or {}
        thresholds = sc.get("default_thresholds")
        thresholds_by_county = sc.get("thresholds_by_county")
    except FileNotFoundError:
        pass

    df2 = apply(df, thresholds=thresholds, thresholds_by_county=thresholds_by_county)

    if args.counties:
        wanted = {c.strip().lower() for c in args.counties.split(",")}
        if "county" in df2.columns:
            df2 = df2[df2["county"].astype(str).str.lower().isin(wanted)]

    pathlib.Path("out").mkdir(exist_ok=True)
    to_csv(df2, args.out)
    to_markdown_report(df2, args.report, top_n=args.top)
    print(f"Saved {args.out} and {args.report}")


if __name__ == "__main__":
    main()
