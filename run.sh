#!/usr/bin/env bash
set -euo pipefail

INPUT="${1-}"
COUNTIES="${2-Peoria,Knox,Woodford}"
TOP="${3-20}"

if [[ -z "$INPUT" ]]; then
  echo "Usage: ./run.sh <input_csv> [counties] [topN]"
  echo 'Example: ./run.sh data/your_weekly_listings.csv "Peoria,Knox" 10'
  exit 1
fi

if [[ ! -d .venv ]]; then
  python -m venv .venv
fi
source .venv/bin/activate

python -m pip install -U pip
python -m pip install -e .[dev]

mkdir -p examples
if [[ ! -f examples/config.example.yaml ]]; then
  cat > examples/config.example.yaml <<YAML
scoring:
  default_thresholds: [1000, 4000, 8000]
  thresholds_by_county:
    peoria:   [1200, 4500, 9000]
    knox:     [1000, 4000, 8000]
    woodford: [1500, 5000, 10000]
    chicago:  [5000, 15000, 40000]
    tazewell: [1300, 4500, 9000]
    henry:    [1100, 4200, 8500]
    canton:   [1100, 4200, 8500]
YAML
fi

python -m land_scout.cli \
  --input "$INPUT" \
  --config examples/config.example.yaml \
  --counties "$COUNTIES" \
  --top "$TOP" \
  --out out/weekly.csv \
  --report out/week.md

echo "Done. See out/weekly.csv and out/week.md"
