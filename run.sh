#!/usr/bin/env bash
set -euo pipefail

INPUT="${1-}"
COUNTIES="${2-Peoria,Knox,Woodford}"
TOP="${3-20}"

if [[ -z "${INPUT}" ]]; then
  echo "Usage: ./run.sh <input_csv> [counties] [topN]" >&2
  echo 'Example: ./run.sh data/your_weekly_listings.csv "Peoria,Knox" 10' >&2
  exit 1
fi

# venv
if [[ ! -d .venv ]]; then
  python -m venv .venv
fi
source .venv/bin/activate

python -m pip -q install -U pip
python -m pip -q install -e .  # ensures console entrypoints are current

# default config if missing
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

# run
python -m land_scout.cli \
  --input "${INPUT}" \
  --config examples/config.example.yaml \
  --report out/week.md \
  --out out/weekly.csv \
  --counties "${COUNTIES}" \
  --top "${TOP}"

echo "Saved out/weekly.csv and out/week.md"

# show a quick preview
echo "----- out/week.md (first 60 lines) -----"
sed -n '1,60p' out/week.md || true
echo "----- out/weekly.csv (first 20 rows) -----"
command -v column >/dev/null 2>&1 \
  && column -s, -t < out/weekly.csv | sed -n '1,20p' \
  || head -n 20 out/weekly.csv
