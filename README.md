# Land Scout Lite

Land Scout Lite is a Streamlit-based Central Illinois property-deal screening prototype connected to the separate [Land Value Predictor](https://github.com/Leaderx777/land-value-predictor) FastAPI service.

## House-flip workflow

The app includes a residential flip analyzer. Enter property details and deal assumptions to calculate:

- total project cost
- projected profit
- ROI
- maximum offer for the target profit
- BUY / REVIEW / PASS against the current buy box

Current default flip rules:

- purchase price: $50,000 max
- rehab target: $20,000 max
- target projected profit: $25,000 minimum

Analyzed properties can be saved, ranked, exported to CSV, and reloaded after the app restarts. Saved deal data is stored locally in `data/saved_flip_deals.json` and is excluded from Git.

## Live residential listings

A Streamlit page at `pages/1_Live_Listings.py` can query active for-sale listings from the RentCast sale-listings API and run the returned properties through Property Scout's residential price screen.

The live search supports the current focus areas of Galesburg, Canton, Brimfield, and Kickapoo, plus custom Illinois cities or ZIP codes. It searches active listings and applies the current maximum asking-price rule without excluding one-bedroom homes or unusual residential property types.

RentCast requires an API key. Either enter it in the Live Listings page or set it locally before starting Streamlit:

```powershell
$env:RENTCAST_API_KEY="your-key-here"
python -m streamlit run app.py
```

The key is never committed to this repository.

Live feed properties initially remain `NEEDS_ARV` because a listing feed does not provide a trustworthy after-repair value or repair budget. ARV and rehab must be developed separately before a listing can be treated as BUY / REVIEW / PASS.

The existing residential CSV intake remains available for exports from other permitted listing sources.

## Initial target market

The first screening region is centered on Central Illinois and currently includes:

- Peoria
- Tazewell
- Woodford
- Fulton
- Knox
- McLean
- Marshall
- Stark
- Mason
- Logan

Listings outside these counties are ignored by the land batch screener.

## Land workflow

1. Upload a deals CSV
2. Keep only listings in the Central Illinois target counties
3. Send each listing's property features to Land Value Predictor
4. Receive an estimated value
5. Compare estimated value with asking price
6. Calculate dollar spread and discount-to-estimate percentage
7. Rank the strongest apparent opportunities
8. Export the ranked results to CSV

A single-property land screen is also available in the Streamlit interface.

## CSV input for land screening

Required columns:

- `listing_id`
- `county`
- `acres`
- `price`
- `distance_to_city_miles`
- `road_frontage_ft`
- `zoning_score`
- `utilities`

A demo template is included at:

```text
examples/central_illinois_deals_template.csv
```

The sample rows are fictional and exist only to demonstrate the input format.

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
python -m streamlit run app.py
```

## Real-data direction

Land Value Predictor includes an official Peoria County GIS/sales-data connector. Peoria is therefore the first county where the project can begin replacing synthetic training inputs with real public parcel and transaction data.

The current land API model itself is still synthetic until the real-data feature engineering and validation pipeline is complete. Rankings should therefore be treated as development/demo outputs, not as investment or appraisal conclusions.

## Tech stack

- Python
- Streamlit
- pandas
- requests
- FastAPI integration through Land Value Predictor
- RentCast live sale-listing integration
- JSON persistence for saved flip opportunities
- batch CSV screening and export

## Tests

```bash
python -m pytest
```
