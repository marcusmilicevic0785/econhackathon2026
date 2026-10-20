# Published ATUS fallback: all persons age 15+

`econhack.atus_published.run()` downloads **official BLS API** series
**TUU10101AA01013951**, average daily hours in the published **Socializing and
communicating** category for the total population, age **15 years and over**,
all days. This is a distinct fallback when the preferred microdata ZIP is
inaccessible. It does **not** provide ages 15–24 or complete the original
T120101 microdata analysis. It writes only the `atus_published` model status;
the original `atus` incomplete status remains visible.

## Official definition and verification

- [BLS series viewer](https://data.bls.gov/timeseries/TUU10101AA01013951).
- [BLS ATUS series dictionary](https://download.bls.gov/pub/time.series/TU/tu.series).
- [BLS 2003 first release, Table 1](https://www.bls.gov/news.release/archives/atus_09142004.pdf)
  distinguishes **hours for the total population** from hours among participants.
  The total-population Socializing and communicating value is **0.78 hours/day**;
  participants' hours and participation percentages are different measures.
- [BLS 2024 release and technical notes](https://www.bls.gov/news.release/archives/atus_06262025.htm)
  show **0.59 hours/day** for total-population socializing and communicating and
  define the population as civilian noninstitutional persons ages 15 and older.
  The category includes social communication and hosting/attending social
  functions. It is broader than the single detailed activity T120101.

Verification uses two independently inspected official Table 1 anchors, not a
third-party series label: the API's 2003 and 2024 values must match the
total-population socializing rows above. `verify_definition_anchors` exports
the reconciliation, source URLs, and population labels. The direct bulk series
dictionary returned HTTP 403 in this environment, and the official API's
`catalog=true` response explicitly says the catalog was disabled. No retrieved
catalog title is claimed. A later revision that disagrees with these archived
anchors stops execution for an explicit vintage/definition reconciliation.

Keep the published category label. Do not call this total face-to-face time,
all communication, a loneliness measure, or a youth series. Interaction during
work, meals, childcare, and other primary activities can fall outside this
category. Telephone calls, texting, and internet voice/video calling have their
own classification. No precise microdata-code sum is assumed here.

## Acquisition and coverage

The public API GET endpoint is
`https://api.bls.gov/publicAPI/v2/timeseries/data/TUU10101AA01013951`.
Requests use explicit `startyear`/`endyear` windows **2003–2012**, **2013–2022**,
and **2023–2024**, each at most ten years. No API key or third-party source is
needed. All raw JSON goes through `common.fetch` into
`data/raw/atus_published/TUU10101AA01013951_START_END.json`, with manifest
hashes, source URLs, acquisition dates, and licensing metadata. Raw BLS
footnotes remain in the JSON and are retained in the annual table as text.

The parser requires `REQUEST_SUCCEEDED`, the exact requested series ID,
annual period **A01**, unique years, plausible finite hours, and complete
coverage of each requested window except 2020. A successful HTTP response
with an API error envelope or truncated data is an error, not a result.
There is no interpolation, secondary mirror, or hand-entered replacement.

The tidy table has **22 calendar rows** and **21 published observations**.
The 2020 row explicitly contains missing hours/minutes and a pandemic-gap
status. BLS could not publish a comparable full-year 2020 estimate because of
the collection interruption; see [BLS pandemic guidance](https://www.bls.gov/tus/notices/2021/covid19tech.htm).
The chart leaves a gap at 2020 and the regression excludes it.
Scope is fixed at 2003–2024; 2025 is not silently appended.

## Estimator, regression, and limitations

BLS has already applied survey weights to its published average over all
eligible people, including people reporting zero time in the activity. Do
not reweight the annual API values or interpret them as participant averages.
`minutes_per_day = 60 * published_hours_per_day`. BLS rounds the published
hours: conversion to minutes does not recover unrounded diary-level precision.

The separate descriptive regression is
`minutes_per_day = intercept + slope * (year - 2003) + residual`, fit by
ordinary least squares to the 21 non-2020 annual points with equal year
weights. Its coefficient table includes both terms, units, sample size,
residual degrees of freedom, R-squared, and RMSE; fitted values/residuals are
exported. This is a summary of temporal direction, with a possible pandemic
level shift and nonlinear history. **No standard errors, p-values, confidence
intervals, or causal inference are reported.** The API response provides no
survey variance in this series, and no such variance is fabricated. Differences
of rounded endpoints are descriptive, not significance tests.

## Outputs and offline replay

- `data/processed/atus_published_annual.csv`: distributed tidy annual extract.
- `outputs/tables/atus_published_annual.csv`: the same series with source URLs,
  population/activity definitions, original published values, coverage flags,
  and footnotes.
- `outputs/tables/atus_published_regression.csv`: two descriptive coefficient rows.
- `outputs/tables/atus_published_fitted.csv`: 21 fitted/residual observations.
- `outputs/tables/atus_published_definition_check.csv`: official Table 1 endpoint reconciliation.
- `outputs/figures/atus_published_trend.png` and `.svg`.
- `outputs/model_status.json`: `atus_published=complete_published_only`; the
  original microdata status remains separate and incomplete when access fails.

Run `PYTHONPATH=src .venv/bin/python -m econhack.atus_published` after acquisition
is authorized. `ECONHACK_OFFLINE=1` replays the distributed processed table,
or the common verified raw cache if the table is absent. The processed table
is validated for definition, population, units, coverage, and the missing 2020
row. The main CLI snapshot includes it in the processed manifest; verify that
manifest before distributing or running companion notebooks.
