# Creative Industries Atlas — multipage Streamlit version

This refactor keeps the existing Streamlit + Pydeck + Plotly design but makes
the indicator views separate pages so each page loads only the data it needs.

## Pages

- Home
- Business Counts
- Turnover
- Employment Size Bands

## Geography control

Each indicator page has a Geography type selector:

1. **Countries**
   - England
   - Scotland
   - Wales
   - Northern Ireland
2. **Distinct Areas**
   - One Creative North
   - South Central
3. **Local Authorities**
   - Individual Local Authorities

South Central uses the supplied 20-LA definition. From 2019 onwards,
Bournemouth, Poole and Christchurch are treated jointly as
`Bournemouth, Christchurch and Poole`.

## Hover tooltip

The Pydeck map tooltip now shows:

- Local Authority
- Region
- Geography
- Year
- indicator value

## Performance changes

- Separate page execution paths
- `st.cache_data` for each dataset
- `st.cache_data` for the boundary file
- No combined `load_all_data()` call
- Only the active page's dataset is read

## Data files

The loader supports the current project filenames and several legacy names.
It looks in both the repository root and `data/`.

Current known files are supported for Business Counts, Turnover and Employment Size Bands.

## Run

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Expected core columns

The fact-long files should contain, or be mappable to:

- `Year`
- `Value`
- `Location`
- `Industry Group`
- `Description`
- `Region_1` (or `Region`)
- `Nation`

The loader includes a few common aliases such as `Local Authority` → `Location`
and `Region` → `Region_1`.


Geography Countries includes United Kingdom, England, Scotland, Wales and Northern Ireland.


For faster map rendering, the app will prefer `data/ltla2025_simplified.geojson` when present.
