# Creative Industries Atlas — multipage Streamlit version

This refactor keeps the existing Streamlit + Pydeck + Plotly design but makes
the indicator views separate pages so each page loads only the data it needs.

## Pages

- Home
- Business Counts
- Employment
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

Current known files are supported for Business Counts, Turnover and Employment
Size Bands.

The **Employment** page is deliberately kept separate from Employment Size
Bands. It expects a true employment-count fact-long file, for example:

- `data/employment_counts_fact_long.csv.gz`
- `data/employment_counts_fact_long.csv`
- `employment_counts_fact_long_2025.csv`
- `data/employment.xlsx` with a `fact_long` sheet

This prevents enterprise employment-size bands from being accidentally
presented as employment headcounts.

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
