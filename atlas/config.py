from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = APP_DIR / "data"

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

COUNTRIES = ["United Kingdom", "England", "Scotland", "Wales", "Northern Ireland"]

TURNOVER_ORDER = [
    "0 to 49 (thousand)",
    "50 to 99 (thousand)",
    "100 to 249 (thousand)",
    "250 to 499 (thousand)",
    "500 to 999 (thousand)",
    "1000 to 1999 (thousand)",
    "2000 to 4999 (thousand)",
    "5000 to 9999 (thousand)",
    "10000 to 49999 (thousand)",
    "50000+ (thousand)",
]

TURNOVER_LABELS = {
    "0 to 49 (thousand)": "£0–£49k",
    "50 to 99 (thousand)": "£50k–£99k",
    "100 to 249 (thousand)": "£100k–£249k",
    "250 to 499 (thousand)": "£250k–£499k",
    "500 to 999 (thousand)": "£500k–£999k",
    "1000 to 1999 (thousand)": "£1m–£1.999m",
    "2000 to 4999 (thousand)": "£2m–£4.999m",
    "5000 to 9999 (thousand)": "£5m–£9.999m",
    "10000 to 49999 (thousand)": "£10m–£49.999m",
    "50000+ (thousand)": "£50m+",
}

EMPLOYMENT_BAND_ORDER = [
    "0 to 4",
    "5 to 9",
    "10 to 19",
    "20 to 49",
    "50 to 99",
    "100 to 249",
    "250 to 499",
    "500 to 999",
    "1000+",
]

# Existing One Creative North geography retained from the current atlas workflow.
ONE_CREATIVE_NORTH = {
    "Greater Manchester": {
        "Bolton", "Bury", "Manchester", "Oldham", "Rochdale",
        "Salford", "Stockport", "Tameside", "Trafford", "Wigan",
    },
    "Liverpool City Region": {
        "Halton", "Knowsley", "Liverpool", "Sefton", "St. Helens",
        "St Helens", "Wirral",
    },
    "West Yorkshire": {"Bradford", "Calderdale", "Kirklees", "Leeds", "Wakefield"},
    "South Yorkshire": {"Barnsley", "Doncaster", "Rotherham", "Sheffield"},
    "North East": {
        "County Durham", "Gateshead", "Newcastle upon Tyne", "North Tyneside",
        "Northumberland", "South Tyneside", "Sunderland",
    },
    "Tees Valley": {
        "Darlington", "Hartlepool", "Middlesbrough",
        "Redcar and Cleveland", "Stockton-on-Tees",
    },
    "York and North Yorkshire": {"York", "North Yorkshire"},
    "Cheshire and Warrington": {
        "Cheshire East", "Cheshire West and Chester", "Warrington",
    },
    "Cumbria": {
        "Cumberland", "Westmorland and Furness",
        "Allerdale", "Barrow-in-Furness", "Carlisle",
        "Copeland", "Eden", "South Lakeland",
    },
    "Lancashire": {
        "Blackburn with Darwen", "Blackpool", "Burnley", "Chorley", "Fylde",
        "Hyndburn", "Lancaster", "Pendle", "Preston", "Ribble Valley",
        "Rossendale", "South Ribble", "West Lancashire", "Wyre",
    },
}

OCN_ALL = set().union(*ONE_CREATIVE_NORTH.values())

# South Central definition supplied for the Atlas.
SOUTH_CENTRAL_LEGACY = {
    "Basingstoke and Deane",
    "Hart",
    "Rushmoor",
    "Test Valley",
    "Winchester",
    "Guildford",
    "Waverley",
    "Woking",
    "Bournemouth",
    "Poole",
    "Portsmouth",
    "Southampton",
    "Isle of Wight",
    "Christchurch",
    "East Hampshire",
    "Eastleigh",
    "Fareham",
    "Gosport",
    "Havant",
    "New Forest",
}

BCP = "Bournemouth, Christchurch and Poole"
SOUTH_CENTRAL_CURRENT = (
    SOUTH_CENTRAL_LEGACY - {"Bournemouth", "Poole", "Christchurch"}
) | {BCP}

DISTINCT_AREAS = ["One Creative North", "South Central"]

COLOR_STOPS = [
    (239, 246, 248),
    (207, 232, 236),
    (156, 207, 214),
    (93, 171, 183),
    (39, 128, 146),
    (12, 82, 104),
]
NO_DATA_COLOR = [224, 228, 231, 100]
BORDER_COLOR = [255, 255, 255, 210]
HIGHLIGHT_COLOR = [245, 176, 65, 210]

DATASETS = {
    "business_counts": {
        "page_title": "Business Counts",
        "kicker": "Creative Industries Atlas",
        "description": "Creative Industries enterprise counts by industry and geography.",
        "metric_label": "Business count",
        "value_axis": "Enterprises",
        "unit_word": "enterprises",
        "band_label": None,
        "bands": None,
        "band_labels": None,
        "candidates": [
            ("business_counts.xlsx", "excel", "fact_long"),
            ("data/business_counts.xlsx", "excel", "fact_long"),
            ("business_counts_fact_long_2025.csv", "csv", None),
            ("data/business_counts_fact_long_2025.csv", "csv", None),
            ("data/business_counts_fact_long.csv", "csv", None),
            ("data/business_counts_fact_long.csv.gz", "csv", None),
        ],
    },
    "turnover": {
        "page_title": "Turnover",
        "kicker": "Creative Industries Atlas",
        "description": (
            "Enterprise counts by annual turnover size band. "
            "The values are counts of enterprises, not monetary turnover totals."
        ),
        "metric_label": "Business count",
        "value_axis": "Enterprises",
        "unit_word": "enterprises",
        "band_label": "Annual turnover band",
        "bands": TURNOVER_ORDER,
        "band_labels": TURNOVER_LABELS,
        "candidates": [
            ("data/turnover_fact_long.csv.gz", "csv", None),
            ("turnover_fact_long.csv.gz", "csv", None),
            ("turnover_fact_long_2025.csv", "csv", None),
            ("data/turnover_fact_long_2025.csv", "csv", None),
            ("data/turnover_fact_long.csv", "csv", None),
        ],
    },
    "employment_size_bands": {
        "page_title": "Employment Size Bands",
        "kicker": "Creative Industries Atlas",
        "description": "Enterprise counts by employment size band.",
        "metric_label": "Business count",
        "value_axis": "Enterprises",
        "unit_word": "enterprises",
        "band_label": "Employment size band",
        "bands": EMPLOYMENT_BAND_ORDER,
        "band_labels": None,
        "candidates": [
            ("data/employment_fact_long.csv.gz", "csv", None),
            ("employment_fact_long.csv.gz", "csv", None),
            ("employment_bands_fact_long_2025.csv", "csv", None),
            ("data/employment_bands_fact_long_2025.csv", "csv", None),
            ("data/employment_bands_fact_long.csv", "csv", None),
        ],
    },
}

GEO_CANDIDATES = [
    "data/ltla2025_simplified.geojson",
    "ltla2025_simplified.geojson",
    "data/ltla2025.json",
    "ltla2025.json",
    "data/england_lads_2024.geojson",
    "england_lads_2024.geojson",
]
