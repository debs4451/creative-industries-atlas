# Creative Self-Employment (Census 2021) — GitHub add-on

This is **one additional Pydeck page** for your existing Creative Industries Atlas. It leaves all six original indicators untouched.

## Copy these files into your existing repository

| New file | Upload to existing repo path |
|---|---|
| `data/creative_self_employment_census2021.csv.gz` | `data/creative_self_employment_census2021.csv.gz` |
| `data/creative_soc2020_selection.csv` | `data/creative_soc2020_selection.csv` |
| `atlas/creative_self_employment.py` | `atlas/creative_self_employment.py` |
| `pages/creative_self_employment.py` | `pages/creative_self_employment.py` |

Do not replace any existing Atlas files. The project uses your existing `atlas.data.load_geojson`, `atlas.map_utils`, geography and styling helpers; the dependencies (`streamlit`, `pandas`, `plotly`, `pydeck`) are already in your `requirements.txt`.

## Update `app.py`

Add the following after the existing `employment = st.Page(...)` definition:

```python
creative_self_employment = st.Page(
    "pages/creative_self_employment.py",
    title="Creative Self-Employment (Census 2021)",
    icon=":material/person:",
)
```

Then add `creative_self_employment,` immediately after `employment,` in your existing `"Indicators"` list within `st.navigation(...)`.

Commit the changes on GitHub. Streamlit Cloud should redeploy automatically if connected to your repo. No new file paths or environment secrets are needed.

## Data and limits

- ONS Census **2021** CT21_0217, lower-tier Local Authority (LA) of **residence** in England/Wales.
- **28 documented selected creative SOC 2020 groups** from the Creative PEC/DCMS classifications, listed explicitly in `data/creative_soc2020_selection.csv`. This is NOT a complete enumeration of all workers in the 31 Creative Industries SIC codes. It measures selected *creative occupations*, including people outside creative-sector businesses.
- The original source's **three distinct columns remain distinct**: Employees; Self-employed with employees; Self-employed without employees.
- Only the category chosen in the sidebar is mapped. No rates or combined totals are added to the CSV.
- Source LADs affected by 2023 reorganisations (North Yorkshire, Cumbria, Somerset) are aggregated to the supplied contemporary Atlas boundaries **for display only**. Downloaded filtered observations preserve original LA values.
- UK geography selection shows England + Wales only. Scotland and Northern Ireland are marked unavailable rather than zero.
- 2011 is excluded: the 2011 uploaded occupation extract is workplace-based and its occupation codes use SOC 2010.
- Disclosure control can cause small differences between national and summed LA counts; a few source occupation rows are absent and remain missing, not zero.

**Source:** https://www.ons.gov.uk/peoplepopulationandcommunity/populationandmigration/populationestimates/adhocs/1941ct210217census2021

**SOC review:** https://www.gov.uk/government/statistics/economic-estimates-employment-january-2025-to-december-2025-for-dcms-sectors/dcms-sectors-economic-estimates-creative-occupations-update-note
