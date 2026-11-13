# Add Creative Workforce by Age (Census 2021) to the existing Creative Industries Atlas

This is an **additive Streamlit + Pydeck page**. It does not modify any of your existing indicator calculations or visualisations.

## 1) Upload the new files to your GitHub repository

Repo: `https://github.com/debs4451/creative-industries-atlas`

Copy the contents of the ZIP to the **same relative paths** in your repository:

| File | Purpose |
|---|---|
| `pages/creative_workforce_age.py` | New Streamlit page entrypoint |
| `atlas/creative_workforce_age.py` | Filters, Pydeck map, age and occupation charts |
| `data/creative_workforce_age_census2021.csv.gz` | Real ONS Census 2021 age counts, filtered to 28 selected creative SOC codes |
| `data/creative_soc2020_selection.csv` | The same 28-code selection used for Self-Employment; only replace if your copy is different |

The ZIP also includes ready-edited `app.py` and `pages/home.py` based on the latest Creative Self-Employment homepage update. **If you have made newer edits to these two files, do not overwrite them wholesale.** Apply the changes below instead.

## 2) Register the page in `app.py`

After the `creative_self_employment = st.Page(...)` block, add:

```python
creative_workforce_age = st.Page(
    "pages/creative_workforce_age.py",
    title="Creative Workforce by Age (Census 2021)",
    icon=":material/calendar_month:",
)
```

In the existing `st.navigation(...)` `"Indicators"` list, insert `creative_workforce_age,` immediately after `creative_self_employment,`.

## 3) Add the home-page link

In `pages/home.py`, beneath the Creative Self-Employment link, add:

```python
st.page_link(
    "pages/creative_workforce_age.py",
    label="Creative Workforce by Age (Census 2021)",
    icon="📅",
)
```

Optionally add this explanation to the home-page *How the Atlas works* section:

> Creative Workforce by Age (Census 2021) reports workers in selected 4-digit SOC 2020 creative occupations by workplace Local Authority and original age bands. It differs from the residence-based Creative Self-Employment indicator. Scotland and Northern Ireland are outside this England-and-Wales source.

## 4) Check deployment

Commit the files to the branch followed by Streamlit Cloud (usually `main`). Your existing `requirements.txt` should already provide `streamlit`, `pandas`, `plotly` and `pydeck`, since they are used by the current Atlas; no new libraries are required.

Open the Home page. The indicator should appear below Creative Self-Employment. Check Country → England, Distinct Areas → One Creative North and South Central, and Local Authorities → Barnsley.

## Source, definitions and limitations

- **Original data:** ONS Census 2021, commissioned table [CT21_0332 — Workplace table: occupation (4 digits) by age](https://www.ons.gov.uk/peoplepopulationandcommunity/populationandmigration/populationestimates/adhocs/2330ct210332census2021), lower-tier Local Authority (merged).
- **Workers:** usual residents aged 16+ who were in employment in the week before Census day; geography is the **workplace**, **not home address**.
- **Occupation definition:** 28 selected 4-digit SOC 2020 occupations carried over from the existing Self-Employment page. They are not equivalent to the 31 SIC-defined Creative Industries businesses, nor claimed to be a complete official DCMS Creative Occupations total.
- **Original measures:** the ONS total plus **13 distinct age bands**, each preserved separately. No age rates are inserted into the source; the chart derives shares from observed counts when needed.
- **Geographic coverage:** England and Wales only. A UK selection is visibly marked as partial. No Scotland or Northern Ireland counts are treated as zero.
- **Merged 2021 source geographies:** Westminster and City of London are combined; Cornwall and Isles of Scilly are combined. Their figures are shown on Westminster and Cornwall, respectively, because their individual contributions cannot be separated. The Atlas's current boundaries are used for display. The 329 source geographies map to 316 current map areas.
- **Missing source observations:** five combinations of selected SOC codes and original Local Authorities are absent. Their counts are stored as missing (`NaN`), not zero. Maps do not show complete LA totals where one of the selected SOC observations is missing; headline numbers use complete LAs only.
- **2011 comparison:** deliberately not included. The uploaded 2011 data use SOC 2010 and are not a harmonised 2011 age-by-occupation table. This 2021 workplace series also should not be numerically compared with the residence-based Self-Employment page without aligning definitions.
- **ONS statistical disclosure control:** small Census counts are perturbed for confidentiality.

## Validation performed here

- Parsed ONS's original `CT21_0332 LTLA merged` worksheet; selected 28 SOC codes.
- Confirmed **329 source workplace geographies**, **28 SOC codes**, **13 age bands**, and **9,212 rows** in the delivered CSV (including five explicitly empty, unpublished combinations).
- Matched source authorities to the mapping used in the existing Creative Self-Employment Atlas.
- Confirmed South Central has **18** current area records and One Creative North **60** current area records.
- Successfully ran the data filters, geography aggregation, TopoJSON-to-GeoJSON map, chart construction and full page rendering with mocked Streamlit/Pydeck frontends. Python syntax compilation passed.
- **Not tested on the live Streamlit Cloud deployment.** If a module import fails after deployment, check that the files were uploaded under the exact paths above.
