# Data dictionary and lineage

All geographic identifiers are strings. Negative ACS sentinel values indicate missing/special values and are never interpreted as measurements. ACS estimates describe overlapping five-year windows; their end year is not a single-year observation.

| Analysis field | Definition / units | Raw source | Grain |
|---|---|---|---|
| `geoid` | State(2)+county(3)+tract(6), 11 characters | ACS `GEO_ID` suffix; Gazetteer `GEOID`; CDC `locationid` | tract |
| `population` | Residents, persons | ACS `B01003_E001` | tract |
| `income` | Median household income, 2023 dollars | ACS `B19013_E001` | tract |
| `poverty_pct` | 100×below-poverty/poverty-status universe | ACS `B17001_E002` / `B17001_E001` | tract |
| `youth_pct` | 100×persons 15–24 / population | ACS B01001 E006–010 + E030–034 | tract |
| `older_pct` | 100×persons 65+ / population | ACS B01001 E020–025 + E044–049 | tract |
| `ALAND_SQMI` | Land area, square miles | 2023 Census Gazetteer | tract |
| `INTPTLAT`, `INTPTLONG` | Internal geographic reference point, degrees | 2023 Census Gazetteer | tract |
| `population_density` | Residents per land square mile | population / land area | tract |
| `nearby_400m/800m/1200m` | Distinct selected site-category locations in stated straight-line radius | NYC FacDB latitude/longitude; code allow-list | tract |
| `within_tract_count` | Selected administrative site records in tract | FacDB borough + ct2020 | tract |
| `log_access` | ln(1+nearby_800m) | derived | tract |
| `loneliness_pct` | Modeled crude adult loneliness prevalence, percent | CDC PLACES 2025, LONELINESS, 2023 | tract |
| `low_confidence_limit`, `high_confidence_limit` | CDC published modeled 95% prevalence bounds | CDC PLACES | tract |
| `uid`, `facname`, `factype`, `category` | Facility identifier/name/source classification/project classification | NYC FacDB | facility |
| `B*_M*` | Published 90% ACS margins of error | Census table-based summary file | tract |

ATUS and county-panel dictionaries, exact equations, raw schema, and caveats are in `docs/models/atus.md` and `docs/models/panel.md`. All analysis tables retain machine-readable names; the corresponding model guide defines their units. The TPI guide distinguishes official ACS inputs from independent OSM-derived scores and explains licensing restrictions.

## Storage and provenance

- `data/raw`: immutable official responses. Every distributed response has an acquisition URL, source, timestamp, byte count, content type, and SHA-256 in `data/manifest.json`.
- Large raw archives/nationwide ACS `.dat` files are excluded from Git. Exact download URLs remain in the manifest, and the acquisition modules regenerate them. These are not silently replaced with examples.
- `data/processed`: distributable geographic extracts and analysis inputs. `data/processed_manifest.json` hashes these files. These files permit offline replay without nationwide downloads. Extracts retain original ACS cell names and MOEs; model files add explicit transformations.
- `data/restricted`: local-only downloads with unresolved redistribution permissions. Never commit these; their source/aggregate QA metadata may be public.
- `outputs/tables`, `outputs/figures`, `outputs/qa`: calculated results, PNG/SVG figures, and machine-readable quality checks. Generated model status records distinguish estimated, incomplete, and not-estimated work.

For a source refresh, start a separate checkout or archive the current manifest and raw/processed files together. Cached bytes are hash-checked; do not hand-edit raw files. A live-source refresh is a new dataset vintage and must be reviewed again.
