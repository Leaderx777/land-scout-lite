import argparse, pathlib
import pandas as pd
from land_scout.core.loader import load_csv, load_cfg
from land_scout.core.score import apply
from land_scout.core.export import to_csv, to_markdown_report

def main():
    p = argparse.ArgumentParser(description="Land Scout Lite")
    p.add_argument("--input", required=True, help="CSV with columns: price, acre(s)")
    p.add_argument("--config", default="config.yaml", help="YAML with scoring thresholds")
    p.add_argument("--out", default="out/weekly.csv", help="Output CSV")
    p.add_argument("--report", default="out/week.md", help="Markdown report path")
    args = p.parse_args()

    df = load_csv(args.input)
    try:
        cfg = load_cfg(args.config)
    except FileNotFoundError:
        cfg = {}

    thresholds = (cfg.get("scoring") or {}).get("price_per_acre_thresholds")
    df2 = apply(df, thresholds=thresholds)

    pathlib.Path("out").mkdir(exist_ok=True)
    to_csv(df2, args.out)
    to_markdown_report(df2, args.report, top_n=20)
    print(f"Saved {args.out} and {args.report}")

if __name__ == "__main__":
    main()
