import json
from pathlib import Path

import pandas as pd
import streamlit as st

from .config import APP_DIR, GEO_CANDIDATES
from .geography import canonical_name, map_boundary_name


def _normalise_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    aliases = {
        "Local Authority": "Location",
        "Local authority": "Location",
        "LAD": "Location",
        "LA": "Location",
        "Region": "Region_1",
        "Industry": "Industry Group",
        "Creative Industries": "Industry Group",
        "Count": "Value",
        "Employment": "Value",
    }

    for old, new in aliases.items():
        if old in df.columns and new not in df.columns:
            df = df.rename(columns={old: new})

    required = ["Year", "Value", "Location"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(
            "Dataset is missing required column(s): " + ", ".join(missing)
        )

    if "Industry Group" not in df.columns:
        df["Industry Group"] = "All Creative Industries"
    if "Description" not in df.columns:
        df["Description"] = "All"
    if "Region_1" not in df.columns:
        df["Region_1"] = ""
    if "Nation" not in df.columns:
        df["Nation"] = ""

    df["Year"] = pd.to_numeric(df["Year"], errors="coerce").astype("Int64")
    df["Value"] = pd.to_numeric(df["Value"], errors="coerce").fillna(0)

    for col in ["Location", "Industry Group", "Description", "Region_1", "Nation"]:
        df[col] = df[col].fillna("").astype(str).str.strip()

    return df


def _resolve(path_text: str) -> Path:
    path = APP_DIR / path_text
    return path


@st.cache_data(show_spinner=False)
def load_dataset(candidates_tuple):
    """
    Load only the dataset needed by the active page.

    candidates_tuple is a tuple of (relative_path, kind, sheet) tuples so it is
    hashable for Streamlit caching.
    """
    errors = []

    for relative_path, kind, sheet in candidates_tuple:
        path = _resolve(relative_path)
        if not path.exists():
            continue
        try:
            if kind == "excel":
                df = pd.read_excel(path, sheet_name=sheet or "fact_long")
            else:
                df = pd.read_csv(path)
            return _normalise_columns(df), str(path.relative_to(APP_DIR))
        except Exception as exc:
            errors.append(f"{relative_path}: {exc}")

    if errors:
        raise RuntimeError("Could not load the dataset:\n" + "\n".join(errors))

    searched = "\n".join(f"• {x[0]}" for x in candidates_tuple)
    raise FileNotFoundError(
        "No matching data file was found. I looked for:\n" + searched
    )


def _close_ring(coords):
    if coords and coords[0] != coords[-1]:
        return coords + [coords[0]]
    return coords


def topojson_to_geojson(topology, object_name="ltla"):
    if topology.get("type") != "Topology":
        return topology

    objects = topology.get("objects", {})
    if not objects:
        return {"type": "FeatureCollection", "features": []}
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
            x += dx
            y += dy
            points.append(
                [x * scale[0] + translate[0], y * scale[1] + translate[1]]
            )
        decoded_arcs.append(points)

    def get_arc(index):
        return (
            decoded_arcs[index]
            if index >= 0
            else list(reversed(decoded_arcs[-index - 1]))
        )

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
            coordinates = [
                [stitch(ring) for ring in polygon] for polygon in arcs
            ]
        else:
            continue

        features.append(
            {
                "type": "Feature",
                "properties": geometry.get("properties", {}),
                "geometry": {
                    "type": geom_type,
                    "coordinates": coordinates,
                },
            }
        )

    return {"type": "FeatureCollection", "features": features}



def _feature_boundary_name(feature):
    props = feature.get("properties", {})
    keys = [
        "areanm", "LAD25NM", "LTLA25NM", "LAD24NM", "LTLA24NM",
        "LAD23NM", "LTLA23NM", "name", "NAME",
    ]
    for key in keys:
        value = props.get(key)
        if value:
            return map_boundary_name(canonical_name(value))
    for key, value in props.items():
        if str(key).upper().endswith("NM") and value:
            return map_boundary_name(canonical_name(value))
    return ""


def _bounds_from_coords(coords):
    min_x = min_y = float("inf")
    max_x = max_y = float("-inf")

    def walk(node):
        nonlocal min_x, min_y, max_x, max_y
        if not isinstance(node, list):
            return
        if (len(node) >= 2 and isinstance(node[0], (int, float))
                and isinstance(node[1], (int, float))):
            x, y = float(node[0]), float(node[1])
            min_x = min(min_x, x); max_x = max(max_x, x)
            min_y = min(min_y, y); max_y = max(max_y, y)
            return
        for child in node:
            walk(child)

    walk(coords)
    if min_x == float("inf"):
        return None
    return [min_x, min_y, max_x, max_y]


def _prepare_geojson(geojson):
    # This runs once inside load_geojson's cache. It avoids repeatedly scanning
    # every polygon coordinate on every Streamlit rerun.
    for feature in geojson.get("features", []):
        props = feature.setdefault("properties", {})
        props["_atlas_name"] = _feature_boundary_name(feature)
        props["_atlas_bbox"] = _bounds_from_coords(
            feature.get("geometry", {}).get("coordinates", [])
        )
    return geojson

@st.cache_data(show_spinner=False)
def load_geojson():
    for relative_path in GEO_CANDIDATES:
        path = _resolve(relative_path)
        if not path.exists():
            continue

        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        return _prepare_geojson(topojson_to_geojson(raw)), str(path.relative_to(APP_DIR))

    raise FileNotFoundError(
        "No boundary file found. Looked for: " + ", ".join(GEO_CANDIDATES)
    )
