import math

import pandas as pd
import pydeck as pdk

from .config import (
    BORDER_COLOR,
    COLOR_STOPS,
    HIGHLIGHT_COLOR,
    NO_DATA_COLOR,
)
from .geography import canonical_name, map_boundary_name


NAME_KEYS = [
    "areanm",
    "LAD25NM",
    "LTLA25NM",
    "LAD24NM",
    "LTLA24NM",
    "LAD23NM",
    "LTLA23NM",
    "name",
    "NAME",
]


def feature_name(feature):
    props = feature.get("properties", {})
    for key in NAME_KEYS:
        value = props.get(key)
        if value:
            return canonical_name(value)
    for key, value in props.items():
        if str(key).upper().endswith("NM") and value:
            return canonical_name(value)
    return ""


def value_to_color(value, vmax, zero_is_data=False):
    if value is None or pd.isna(value):
        return NO_DATA_COLOR
    value = float(value)
    if value <= 0 and not zero_is_data:
        return NO_DATA_COLOR
    if vmax <= 0:
        return list(COLOR_STOPS[0]) + [210]

    value = max(value, 0.0)
    t = min(1.0, math.sqrt(value / float(vmax)))
    idx = min(len(COLOR_STOPS) - 1, int(t * (len(COLOR_STOPS) - 1)))
    return list(COLOR_STOPS[idx]) + [215]


def diverging_color(value, max_abs):
    """Muted red for decline, pale neutral around zero, teal for growth."""
    if value is None or pd.isna(value):
        return NO_DATA_COLOR
    value = float(value)
    if max_abs <= 0:
        return [225, 232, 233, 215]
    strength = min(1.0, math.sqrt(abs(value) / float(max_abs)))
    neutral = (232, 237, 238)
    target = (24, 115, 132) if value >= 0 else (177, 73, 67)
    rgb = [
        int(neutral[i] + strength * (target[i] - neutral[i]))
        for i in range(3)
    ]
    return rgb + [215]


def enrich_geojson(
    base_geojson,
    values,
    year,
    geography_label,
    metric_label,
    value_suffix="",
    value_prefix="",
    value_decimals=0,
    color_mode="sequential",
    zero_is_data=False,
):
    lookup = (
        values.set_index("MapLocation").to_dict("index")
        if not values.empty
        else {}
    )
    allowed = set(values["MapLocation"]) if not values.empty else set()
    numeric = pd.to_numeric(values["Value"], errors="coerce") if not values.empty else pd.Series(dtype=float)
    vmax = float(numeric.max()) if not numeric.dropna().empty else 0
    max_abs = float(numeric.abs().max()) if not numeric.dropna().empty else 0

    features = []
    for feature in base_geojson.get("features", []):
        base_props = feature.get("properties", {})
        current_name = base_props.get("_atlas_name") or map_boundary_name(feature_name(feature))

        if current_name not in allowed:
            continue

        row = lookup.get(current_name)
        value = float(row["Value"]) if row and not pd.isna(row["Value"]) else float("nan")
        if color_mode == "diverging":
            fill = diverging_color(value, max_abs)
        else:
            fill = value_to_color(value, vmax, zero_is_data=zero_is_data)

        value_display = "—" if pd.isna(value) else f"{value_prefix}{value:,.{int(value_decimals)}f}{value_suffix}"
        props = {
            "_atlas_name": current_name,
            "_atlas_bbox": base_props.get("_atlas_bbox"),
            "local_authority": current_name,
            "region": str(row["Region"]) if row else "",
            "nation": str(row["Nation"]) if row else "",
            "year": str(year),
            "geography": geography_label,
            "metric_label": metric_label,
            "value": value,
            "value_display": value_display,
            "fill_color": fill,
        }
        features.append({
            "type": "Feature",
            "properties": props,
            "geometry": feature.get("geometry", {}),
        })

    return {"type": "FeatureCollection", "features": features}


def _iter_points(coords):
    if not isinstance(coords, list):
        return
    if (
        len(coords) >= 2
        and isinstance(coords[0], (int, float))
        and isinstance(coords[1], (int, float))
    ):
        yield coords[0], coords[1]
        return
    for item in coords:
        yield from _iter_points(item)


def view_state_for_geojson(geojson):
    bboxes = [
        f.get("properties", {}).get("_atlas_bbox")
        for f in geojson.get("features", [])
    ]
    bboxes = [b for b in bboxes if b and len(b) == 4]

    if bboxes:
        min_x = min(b[0] for b in bboxes)
        min_y = min(b[1] for b in bboxes)
        max_x = max(b[2] for b in bboxes)
        max_y = max(b[3] for b in bboxes)
    else:
        points = []
        for feature in geojson.get("features", []):
            points.extend(list(_iter_points(feature.get("geometry", {}).get("coordinates", []))))
        if not points:
            return pdk.ViewState(latitude=54.4, longitude=-3.1, zoom=4.65, min_zoom=3.2, max_zoom=12)
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)

    width = max(max_x - min_x, 0.05)
    height = max(max_y - min_y, 0.05)
    span = max(width, height * 0.7)

    if span > 8:
        zoom = 4.2
    elif span > 5:
        zoom = 4.8
    elif span > 3:
        zoom = 5.4
    elif span > 1.6:
        zoom = 6.2
    elif span > 0.8:
        zoom = 7.0
    elif span > 0.35:
        zoom = 8.0
    else:
        zoom = 9.0

    return pdk.ViewState(
        latitude=(min_y + max_y) / 2,
        longitude=(min_x + max_x) / 2,
        zoom=zoom,
        min_zoom=3.2,
        max_zoom=12,
    )


def build_deck(map_geojson, metric_label):
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
        highlight_color=HIGHLIGHT_COLOR,
    )

    tooltip = {
        "html": (
            "<b>Local Authority:</b> {local_authority}<br/>"
            "<b>Region:</b> {region}<br/>"
            "<b>Geography:</b> {geography}<br/>"
            "<b>Year:</b> {year}<br/>"
            f"<b>{metric_label}:</b> {{value_display}}"
        ),
        "style": {
            "backgroundColor": "#10242d",
            "color": "white",
            "fontSize": "13px",
        },
    }

    return pdk.Deck(
        layers=[layer],
        initial_view_state=view_state_for_geojson(map_geojson),
        map_style=None,
        tooltip=tooltip,
    )
