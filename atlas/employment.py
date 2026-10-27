import html

import pandas as pd
import streamlit as st

from .config import INDUSTRY_ORDER
from .geography import filter_geography, geography_options, map_boundary_name
from .styles import inject_styles

STATUS_ORDER = ["Employees", "Full-time employees", "Part-time employees"]
STATUS_LABELS = {
    "Employees": "Employees",
    "Full-time employees": "Full-time employees",
    "Part-time employees": "Part-time employees",
}


def _safe(value):
    return html.escape(str(value or ""))


def _first_nonempty(series):
    return next((str(x) for x in series if str(x).strip()), "")


def _available_industries(df):
    present = set(df["Industry Group"].dropna().astype(str))
    ordered = [x for x in INDUSTRY_ORDER if x in present]
    return ordered + sorted(x for x in present if x and x not in ordered)


def _wide_by_boundary(rows):
    if rows.empty:
        return pd.DataFrame(
            columns=["MapLocation", "Location", "Region", "Nation"] + STATUS_ORDER
        )
    work = rows.copy()
    work["MapLocation"] = work["Location"].map(map_boundary_name)
    grouped = (
        work.groupby(["MapLocation", "Employment Status"], as_index=False)
        .agg(
            Value=("Value", "sum"),
            Region=("Region_1", _first_nonempty),
            Nation=("Nation", _first_nonempty),
        )
    )
    value_wide = grouped.pivot_table(
        index="MapLocation",
        columns="Employment Status",
        values="Value",
        aggfunc="sum",
        fill_value=0,
    ).reset_index()
    meta = grouped.groupby("MapLocation", as_index=False).agg(
        Region=("Region", _first_nonempty), Nation=("Nation", _first_nonempty)
    )
    out = value_wide.merge(meta, on="MapLocation", how="left")
    for status in STATUS_ORDER:
        if status not in out.columns:
            out[status] = 0
    out["Location"] = out["MapLocation"]
    return out


@st.fragment
def _employment_map(
    map_geojson,
    la_wide,
    map_status,
    year,
    geography_value,
    data_source,
    boundary_source,
    filtered_rows,
):
    from .map_utils import build_deck

    st.write("")
    map_col, detail_col = st.columns([3.3, 1.15], gap="large")
    with map_col:
        if map_geojson.get("features"):
            deck = build_deck(map_geojson, STATUS_LABELS[map_status])
            event = st.pydeck_chart(
                deck,
                height=720,
                on_select="rerun",
                selection_mode="single-object",
                key=f"employment_map_{year}_{geography_value}_{map_status}",
            )
        else:
            event = None
            st.info("No mapped Local Authorities match the current filters.")

    selected_name = None
    if event is not None:
        try:
            selected = event.selection.get("objects", {}).get("local-authorities", [])
            if selected:
                selected_name = selected[0].get("properties", selected[0]).get(
                    "local_authority"
                )
        except Exception:
            selected_name = None
    if not selected_name and not la_wide.empty:
        selected_name = (
            la_wide.sort_values(map_status, ascending=False).iloc[0]["MapLocation"]
        )

    with detail_col:
        st.subheader("Area detail")
        if selected_name:
            row = la_wide[la_wide["MapLocation"] == selected_name]
            if not row.empty:
                r = row.iloc[0]
                ft = float(r.get("Full-time employees", 0))
                pt = float(r.get("Part-time employees", 0))
                denom = ft + pt
                pt_share = 100 * pt / denom if denom else float("nan")
                st.markdown(
                    f"""
                    <div class="detail-card">
                        <div class="detail-title">{_safe(selected_name)}</div>
                        <div class="detail-meta">{_safe(r.get('Region',''))}{' · ' if r.get('Region','') and r.get('Nation','') else ''}{_safe(r.get('Nation',''))}</div>
                        <div class="detail-row"><span>Employees</span><b>{float(r.get('Employees',0)):,.0f}</b></div>
                        <div class="detail-row"><span>Full-time employees</span><b>{ft:,.0f}</b></div>
                        <div class="detail-row"><span>Part-time employees</span><b>{pt:,.0f}</b></div>
                        <div class="detail-row"><span>Part-time share</span><b>{'—' if pd.isna(pt_share) else f'{pt_share:.1f}%'}</b></div>
                        <div class="detail-row"><span>Year</span><b>{year}</b></div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        else:
            st.info("No Local Authorities match the current filters.")

        st.write("")
        st.download_button(
            "Download filtered employment data",
            data=filtered_rows.drop(columns=["_LocationCanonical"], errors="ignore")
            .to_csv(index=False)
            .encode("utf-8"),
            file_name=f"creative_industries_employment_{year}.csv",
            mime="text/csv",
        )
        st.markdown(
            (
                "<div class='small-note'>"
                f"Data: {_safe(data_source)}<br/>"
                f"Map boundaries: {_safe(boundary_source)}.<br/>"
                "BRES covers Great Britain, not Northern Ireland."
                "</div>"
            ),
            unsafe_allow_html=True,
        )


def render_employment_page():
    import plotly.express as px

    from .data import load_dataset, load_geojson
    from .map_utils import enrich_geojson

    inject_styles()

    st.sidebar.markdown(
        "<div class='atlas-kicker'>Creative Industries Atlas</div>",
        unsafe_allow_html=True,
    )
    st.sidebar.title("Employment")
    st.sidebar.caption(
        "BRES employees by year, Creative Industries group and geography, with full-time and part-time breakdowns."
    )

    try:
        employment_candidates = (
            ("data/bres_employment_fact_long.csv.gz", "csv", None),
            ("bres_employment_fact_long.csv.gz", "csv", None),
        )
        df_all, data_source = load_dataset(employment_candidates)
        base_geojson, boundary_source = load_geojson()
    except Exception as exc:
        st.title("Employment")
        st.warning(str(exc))
        return

    if "Employment Status" not in df_all.columns:
        st.error("The BRES dataset does not contain an Employment Status column.")
        return

    years = sorted(df_all["Year"].dropna().astype(int).unique())
    year = st.sidebar.select_slider("Year", years, value=max(years))

    industries = _available_industries(df_all)
    industry_choice = st.sidebar.multiselect(
        "Creative Industries", industries, default=industries
    )
    if not industry_choice:
        st.warning("Select at least one Creative Industries group.")
        return

    map_status = st.sidebar.selectbox(
        "Map measure",
        STATUS_ORDER,
        format_func=lambda x: STATUS_LABELS[x],
    )

    year_rows = df_all[
        (df_all["Year"].astype("Int64") == int(year))
        & (df_all["Industry Group"].isin(industry_choice))
    ].copy()

    st.sidebar.markdown("---")
    st.sidebar.subheader("Geography")
    geography_type = st.sidebar.selectbox(
        "Geography type", ["Countries", "Distinct Areas", "Local Authorities"]
    )
    options = geography_options(year_rows, geography_type)
    if geography_type == "Countries":
        label = "Country"
        default = options.index("United Kingdom") if "United Kingdom" in options else 0
    elif geography_type == "Distinct Areas":
        label = "Distinct area"
        default = 0
    else:
        label = "Local Authority"
        default = 0
    geography_value = st.sidebar.selectbox(label, options, index=default)

    filtered = filter_geography(year_rows, geography_type, geography_value, year)

    st.markdown(
        "<div class='atlas-kicker'>Creative Industries Atlas</div>",
        unsafe_allow_html=True,
    )
    st.title("Employment")
    st.markdown(
        "<div class='atlas-subtitle'>Creative Industries employees from the Business Register and Employment Survey (BRES), with full-time and part-time breakdowns.</div>",
        unsafe_allow_html=True,
    )

    if geography_type == "Countries" and geography_value == "Northern Ireland":
        st.info(
            "BRES covers Great Britain and does not include Northern Ireland. "
            "No Northern Ireland employment values are available in this NOMIS BRES extract."
        )
        return
    if geography_type == "Countries" and geography_value == "United Kingdom":
        st.warning(
            "Employment uses BRES, which covers Great Britain only. The United Kingdom view therefore shows England, Scotland and Wales; Northern Ireland is not included."
        )

    if filtered.empty:
        st.info("No employment data match the current filters.")
        return

    la_wide = _wide_by_boundary(filtered)
    map_values = la_wide[["MapLocation", "Location", "Region", "Nation", map_status]].copy()
    map_values = map_values.rename(columns={map_status: "Value"})
    geography_label = f"{geography_type}: {geography_value}"
    if geography_type == "Countries" and geography_value == "United Kingdom":
        geography_label += " (BRES: Great Britain coverage)"
    # Use the original five-argument enrich_geojson signature for compatibility
    # with earlier Atlas map modules, then apply display formatting locally.
    map_geojson = enrich_geojson(
        base_geojson, map_values, year, geography_label, STATUS_LABELS[map_status]
    )
    for feature in map_geojson.get("features", []):
        props = feature.setdefault("properties", {})
        value = props.get("value")
        try:
            props["value_display"] = f"{float(value):,.0f}"
        except (TypeError, ValueError):
            props["value_display"] = "—"

    status_totals = (
        filtered.groupby("Employment Status")["Value"].sum().reindex(STATUS_ORDER).fillna(0)
    )
    employees = float(status_totals.get("Employees", 0))
    ft = float(status_totals.get("Full-time employees", 0))
    pt = float(status_totals.get("Part-time employees", 0))
    pt_share = 100 * pt / (ft + pt) if (ft + pt) else float("nan")

    cols = st.columns(4)
    metrics = [
        ("Employees", f"{employees:,.0f}"),
        ("Full-time employees", f"{ft:,.0f}"),
        ("Part-time employees", f"{pt:,.0f}"),
        ("Part-time share", "—" if pd.isna(pt_share) else f"{pt_share:.1f}%"),
    ]
    for col, (label_text, value) in zip(cols, metrics):
        col.markdown(
            f"<div class='metric-card'><div class='metric-label'>{_safe(label_text)}</div><div class='metric-value'>{_safe(value)}</div></div>",
            unsafe_allow_html=True,
        )

    _employment_map(
        map_geojson,
        la_wide,
        map_status,
        year,
        geography_value,
        data_source,
        boundary_source,
        filtered,
    )

    st.divider()
    st.subheader("Employment profile")
    left, right = st.columns(2, gap="large")

    with left:
        rank = la_wide.sort_values(map_status, ascending=False).head(25).sort_values(map_status)
        if not rank.empty:
            fig = px.bar(
                rank,
                x=map_status,
                y="Location",
                orientation="h",
                labels={map_status: STATUS_LABELS[map_status], "Location": ""},
                title=f"{STATUS_LABELS[map_status]} by Local Authority",
            )
            fig.update_layout(height=650, showlegend=False, margin=dict(l=0, r=10, t=48, b=20))
            fig.update_traces(hovertemplate="%{y}<br>%{x:,.0f}<extra></extra>")
            st.plotly_chart(fig, use_container_width=True)

    with right:
        comp = (
            filtered[filtered["Employment Status"].isin(["Full-time employees", "Part-time employees"])]
            .groupby(["Industry Group", "Employment Status"], as_index=False)["Value"]
            .sum()
        )
        if not comp.empty:
            fig = px.bar(
                comp,
                x="Value",
                y="Industry Group",
                color="Employment Status",
                barmode="group",
                orientation="h",
                labels={"Value": "Employees", "Industry Group": "", "Employment Status": ""},
                title="Full-time and part-time employees by industry group",
            )
            fig.update_layout(height=650, margin=dict(l=0, r=10, t=48, b=20), legend_title_text="")
            fig.update_traces(hovertemplate="%{y}<br>%{x:,.0f}<extra></extra>")
            st.plotly_chart(fig, use_container_width=True)

    st.subheader("Employment over time")
    trend_base = df_all[df_all["Industry Group"].isin(industry_choice)].copy()
    # Current BRES geography is fixed to April 2023 boundaries, so the selected
    # geography can be applied consistently across the whole 2015–2024 series.
    trend_filtered = filter_geography(
        trend_base, geography_type, geography_value, int(year)
    )
    trend = (
        trend_filtered.groupby(["Year", "Employment Status"], as_index=False)["Value"]
        .sum()
    )
    if not trend.empty:
        fig = px.line(
            trend,
            x="Year",
            y="Value",
            color="Employment Status",
            markers=True,
            category_orders={"Employment Status": STATUS_ORDER},
            labels={"Value": "Employees", "Employment Status": ""},
        )
        fig.update_layout(height=430, margin=dict(l=0, r=10, t=20, b=20), legend_title_text="")
        fig.update_traces(hovertemplate="%{x}<br>%{y:,.0f}<extra></extra>")
        st.plotly_chart(fig, use_container_width=True)

    st.caption(
        "Source: NOMIS Business Register and Employment Survey (BRES), open access. "
        "The supplied extract covers 2015–2024 and Great Britain. Counts are summed across the 31 Creative Industries SIC codes. "
        "NOMIS disclosure rounding means summed Full-time + Part-time cells can differ slightly from separately summed Employees."
    )
