import re
import pandas as pd

from .config import (
    BCP,
    COUNTRIES,
    DISTINCT_AREAS,
    OCN_ALL,
    SOUTH_CENTRAL_CURRENT,
    SOUTH_CENTRAL_LEGACY,
)


def canonical_name(value: str) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    aliases = {
        "St. Helens": "St Helens",
        "City of Edinburgh": "Edinburgh",
    }
    return aliases.get(text, text)


def map_boundary_name(value: str) -> str:
    """
    Map legacy Bournemouth/Poole/Christchurch values to the current BCP
    boundary so historic values can still be drawn on the supplied current map.
    """
    name = canonical_name(value)
    if name in {"Bournemouth", "Poole", "Christchurch"}:
        return BCP
    return name


def south_central_names_for_year(year: int):
    if int(year) >= 2019:
        return {canonical_name(x) for x in SOUTH_CENTRAL_CURRENT}
    return {canonical_name(x) for x in SOUTH_CENTRAL_LEGACY}


def filter_geography(
    df: pd.DataFrame,
    geography_type: str,
    geography_value: str,
    year: int,
) -> pd.DataFrame:
    out = df.copy()
    out["_LocationCanonical"] = out["Location"].map(canonical_name)

    if geography_type == "Countries":
        target = str(geography_value).strip().casefold()
        nation = out["Nation"].astype(str).str.strip().str.casefold()
        region = out["Region_1"].astype(str).str.strip().str.casefold()
        # Nation is preferred. Region fallback keeps older Scotland/Wales/NI
        # source structures working.
        mask = nation.eq(target)
        if not mask.any():
            mask = region.eq(target)
        return out[mask].copy()

    if geography_type == "Distinct Areas":
        if geography_value == "One Creative North":
            allowed = {canonical_name(x) for x in OCN_ALL}
        elif geography_value == "South Central":
            allowed = south_central_names_for_year(year)
        else:
            allowed = set()
        return out[out["_LocationCanonical"].isin(allowed)].copy()

    if geography_type == "Local Authorities":
        target = canonical_name(geography_value)
        return out[out["_LocationCanonical"].eq(target)].copy()

    return out.iloc[0:0].copy()


def geography_options(df: pd.DataFrame, geography_type: str):
    if geography_type == "Countries":
        return COUNTRIES
    if geography_type == "Distinct Areas":
        return DISTINCT_AREAS
    if geography_type == "Local Authorities":
        return sorted(
            {
                canonical_name(x)
                for x in df["Location"].dropna().astype(str)
                if str(x).strip()
            }
        )
    return []


def aggregate_for_map(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate filtered rows to one value per current map boundary.

    Legacy Bournemouth, Poole and Christchurch values are combined into BCP
    because the Atlas displays current LTLA boundaries.
    """
    if df.empty:
        return pd.DataFrame(
            columns=["MapLocation", "Location", "Region", "Nation", "Value"]
        )

    work = df.copy()
    work["MapLocation"] = work["Location"].map(map_boundary_name)

    grouped = (
        work.groupby(["MapLocation"], as_index=False)
        .agg(
            Value=("Value", "sum"),
            Region=("Region_1", lambda s: next((x for x in s if str(x).strip()), "")),
            Nation=("Nation", lambda s: next((x for x in s if str(x).strip()), "")),
        )
    )
    grouped["Location"] = grouped["MapLocation"]
    return grouped
