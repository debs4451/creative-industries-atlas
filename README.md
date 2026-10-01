# Creative Industries Atlas — DSIT-style Streamlit redesign

This version combines the supplied Business Counts, Turnover and Employment-size datasets into one interactive UK atlas.

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Streamlit Cloud

Upload this entire folder to the GitHub repository (keep the `data/` subfolder), then set the app entry point to `app.py`.

## Main changes

- Large Pydeck UK map with hover and click selection
- DSIT-inspired left-hand exploration controls
- One app for Business Counts, Turnover profile and Employment-size profile
- Year and Creative Industries filters
- UK regions/nations and One Creative North groupings
- Clicked Local Authority detail panel
- Plotly composition, ranking and time-trend charts
- Download of the filtered data

The app expects the supplied 2025 LTLA TopoJSON and keeps the source terminology for the nine Creative Industries groups.
