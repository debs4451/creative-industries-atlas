import html
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from .config import DATASETS, INDUSTRY_ORDER
from .data import load_dataset, load_geojson
from .geography import (
    aggregate_for_map,
    filter_geography,
    geography_options,
)
from .map_utils import build_deck, enrich_geojson


def inject_styles():
    st.markdown(
        """
        <style>
        .block-container {
            padding: 1rem 1.35rem 2.5rem 1.35rem;
            max-width: 1800px;
        }
        [data-testid="stSidebar"] {
            border-right: 1px solid #dde3e7;
        }
        [data-testid="stSidebar"] .block-container {
            padding-top: 1rem;
        }
        h1 {
            font-size: 2.0rem !important;
            letter-spacing: -.02em;
            margin-bottom: .15rem !important;
        }
        h2, h3 { letter-spacing: -.01em; }
        .atlas-kicker {
            font-size:.76rem;
            text-transform:uppercase;
            letter-spacing:.12em;
            font-weight:700;
            color:#50616a;
            margin-bottom:.15rem;
        }
        .atlas-subtitle {
            font-size:1rem;
            color:#53636c;
            margin-bottom:1rem;
            max-width:950px;
        }
        .metric-card {
            border:1px solid #dfe5e8;
            border-radius:12px;
            padding:14px 16px;
            background:#fff;
            min-height:92px;
        }
        .metric-label {
            font-size:.76rem;
            text-transform:uppercase;
            letter-spacing:.06em;
            color:#66747c;
        }
        .metric-value {
            font-size:1.55rem;
            font-weight:700;
            color:#12262f;
            margin-top:2px;
        }
        .detail-card {
            border:1px solid #dfe5e8;
            border-radius:14px;
            padding:16px 18px;
            background:#fff;
        }
        .detail-title {
            font-size:1.2rem;
            font-weight:700;
            color:#12262f;
            margin-bottom:.15rem;
        }
        .detail-meta {
            font-size:.88rem;
            color:#61717a;
            margin-bottom:.85rem;
        }
        .detail-row {
            display:flex;
            justify-content:space-between;
            gap:18px;
            padding:8px 0;
            border-top:1px solid #edf0f2;
            font-size:.92rem;
        }
        .detail-row b { color:#12262f; }
        .small-note { font-size:.82rem; color:#6b7880; }
        div[data-testid="stDownloadButton"] button { width:100%; }
        .stPlotlyChart {
            border:1px solid #edf0f2;
            border-radius:12px;
            overflow:hidden;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _data_error_page(config, exc):
    st.markdown(
        "<div class='atlas-kicker'>Creative Industries Atlas</div>",
        unsafe_allow_html=True,
    )
    st.title(config["page_title"])
    st.warning(str(exc))


def _available_industries(df):
    present = set(df["Industry Group"].dropna().astype(str))
    ordered = [x for x in INDUSTRY_ORDER if x in present]
    extras = sorted(
        x for x in present
        if x and x not in ordered and x.lower() not in {"nan", "none"}
    )
    return ordered + extras


def _base_filter_controls(df, config):
    years = sorted(df["Year"].dropna().astype(int).unique())
    if not years:
        st.error("No valid years were found in this dataset.")
        st.stop()

    year = st.sidebar.select_slider("Year", years, value=max(years))

    industries = _available_industries(df)
    default_industries = industries.copy()
    industry_choice = st.sidebar.multiselect(
        "Creative Industries",
        industries,
        default=default_industries,
    )

    band_choice = None
    if config["bands"]:
        available = [
            b for b in config["bands"]
            if b in set(df["Description"].dropna().astype(str))
        ]
        band_choice = st.sidebar.multiselect(
            config["band_label"],
            available,
            default=available,
            format_func=(
                (lambda x: config["band_labels"].get(x, x))
                if config["band_labels"]
                else str
            ),
        )

    return year, industry_choice, band_choice


def _filter_before_geography(df, year, industry_choice, band_choice):
    out = df[df["Year"].astype("Int64") == int(year)].copy()

    if industry_choice:
        out = out[out["Industry Group"].isin(industry_choice)]
    else:
        out = out.iloc[0:0]

    if band_choice is not None:
        out = out[out["Description"].isin(band_choice)] if band_choice else out.iloc[0:0]

    return out


def _geography_controls(filtered_for_options, year):
    st.sidebar.markdown("---")
    st.sidebar.subheader("Geography")

    geography_type = st.sidebar.selectbox(
        "Geography type",
        ["Countries", "Distinct Areas", "Local Authorities"],
        index=0,
    )

    options = geography_options(filtered_for_options, geography_type)
    if not options:
        st.sidebar.warning("No geography options match the current filters.")
        return geography_type, None

    if geography_type == "Countries":
        label = "Country"
        default_index = options.index("England") if "England" in options else 0
    elif geography_type == "Distinct Areas":
        label = "Distinct area"
        default_index = 0
    else:
        label = "Local Authority"
        default_index = 0

    geography_value = st.sidebar.selectbox(
        label,
        options,
        index=default_index,
    )
    return geography_type, geography_value


def _apply_non_year_filters(df, industry_choice, band_choice):
    out = df.copy()
    if industry_choice:
        out = out[out["Industry Group"].isin(industry_choice)]
    else:
        out = out.iloc[0:0]
    if band_choice is not None:
        out = out[out["Description"].isin(band_choice)] if band_choice else out.iloc[0:0]
    return out


def _geography_label(geography_type, geography_value):
    return f"{geography_type}: {geography_value}"


def _top_industry(selected_rows):
    if selected_rows.empty:
        return "—", 0
    grouped = (
        selected_rows.groupby("Industry Group")["Value"]
        .sum()
        .sort_values(ascending=False)
    )
    if grouped.empty:
        return "—", 0
    return str(grouped.index[0]), float(grouped.iloc[0])


def _safe(value):
    return html.escape(str(value or ""))



@st.fragment
def _render_map_and_detail(dataset_key, config, map_geojson, la_values, df, year, geography_type, geography_value, data_source, boundary_source):
    st.write("")
    map_col, detail_col = st.columns([3.3, 1.15], gap="large")

    with map_col:
        if map_geojson.get("features"):
            deck = build_deck(map_geojson, config["metric_label"])
            event = st.pydeck_chart(
                deck,
                height=720,
                on_select="rerun",
                selection_mode="single-object",
                key=f"map_{dataset_key}_{geography_type}_{geography_value}_{year}",
            )
        else:
            event = None
            st.info("No mapped Local Authorities match the current filters.")

    selected_name = None
    if event is not None:
        try:
            selected_objects = (
                event.selection.get("objects", {})
                .get("local-authorities", [])
            )
            if selected_objects:
                obj = selected_objects[0]
                props = obj.get("properties", obj)
                selected_name = props.get("local_authority")
        except Exception:
            selected_name = None

    if not selected_name and not la_values.empty:
        selected_name = (
            la_values.sort_values("Value", ascending=False)
            .iloc[0]["MapLocation"]
        )

    with detail_col:
        st.subheader("Area detail")
        if selected_name:
            row = la_values[la_values["MapLocation"] == selected_name]
            total = float(row["Value"].sum()) if not row.empty else 0
            region = str(row["Region"].iloc[0]) if not row.empty else ""
            nation = str(row["Nation"].iloc[0]) if not row.empty else ""

            # For BCP this intentionally includes legacy component rows where
            # present, because aggregate_for_map maps them to the current boundary.
            selected_rows = df[
                df["Location"].astype(str).isin(
                    [selected_name, "Bournemouth", "Poole", "Christchurch"]
                    if selected_name == "Bournemouth, Christchurch and Poole"
                    else [selected_name]
                )
            ].copy()

            top_ind_name, top_ind_value = _top_industry(selected_rows)

            st.markdown(
                f"""
                <div class="detail-card">
                    <div class="detail-title">{_safe(selected_name)}</div>
                    <div class="detail-meta">{_safe(region)}{' · ' if region and nation else ''}{_safe(nation)}</div>
                    <div class="detail-row"><span>{_safe(config['metric_label'])}</span><b>{total:,.0f}</b></div>
                    <div class="detail-row"><span>Largest selected sector</span><b>{_safe(top_ind_name)}</b></div>
                    <div class="detail-row"><span>Sector value</span><b>{top_ind_value:,.0f}</b></div>
                    <div class="detail-row"><span>Year</span><b>{year}</b></div>
                    <div class="detail-row"><span>Geography</span><b>{_safe(geography_value)}</b></div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.info("No Local Authorities match the current filters.")

        st.write("")
        st.download_button(
            "Download filtered data",
            data=df.drop(columns=["_LocationCanonical"], errors="ignore")
                   .to_csv(index=False)
                   .encode("utf-8"),
            file_name=f"{dataset_key}_{year}_{str(geography_value).lower().replace(' ', '_')}.csv",
            mime="text/csv",
        )
        st.markdown(
            (
                "<div class='small-note'>"
                f"Data: {_safe(data_source)}<br/>"
                f"Map boundaries: {_safe(boundary_source)}. Historical values are displayed on the supplied current boundary geography."
                "</div>"
            ),
            unsafe_allow_html=True,
        )

def render_indicator_page(dataset_key):
    inject_styles()
    config = DATASETS[dataset_key]

    st.sidebar.markdown(
        "<div class='atlas-kicker'>Creative Industries Atlas</div>",
        unsafe_allow_html=True,
    )
    st.sidebar.title(config["page_title"])
    st.sidebar.caption(
        "Change the year, industry and geography. Hover over the map to see the Local Authority and value."
    )

    try:
        df_all, data_source = load_dataset(tuple(config["candidates"]))
        base_geojson, boundary_source = load_geojson()
    except Exception as exc:
        _data_error_page(config, exc)
        return

    year, industry_choice, band_choice = _base_filter_controls(df_all, config)
    year_filtered = _filter_before_geography(
        df_all, year, industry_choice, band_choice
    )

    geography_type, geography_value = _geography_controls(
        year_filtered, year
    )
    if geography_value is None:
        st.stop()

    df = filter_geography(
        year_filtered,
        geography_type,
        geography_value,
        year,
    )

    la_values = aggregate_for_map(df)
    geography_label = _geography_label(geography_type, geography_value)
    map_geojson = enrich_geojson(
        base_geojson,
        la_values,
        year,
        geography_label,
        config["metric_label"],
    )

    st.markdown(
        f"<div class='atlas-kicker'>{_safe(config['kicker'])}</div>",
        unsafe_allow_html=True,
    )
    st.title(config["page_title"])
    st.markdown(
        f"<div class='atlas-subtitle'>{_safe(config['description'])}</div>",
        unsafe_allow_html=True,
    )

    k1, k2, k3, k4 = st.columns(4)
    total_value = float(la_values["Value"].sum()) if not la_values.empty else 0
    kpis = [
        (config["metric_label"], f"{total_value:,.0f}"),
        ("Local Authorities shown", f"{la_values['MapLocation'].nunique():,}"),
        ("Creative sectors", f"{len(industry_choice):,}"),
        ("Year", str(year)),
    ]
    for col, (label, value) in zip((k1, k2, k3, k4), kpis):
        col.markdown(
            (
                "<div class='metric-card'>"
                f"<div class='metric-label'>{_safe(label)}</div>"
                f"<div class='metric-value'>{_safe(value)}</div>"
                "</div>"
            ),
            unsafe_allow_html=True,
        )

    _render_map_and_detail(
        dataset_key, config, map_geojson, la_values, df, year,
        geography_type, geography_value, data_source, boundary_source,
    )

    st.divider()
    st.subheader("Explore the selected geography")

    left, right = st.columns(2, gap="large")

    with left:
        industry = (
            df.groupby("Industry Group", as_index=False)["Value"]
            .sum()
            .sort_values("Value", ascending=True)
        )
        if not industry.empty:
            fig_ind = px.bar(
                industry,
                x="Value",
                y="Industry Group",
                orientation="h",
                labels={
                    "Value": config["value_axis"],
                    "Industry Group": "",
                },
            )
            fig_ind.update_layout(
                title="Creative Industries composition",
                height=460,
                margin=dict(l=0, r=10, t=48, b=20),
                showlegend=False,
            )
            fig_ind.update_traces(
                hovertemplate=f"%{{y}}<br>%{{x:,.0f}} {config['unit_word']}<extra></extra>"
            )
            st.plotly_chart(fig_ind, use_container_width=True)
        else:
            st.info("No industry composition is available for this selection.")

    with right:
        la_rank = (
            la_values.sort_values("Value", ascending=False)
            .head(20)
            .sort_values("Value")
        )
        if not la_rank.empty:
            fig_la = px.bar(
                la_rank,
                x="Value",
                y="MapLocation",
                orientation="h",
                labels={
                    "Value": config["value_axis"],
                    "MapLocation": "",
                },
                hover_data=["Region", "Nation"],
            )
            fig_la.update_layout(
                title="Top Local Authorities",
                height=460,
                margin=dict(l=0, r=10, t=48, b=20),
                showlegend=False,
            )
            st.plotly_chart(fig_la, use_container_width=True)
        else:
            st.info("No Local Authority ranking is available for this selection.")

    if config["bands"]:
        profile = df.groupby("Description", as_index=False)["Value"].sum()
        order = config["bands"]
        profile["order"] = profile["Description"].map(
            {x: i for i, x in enumerate(order)}
        )
        profile = profile.sort_values("order")
        if config["band_labels"]:
            profile["Band"] = (
                profile["Description"]
                .map(config["band_labels"])
                .fillna(profile["Description"])
            )
        else:
            profile["Band"] = profile["Description"]

        if not profile.empty:
            fig_band = px.bar(
                profile,
                x="Band",
                y="Value",
                labels={
                    "Band": config["band_label"],
                    "Value": config["value_axis"],
                },
                text_auto=",.0f",
            )
            fig_band.update_layout(
                title=f"{config['band_label']} profile",
                height=410,
                margin=dict(l=0, r=10, t=48, b=20),
            )
            st.plotly_chart(fig_band, use_container_width=True)

    # Trend: same industry/band/geography selection, all years.
    trend_base = _apply_non_year_filters(
        df_all, industry_choice, band_choice
    )
    trend_frames = []
    for trend_year in sorted(
        trend_base["Year"].dropna().astype(int).unique()
    ):
        year_slice = trend_base[
            trend_base["Year"].astype("Int64") == trend_year
        ].copy()
        geo_slice = filter_geography(
            year_slice,
            geography_type,
            geography_value,
            trend_year,
        )
        trend_frames.append(
            {"Year": trend_year, "Value": float(geo_slice["Value"].sum())}
        )

    trend = pd.DataFrame(trend_frames)
    if not trend.empty:
        fig_trend = px.line(
            trend,
            x="Year",
            y="Value",
            markers=True,
            labels={"Value": config["value_axis"], "Year": "Year"},
        )
        fig_trend.add_vline(x=year, line_dash="dot", opacity=.5)
        fig_trend.update_layout(
            title="Trend across all available years",
            height=390,
            margin=dict(l=0, r=10, t=48, b=20),
        )
        st.plotly_chart(fig_trend, use_container_width=True)

    with st.expander("Methodology and data notes"):
        st.markdown(
            """
            **Geography.** The Geography control is organised into three types:
            **Countries** (England, Scotland, Wales and Northern Ireland),
            **Distinct Areas** (One Creative North and South Central), and
            **Local Authorities**.

            **South Central.** The South Central definition covers the 20 supplied
            pre-reorganisation Local Authorities. For data from 2019 onwards,
            Bournemouth, Poole and Christchurch are treated jointly as
            **Bournemouth, Christchurch and Poole (BCP)**. Historic component
            values are aggregated to the current BCP map boundary when required
            for display.

            **One Creative North.** The existing One Creative North Local
            Authority grouping is retained.

            **Map hover.** Hovering over a Local Authority shows the Local
            Authority name, region, selected geography, year and indicator value.

            **Current boundaries.** Historical values are displayed against the
            supplied current Local Authority boundary file.
            """
        )
        if dataset_key == "turnover":
            st.markdown(
                "**Turnover.** Values are enterprise counts within turnover bands; "
                "they are not £ turnover totals."
            )
        if dataset_key == "employment_size_bands":
            st.markdown(
                "**Employment Size Bands.** Values are enterprise counts within "
                "employment-size bands; they are not employment headcounts."
            )

    st.caption("Creative Industries Atlas · Streamlit + Pydeck + Plotly")
