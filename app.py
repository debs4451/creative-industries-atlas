from pathlib import Path
import json
import pandas as pd
import plotly.express as px
import streamlit as st

APP_DIR = Path(__file__).resolve().parent
DATA_DIR = APP_DIR / "data"

st.set_page_config(
    page_title="Creative Industries Atlas — England, 2025",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

REGION_ORDER = [
    "North East", "North West", "Yorkshire and the Humber", "East Midlands",
    "West Midlands", "East of England", "London", "South East", "South West"
]

EMPLOYMENT_BANDS = ["0 to 4", "5 to 9", "10 to 19", "20 to 49", "50 to 99", "100 to 249", "250 to 499", "500 to 999", "1000+"]
TURNOVER_ORDER = [
    "0 to 49 (thousand)", "50 to 99  (thousand)", "100 to 249 (thousand)",
    "250 to 499 (thousand)", "500 to 999 (thousand)", "1000 to 1999 (thousand)",
    "2000 to 4999 (thousand)", "5000 to 9999 (thousand)",
    "10000 to 49999 (thousand)", "50000+ (thousand)"
]
TURNOVER_LABELS = {
    "0 to 49 (thousand)": "£0–£49k",
    "50 to 99  (thousand)": "£50k–£99k",
    "100 to 249 (thousand)": "£100k–£249k",
    "250 to 499 (thousand)": "£250k–£499k",
    "500 to 999 (thousand)": "£500k–£999k",
    "1000 to 1999 (thousand)": "£1m–£1.999m",
    "2000 to 4999 (thousand)": "£2m–£4.999m",
    "5000 to 9999 (thousand)": "£5m–£9.999m",
    "10000 to 49999 (thousand)": "£10m–£49.999m",
    "50000+ (thousand)": "£50m+",
}

DATASET_CONFIG = {
    "Business Counts": {
        "icon": "🏢",
        "fact": "business_counts_fact_long_2025.csv",
        "totals": "business_counts_la_totals_2025.csv",
        "title": "Creative Industries Business Counts",
        "caption": "Counts of Creative Industries enterprises by Local Authority District and English region.",
        "profile_title": "Business activity profile",
        "profile_x": "Enterprises",
        "filter_label": "Business activity (SIC 2007)",
        "download": "creative_industries_business_counts_2025_long.csv",
    },
    "Employment Size Bands": {
        "icon": "👥",
        "fact": "employment_bands_fact_long_2025.csv",
        "totals": "employment_bands_la_totals_2025.csv",
        "title": "Creative Industries Enterprise Employment Size Profile",
        "caption": "Counts of Creative Industries enterprises by employment size band, Local Authority District and English region.",
        "profile_title": "Employment size-band profile",
        "profile_x": "Enterprises",
        "filter_label": "Employment size band",
        "download": "creative_industries_employment_bands_2025_long.csv",
    },
    "Enterprise Turnover": {
        "icon": "💷",
        "fact": "turnover_fact_long_2025.csv",
        "totals": "turnover_la_totals_2025.csv",
        "title": "Creative Industries Enterprise Turnover Profile",
        "caption": "Counts of Creative Industries enterprises by annual turnover size band, Local Authority District and English region. Values are enterprise counts, not monetary turnover totals.",
        "profile_title": "Turnover size-band profile",
        "profile_x": "Enterprises",
        "filter_label": "Turnover size band",
        "download": "creative_industries_turnover_2025_long.csv",
    },
}

@st.cache_data
def load_geojson():
    with open(DATA_DIR / "england_lads_2024.geojson", "r", encoding="utf-8") as f:
        return json.load(f)

@st.cache_data
def load_dataset(dataset_name):
    cfg = DATASET_CONFIG[dataset_name]
    la = pd.read_csv(DATA_DIR / cfg["totals"])
    fact = pd.read_csv(DATA_DIR / cfg["fact"])
    region_map = la.set_index("Region")["Region_1"].to_dict()
    fact["Region_1"] = fact["Location"].map(region_map)
    return la, fact

geojson = load_geojson()

st.markdown("""
<style>
.block-container {padding-top: 1rem; padding-bottom: 2rem; max-width: 1500px;}
[data-testid="stMetric"] {border: 1px solid rgba(128,128,128,.25); border-radius: 10px; padding: 10px 14px;}
.atlas-note {font-size: .9rem; opacity: .78;}
</style>
""", unsafe_allow_html=True)

# -------------------- Sidebar / global navigation --------------------
st.sidebar.title("Creative Industries Atlas")
dataset_name = st.sidebar.radio(
    "Dataset",
    list(DATASET_CONFIG.keys()),
    help="Switch between the three 2025 Nomis views within the same website."
)
cfg = DATASET_CONFIG[dataset_name]
la_totals, fact = load_dataset(dataset_name)

if "region_choice" not in st.session_state:
    st.session_state.region_choice = "All England"

st.sidebar.divider()
st.sidebar.subheader("Explore")
region_options = ["All England"] + REGION_ORDER
# Keep state valid when switching datasets.
if st.session_state.region_choice not in region_options:
    st.session_state.region_choice = "All England"
region_choice = st.sidebar.selectbox(
    "Region",
    region_options,
    index=region_options.index(st.session_state.region_choice),
    key="region_select"
)
st.session_state.region_choice = region_choice

industries = sorted(fact["Industry Group"].dropna().unique())
industry_choice = st.sidebar.multiselect("Creative Industries", industries, default=industries)

if dataset_name == "Business Counts":
    secondary_options = sorted(fact["Description"].dropna().unique())
    secondary_choice = st.sidebar.multiselect(cfg["filter_label"], secondary_options, default=secondary_options)
    secondary_col = "Description"
elif dataset_name == "Employment Size Bands":
    fact["Employment Size Band"] = fact["Description"]
    secondary_options = [x for x in EMPLOYMENT_BANDS if x in set(fact["Employment Size Band"])]
    secondary_choice = st.sidebar.multiselect(cfg["filter_label"], secondary_options, default=secondary_options)
    secondary_col = "Employment Size Band"
else:
    fact["Turnover Band"] = fact["Description"]
    secondary_options = [x for x in TURNOVER_ORDER if x in set(fact["Turnover Band"])]
    secondary_choice = st.sidebar.multiselect(
        cfg["filter_label"], secondary_options, default=secondary_options,
        format_func=lambda x: TURNOVER_LABELS.get(x, x)
    )
    secondary_col = "Turnover Band"

if region_choice == "All England":
    la_options = sorted(fact["Location"].dropna().unique())
else:
    la_options = sorted(fact.loc[fact["Region_1"] == region_choice, "Location"].dropna().unique())
la_choice = st.sidebar.multiselect("Local Authority", la_options, default=[])

st.sidebar.divider()
source_export = fact.drop(columns=[c for c in ["Region_1", "Employment Size Band", "Turnover Band"] if c in fact.columns])
st.sidebar.download_button(
    "Download source long data (CSV)",
    data=source_export.to_csv(index=False).encode("utf-8"),
    file_name=cfg["download"],
    mime="text/csv"
)

# -------------------- Header --------------------
st.title(f"{cfg['icon']} {cfg['title']} — England, 2025")
st.caption(cfg["caption"])
st.markdown(
    "Use the dataset selector in the sidebar to move between **Business Counts**, **Employment Size Bands**, and **Enterprise Turnover** without leaving the website."
)

# -------------------- Filtering --------------------
filtered = fact.copy()
if region_choice != "All England":
    filtered = filtered[filtered["Region_1"] == region_choice]
filtered = filtered[filtered["Industry Group"].isin(industry_choice)] if industry_choice else filtered.iloc[0:0]
filtered = filtered[filtered[secondary_col].isin(secondary_choice)] if secondary_choice else filtered.iloc[0:0]
if la_choice:
    filtered = filtered[filtered["Location"].isin(la_choice)]

la_filtered = filtered.groupby(["Location", "Region_1"], as_index=False)["Value"].sum()

# -------------------- Region navigation --------------------
st.subheader("Region navigation")
st.caption("Select a region from the sidebar for detailed analysis. Headline region totals use the published Total enterprise figures.")
nav_cols = st.columns(3)
for i, region in enumerate(REGION_ORDER):
    total = int(la_totals.loc[la_totals["Region_1"] == region, "Enterprise Count"].sum())
    nav_cols[i % 3].metric(region, f"{total:,} enterprises")

# -------------------- KPIs --------------------
st.subheader(region_choice if region_choice != "All England" else "England overview")
c1, c2, c3, c4 = st.columns(4)
# When all dimensions are selected, use published Total to avoid disclosure-rounding mismatch.
all_industries = len(industry_choice) == len(industries)
all_secondary = len(secondary_choice) == len(secondary_options)
no_la_filter = len(la_choice) == 0
if all_industries and all_secondary and no_la_filter:
    if region_choice == "All England":
        headline = int(la_totals["Enterprise Count"].sum())
    else:
        headline = int(la_totals.loc[la_totals["Region_1"] == region_choice, "Enterprise Count"].sum())
else:
    headline = int(filtered["Value"].sum())

c1.metric("Selected enterprise count", f"{headline:,}")
c2.metric("Local authorities shown", f"{la_filtered['Location'].nunique():,}")
c3.metric("Creative Industries selected", f"{len(industry_choice):,}")
c4.metric(cfg["filter_label"] + " selected", f"{len(secondary_choice):,}")

# -------------------- Map --------------------
st.subheader("Enterprise distribution by Local Authority")
if not la_filtered.empty:
    fig_map = px.choropleth(
        la_filtered,
        geojson=geojson,
        locations="Location",
        featureidkey="properties.LAD24NM",
        color="Value",
        hover_name="Location",
        hover_data={"Region_1": True, "Value": ":,", "Location": False},
        labels={"Value": "Enterprises", "Region_1": "Region"},
    )
    fig_map.update_geos(fitbounds="locations", visible=False)
    fig_map.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=620, coloraxis_colorbar_title="Enterprises")
    st.plotly_chart(fig_map, use_container_width=True)
else:
    st.info("No data match the current filters.")

# -------------------- Core charts --------------------
left, right = st.columns(2)
with left:
    st.subheader("Local Authority comparison")
    rank = la_filtered.sort_values("Value", ascending=False).head(25)
    if not rank.empty:
        fig_la = px.bar(
            rank.sort_values("Value"), x="Value", y="Location", orientation="h",
            labels={"Value": "Enterprises", "Location": "Local Authority"}
        )
        fig_la.update_layout(height=max(450, 23 * len(rank)), margin=dict(l=0, r=0, t=10, b=0))
        st.plotly_chart(fig_la, use_container_width=True)

with right:
    st.subheader("Creative Industries composition")
    industry = filtered.groupby("Industry Group", as_index=False)["Value"].sum().sort_values("Value", ascending=False)
    if not industry.empty:
        fig_ind = px.bar(
            industry, x="Value", y="Industry Group", orientation="h",
            labels={"Value": "Enterprises", "Industry Group": "Creative Industries group"}
        )
        fig_ind.update_layout(height=500, margin=dict(l=0, r=0, t=10, b=0), yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(fig_ind, use_container_width=True)

# -------------------- Dataset-specific profile --------------------
st.subheader(cfg["profile_title"])
if dataset_name == "Business Counts":
    profile = filtered.groupby("Description", as_index=False)["Value"].sum().sort_values("Value", ascending=False).head(25)
    if not profile.empty:
        fig = px.bar(
            profile.sort_values("Value"), x="Value", y="Description", orientation="h",
            labels={"Value": "Enterprises", "Description": "SIC 2007 business activity"}
        )
        fig.update_layout(height=max(500, 22 * len(profile)), margin=dict(l=0, r=0, t=10, b=0))
        st.plotly_chart(fig, use_container_width=True)

elif dataset_name == "Employment Size Bands":
    profile = filtered.groupby("Employment Size Band", as_index=False)["Value"].sum()
    profile["order"] = profile["Employment Size Band"].map({b: i for i, b in enumerate(EMPLOYMENT_BANDS)})
    profile = profile.sort_values("order")
    if not profile.empty:
        fig = px.bar(
            profile, x="Employment Size Band", y="Value",
            labels={"Employment Size Band": "Enterprise employment size band", "Value": "Enterprises"}, text_auto=","
        )
        fig.update_layout(height=440, margin=dict(l=0, r=0, t=10, b=0))
        st.plotly_chart(fig, use_container_width=True)

else:
    profile = filtered.groupby("Turnover Band", as_index=False)["Value"].sum()
    profile["order"] = profile["Turnover Band"].map({b: i for i, b in enumerate(TURNOVER_ORDER)})
    profile["Turnover"] = profile["Turnover Band"].map(TURNOVER_LABELS)
    profile = profile.sort_values("order")
    if not profile.empty:
        fig = px.bar(
            profile, x="Turnover", y="Value",
            labels={"Turnover": "Annual turnover size band", "Value": "Enterprises"}, text_auto=","
        )
        fig.update_layout(height=440, margin=dict(l=0, r=0, t=10, b=0))
        st.plotly_chart(fig, use_container_width=True)

# -------------------- Regional summary --------------------
st.subheader("Regional summary")
summary = (
    la_totals.groupby("Region_1", as_index=False)["Enterprise Count"].sum()
    .rename(columns={"Region_1": "Region", "Enterprise Count": "Enterprises"})
)
summary["Region"] = pd.Categorical(summary["Region"], REGION_ORDER, ordered=True)
summary = summary.sort_values("Region")
st.dataframe(summary, use_container_width=True, hide_index=True)

if dataset_name in ["Employment Size Bands", "Enterprise Turnover"]:
    st.caption("Region navigation and Regional summary use the published Total enterprise counts. Detailed band charts use rounded banded data, so their sums may differ slightly from published totals.")
else:
    st.caption("Regional summary uses the same headline enterprise totals as Region navigation.")

# -------------------- Notes --------------------
with st.expander("Methodology and notes", expanded=False):
    if dataset_name == "Business Counts":
        st.markdown("""
**Source:** Nomis, *UK Business Counts – enterprises by industry and employment size band*, 2025, with employment size band set to **Total**.

**Measure:** Values are counts of **enterprises**. An enterprise is the overall business organisation and may operate from more than one local unit/workplace.

**Creative Industries:** Selected SIC 2007 activities are grouped into the Creative Industries categories used in this project.

**Geography:** England only — 296 Local Authority Districts across the nine English regions.

**Rounding:** Nomis rounds business-count figures to reduce disclosure risk. Some values may be rounded down to zero and totals created from detailed SIC values can differ slightly from separately published totals.
        """)
    elif dataset_name == "Employment Size Bands":
        st.markdown("""
**Source:** Nomis, *UK Business Counts – enterprises by industry and employment size band*, 2025.

**Measure:** Values are counts of **enterprises** falling within each employment size band. The bands refer to enterprise employment size, not the number of Creative Industries workers resident in the area.

**Enterprise:** An enterprise is the overall business organisation and may operate from more than one local unit/workplace.

**Creative Industries:** Selected SIC 2007 activities are grouped into the Creative Industries categories used in this project.

**Geography:** England only — 296 Local Authority Districts across the nine English regions.

**Headline totals:** Region navigation and Regional summary use the published Total enterprise counts. Detailed employment-band values are rounded by Nomis for disclosure, so summing the bands may not reproduce the published Total exactly.
        """)
    else:
        st.markdown("""
**Source:** Nomis, *UK Business Counts – enterprises by industry and turnover size band*, 2025.

**Measure:** Each value is a **count of enterprises** falling within a turnover-size category. It is **not the value of turnover in pounds**.

**Enterprise:** An enterprise is the overall business organisation and can operate from more than one local unit/workplace.

**Creative Industries:** The dataset uses 31 DCMS SIC 2007 codes grouped into nine Creative Industries categories.

**Geography:** England only — 296 Local Authority Districts across the nine English regions.

**Legal status:** Total, so both private- and public-sector enterprises are included.

**Headline totals:** Region navigation and Regional summary use the separately published Nomis **Total** enterprise counts. Detailed turnover-band values are rounded for disclosure and therefore may not sum exactly to the published Total.
        """)

st.caption("Creative Industries Atlas — England, 2025. Source: Nomis. Boundary geography: Local Authority Districts, May 2024.")
