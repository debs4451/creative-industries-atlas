"""Creative Workforce by Age — Census 2021 (ONS CT21_0332).

Standalone/additive Atlas page. Works with the original Atlas map utilities.
Workplace geography, England and Wales only. Creative occupations = selected
SOC 2020 4-digit codes, not SIC-defined Creative Industries employees.
"""

from pathlib import Path
import pandas as pd
import plotly.express as px
import streamlit as st

from .config import APP_DIR, OCN_ALL, SOUTH_CENTRAL_CURRENT
from .data import load_geojson
from .geography import canonical_name
from .map_utils import enrich_geojson, build_deck
from .styles import inject_styles

DATA_FILE = APP_DIR / "data" / "creative_workforce_age_census2021.csv.gz"

# Original ONS CT21_0332 bands. Preserve counts exactly as published.
AGE_BANDS = [
    "Aged 16 to 19 years", "Aged 20 to 24 years", "Aged 25 to 29 years",
    "Aged 30 to 34 years", "Aged 35 to 39 years", "Aged 40 to 44 years",
    "Aged 45 to 49 years", "Aged 50 to 54 years", "Aged 55 to 59 years",
    "Aged 60 to 64 years", "Aged 65 to 69 years", "Aged 70 to 74 years",
    "Aged 75 years or over",
]
MEASURES = ["Total workers"] + AGE_BANDS

# The published source merges these two pairs of local authorities.
MERGED_AREAS_NOTE = (
    "ONS combines **Westminster + City of London** and **Cornwall + Isles of Scilly** "
    "in this workplace table. Their totals cannot be split into the constituent "
    "authorities using this release. On the current-boundary map, the combined "
    "figures are shown against Westminster and Cornwall, respectively."
)


@st.cache_data(show_spinner=False)
def _load_age():
    df = pd.read_csv(
        DATA_FILE,
        dtype={"SOC Code": str, "Source LA Code": str},
    )
    required = {
        "Year", "Source LA Code", "Location", "MapLocation", "Nation",
        "Region_1", "SOC Code", "Occupation", "Creative Occupation Group",
        *MEASURES,
    }
    absent = required.difference(df.columns)
    if absent:
        raise ValueError("Missing Census age fields: " + ", ".join(sorted(absent)))

    for col in MEASURES:
        # Empty ONS rows remain missing, NEVER filled with zero.
        df[col] = pd.to_numeric(df[col], errors="coerce")
    for col in ["Location", "MapLocation", "Nation", "Region_1", "Occupation", "Creative Occupation Group"]:
        df[col] = df[col].fillna("").astype(str).str.strip()
    if not df["Year"].eq(2021).all():
        raise ValueError("This page requires Census 2021 data only.")
    return df


def _select_geography(data, kind, selection):
    if kind == "Countries":
        if selection == "United Kingdom":
            return data  # England and Wales ONLY; a prominent warning follows.
        return data[data["Nation"].eq(selection)]
    if kind == "Distinct Areas":
        if selection == "South Central":
            allowed = {canonical_name(x) for x in SOUTH_CENTRAL_CURRENT}
        elif selection == "One Creative North":
            # Older Atlas config omitted the Hull & East Yorkshire OCN grouping.
            allowed = {canonical_name(x) for x in OCN_ALL} | {
                "Kingston upon Hull", "Kingston upon Hull, City of", "East Riding of Yorkshire"
            }
        else:
            allowed = set()
        return data[data["MapLocation"].map(canonical_name).isin(allowed)]
    return data[data["MapLocation"].map(canonical_name).eq(canonical_name(selection))]


def _aggregate_by_la(df, measure):
    if df.empty:
        return pd.DataFrame(columns=["MapLocation", "Region", "Nation", "Value", "Complete"])
    by_la = (
        df.groupby("MapLocation", dropna=False)
        .agg(
            Value=(measure, lambda s: s.sum(min_count=1)),
            Complete=(measure, lambda s: bool(s.notna().all())),
            Region=("Region_1", "first"),
            Nation=("Nation", "first"),
        )
        .reset_index()
    )
    # If any selected SOC occupation is absent, do not display a partial total
    # as a complete LA creative workforce count.
    by_la.loc[~by_la["Complete"], "Value"] = float("nan")
    by_la["MapLocation"] = by_la["MapLocation"].map(canonical_name)
    return by_la


def _make_age_profile(complete_rows):
    """Age composition for the same complete mapped LAs used in the choropleth."""
    if complete_rows.empty:
        return pd.DataFrame(columns=["Age band", "Workers", "Share (%)"])
    counts = complete_rows[AGE_BANDS].sum(min_count=1)
    total = counts.sum(min_count=1)
    return pd.DataFrame({
        "Age band": [x.replace("Aged ", "").replace(" years", "") for x in AGE_BANDS],
        "Workers": counts.to_numpy(),
        "Share (%)": (counts / total * 100).to_numpy() if pd.notna(total) and total > 0 else [float("nan")] * len(AGE_BANDS),
    })


def render():
    inject_styles()
    st.markdown("<div class='atlas-kicker'>Creative Industries Atlas · Census 2021</div>", unsafe_allow_html=True)
    st.title("Creative Workforce by Age")
    st.caption("ONS Census 2021 · CT21_0332 · SOC 2020 (4 digits) · **workplace** Local Authorities · England and Wales")
    st.info(
        "This page shows people working in **selected creative occupations**, including those employed outside "
        "SIC-defined Creative Industries. It uses **workplace** geography, unlike the residence-based "
        "Creative Self-Employment Census page."
    )

    try:
        data = _load_age()
        geojson, _ = load_geojson()
    except (OSError, ValueError, KeyError) as exc:
        st.error(f"Could not load the creative workforce age data or boundaries: {exc}")
        st.stop()

    # Mirror the control layout of the existing creative self-employment page.
    measure = st.sidebar.selectbox("Age category", MEASURES, key="cwa_age_category")
    groups = sorted(data["Creative Occupation Group"].unique())
    chosen_groups = st.sidebar.multiselect(
        "Creative occupation groups", groups, default=groups, key="cwa_groups",
    )
    # Keep all 28 selected SOC 2020 occupations in the underlying dataset.
    # The occupation-group control remains; there is no individual SOC filter.
    filtered = data[data["Creative Occupation Group"].isin(chosen_groups)].copy()
    if filtered.empty:
        st.warning("Select at least one creative occupation group.")
        st.stop()

    st.sidebar.markdown("---")
    st.sidebar.subheader("Geography")
    geo_type = st.sidebar.selectbox(
        "Geography type", ["Countries", "Distinct Areas", "Local Authorities"], key="cwa_geo_type",
    )
    if geo_type == "Countries":
        geo_choices = ["United Kingdom", "England", "Scotland", "Wales", "Northern Ireland"]
    elif geo_type == "Distinct Areas":
        geo_choices = ["One Creative North", "South Central"]
    else:
        geo_choices = sorted(filtered["MapLocation"].dropna().unique())
    geo_selection = st.sidebar.selectbox("Area", geo_choices, key="cwa_area")

    if geo_type == "Countries" and geo_selection in {"Scotland", "Northern Ireland"}:
        st.warning(
            f"No {geo_selection} workplace observations are available in this England-and-Wales "
            "Census 2021 table. Missing coverage does not mean zero creative employment."
        )
        st.stop()
    if geo_type == "Countries" and geo_selection == "United Kingdom":
        st.warning(
            "This **United Kingdom** selection displays **England and Wales only**, because "
            "CT21_0332 has no LA-level workplace observations for Scotland or Northern Ireland. "
            "It is not a UK workforce total."
        )

    selected = _select_geography(filtered, geo_type, geo_selection)
    if selected.empty:
        st.warning("No observations match the selected geography and occupations.")
        st.stop()

    by_la = _aggregate_by_la(selected, measure)
    good = by_la.loc[by_la["Complete"], "MapLocation"]
    complete_rows = selected[selected["MapLocation"].isin(good)].copy()

    st.subheader(f"{measure} · Creative occupations")
    total = by_la["Value"].sum(min_count=1)
    complete_count = int(by_la["Complete"].sum())
    incomplete_count = int((~by_la["Complete"]).sum())
    a, b, c = st.columns(3)
    a.metric("Sum across complete LAs", f"{total:,.0f}" if pd.notna(total) else "Not available")
    b.metric("Local authorities with complete data", f"{complete_count:,}")
    c.metric("LAs with missing occupation values", f"{incomplete_count:,}")
    if incomplete_count:
        st.caption(
            "Some source occupation-by-LA combinations were not published. Those mapped LA totals "
            "are shown as missing rather than treating the omitted records as zero; the headline "
            "subtotal excludes incomplete areas."
        )

    map_data = enrich_geojson(
        geojson, by_la[["MapLocation", "Region", "Nation", "Value"]],
        2021, f"{geo_type}: {geo_selection}", measure, zero_is_data=True,
    )
    left, right = st.columns([3.1, 1.4], gap="large")
    with left:
        st.pydeck_chart(build_deck(map_data, measure), height=650, key="cwa_map")
    with right:
        st.markdown("**Local Authority comparison**")
        top = by_la.dropna(subset=["Value"]).nlargest(12, "Value").sort_values("Value")
        if top.empty:
            st.caption("No complete Local Authority observations for this selection.")
        else:
            fig = px.bar(
                top, x="Value", y="MapLocation", orientation="h",
                labels={"Value": "Workers", "MapLocation": ""},
                height=475,
            )
            fig.update_layout(margin=dict(l=8, r=8, t=10, b=10), showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

    st.subheader("Age composition of the selected creative workforce")
    st.caption(
        "The age chart uses the same fully observed Local Authorities as the map. "
        "Age categories are kept exactly as reported in ONS Census 2021."
    )
    profile = _make_age_profile(complete_rows)
    if not profile.empty:
        fig = px.bar(
            profile, x="Age band", y="Workers",
            hover_data={"Share (%)": ":.1f"},
            labels={"Age band": "Age", "Workers": "Creative workers"},
        )
        fig.update_layout(margin=dict(l=8, r=8, t=8, b=8), showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.caption("No complete age observations for this selection.")

    st.subheader("Creative workers by occupation group")
    if not complete_rows.empty:
        grouped = (
            complete_rows.groupby("Creative Occupation Group", as_index=False)[measure]
            .sum().rename(columns={measure: "Workers"})
            .sort_values("Workers", ascending=False)
        )
        fig2 = px.bar(
            grouped, x="Creative Occupation Group", y="Workers",
            labels={"Creative Occupation Group": "Occupation group"},
            height=420,
        )
        fig2.update_layout(margin=dict(l=8, r=8, t=8, b=10), xaxis_tickangle=-25)
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.caption("No complete occupation group observations for this selection.")

    with st.expander("Source and methodology"):
        st.markdown(
            "**Source:** ONS Census 2021, commissioned table **CT21_0332**, "
            "*Workplace table: occupation (4 digits) by age*, lower-tier Local Authorities "
            "(merged), England and Wales. The population is usual residents aged 16 or over "
            "in employment in the week before Census day (21 March 2021). "
            "[Official ONS table](https://www.ons.gov.uk/peoplepopulationandcommunity/populationandmigration/populationestimates/adhocs/2330ct210332census2021). "
            "\n\n**Occupation definition:** 28 selected creative 4-digit SOC 2020 occupations, "
            "matching the Atlas's Creative Self-Employment page. This is an occupational definition, "
            "**not** the 31 SIC-defined Creative Industries or a complete official DCMS "
            "creative-workforce total. The list is in `data/creative_soc2020_selection.csv`. "
            "\n\n**Geographical treatment:** The original source uses **workplace** Local Authority "
            "and the Atlas displays today's boundaries. " + MERGED_AREAS_NOTE +
            " Historical administrative changes are harmonised only for mapping and aggregation. "
            "Scotland and Northern Ireland LA data are not available in this extract. "
            "\n\n**Missing data and comparability:** Five occupation-by-LA records are absent in "
            "the ONS worksheet and remain missing. Census disclosure controls perturb small counts, "
            "so exact additivity is not guaranteed across published tables. "
            "We have not calculated a 2011–2021 trend: the available 2011 files use an earlier "
            "SOC classification and do not provide a directly harmonised age-by-occupation comparison. "
            "This 2021 age indicator is **workplace-based** and should not be directly compared "
            "with the residence-based Creative Self-Employment indicator."
        )
