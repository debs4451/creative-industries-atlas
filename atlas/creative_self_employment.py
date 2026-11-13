"""Standalone additive page; does not change any existing Creative Industries Atlas indicator."""
import pandas as pd
import plotly.express as px
import streamlit as st

from .config import APP_DIR, OCN_ALL, SOUTH_CENTRAL_CURRENT
from .data import load_geojson
from .geography import canonical_name
from .map_utils import build_deck, enrich_geojson
from .styles import inject_styles

PATH = APP_DIR / "data" / "creative_self_employment_census2021.csv.gz"
COLUMNS = (
    "Employees",
    "Self-employed with employees",
    "Self-employed without employees",
)


@st.cache_data(show_spinner=False)
def _data():
    df = pd.read_csv(PATH, dtype={"SOC Code": str, "Source LA Code": str})
    for name in COLUMNS:
        df[name] = pd.to_numeric(df[name], errors="coerce")
    for name in ["Location", "MapLocation", "Nation", "Region_1", "Occupation", "Creative Occupation Group"]:
        df[name] = df[name].fillna("").astype(str).str.strip()
    # Do not recode missing Census records as zero.
    return df


def _sum_complete(df, field, group_fields):
    """When any selected occupation is absent, do not silently undercount a mapped area."""
    if df.empty:
        return pd.DataFrame(columns=list(group_fields) + ["Value", "Complete"])
    grouped = (df.groupby(list(group_fields), dropna=False)
        .agg(Value=(field, "sum"), Complete=(field, lambda s: bool(s.notna().all())))
        .reset_index())
    grouped.loc[~grouped["Complete"], "Value"] = float("nan")
    return grouped


def _filter_geography(df, kind, label):
    if kind == "Countries":
        if label in ("United Kingdom", "England and Wales"):
            return df
        return df[df["Nation"].eq(label)]
    if kind == "Distinct Areas":
        if label == "South Central":
            allowed = set(SOUTH_CENTRAL_CURRENT)
        elif label == "One Creative North":
            # Include Hull/East Riding in the 11 strategic subareas even when an older
            # Atlas config has only the first ten OCN groups.
            allowed = set(OCN_ALL) | {"Kingston upon Hull, City of", "Kingston upon Hull", "East Riding of Yorkshire"}
        else:
            allowed = set()
        return df[df["MapLocation"].isin(allowed)]
    return df[df["MapLocation"].eq(label)]


def render():
    inject_styles()
    st.markdown("<div class='atlas-kicker'>Creative Industries Atlas · Census 2021</div>", unsafe_allow_html=True)
    st.title("Creative Self-Employment (Census 2021)")
    st.caption("ONS Census 2021 · Creative occupations (SOC 2020) · Local Authority of residence · England and Wales")
    st.info(
        "This measures people in selected **creative occupations**, including people who work "
        "outside SIC-defined Creative Industries. It is different from the workplace-based BRES Employment page."
    )
    try:
        df = _data()
        geo, _ = load_geojson()
    except (OSError, ValueError) as exc:
        st.error(f"Could not load Creative Self-Employment data or map: {exc}")
        st.stop()

    # Three original Census categories are separate and independently selectable.
    measure = st.sidebar.selectbox("Employment category", COLUMNS, key="cse_metric")
    groups = sorted(df["Creative Occupation Group"].unique())
    chosen_groups = st.sidebar.multiselect("Creative occupation groups", groups, default=groups, key="cse_groups")
    # Keep all 28 selected SOC 2020 occupations in the underlying dataset.
    # The occupation-group control remains; there is no individual SOC filter.
    filtered = df[df["Creative Occupation Group"].isin(chosen_groups)].copy()

    st.sidebar.markdown("---")
    st.sidebar.subheader("Geography")
    kind = st.sidebar.selectbox("Geography type", ["Countries", "Distinct Areas", "Local Authorities"], key="cse_geotype")
    if kind == "Countries":
        options_geo = ["United Kingdom", "England", "Scotland", "Wales", "Northern Ireland"]
    elif kind == "Distinct Areas":
        options_geo = ["One Creative North", "South Central"]
    else:
        options_geo = sorted(filtered["MapLocation"].dropna().unique())
    if not options_geo:
        st.warning("No data match the selected creative occupation groups.")
        st.stop()
    geo_choice = st.sidebar.selectbox("Area", options_geo, key="cse_area")
    selected = _filter_geography(filtered, kind, geo_choice)

    if kind == "Countries" and geo_choice == "United Kingdom":
        st.warning("**Geographic coverage:** the Census extract contains England and Wales only. Scotland and Northern Ireland are not included in this UK selection.")
    elif kind == "Countries" and geo_choice in ["Scotland", "Northern Ireland"]:
        st.warning(f"No {geo_choice} observations are included in this Census 2021 England and Wales dataset. This is missing coverage, not zero self-employment.")
        st.stop()
    if selected.empty:
        st.warning("No observations match this selection.")
        st.stop()

    # Build the LA map for the one requested category; no invented total or rate columns.
    by_la = _sum_complete(selected, measure, ["MapLocation", "Region_1", "Nation"])
    by_la = by_la.rename(columns={"Region_1": "Region"})
    by_la["MapLocation"] = by_la["MapLocation"].map(canonical_name)

    st.subheader(measure)
    total = by_la["Value"].sum(min_count=1)
    valid_las = int(by_la["Value"].notna().sum())
    missing_las = int(by_la["Value"].isna().sum())
    c1,c2,c3 = st.columns(3)
    c1.metric(measure, f"{total:,.0f}" if pd.notna(total) else "Not available")
    c2.metric("Local authorities with complete data", f"{valid_las:,}")
    c3.metric("Incomplete local authority totals", f"{missing_las:,}")
    if missing_las:
        st.caption("Where any selected SOC occupation is absent in the source, the area's complete aggregate is left missing rather than counted as zero.")

    map_json = enrich_geojson(geo, by_la, 2021, f"{kind}: {geo_choice}", measure)
    left,right = st.columns([3.2,1.3], gap="large")
    with left:
        st.pydeck_chart(build_deck(map_json, measure), height=680, key="cse_map")
    with right:
        st.markdown("**Local Authority comparison**")
        top = by_la.dropna(subset=["Value"]).nlargest(12,"Value").sort_values("Value")
        if len(top):
            fig = px.bar(top, x="Value", y="MapLocation", orientation="h", labels={"Value":measure,"MapLocation":""}, height=470)
            fig.update_layout(margin=dict(l=8,r=10,t=10,b=8),showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.caption("No complete local authority totals for this selection.")

    st.subheader("By creative occupation")
    by_soc = _sum_complete(selected, measure, ["SOC Code", "Occupation", "Creative Occupation Group"])
    by_soc["SOC"] = by_soc["SOC Code"] + " · " + by_soc["Occupation"]
    fig = px.bar(by_soc.dropna(subset=["Value"]).sort_values("Value",ascending=False), x="SOC", y="Value", color="Creative Occupation Group", labels={"Value":measure, "SOC":"Occupation (SOC 2020)"})
    fig.update_layout(xaxis_tickangle=-45,margin=dict(l=8,r=8,t=8,b=20),legend_title_text="Creative occupation group")
    st.plotly_chart(fig, use_container_width=True)

    with st.expander("Source and methodology"):
        st.markdown(
            "**Source:** ONS Census 2021 commissioned table **CT21_0217**, occupation (SOC 2020, 4 digit) × selected economic activity status × lower-tier Local Authority. "
            "Counts are for residents aged 16+ who were employed the week before the Census. The three status categories are retained verbatim. "
            "The SOC selection is documented in `data/creative_soc2020_selection.csv` and includes 28 selected creative unit groups; "
            "it should **not** be presented as a full SIC-defined Creative Industries workforce. "
            "2021 LA values are aggregated onto current Atlas map boundaries only where councils have reorganised. "
            "This dataset is residence-based; the separately available 2011 workplace-based table has not been combined into a misleading time series. "
            "Small cells are subject to Census statistical disclosure control; the sum of LA figures may differ slightly from national figures. "
            "No England/Wales observations are available for Scotland or Northern Ireland. "
            "[ONS table](https://www.ons.gov.uk/peoplepopulationandcommunity/populationandmigration/populationestimates/adhocs/1941ct210217census2021) · "
            "[DCMS SOC 2020 update](https://www.gov.uk/government/statistics/economic-estimates-employment-january-2025-to-december-2025-for-dcms-sectors/dcms-sectors-economic-estimates-creative-occupations-update-note)"
        )
