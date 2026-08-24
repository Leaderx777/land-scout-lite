# Land Scout Lite

Land Scout Lite is a Streamlit-based land-deal screening prototype that now connects directly to the separate [Land Value Predictor](https://github.com/Leaderx777/land-value-predictor) service.

## Current workflow

1. Load land/deal CSV data
2. Review candidate properties
3. Enter property features for a selected deal
4. Send those features to the Land Value Predictor FastAPI service
5. Receive a model-estimated land value
6. Compare that estimate with asking price and other deal information

## Predictor integration

Land Scout calls the predictor over HTTP using `land_scout/core/value_predictor.py`.

By default it expects the API at:

```text
http://127.0.0.1:8000
```

You can also set:

```bash
LAND_VALUE_API_URL=http://127.0.0.1:8000
```

Start the predictor first:

```bash
git clone https://github.com/Leaderx777/land-value-predictor.git
cd land-value-predictor
pip install -r requirements.txt
python train.py
uvicorn api:app --reload --port 8000
```

Then start Land Scout in a second terminal:

```bash
git clone https://github.com/Leaderx777/land-scout-lite.git
cd land-scout-lite
pip install -r requirements.txt
streamlit run app.py
```

## Expected deal data

Typical fields include:

- `listing_id`
- `county`
- `acres`
- `price`
- `distance_to_city_miles`
- `road_frontage_ft`
- `zoning_score`
- `utilities`

## Tech stack

- Python
- Streamlit
- pandas
- requests
- scikit-learn
- joblib
- APScheduler
- FastAPI integration through Land Value Predictor

## Status

This remains a portfolio prototype. The connected valuation model is currently trained on synthetic data, so model output is for workflow demonstration only and is not a real appraisal.
