# Third Place Index: restricted source and descriptive comparison

## Scope and source

This optional module checks a third-party index and compares venue counts with
the main NYC access pipeline. It does not estimate a treatment effect or replace
the official-source access measure.

The creator's [download link](https://thirdplaceindex.org/data/third_place_index-main.zip)
is a ZIP despite the website's CSV label. In-memory source inspection found
`third_place_index-main/third_place_index_1.1.csv`, a README, and macOS metadata.
The README identifies the release as 2025 v1.1, corrected October 2026, containing
84,414 tracts. These are source claims, not an independent national coverage audit.
The download URL is mutable: retain the common manifest's retrieval date and
SHA-256, and the status record's selected archive member.

The archive README corrects the [website methodology](https://thirdplaceindex.org/methodology/):
scores are 0–1 ranks within urban/rural class, using a reference distribution
excluding Connecticut. `geoid` uses 2020 tract codes; `geoid_2022` supports later
ACS joins and differs in Connecticut, including missing water-only mappings.
The README warns that `area_sq_miles` is overstated and its density inherits
that error. Neither field is used in comparisons. Collection-year descriptions
also differ between website and archive; do not label this a verified 2024/2025
time series.

## Acquisition and redistribution boundary

From the repository root:

```sh
PYTHONPATH=src python -m econhack.third_place_index --download
PYTHONPATH=src python -m econhack.third_place_index
ECONHACK_OFFLINE=1 PYTHONPATH=src python -m econhack.third_place_index
PYTHONPATH=src python -m econhack.third_place_index --aggregate-figure
```

`run(download=False, make_figure=False)` is independently callable. The main
`econhack run` CLI explicitly downloads this restricted source and requests the
aggregate figure; `--offline` does not download it. Without `--download` in the standalone module, an absent archive
records `not_downloaded` and stops; it never initiates a network request. An
existing archive is still verified through `common.fetch`; offline mode uses
that verified cache and never trusts an unmanifested local file.

Acquisition uses `fetch` with `../restricted/third_place_index.zip`, placing
bytes in `data/restricted/`, already excluded by the repository `.gitignore`.
The module checks the ignore rule and resolved destination first. The common
manifest can contain the lexical path `data/raw/../restricted/...`; it resolves
to the restricted directory. Only public provenance metadata belong in that
manifest. ZIP entries are read in memory, never extracted or executed.

The source names OSM ODbL and public-domain Census inputs, but does not clearly
grant separate redistribution permission for the compiled index. Accordingly:

- Never export the ZIP, CSV, tract subset, joined rows, GEOID/value pairs,
  fitted tract values, maps, or per-tract residuals to public directories.
- No processed TPI cache is written. The joined comparison exists only in memory.
- Successful acquisition records `downloaded_not_redistributed`; this is not
  a license clearance. Failures record `incomplete_not_redistributed`.
- Public outputs are restricted to archive/schema metadata, pooled QA counts,
  and coarse, non-reconstructive descriptive correlations. This operational
  boundary is not a legal opinion. Clarify permission before expanding exports.
- Distributing the repository requires checking that restricted data are absent
  from archives, notebook outputs and attachments; `.gitignore` alone does not
  govern those channels.

## Schema QA and failure behavior

Require one identifiable CSV with `geoid`, `geoid_2022`, `state_fips`,
`urban_rural_class`, `third_place_percentile` and `total_places`. Ignore
`__MACOSX` and hidden members, reject duplicate headers and ambiguous CSVs,
and bound member count, expanded size and compression ratio. Preserve keys as
text; never repair malformed GEOIDs by silently padding them.

Checks fail on empty data, missing required schema, malformed/duplicate primary
GEOIDs, inconsistent state codes, unexpected urban/rural classes, non-Connecticut
GEOID-vintage disagreement, nonfinite/out-of-range scores, or missing, negative,
fractional or malformed counts. When all ten category totals exist, require
their sum to equal `total_places`. Individual place-type columns overlap these
categories and are not added again. Report missing optional category fields.

The schema summary counts missing, negative and malformed optional numeric
values. It does not certify optional demographic values, density accuracy,
national completeness, or equivalence to Census geometry. Schema changes require
review; the code does not guess a new score scale or choose an arbitrary CSV.

## Matched NYC comparison

Read `data/processed/nyc_access.csv` if it exists; do not automatically rerun or
download the NYC pipeline. Require unique eleven-digit NYC GEOIDs, valid count
fields, `within_tract_count` and `nearby_800m`. Other existing radius columns are
included. Match NYC `geoid` to TPI `geoid_2022` one-to-one, after validating that
the two TPI GEOID versions agree in New York. Report both unmatched counts and
the exact official-input hash. Exact key agreement does not independently prove
identical geometry; no crosswalk or zero-filling of absent TPI tracts is applied.

For each official count, calculate Spearman correlation with TPI `total_places`
on the same matched rows using average ranks for ties. Export no p-values or
confidence intervals. Require at least 100 matched tracts and three distinct
values in both measures; otherwise suppress the coefficient. Round published
coefficients to three decimals. This support gate limits misleading/small-cell
outputs; it is not proof of statistical power or permission to redistribute.

The broad OSM venue taxonomy includes commercial and religious locations. NYC
uses selected official facility categories, within-tract counts, and nearby
counts around a tract internal point at straight-line radii. These measure
different constructs. Correlation describes agreement, not accuracy, equality,
walkability, use, welcoming conditions or causal social connection. Current NYC
facilities and the historical TPI snapshot are not temporally aligned. Tract
size, land use, mapping completeness, boundaries and spatial dependence can
drive agreement or disagreement. Neither income nor poverty coefficients are
estimated here.

## Runtime outputs

- `outputs/tables/third_place_index_archive_inventory.csv`: member names,
  sizes and ignored flags only.
- `outputs/tables/third_place_index_schema.csv`: field-level QA counts only.
- `outputs/tables/third_place_index_qa_summary.csv`: pooled coverage and join counts.
- `outputs/tables/third_place_index_comparison.csv`: at most four pooled
  correlations, or explicit suppression; absent when NYC input is unavailable.
- With `--aggregate-figure`, `outputs/figures/third_place_index_aggregate_comparison.png`
  and `.svg`: correlation bars only, when support gates pass; no tract marks.
- `outputs/model_status.json`: source/restriction, hashes, QA/comparison status.

These are runtime outputs, not evidence that acquisition or comparison has
already run. Missing official access data leave comparison explicitly pending.
