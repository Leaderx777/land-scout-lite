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

1. Search or upload land listings
2. Screen by property type, location, price, lot size, and listing facts
3. Rank candidates preliminarily
4. Request a direct value estimate when available
5. Fall back to comparable price-per-acre analysis when a direct land AVM is unavailable
6. Compare estimated value with asking price
7. Calculate dollar spread and discount-to-estimate percentage
8. Rank the strongest apparent opportunities
9. Export the results to CSV

A single-property land screen is also available in the Streamlit interface.

### Land valuation evidence hierarchy

Property Scout now distinguishes transaction evidence from listing-price evidence:

1. **Verified closed sales** — strongest comp input. Use `pages/3_Verified_Land_Comps.py` with actual closed sale prices from a county record, MLS, or another verified source.
2. **Direct AVM** — useful model-based value evidence when the provider returns a usable estimate.
3. **Active/inactive listing asking prices** — preliminary market evidence only. These prices are not treated as closed sales.

The RentCast AVM comparable records contain listing prices. Therefore the automatic land comp fallback is intentionally labeled and scored conservatively. A listing-ask fallback can move a parcel to **Worth Reviewing**, but cannot by itself earn the strongest **Best Deal** label.

The verified-sold-comps page accepts manual entry or a CSV with at least:

- `sale_price`
- `lot_size` (square feet)

Optional columns include `address`, `sale_date`, and `source`. At least two usable sold comps are required for an estimate.

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
- automated pytest checks with GitHub Actions

## Tests

Run locally:

```bash
python -m pytest
```

Pull requests and pushes to `main` also run the test suite automatically through GitHub Actions.
