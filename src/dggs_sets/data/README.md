# Data

Loaded by `dggs_sets.data`. The package stores as little as it can: the
boundaries are fetched from their sources on first use and cached (in
`~/.cache/dggs_sets`, or `$DGGS_SETS_CACHE`); only the NYC fields ship in
the package, because they can't be regenerated from public data.

## Fetched

- **US states** (`states()`): US Census Bureau cartographic boundary files,
  2010, 1:500k, as GeoJSON (`GEO_ID`, `STATE`, `NAME`, `LSAD`, `CENSUSAREA`).
  Public domain. Fetched from the copy in
  [h3coco](https://github.com/ajfriend/h3coco), pinned to a commit so the
  talk's numbers stay reproducible.
- **Connecticut counties** (`ct_counties()`): "Connecticut County Index",
  State of Connecticut Department of Energy & Environmental Protection
  (with the USGS National Mapping Program), on
  [CT DEEP's open data site](https://ct-deep-gis-open-data-website-ctdeep.hub.arcgis.com/datasets/CTDEEP::connecticut-county-index/about).
  License: CC0. Fetched as GeoJSON in lng/lat from its ArcGIS feature
  service (item `65c5bc765d3b4ebe9826289dd8df59b3`).

## Shipped

- `nyc_h3r10_field.csv.gz`, `nyc_s2l16_field.csv.gz` (`nyc_field('h3')`,
  `nyc_field('s2')`): driving minutes from downtown Brooklyn
  (40.6928, -73.9866) to every cell in the five-borough box (lat 40.50–40.91,
  lng -74.25 to -73.70), in H3 res 10 and in S2 level 16, the S2 level closest
  in cell area. Speeds are OpenStreetMap speed limits capped per road class,
  plus signal and stop penalties. Columns: `cell` (H3 hex string or S2
  token), `minutes` (empty if unreachable) and `status` (`reached` or
  `unreachable`). Every cell in the box is present.

  Derived from OpenStreetMap data: © OpenStreetMap contributors, available
  under the Open Database License (ODbL), https://www.openstreetmap.org/copyright.
  These two files are shared under the ODbL as well.
