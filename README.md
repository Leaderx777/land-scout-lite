# Land Scout Lite

Land Scout Lite is a Streamlit-based prototype for screening and organizing land investment opportunities from structured CSV data.

## Current status

The repository is a working prototype scaffold. The Streamlit interface runs, accepts the expected deal-data structure, and provides the foundation for adding ingestion, enrichment, scoring, and model-assisted screening.

## Planned workflow

1. Load land/deal CSV data
2. Validate and normalize listing fields
3. Enrich records with derived investment metrics
4. Score or categorize opportunities
5. Review candidate properties in a Streamlit interface
6. Export or retain promising leads for deeper analysis

## Expected data

Typical fields include:

- `listing_id`
- `county`
- `acres`
- `price`
- `estimated_value`

Additional fields can be added as the scoring model evolves.

## Tech stack

- Python
- Streamlit
- pandas
- scikit-learn
- requests
- joblib
- APScheduler

## Run locally

```bash
git clone https://github.com/Leaderx777/land-scout-lite.git
cd land-scout-lite
python -m venv .venv
```

Activate the virtual environment and install dependencies:

```bash
pip install -r requirements.txt
```

Start the app:

```bash
streamlit run app.py
```

## Portfolio note

This project demonstrates an application concept for automating repetitive real-estate screening work. It is intentionally labeled as a prototype until the ingestion, enrichment, and scoring pipeline is fully implemented.
