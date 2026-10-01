from pathlib import Path
import copy
import json
import math

import pandas as pd
import plotly.express as px
import pydeck as pdk
import streamlit as st

APP_DIR = Path(__file__).resolve().parent
DATA_DIR = APP_DIR / "data"

st.set_page_config(
    page_title="Creative Industries Atlas",
    page_icon="◉",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -------------------- Constants --------------------
REGION_ORDER = [
    "North East", "North West", "Yorkshire and the Humber", "East Midlands",
    "West Midlands", "East of England", "London", "South East", "South West",
    "Scotland", "Wales", "Northern Ireland",
]

INDUSTRY_ORDER = [
    "Advertising and marketing",
    "Architecture",
    "Crafts",
    "Design and designer fashion",
    "Film, TV, video, radio and photography",
    "IT, software and computer services",
    "Museums, galleries and libraries",
    "Music, performing and visual arts",
    "Publishing",
]

TURNOVER_ORDER = [
    "0 to 49 (thousand)", "50 to 99  (thousand)", "100 to 249 (thousand)",
    "250 to 499 (thousand)", "500 to 999 (thousand)", "1000 to 1999 (thousand)",
    "2000 to 4999 (thousand)", "5000 to 9999 (thousand)",
    "10000 to 49999 (thousand)", "50000+ (thousand)",
]
TURNOVER_LABELS = {
    "0 to 49 (thousand)": "£0–£49k", "50 to 99  (thousand)": "£50k–£99k",
    "100 to 249 (thousand)": "£100k–£249k", "250 to 499 (thousand)": "£250k–£499k",
    "500 to 999 (thousand)": "£500k–£999k", "1000 to 1999 (thousand)": "£1m–£1.999m",
    "2000 to 4999 (thousand)": "£2m–£4.999m", "5000 to 9999 (thousand)": "£5m–£9.999m",
    "10000 to 49999 (thousand)": "£10m–£49.999m", "50000+ (thousand)": "£50m+",
}
EMPLOYMENT_ORDER = ["0 to 4", "5 to 9", "10 to 19", "20 to 49", "50 to 99", "100 to 249", "250 to 499", "500 to 999", "1000+"]

ONE_CREATIVE_NORTH = {
    "All One Creative North": None,
    "Greater Manchester": {"Bolton", "Bury", "Manchester", "Oldham", "Rochdale", "Salford", "Stockport", "Tameside", "Trafford", "Wigan"},
    "Liverpool City Region": {"Halton", "Knowsley", "Liverpool", "Sefton", "St. Helens", "St Helens", "Wirral"},
    "West Yorkshire": {"Bradford", "Calderdale", "Kirklees", "Leeds", "Wakefield"},
    "South Yorkshire": {"Barnsley", "Doncaster", "Rotherham", "Sheffield"},
    "North East": {"County Durham", "Gateshead", "Newcastle upon Tyne", "North Tyneside", "Northumberland", "South Tyneside", "Sunderland"},
    "Tees Valley": {"Darlington", "Hartlepool", "Middlesbrough", "Redcar and Cleveland", "Stockton-on-Tees"},
    "York and North Yorkshire": {"York", "North Yorkshire"},
    "Cheshire and Warrington": {"Cheshire East", "Cheshire West and Chester", "Warrington"},
    "Cumbria": {"Cumberland", "Westmorland and Furness", "Allerdale", "Barrow-in-Furness", "Carlisle", "Copeland", "Eden", "South Lakeland"},
    "Lancashire": {"Blackburn with Darwen", "Blackpool", "Burnley", "Chorley", "Fylde", "Hyndburn", "Lancaster", "Pendle", "Preston", "Ribble Valley", "Rossendale", "South Ribble", "West Lancashire", "Wyre"},
}
OCN_ALL = set().union(*[v for v in ONE_CREATIVE_NORTH.values() if v])

# DSIT-inspired neutral blue/teal scale, deliberately kept accessible on a light basemap.
COLOR_STOPS = [
    (239, 246, 248), (207, 232, 236), (156, 207, 214),
    (93, 171, 183), (39, 128, 146), (12, 82, 104),
]
NO_DATA_COLOR = [224, 228, 231, 100]
BORDER_COLOR = [255, 255, 255, 210]

# -------------------- Styling --------------------
st.markdown(
    """
    <style>
      .block-container {padding: 1rem 1.35rem 2.5rem 1.35rem; max-width: 1800px;}
      [data-testid="stSidebar"] {border-right: 1px solid #dde3e7;}
      [data-testid="stSidebar"] .block-container {padding-top: 1rem;}
      h1 {font-size: 2.0rem !important; letter-spacing: -.02em; margin-bottom: .15rem !important;}
      h2, h3 {letter-spacing: -.01em;}
      .atlas-kicker {font-size:.76rem; text-transform:uppercase; letter-spacing:.12em; font-weight:700; color:#50616a; margin-bottom:.15rem;}
      .atlas-subtitle {font-size:1rem; color:#53636c; margin-bottom:1rem; max-width:900px;}
      .metric-card {border:1px solid #dfe5e8; border-radius:12px; padding:14px 16px; background:#fff; min-height:92px;}
      .metric-label {font-size:.76rem; text-transform:uppercase; letter-spacing:.06em; color:#66747c;}
      .metric-value {font-size:1.55rem; font-weight:700; color:#12262f; margin-top:2px;}
      .detail-card {border:1px solid #dfe5e8; border-radius:14px; padding:16px 18px; background:#fff;}
      .detail-title {font-size:1.2rem; font-weight:700; color:#12262f; margin-bottom:.15rem;}
      .detail-meta {font-size:.88rem; color:#61717a; margin-bottom:.85rem;}
      .detail-row {display:flex; justify-content:space-between; gap:18px; padding:8px 0; border-top:1px solid #edf0f2; font-size:.92rem;}
      .detail-row b {color:#12262f;}
      .small-note {font-size:.82rem; color:#6b7880;}
      div[data-testid="stDownloadButton"] button {width:100%;}
      div[data-testid="stMetric"] {border:1px solid #dfe5e8; border-radius:12px; padding:10px 14px;}
      .stPlotlyChart {border:1px solid #edf0f2; border-radius:12px; overflow:hidden;}
    </style>
    """,
    unsafe_allow_html=True,
)

# -------------------- Data loading --------------------
def _close_ring(coords):
    if coords and coords[0] != coords[-1]:
        return coords + [coords[0]]
    return coords


def topojson_to_geojson(topology, object_name="ltla"):
    if topology.get("type") != "Topology":
        return topology
    objects = topology.get("objects", {})
    if object_name not in objects:
        object_name = next(iter(objects))
    transform = topology.get("transform")
    scale = transform.get("scale", [1, 1]) if transform else [1, 1]
    translate = transform.get("translate", [0, 0]) if transform else [0, 0]
    decoded_arcs = []
    for arc in topology.get("arcs", []):
        x = y = 0
        points = []
        for dx, dy in arc:
            x += dx; y += dy
            points.append([x * scale[0] + translate[0], y * scale[1] + translate[1]])
        decoded_arcs.append(points)

    def get_arc(index):
        return decoded_arcs[index] if index >= 0 else list(reversed(decoded_arcs[-index - 1]))

    def stitch(arc_indices):
        coords = []
        for index in arc_indices:
            part = get_arc(index)
            if not part:
                continue
            coords.extend(part[1:] if coords and coords[-1] == part[0] else part)
        return _close_ring(coords)

    features = []
    for geometry in objects[object_name].get("geometries", []):
        geom_type = geometry.get("type")
        arcs = geometry.get("arcs", [])
        if geom_type == "Polygon":
            coordinates = [stitch(ring) for ring in arcs]
        elif geom_type == "MultiPolygon":
            coordinates = [[stitch(ring) for ring in polygon] for polygon in arcs]
        else:
            continue
        features.append({"type": "Feature", "properties": geometry.get("properties", {}), "geometry": {"type": geom_type, "coordinates": coordinates}})
    return {"type": "FeatureCollection", "features": features}


@st.cache_data(show_spinner=False)
def load_all_data():
    business = pd.read_excel(DATA_DIR / "business_counts.xlsx", sheet_name="fact_long")
    turnover = pd.read_csv(DATA_DIR / "turnover_fact_long.csv.gz")
    employment = pd.read_csv(DATA_DIR / "employment_fact_long.csv.gz")
    turnover_summary = pd.read_csv(DATA_DIR / "turnover_summary.csv")
    employment_summary = pd.read_csv(DATA_DIR / "employment_summary.csv")
    with open(DATA_DIR / "ltla2025.json", "r", encoding="utf-8") as f:
        geo = topojson_to_geojson(json.load(f))

    business = business.rename(columns={"Region": "Region_1"})
    for df in (business, turnover, employment):
        df["Year"] = pd.to_numeric(df["Year"], errors="coerce").astype("Int64")
        df["Value"] = pd.to_numeric(df["Value"], errors="coerce").fillna(0)
        df["Location"] = df["Location"].astype(str).str.strip()
        df["Industry Group"] = df["Industry Group"].astype(str).str.strip()
        df["Description"] = df["Description"].astype(str).str.strip()
        df["Region_1"] = df["Region_1"].astype(str).str.strip()
        df["Nation"] = df["Nation"].astype(str).str.strip()
    return business, turnover, employment, turnover_summary, employment_summary, geo


business_df, turnover_df, employment_df, turnover_summary, employment_summary, base_geojson = load_all_data()

DATASETS = {
    "Business counts": {
        "df": business_df,
        "unit": "enterprises",
        "metric_label": "Creative enterprises",
        "band_label": "SIC activity",
        "bands": None,
        "band_labels": None,
        "description": "Counts of Creative Industries enterprises by detailed SIC activity.",
    },
    "Turnover profile": {
        "df": turnover_df,
        "unit": "enterprises",
        "metric_label": "Enterprises in selected turnover bands",
        "band_label": "Annual turnover band",
        "bands": TURNOVER_ORDER,
        "band_labels": TURNOVER_LABELS,
        "description": "Enterprise counts by annual turnover size band. Values are counts of enterprises, not £ turnover totals.",
    },
    "Employment-size profile": {
        "df": employment_df,
        "unit": "enterprises",
        "metric_label": "Enterprises in selected employment bands",
        "band_label": "Employment size band",
        "bands": EMPLOYMENT_ORDER,
        "band_labels": None,
        "description": "Enterprise counts by employment size band.",
    },
}

# -------------------- Controls --------------------
st.sidebar.markdown("<div class='atlas-kicker'>Creative Industries Atlas</div>", unsafe_allow_html=True)
st.sidebar.title("Explore the map")
st.sidebar.caption("Filter the UK creative economy and click a Local Authority for detail.")

measure_choice = st.sidebar.selectbox("Measure", list(DATASETS.keys()), index=0)
config = DATASETS[measure_choice]
df_all = config["df"]

years = sorted(df_all["Year"].dropna().astype(int).unique())
year_choice = st.sidebar.select_slider("Year", years, value=max(years))

industry_available = [x for x in INDUSTRY_ORDER if x in set(df_all["Industry Group"])]
industry_choice = st.sidebar.multiselect("Creative Industries", industry_available, default=industry_available)

if measure_choice != "Business counts":
    available_bands = [b for b in config["bands"] if b in set(df_all["Description"])]
    band_choice = st.sidebar.multiselect(
        config["band_label"], available_bands, default=available_bands,
        format_func=(lambda x: config["band_labels"].get(x, x)) if config["band_labels"] else str,
    )
else:
    band_choice = None

geography_choice = st.sidebar.selectbox(
    "Geography",
    ["All UK", "One Creative North"] + REGION_ORDER,
    index=0,
)

ocn_choice = None
if geography_choice == "One Creative North":
    ocn_choice = st.sidebar.selectbox("One Creative North area", list(ONE_CREATIVE_NORTH.keys()), index=0)

# -------------------- Filtering --------------------
df = df_all[df_all["Year"] == year_choice].copy()
if industry_choice:
    df = df[df["Industry Group"].isin(industry_choice)]
else:
    df = df.iloc[0:0]

if band_choice is not None:
    df = df[df["Description"].isin(band_choice)] if band_choice else df.iloc[0:0]

if geography_choice == "One Creative North":
    chosen_set = OCN_ALL if ocn_choice == "All One Creative North" else ONE_CREATIVE_NORTH.get(ocn_choice, set())
    df = df[df["Location"].isin(chosen_set)]
elif geography_choice != "All UK":
    df = df[df["Region_1"] == geography_choice]

la_values = (
    df.groupby(["Location", "Region_1", "Nation"], as_index=False)["Value"]
      .sum()
      .rename(columns={"Region_1": "Region"})
)

# -------------------- Map enrichment --------------------
def value_to_color(value, vmax):
    if value is None or pd.isna(value) or value <= 0:
        return NO_DATA_COLOR
    if vmax <= 0:
        return COLOR_STOPS[0] + (210,)
    # sqrt scale preserves local contrast while keeping big-city outliers readable
    t = min(1.0, math.sqrt(float(value) / float(vmax)))
    idx = min(len(COLOR_STOPS) - 1, int(t * (len(COLOR_STOPS) - 1)))
    return list(COLOR_STOPS[idx]) + [215]


def make_map_geojson(base, values):
    lookup = values.set_index("Location").to_dict("index") if not values.empty else {}
    vmax = float(values["Value"].max()) if not values.empty else 0
    allowed = set(values["Location"]) if geography_choice != "All UK" else None
    features = []
    for f in base["features"]:
        name = str(f.get("properties", {}).get("areanm", "")).strip()
        if allowed is not None and name not in allowed:
            continue
        nf = copy.deepcopy(f)
        row = lookup.get(name)
        nf["properties"]["value"] = int(row["Value"]) if row else 0
        nf["properties"]["region"] = row["Region"] if row else ""
        nf["properties"]["nation"] = row["Nation"] if row else ""
        nf["properties"]["fill_color"] = value_to_color(nf["properties"]["value"], vmax)
        features.append(nf)
    return {"type": "FeatureCollection", "features": features}

map_geojson = make_map_geojson(base_geojson, la_values)

# -------------------- Header --------------------
st.markdown("<div class='atlas-kicker'>UK Creative Economy</div>", unsafe_allow_html=True)
st.title("Creative Industries Atlas")
st.markdown(
    f"<div class='atlas-subtitle'>{config['description']} Use the controls to change year, sector and geography, then click a Local Authority on the map.</div>",
    unsafe_allow_html=True,
)

# KPI strip
k1, k2, k3, k4 = st.columns(4)
total_value = int(la_values["Value"].sum()) if not la_values.empty else 0
kpi_data = [
    ("Selected enterprise count", f"{total_value:,}"),
    ("Local Authorities shown", f"{la_values['Location'].nunique():,}"),
    ("Creative sectors", f"{len(industry_choice):,}"),
    ("Year", str(year_choice)),
]
for col, (label, val) in zip((k1, k2, k3, k4), kpi_data):
    col.markdown(f"<div class='metric-card'><div class='metric-label'>{label}</div><div class='metric-value'>{val}</div></div>", unsafe_allow_html=True)

st.write("")

# -------------------- Main map + detail panel --------------------
map_col, detail_col = st.columns([3.3, 1.15], gap="large")

with map_col:
    layer = pdk.Layer(
        "GeoJsonLayer",
        id="local-authorities",
        data=map_geojson,
        pickable=True,
        auto_highlight=True,
        stroked=True,
        filled=True,
        get_fill_color="properties.fill_color",
        get_line_color=BORDER_COLOR,
        line_width_min_pixels=0.7,
        highlight_color=[245, 176, 65, 210],
    )
    view = pdk.ViewState(latitude=54.4, longitude=-3.1, zoom=4.65, min_zoom=3.5, max_zoom=11)
    deck = pdk.Deck(
        layers=[layer],
        initial_view_state=view,
        map_style=None,
        tooltip={
            "html": "<b>{areanm}</b><br/>{region}<br/><b>{value}</b> enterprises",
            "style": {"backgroundColor": "#10242d", "color": "white", "fontSize": "13px"},
        },
    )
    event = st.pydeck_chart(
        deck,
        height=720,
        on_select="rerun",
        selection_mode="single-object",
        key="creative_atlas_map",
    )

# Resolve clicked Local Authority; default to largest visible LA for a useful panel.
selected_name = None
try:
    selected_objects = event.selection.get("objects", {}).get("local-authorities", [])
    if selected_objects:
        obj = selected_objects[0]
        props = obj.get("properties", obj)
        selected_name = props.get("areanm")
except Exception:
    selected_name = None

if not selected_name and not la_values.empty:
    selected_name = la_values.sort_values("Value", ascending=False).iloc[0]["Location"]

with detail_col:
    st.subheader("Area detail")
    if selected_name:
        selected_la = df[df["Location"] == selected_name].copy()
        row = la_values[la_values["Location"] == selected_name]
        total = int(row["Value"].sum()) if not row.empty else 0
        region = row["Region"].iloc[0] if not row.empty else ""
        nation = row["Nation"].iloc[0] if not row.empty else ""
        top_ind = (
            selected_la.groupby("Industry Group")["Value"].sum().sort_values(ascending=False)
            if not selected_la.empty else pd.Series(dtype=float)
        )
        top_ind_name = top_ind.index[0] if len(top_ind) else "—"
        top_ind_val = int(top_ind.iloc[0]) if len(top_ind) else 0
        st.markdown(
            f"""
            <div class="detail-card">
              <div class="detail-title">{selected_name}</div>
              <div class="detail-meta">{region}{' · ' if region and nation else ''}{nation}</div>
              <div class="detail-row"><span>{config['metric_label']}</span><b>{total:,}</b></div>
              <div class="detail-row"><span>Largest selected sector</span><b>{top_ind_name}</b></div>
              <div class="detail-row"><span>Sector count</span><b>{top_ind_val:,}</b></div>
              <div class="detail-row"><span>Year</span><b>{year_choice}</b></div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.write("")
        area_options = sorted(la_values["Location"].unique())
        focus = st.selectbox("Or choose an area", area_options, index=area_options.index(selected_name) if selected_name in area_options else 0)
        if focus != selected_name:
            st.caption("Click the chosen area on the map to update the detail card.")
    else:
        st.info("No Local Authorities match the current filters.")

    st.write("")
    st.download_button(
        "Download filtered data",
        data=df.to_csv(index=False).encode("utf-8"),
        file_name=f"creative_industries_{measure_choice.lower().replace(' ', '_')}_{year_choice}.csv",
        mime="text/csv",
    )
    st.markdown("<div class='small-note'>Map boundaries: LTLA 2025. Historical values are shown against the supplied 2025 boundary geography.</div>", unsafe_allow_html=True)

# -------------------- Charts --------------------
st.divider()
st.subheader("Explore the selected geography")

left, right = st.columns(2, gap="large")
with left:
    industry = df.groupby("Industry Group", as_index=False)["Value"].sum().sort_values("Value", ascending=True)
    fig_ind = px.bar(industry, x="Value", y="Industry Group", orientation="h", labels={"Value": "Enterprises", "Industry Group": ""})
    fig_ind.update_layout(title="Creative Industries composition", height=460, margin=dict(l=0, r=10, t=48, b=20), showlegend=False)
    fig_ind.update_traces(hovertemplate="%{y}<br>%{x:,} enterprises<extra></extra>")
    st.plotly_chart(fig_ind, use_container_width=True)

with right:
    la_rank = la_values.sort_values("Value", ascending=False).head(20).sort_values("Value")
    fig_la = px.bar(la_rank, x="Value", y="Location", orientation="h", labels={"Value": "Enterprises", "Location": ""}, hover_data=["Region", "Nation"])
    fig_la.update_layout(title="Top Local Authorities", height=460, margin=dict(l=0, r=10, t=48, b=20), showlegend=False)
    st.plotly_chart(fig_la, use_container_width=True)

if measure_choice != "Business counts":
    profile = df.groupby("Description", as_index=False)["Value"].sum()
    order = config["bands"]
    profile["order"] = profile["Description"].map({x: i for i, x in enumerate(order)})
    profile = profile.sort_values("order")
    profile["Band"] = profile["Description"].map(config["band_labels"]).fillna(profile["Description"]) if config["band_labels"] else profile["Description"]
    fig_band = px.bar(profile, x="Band", y="Value", labels={"Band": config["band_label"], "Value": "Enterprises"}, text_auto=",.")
    fig_band.update_layout(title=f"{config['band_label']} profile", height=410, margin=dict(l=0, r=10, t=48, b=20))
    st.plotly_chart(fig_band, use_container_width=True)

# Time trend with same sector + geographic filters
trend = df_all.copy()
if industry_choice:
    trend = trend[trend["Industry Group"].isin(industry_choice)]
else:
    trend = trend.iloc[0:0]
if band_choice is not None:
    trend = trend[trend["Description"].isin(band_choice)] if band_choice else trend.iloc[0:0]
if geography_choice == "One Creative North":
    chosen_set = OCN_ALL if ocn_choice == "All One Creative North" else ONE_CREATIVE_NORTH.get(ocn_choice, set())
    trend = trend[trend["Location"].isin(chosen_set)]
elif geography_choice != "All UK":
    trend = trend[trend["Region_1"] == geography_choice]
trend = trend.groupby("Year", as_index=False)["Value"].sum().sort_values("Year")
fig_trend = px.line(trend, x="Year", y="Value", markers=True, labels={"Value": "Enterprises", "Year": "Year"})
fig_trend.add_vline(x=year_choice, line_dash="dot", opacity=.5)
fig_trend.update_layout(title="Trend across all available years", height=390, margin=dict(l=0, r=10, t=48, b=20))
st.plotly_chart(fig_trend, use_container_width=True)

with st.expander("Methodology and data notes"):
    st.markdown(
        """
**Source and structure.** The atlas uses the supplied Nomis-derived Creative Industries datasets for business counts, turnover-size bands and employment-size bands, covering 2010–2025.

**Creative Industries.** The nine supplied Creative Industries groups are retained exactly as provided in the source files.

**Turnover and employment profiles.** These views show **counts of enterprises** in each size band. Turnover-profile values are not monetary turnover totals, and employment-profile values are not employment headcounts.

**Geography.** The map uses the supplied LTLA 2025 boundary file. Historical values are therefore displayed using the supplied 2025 geography rather than attempting to reconstruct historical boundaries.

**One Creative North.** The One Creative North control groups the named northern Local Authorities into the project areas used in the existing atlas workflow. Where historic local-government reorganisations create legacy names, both current and common legacy names are allowed in the filter.

**Rounding.** Nomis business counts may be rounded for disclosure control, so sums of detailed categories can differ slightly from separately published headline totals.
        """
    )

st.caption("Creative Industries Atlas · Streamlit + Pydeck + Plotly")
