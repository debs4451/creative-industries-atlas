# Creative Industries Atlas — England, 2025

A single Streamlit website combining three 2025 Nomis views:

- Business Counts
- Employment Size Bands
- Enterprise Turnover

## Run locally

```bat
cd /d "C:\path\to\creative_industries_atlas_website"
pip install -r requirements.txt
streamlit run app.py
```

The app opens at `http://localhost:8501` by default.

## Deploy as a public website with Streamlit Community Cloud

1. Create a GitHub repository, e.g. `creative-industries-atlas`.
2. Upload the entire contents of this folder, including `app.py`, `requirements.txt`, and the `data` folder.
3. Go to Streamlit Community Cloud and create a new app from that repository.
4. Set the entrypoint to `app.py`.
5. Deploy. Streamlit will provide a public `streamlit.app` URL that can be shared with anyone.

## Data

The site covers England only: 296 Local Authority Districts across the nine English regions. Headline region totals use the published Nomis Total enterprise counts where applicable. Detailed turnover and employment-band charts use the rounded banded values supplied by Nomis.
