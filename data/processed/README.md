# Processed data

These CSVs contain the extracts and joined datasets used in the graphs. Each filename below links to the file. The [data dictionary](../../docs/data_dictionary.md) explains the variables; the [graph guide](../../docs/graph_guide.md) connects them to the figures.

## Main datasets

| File | What one row represents | What's in it | Related graphs and methods |
| --- | --- | --- | --- |
| [nyc_access.csv](nyc_access.csv) | One NYC Census tract | Population, income, poverty, age shares, land area, and selected nearby facilities | [Access, income groups and regression](../../docs/graph_guide.md#2-nyc-access-and-income); [methods](../../docs/models/nyc_equity.md) |
| [nyc_loneliness.csv](nyc_loneliness.csv) | One NYC Census tract matched to CDC data | The access dataset plus modeled adult loneliness prevalence and CDC confidence bounds | [Loneliness graphs](../../docs/graph_guide.md#4-access-and-loneliness); [methods](../../docs/models/loneliness.md) |
| [panel_county_year.csv](panel_county_year.csv) | One New York county in one year, 2018–2023 | Snack/beverage establishments, business applications, population, rates, lags and source-status fields | [County graphs](../../docs/graph_guide.md#6-county-trends); [methods](../../docs/models/panel.md) |
| [atus_published_annual.csv](atus_published_annual.csv) | One published annual BLS observation | Socializing time for people age 15+, in hours and minutes per day, with source notes | [Time trend](../../docs/graph_guide.md#1-socializing-time); [methods](../../docs/models/atus_published.md) |

The CSVs can contain rows excluded from a particular regression. The NYC models use 2,190 complete-case tracts with at least 100 residents. The county panel has 372 rows; the matched current/lag models use 310. Exact samples are recorded in [QA](../../outputs/qa) and [model tables](../../outputs/tables).

## Source extracts and supporting files

| File | Contents | Used for |
| --- | --- | --- |
| [acs2023_nyc_b01001.csv](acs2023_nyc_b01001.csv) | Selected age-by-sex counts for NYC tracts, plus margins of error | Ages 15–24 and 65+ shares in the NYC datasets |
| [acs2023_nyc_b01003.csv](acs2023_nyc_b01003.csv) | Total population estimates and margins of error | NYC population and density |
| [acs2023_nyc_b17001.csv](acs2023_nyc_b17001.csv) | Poverty-status universe and below-poverty counts, plus margins of error | NYC poverty percentage |
| [acs2023_nyc_b19013.csv](acs2023_nyc_b19013.csv) | Median household income estimates and margins of error | NYC income comparisons and regressions |
| [cdc_ny_loneliness.csv](cdc_ny_loneliness.csv) | New York tract records from CDC PLACES 2025, including modeled adult loneliness and confidence bounds | The CDC side of the NYC loneliness join |
| [nyc_selected_facilities.csv](nyc_selected_facilities.csv) | Selected NYC FacDB site-category records, coordinates, categories and coordinate-validity flags | Nearby-facility counts and the independent-index comparison |
| [panel_acquisition.csv](panel_acquisition.csv) | Download/extraction status, source URLs and row counts by source/year | County-panel source checks; this is a log, not a model dataset |

These supporting files do not each have a separate graph. They feed the joined datasets above. ACS extracts use the original Census cell names: `E` means estimate and `M` means the published 90% margin of error. The four NYC ACS extracts describe 2019–2023, not just 2023.

## A few details that matter

- Keep `geoid`, `GEO_ID` and county FIPS as text when importing into a spreadsheet. Leading zeros are part of the identifiers.
- `nearby_800m` counts selected facilities within 800 metres of a tract's Census internal point, using straight-line distance. It does not measure walking routes, opening hours or eligibility. Records with invalid coordinates are excluded from these counts.
- `loneliness_pct` is a modeled adult area estimate for 2023. It is not a youth-specific survey or an observation of each resident.
- `proxy_establishments` covers NAICS 722515 employer establishments, broader than cafés. `business_applications` counts applications, not businesses that actually opened.
- The BLS series covers age 15+, with no comparable 2020 annual observation. The youth microdata analysis is incomplete.
- Missing/suppressed values and observed zeros have different meanings. Negative special ACS codes are converted to missing in analysis variables; source extracts retain source cells.

The [processed manifest](../processed_manifest.json) records CSV hashes and lineage. The [source manifest](../manifest.json) records download URLs and source-file hashes. Redistribution notes are in [data licenses](../../DATA_LICENSES.md). Row-level Third Place Index data are not included because redistribution permission remains unclear; its [aggregate comparison](../../outputs/tables/third_place_index_comparison.csv) is separate from these CSVs.
