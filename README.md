# Creative Industries Atlas — NOMIS update

This build keeps the existing multipage Streamlit Atlas and adds the latest NOMIS data supplied on 27 October 2026.

## Navigation

- Home
- Business Counts
- Creative Business Intensity
- Creative Industry Growth
- Employment
- Turnover
- Employment Size Bands

## New / updated data in this package

### Business Counts
`data/business_counts_fact_long.csv.gz`

- Source: NOMIS — UK Business Counts, enterprises by industry and employment size band
- Years: **2010–2026**
- Geography: **361 UK Local Authorities** on the supplied/current NOMIS geography
- Creative Industries: **31 SIC 2007 codes**, grouped into 9 Creative Industries groups
- Employment size band: Total
- Legal status: Total

This replaces the older Business Counts series when both are present because it is first in the dataset candidate list.

### Creative Business Intensity
`data/all_enterprises_by_la_year.csv.gz`

Calculated as:

**selected Creative Industries enterprises / all enterprises × 100**

The denominator is the all-industry `Column Total` from the same NOMIS UK Business Counts extract, for each Local Authority and year. No live NOMIS/API request is made when the page opens.

### Creative Industry Growth
Uses the updated Business Counts series above and therefore supports comparisons through **2026**.

### Employment
`data/bres_employment_fact_long.csv.gz`

- Source: NOMIS — Business Register and Employment Survey (BRES), open access
- Years: **2015–2024**
- Geography: **350 Great Britain Local Authorities**
- Measures included: **Employees, Full-time employees, Part-time employees**
- Creative Industries: the same 31 SIC 2007 codes / 9 groups

BRES does **not** cover Northern Ireland. The Employment page therefore:

- supports England, Scotland and Wales;
- keeps United Kingdom in the common geography menu but clearly warns that this view is Great Britain coverage only;
- shows an explicit no-data message for Northern Ireland rather than treating missing values as zero.

Because NOMIS applies disclosure rounding, sums of detailed Full-time + Part-time cells can differ slightly from separately summed Employees.

## Geography controls

All relevant pages retain:

**Countries**
- United Kingdom
- England
- Scotland
- Wales
- Northern Ireland

**Distinct Areas**
- One Creative North
- South Central

**Local Authorities**
- individual Local Authorities

South Central uses the current BCP boundary when the source itself is published on current Local Authority geography.

## Existing files to keep in your GitHub `data/` folder

This package includes the three new compact NOMIS files above. Keep your existing files for:

- Turnover
- Employment Size Bands
- UK Local Authority GeoJSON / TopoJSON boundary file

The preferred boundary filename remains `data/ltla2025_simplified.geojson` when available, with the existing fallbacks still supported.

## Performance

The large raw NOMIS downloads are **not** parsed by Streamlit. They have been preprocessed into compressed long-format CSV files. Each indicator page loads only the dataset it needs and uses Streamlit caching.
