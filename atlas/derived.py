import html
import pandas as pd
import streamlit as st

from .config import INDUSTRY_ORDER
from .geography import (
    canonical_name,
    filter_geography,
    geography_options,
    map_boundary_name,
)
from .styles import inject_styles


def _safe(value):
    return html.escape(str(value or ""))


def _available_industries(df):
    present = set(df["Industry Group"].dropna().astype(str))
    ordered = [x for x in INDUSTRY_ORDER if x in present]
    extras = sorted(
        x for x in present
        if x and x not in ordered and x.lower() not in {"nan", "none"}
    )
    return ordered + extras


def _load_business_data():
    # Load the new Business Counts file directly so this page does not depend
    # on an older DATASETS registry left behind in an existing GitHub repo.
    from .data import load_dataset
    candidates = (
        ("data/business_counts_fact_long.csv.gz", "csv", None),
        ("business_counts_fact_long.csv.gz", "csv", None),
        ("data/business_counts_fact_long.csv", "csv", None),
    )
    return load_dataset(candidates)


def _sidebar_geography(df, key_prefix="derived"):
    st.sidebar.markdown("---")
    st.sidebar.subheader("Geography")
    geography_type = st.sidebar.selectbox(
        "Geography type",
        ["Countries", "Distinct Areas", "Local Authorities"],
        key=f"{key_prefix}_geo_type",
    )
    options = geography_options(df, geography_type)
    if not options:
        return geography_type, None

    if geography_type == "Countries":
        label = "Country"
        default = options.index("United Kingdom") if "United Kingdom" in options else 0
    elif geography_type == "Distinct Areas":
        label = "Distinct area"
        default = 0
    else:
        label = "Local Authority"
        default = 0

    geography_value = st.sidebar.selectbox(
        label,
        options,
        index=default,
        key=f"{key_prefix}_geo_value",
    )
    return geography_type, geography_value


def _selected_industries(df, key):
    industries = _available_industries(df)
    return st.sidebar.multiselect(
        "Creative Industries",
        industries,
        default=industries,
        key=key,
    )


def _ensure_region_nation(df):
    out = df.copy()
    if "Region_1" not in out.columns:
        out["Region_1"] = ""
    if "Nation" not in out.columns:
        out["Nation"] = ""
    return out


def load_nomis_total_enterprises(year: int):
    """Load the local all-industry denominator without relying on old data.py helpers."""
    from pathlib import Path
    app_dir = Path(__file__).resolve().parents[1]
    candidates = [
        app_dir / "data" / "all_enterprises_by_la_year.csv.gz",
        app_dir / "all_enterprises_by_la_year.csv.gz",
        app_dir / "data" / "all_enterprises_by_la_year.csv",
    ]
    last_error = None
    for path in candidates:
        if not path.exists():
            continue
        try:
            totals = pd.read_csv(path)
            required = {"Location", "Year", "All Enterprises"}
            missing = required - set(totals.columns)
            if missing:
                raise ValueError("Denominator file is missing: " + ", ".join(sorted(missing)))
            totals["Year"] = pd.to_numeric(totals["Year"], errors="coerce").astype("Int64")
            totals["All Enterprises"] = pd.to_numeric(totals["All Enterprises"], errors="coerce").fillna(0)
            totals["Location"] = totals["Location"].fillna("").astype(str).str.strip().map(canonical_name)
            for col in ["Region_1", "Nation"]:
                if col not in totals.columns:
                    totals[col] = ""
                totals[col] = totals[col].fillna("").astype(str).str.strip()
            out = totals[totals["Year"] == int(year)].copy()
            return out, str(path.relative_to(app_dir))
        except Exception as exc:
            last_error = exc
    if last_error:
        raise last_error
    raise FileNotFoundError(
        "I could not load the all-enterprise denominator. "
        "Make sure data/all_enterprises_by_la_year.csv.gz is uploaded to GitHub."
    )


def _enrich_geojson_compat(base_geojson, values, year, geography_label, metric_label, **kwargs):
    """Work with both the newest and older Atlas map_utils.enrich_geojson signatures."""
    try:
        return enrich_geojson(
            base_geojson, values, year, geography_label, metric_label, **kwargs
        )
    except TypeError:
        # Older map_utils accepted only the original five positional arguments.
        result = enrich_geojson(base_geojson, values, year, geography_label, metric_label)
        suffix = kwargs.get("value_suffix", "")
        prefix = kwargs.get("value_prefix", "")
        decimals = int(kwargs.get("value_decimals", 0))
        for feature in result.get("features", []):
            props = feature.setdefault("properties", {})
            raw = props.get("value")
            try:
                props["value_display"] = f"{prefix}{float(raw):,.{decimals}f}{suffix}"
            except (TypeError, ValueError):
                props["value_display"] = "—"
        return result


def _intensity_table(ci_rows, totals):
    ci = _ensure_region_nation(ci_rows)
    ci["Location"] = ci["Location"].map(canonical_name)
    ci_totals = (
        ci.groupby("Location", as_index=False)
        .agg(
            Creative_Enterprises=("Value", "sum"),
            Region_1=("Region_1", lambda s: next((x for x in s if str(x).strip()), "")),
            Nation=("Nation", lambda s: next((x for x in s if str(x).strip()), "")),
        )
    )

    total = totals.copy()
    total["Location"] = total["Location"].map(canonical_name)
    merged = ci_totals.merge(total[["Location", "All Enterprises"]], on="Location", how="inner")
    merged = merged[merged["All Enterprises"] > 0].copy()
    merged["Value"] = 100 * merged["Creative_Enterprises"] / merged["All Enterprises"]
    merged["Description"] = "Creative business intensity"
    merged["Industry Group"] = "Selected Creative Industries"
    return merged


def _aggregate_intensity_boundaries(df):
    """Combine legacy Bournemouth/Poole/Christchurch before calculating BCP intensity."""
    if df.empty:
        return df.copy()
    work = df.copy()
    work["MapLocation"] = work["Location"].map(map_boundary_name)
    out = (
        work.groupby("MapLocation", as_index=False)
        .agg(
            Creative_Enterprises=("Creative_Enterprises", "sum"),
            All_Enterprises=("All Enterprises", "sum"),
            Region_1=("Region_1", lambda s: next((x for x in s if str(x).strip()), "")),
            Nation=("Nation", lambda s: next((x for x in s if str(x).strip()), "")),
        )
    )
    out = out.rename(columns={"All_Enterprises": "All Enterprises"})
    out["Value"] = 100 * out["Creative_Enterprises"] / out["All Enterprises"]
    out["Location"] = out["MapLocation"]
    out["Description"] = "Creative business intensity"
    out["Industry Group"] = "Selected Creative Industries"
    return out


def _growth_table(df_all, start_year, end_year, industry_choice):
    work = _ensure_region_nation(df_all)
    work = work[work["Industry Group"].isin(industry_choice)].copy()
    work["Location"] = work["Location"].map(canonical_name)
    # Compare on current map boundaries so Bournemouth, Poole and Christchurch
    # are combined consistently with BCP across the 2019 reorganisation.
    work["MapLocation"] = work["Location"].map(map_boundary_name)

    base = (
        work[work["Year"].astype("Int64") == int(start_year)]
        .groupby("MapLocation", as_index=False)
        .agg(
            Start_Value=("Value", "sum"),
            Region_1=("Region_1", lambda s: next((x for x in s if str(x).strip()), "")),
            Nation=("Nation", lambda s: next((x for x in s if str(x).strip()), "")),
        )
    )
    end = (
        work[work["Year"].astype("Int64") == int(end_year)]
        .groupby("MapLocation", as_index=False)
        .agg(End_Value=("Value", "sum"))
    )
    merged = base.merge(end, on="MapLocation", how="outer")
    merged["Location"] = merged["MapLocation"]
    merged["Start_Value"] = pd.to_numeric(merged["Start_Value"], errors="coerce").fillna(0)
    merged["End_Value"] = pd.to_numeric(merged["End_Value"], errors="coerce").fillna(0)
    if "Region_1" not in merged.columns:
        merged["Region_1"] = ""
    else:
        merged["Region_1"] = merged["Region_1"].fillna("")
    if "Nation" not in merged.columns:
        merged["Nation"] = ""
    else:
        merged["Nation"] = merged["Nation"].fillna("")

    merged["Value"] = pd.NA
    valid = merged["Start_Value"] > 0
    merged.loc[valid, "Value"] = (
        100
        * (merged.loc[valid, "End_Value"] - merged.loc[valid, "Start_Value"])
        / merged.loc[valid, "Start_Value"]
    )
    merged["Value"] = pd.to_numeric(merged["Value"], errors="coerce")
    merged["Description"] = f"{start_year}–{end_year} growth"
    merged["Industry Group"] = "Selected Creative Industries"
    return merged


def _derived_map_values(df):
    """Map values without summing percentages across legacy BCP components."""
    if df.empty:
        return pd.DataFrame(columns=["MapLocation", "Location", "Region", "Nation", "Value"])
    work = df.copy()
    work["MapLocation"] = work["Location"].map(map_boundary_name)

    # For BCP legacy rows, aggregate underlying counts then calculate metrics in
    # caller before this point wherever possible. If multiple percentage rows
    # still map to the same boundary, use their mean rather than their sum.
    grouped = (
        work.groupby("MapLocation", as_index=False)
        .agg(
            Value=("Value", "mean"),
            Region=("Region_1", lambda s: next((x for x in s if str(x).strip()), "")),
            Nation=("Nation", lambda s: next((x for x in s if str(x).strip()), "")),
        )
    )
    grouped["Location"] = grouped["MapLocation"]
    return grouped


@st.fragment
def _render_percent_map(
    page_key,
    map_geojson,
    la_values,
    detail_df,
    metric_label,
    period_label,
    geography_value,
    data_source,
    boundary_source,
    detail_rows,
):
    from .map_utils import build_deck

    st.write("")
    map_col, detail_col = st.columns([3.3, 1.15], gap="large")
    with map_col:
        if map_geojson.get("features"):
            deck = build_deck(map_geojson, metric_label)
            event = st.pydeck_chart(
                deck,
                height=720,
                on_select="rerun",
                selection_mode="single-object",
                key=f"map_{page_key}_{geography_value}_{period_label}",
            )
        else:
            event = None
            st.info("No mapped Local Authorities match the current filters.")

    selected_name = None
    if event is not None:
        try:
            selected = event.selection.get("objects", {}).get("local-authorities", [])
            if selected:
                selected_name = selected[0].get("properties", selected[0]).get("local_authority")
        except Exception:
            selected_name = None
    if not selected_name and not la_values.empty:
        selected_name = la_values.sort_values("Value", ascending=False).iloc[0]["MapLocation"]

    with detail_col:
        st.subheader("Area detail")
        if selected_name:
            row = detail_df[detail_df["Location"].map(map_boundary_name) == selected_name]
            value = float(row["Value"].mean()) if not row.empty else float("nan")
            region = str(row["Region_1"].iloc[0]) if not row.empty else ""
            nation = str(row["Nation"].iloc[0]) if not row.empty else ""
            extras = detail_rows(row)
            extra_html = "".join(
                f"<div class='detail-row'><span>{_safe(label)}</span><b>{_safe(val)}</b></div>"
                for label, val in extras
            )
            display_value = "—" if pd.isna(value) else f"{value:,.1f}%"
            st.markdown(
                f"""
                <div class="detail-card">
                    <div class="detail-title">{_safe(selected_name)}</div>
                    <div class="detail-meta">{_safe(region)}{' · ' if region and nation else ''}{_safe(nation)}</div>
                    <div class="detail-row"><span>{_safe(metric_label)}</span><b>{display_value}</b></div>
                    {extra_html}
                    <div class="detail-row"><span>Period</span><b>{_safe(period_label)}</b></div>
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
            data=detail_df.to_csv(index=False).encode("utf-8"),
            file_name=f"{page_key}_{str(period_label).replace(' ', '_')}.csv",
            mime="text/csv",
        )
        st.markdown(
            (
                "<div class='small-note'>"
                f"Data: {_safe(data_source)}<br/>"
                f"Map boundaries: {_safe(boundary_source)}."
                "</div>"
            ),
            unsafe_allow_html=True,
        )


def render_business_intensity_page():
    import plotly.express as px
    from .data import load_geojson

    inject_styles()
    st.sidebar.markdown("<div class='atlas-kicker'>Creative Industries Atlas</div>", unsafe_allow_html=True)
    st.sidebar.title("Creative Business Intensity")
    st.sidebar.caption("Creative Industries enterprises as a percentage of all enterprises.")

    try:
        df_all, business_source = _load_business_data()
        base_geojson, boundary_source = load_geojson()
    except Exception as exc:
        st.title("Creative Business Intensity")
        st.warning(str(exc))
        return

    years = sorted(df_all["Year"].dropna().astype(int).unique())
    if not years:
        st.error("No valid years were found in Business Counts.")
        return
    year = st.sidebar.select_slider("Year", years, value=max(years), key="intensity_year")
    industries = _selected_industries(df_all, "intensity_industries")
    if not industries:
        st.warning("Select at least one Creative Industries group.")
        return

    ci_year = df_all[
        (df_all["Year"].astype("Int64") == int(year))
        & (df_all["Industry Group"].isin(industries))
    ].copy()

    geography_type, geography_value = _sidebar_geography(ci_year, "intensity")
    if geography_value is None:
        st.stop()

    try:
        nomis_totals, denominator_source = load_nomis_total_enterprises(int(year))
    except Exception as exc:
        st.title("Creative Business Intensity")
        st.error("I could not load the all-enterprise denominator.")
        st.caption(str(exc))
        return

    intensity_all = _intensity_table(ci_year, nomis_totals)
    filtered = filter_geography(intensity_all, geography_type, geography_value, year)
    intensity_map = _aggregate_intensity_boundaries(filtered)
    la_values = _derived_map_values(intensity_map)
    geography_label = f"{geography_type}: {geography_value}"
    map_geojson = _enrich_geojson_compat(
        base_geojson,
        la_values,
        year,
        geography_label,
        "Creative business intensity",
        value_suffix="%",
        value_decimals=1,
        zero_is_data=True,
    )

    st.markdown("<div class='atlas-kicker'>Creative Industries Atlas</div>", unsafe_allow_html=True)
    st.title("Creative Business Intensity")
    st.markdown(
        "<div class='atlas-subtitle'>Selected Creative Industries enterprises as a percentage of all enterprises in each Local Authority.</div>",
        unsafe_allow_html=True,
    )

    creative_total = float(filtered["Creative_Enterprises"].sum()) if not filtered.empty else 0
    enterprise_total = float(filtered["All Enterprises"].sum()) if not filtered.empty else 0
    overall_intensity = 100 * creative_total / enterprise_total if enterprise_total else float("nan")
    median_intensity = float(filtered["Value"].median()) if not filtered.empty else float("nan")

    cols = st.columns(4)
    metrics = [
        ("Creative business intensity", "—" if pd.isna(overall_intensity) else f"{overall_intensity:.1f}%"),
        ("Creative enterprises", f"{creative_total:,.0f}"),
        ("All enterprises", f"{enterprise_total:,.0f}"),
        ("Median LA intensity", "—" if pd.isna(median_intensity) else f"{median_intensity:.1f}%"),
    ]
    for col, (label, value) in zip(cols, metrics):
        col.markdown(
            f"<div class='metric-card'><div class='metric-label'>{_safe(label)}</div><div class='metric-value'>{_safe(value)}</div></div>",
            unsafe_allow_html=True,
        )

    def intensity_details(row):
        if row.empty:
            return []
        return [
            ("Creative enterprises", f"{float(row['Creative_Enterprises'].sum()):,.0f}"),
            ("All enterprises", f"{float(row['All Enterprises'].sum()):,.0f}"),
            ("Year", str(year)),
        ]

    _render_percent_map(
        "creative_business_intensity",
        map_geojson,
        la_values,
        intensity_map,
        "Creative business intensity",
        str(year),
        geography_value,
        f"{business_source} + {denominator_source}",
        boundary_source,
        intensity_details,
    )

    st.divider()
    st.subheader("Compare Local Authorities")
    rank = intensity_map.dropna(subset=["Value"]).sort_values("Value", ascending=False).head(25)
    if not rank.empty:
        fig = px.bar(
            rank.sort_values("Value"),
            x="Value",
            y="Location",
            orientation="h",
            labels={"Value": "Creative business intensity (%)", "Location": ""},
        )
        fig.update_layout(height=650, showlegend=False, margin=dict(l=0, r=10, t=20, b=20))
        fig.update_traces(hovertemplate="%{y}<br>%{x:.1f}%<extra></extra>")
        st.plotly_chart(fig, use_container_width=True)

    st.caption(
        "Definition: selected Creative Industries enterprises ÷ all enterprises × 100. "
        "All-enterprise totals come from the same NOMIS UK Business Counts extract (all industries, total employment size band, total legal status)."
    )


def render_growth_page():
    import plotly.express as px
    from .data import load_geojson

    inject_styles()
    st.sidebar.markdown("<div class='atlas-kicker'>Creative Industries Atlas</div>", unsafe_allow_html=True)
    st.sidebar.title("Creative Industry Growth")
    st.sidebar.caption("Percentage change in Creative Industries enterprise counts between two years.")

    try:
        df_all, business_source = _load_business_data()
        base_geojson, boundary_source = load_geojson()
    except Exception as exc:
        st.title("Creative Industry Growth")
        st.warning(str(exc))
        return

    years = sorted(df_all["Year"].dropna().astype(int).unique())
    if len(years) < 2:
        st.title("Creative Industry Growth")
        st.warning("Growth needs at least two years in the Business Counts dataset.")
        return

    default_start = 2019 if 2019 in years else years[0]
    start_year = st.sidebar.selectbox(
        "Start year",
        years[:-1],
        index=years[:-1].index(default_start) if default_start in years[:-1] else 0,
        key="growth_start",
    )
    valid_end = [y for y in years if y > int(start_year)]
    end_year = st.sidebar.selectbox(
        "End year",
        valid_end,
        index=len(valid_end) - 1,
        key="growth_end",
    )
    industries = _selected_industries(df_all, "growth_industries")
    if not industries:
        st.warning("Select at least one Creative Industries group.")
        return

    growth_all = _growth_table(df_all, start_year, end_year, industries)
    geography_type, geography_value = _sidebar_geography(growth_all, "growth")
    if geography_value is None:
        st.stop()

    geography_filter_year = max(int(end_year), 2019)
    filtered = filter_geography(growth_all, geography_type, geography_value, geography_filter_year)
    mapped = filtered.dropna(subset=["Value"]).copy()
    la_values = _derived_map_values(mapped)
    geography_label = f"{geography_type}: {geography_value}"
    period = f"{start_year}–{end_year}"
    map_geojson = _enrich_geojson_compat(
        base_geojson,
        la_values,
        period,
        geography_label,
        "Creative industry growth",
        value_suffix="%",
        value_decimals=1,
        color_mode="diverging",
        zero_is_data=True,
    )

    st.markdown("<div class='atlas-kicker'>Creative Industries Atlas</div>", unsafe_allow_html=True)
    st.title("Creative Industry Growth")
    st.markdown(
        f"<div class='atlas-subtitle'>Change in selected Creative Industries enterprise counts between {start_year} and {end_year}.</div>",
        unsafe_allow_html=True,
    )

    # Aggregate growth for the selected geography should be calculated from
    # counts, not by averaging Local Authority percentage changes.
    start_total = float(filtered["Start_Value"].sum()) if not filtered.empty else 0
    end_total = float(filtered["End_Value"].sum()) if not filtered.empty else 0
    overall_growth = 100 * (end_total - start_total) / start_total if start_total else float("nan")
    valid_growth = filtered["Value"].dropna()
    positive = int((valid_growth > 0).sum())
    median_growth = float(valid_growth.median()) if not valid_growth.empty else float("nan")

    cols = st.columns(4)
    metrics = [
        ("Overall growth", "—" if pd.isna(overall_growth) else f"{overall_growth:+.1f}%"),
        (f"Enterprises in {start_year}", f"{start_total:,.0f}"),
        (f"Enterprises in {end_year}", f"{end_total:,.0f}"),
        ("LAs with positive growth", f"{positive:,}"),
    ]
    for col, (label, value) in zip(cols, metrics):
        col.markdown(
            f"<div class='metric-card'><div class='metric-label'>{_safe(label)}</div><div class='metric-value'>{_safe(value)}</div></div>",
            unsafe_allow_html=True,
        )

    def growth_details(row):
        if row.empty:
            return []
        return [
            (f"Enterprises in {start_year}", f"{float(row['Start_Value'].sum()):,.0f}"),
            (f"Enterprises in {end_year}", f"{float(row['End_Value'].sum()):,.0f}"),
            ("Absolute change", f"{float(row['End_Value'].sum()-row['Start_Value'].sum()):+,.0f}"),
        ]

    _render_percent_map(
        "creative_industry_growth",
        map_geojson,
        la_values,
        filtered,
        "Creative industry growth",
        period,
        geography_value,
        business_source,
        boundary_source,
        growth_details,
    )

    st.divider()
    left, right = st.columns(2, gap="large")

    with left:
        st.subheader("Local Authority growth")
        rank = filtered.dropna(subset=["Value"]).copy()
        if not rank.empty:
            # Show strongest growth and weakest growth together where there are
            # many areas; otherwise show all.
            if len(rank) > 24:
                rank = pd.concat([
                    rank.nsmallest(12, "Value"),
                    rank.nlargest(12, "Value"),
                ]).drop_duplicates("Location")
            rank = rank.sort_values("Value")
            fig = px.bar(
                rank,
                x="Value",
                y="Location",
                orientation="h",
                labels={"Value": "Growth (%)", "Location": ""},
            )
            fig.update_layout(height=650, showlegend=False, margin=dict(l=0, r=10, t=20, b=20))
            fig.update_traces(hovertemplate="%{y}<br>%{x:+.1f}%<extra></extra>")
            st.plotly_chart(fig, use_container_width=True)

    with right:
        st.subheader("Selected geography over time")
        series = df_all[df_all["Industry Group"].isin(industries)].copy()
        # Apply the same geography to each year so the trend uses the selected area.
        pieces = []
        for y in years:
            yrows = series[series["Year"].astype("Int64") == int(y)]
            yrows = filter_geography(yrows, geography_type, geography_value, y)
            pieces.append({"Year": y, "Enterprises": float(yrows["Value"].sum())})
        trend = pd.DataFrame(pieces)
        trend = trend[trend["Year"].between(int(start_year), int(end_year))]
        if not trend.empty:
            fig2 = px.line(
                trend,
                x="Year",
                y="Enterprises",
                markers=True,
                labels={"Enterprises": "Creative Industries enterprises"},
            )
            fig2.update_layout(height=420, margin=dict(l=0, r=10, t=20, b=20), showlegend=False)
            fig2.update_traces(hovertemplate="%{x}<br>%{y:,.0f} enterprises<extra></extra>")
            st.plotly_chart(fig2, use_container_width=True)

        st.metric(
            "Median Local Authority growth",
            "—" if pd.isna(median_growth) else f"{median_growth:+.1f}%",
        )
        st.caption(
            "Percentage growth is left undefined where an area's starting business count is zero. "
            "The overall growth KPI is calculated from aggregate enterprise counts, not the average of Local Authority growth rates."
        )
