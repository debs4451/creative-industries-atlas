# Creative Self-Employment (Census 2021) — Atlas homepage and page update

This package fixes the missing home-page link and explicitly marks the source as Census 2021. It also removes the final on-page data table and its download button. All maps, three independent employment-category selectors, charts, geographic filters and the methodology expander remain.

## Upload to your EXISTING GitHub repository

Keep folder paths identical. In https://github.com/debs4451/creative-industries-atlas, replace or add:

1. `pages/home.py` — adds the new indicator to the **Home > Indicators** list and explains Census 2021.
2. `atlas/creative_self_employment.py` — new page label and removes the last data table.
3. `app.py` — registers the new page in the sidebar **Indicators** menu (only necessary if you haven't already registered it).
4. `pages/creative_self_employment.py` — page loader (already installed if the earlier add-on is working).
5. `data/creative_self_employment_census2021.csv.gz` — unchanged Census source extract (already installed if earlier add-on works).
6. `data/creative_soc2020_selection.csv` — unchanged list of 28 selected occupations.

If your `app.py` has newer custom edits, DON'T overwrite it blindly; make sure it has this page registration and `creative_self_employment` in `st.navigation`:

```python
creative_self_employment = st.Page(
    "pages/creative_self_employment.py",
    title="Creative Self-Employment (Census 2021)",
    icon=":material/person:",
)
```

Then insert `creative_self_employment,` immediately after `employment,` in the `"Indicators"` list.

Do not upload this ZIP file as a single file to the repo: extract it, then commit the files under their specified folders. Streamlit Cloud should then redeploy if configured to follow your `main` branch.

## Scope

The measure is **selected creative SOC occupations**, not all employees of the **31 SIC-defined Creative Industries**. The 2021 dataset covers England and Wales, based on area of residence. Scotland and Northern Ireland have no observations in this source. No direct 2011 comparison: the uploaded 2011 source is workplace-based and uses SOC 2010.
