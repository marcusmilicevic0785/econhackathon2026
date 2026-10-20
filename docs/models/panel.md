# New York county-year establishments / applications panel

## Scope and definitions

`econhack.panel.run()` builds the explicit universe of **all 62 New York State
counties**, county FIPS `36001`, `36003`, …, `36123`, for **2018–2023** (372 rows).
The five New York City borough-counties remain separate. This is a New York
analysis, not a nationwide panel or an inference about all US counties.

The exposure is annual Census County Business Patterns **EST/ESTAB** for
**NAICS 722515, Snack and nonalcoholic beverage bars**. It is a proxy broader
than cafes: it includes other snack and beverage establishments, excludes some
businesses people might call cafes, covers establishments with paid employees,
and is a stock rather than new openings. All six CBP releases use **2017 NAICS**,
including 2023; a calendar year after 2022 does not imply 2022 NAICS.

The outcome is annual county BFS **Business Applications (BA)**, across all
industries covered by that series. These are qualifying EIN applications, **not
realized business formations, firm births, cafe applications, or openings**.
The county release adds disclosure-avoidance noise, clips negative noisy values
to zero, and calibrates to state totals. A published BFS zero is preserved but
does not prove zero underlying applications. Source vintages may revise past
counts, so the shared fetch manifest records the exact downloaded bytes.

## Official sources and verified schemas

- [CBP downloadable county files](https://www2.census.gov/programs-surveys/cbp/datasets/2023/):
  `https://www2.census.gov/programs-surveys/cbp/datasets/{year}/cbp{yy}co.zip`.
  The archive contains `cbp{yy}co.txt`, a CSV with `fipstate`, `fipscty`, `naics`,
  and **`est`** (not `emp`, `n<5`, or a sum of employment size categories).
  NY is `fipstate=36`; industry is exactly `722515`. If supplied, legal-form and
  employment-size dimensions must both be `001` (all establishments). See the
  [2023 official table, identifying 2017 NAICS](https://data.census.gov/table/CBP2023.CB2300CBP?codeset=naics~722515).
- [BFS annual county release](https://www.census.gov/econ/bfs/data/county.html):
  **`https://www.census.gov/econ/bfs/xlsx/bfs_county_apps_annual.xlsx`**.
  The [official county dictionary](https://www.census.gov/econ/bfs/pdf/bfs_county_data_dictionary.pdf)
  specifies wide columns `State`, `County`, `County Code` (five-digit FIPS),
  `state_fips`, `county_fips`, `BA2005` … `BA2025` in the 2026 release. The parser
  locates this header below any workbook title rows, selects `BA2018` …
  `BA2023`, and reshapes to one county-year per row. It does not guess a monthly
  BFS URL or use the state formation series. The
  [BFS methodology](https://www.census.gov/econ/bfs/technicaldocumentation/methodology.html)
  describes qualifying applications and differential privacy.
- [ACS table-based summary files](https://www.census.gov/programs-surveys/acs/data/summary-file.html):
  `B01003` total population, annual **5-year** releases. For 2021–2023 use
  `https://www2.census.gov/programs-surveys/acs/summary_file/{year}/table-based-SF/data/5YRData/acsdt5y{year}-b01003.dat`.
  For 2018–2020 use the official `prototype/5YRData/` folder in place of
  `table-based-SF/data/5YRData/`; see [2018](https://www2.census.gov/programs-surveys/acs/summary_file/2018/prototype/5YRData/),
  [2019](https://www2.census.gov/programs-surveys/acs/summary_file/2019/prototype/5YRData/),
  and [2020](https://www2.census.gov/programs-surveys/acs/summary_file/2020/prototype/5YRData/).
  These are national files filtered to exact county-level GEO_ID
  `0500000US36xxx`, never tract sums or county subdivisions. Verified 2023
  pipe-delimited columns are `GEO_ID|B01003_E001|B01003_M001`; earlier
  `B01003_001E`/`B01003_001M` names and CSV delimiters are supported. Estimate
  and nonnegative 90% MOE are retained separately.

All acquisitions use the shared `fetch` contract and official bulk sources;
no API key or API request is needed. Census API endpoints can return HTTP 200
with HTML “Missing Key,” which is not valid data. Files are cached as
`panel/cbp/cbp{yy}co.zip`, `panel/acs/acsdt5y{year}-b01003.dat`, and
`panel/bfs_county_apps_annual.xlsx` under the shared raw-data root. Main owns
live acquisition/execution; unit tests use small synthetic files and no network.

## Denominators, missingness, and timing

Both measures are normalized per 10,000 residents using **that year's ACS
5-year release**, not one fixed 2023 population. The 2018 denominator covers
2014–2018; 2023 covers 2019–2023. Adjacent releases overlap in four years, are
smoothed period estimates rather than independent annual population counts,
and span the pandemic even in some nominally non-COVID outcome years. MOEs
are exported but denominator uncertainty is not propagated into standard errors.
No population estimates from another program are silently substituted.

Suppression markers, invalid/sentinel values, blank cells, absent county/industry
rows, and observed numeric zero remain distinguishable in source status and raw
value columns. Employment suppression flags do not suppress a published `est`.
An absent CBP industry record is **missing, not imputed zero**. Nonpositive
population cannot form a rate. Duplicate county-year keys fail validation;
there is no many-to-many merge, interpolation, forward fill, or zero fill.

The lag is the prior year's **rate with the prior year's denominator**. It is
joined by county and exactly `year-1`; it never bridges a missing year. The
first usable lag is 2019 from 2018, with `lag_source_year` exported. BFS years
follow IRS processing weeks rather than exact calendar boundaries: 2020 has
53 weeks, other sample years 52. CBP is an annual establishment stock and BFS
an applications flow; contemporaneous timing is not evidence of precedence.

## Models and comparisons

The dependent variable is applications per 10,000 residents. OLS includes an
intercept, county fixed effects and year fixed effects. Estimates are unweighted;
counties are the analytical units. Standard errors cluster by county, use the
finite-sample sandwich correction, and report two-sided t tests/95% intervals
with `G-1` county-cluster degrees of freedom.

Each of two sensitivities has four models:

1. `current`: contemporaneous proxy on its complete current sample.
2. `current_matched`: contemporaneous proxy restricted to the common complete
   current + lag + outcome sample.
3. `lag1_matched`: prior-year proxy on precisely the same sample as (2).
4. `joint_matched`: current and lagged proxy together on that same sample.

The sensitivities are `all_years` and `exclude_2020_2021`. The latter removes
2020 and 2021 outcomes and, for **all matched models**, also removes rows whose
lag exposure year is 2020 or 2021. Thus a complete sensitivity has matched
outcome years **2019 and 2023** (not 2022 with a 2021 exposure). This is a
strict, short-panel robustness check, not a claim to remove pandemic effects
from overlapping ACS windows or later county conditions.

Models with inadequate counties/years, rank deficiency, zero within-outcome
variation, no residual degrees of freedom, or invalid inference are reported as
not estimable rather than publishing a pseudoinverse coefficient as identified.
Diagnostics report rank, residual degrees of freedom, county clusters, singleton
counties, within variation, overall/within R², RMSE, condition number and maximum
leverage. Fitted values and residuals are exported. Shared population denominators,
reverse causality, time-varying county confounders, spatial/cross-county dependence,
small clusters, and measurement error remain limitations. Lags and fixed effects
do not identify a causal effect or establish out-of-sample predictive performance.

## Outputs and execution

`run()` saves the processed `panel_county_year.csv`, calls `save_table` for:

- `panel_county_year`, `panel_acquisition`, `panel_coverage`, `panel_annual_summary`;
- `panel_coefficients`, `panel_model_diagnostics`, `panel_model_samples`;
- `panel_coefficient_covariance`, `panel_residuals`, `panel_correlations_covariance`.

Correlations export pairwise complete-case sample sizes, Pearson/Spearman and
sample covariance (`ddof=1`), both pooled and after removing county/year effects
by least squares. This projection is valid for an unbalanced panel; simply
subtracting two means once need not be. Residual sample covariance uses `n-1`,
not a regression-unbiased residual variance estimator. Correlations have no
causal or independent-observation significance claim. Annual trend totals and
denominators use the **same paired observed counties**, with coverage exported.

PNG and SVG charts show annual rates, coverage, matched within associations,
clustered coefficient intervals, and matched-current residual/QQ diagnostics
when estimable. Titles identify the proxy and applications distinction.

`record_status("panel", ...)` records complete/partial/blocked coverage, failed
source reasons, output paths and caveats. Failed year/source downloads retain
the 372-row grid and do not silently narrow the geographic scope. A complete
status requires all inputs, 372 usable current rows and all eight estimable
models. Run through the project's main entrypoint; focused validation is
`python -m pytest tests/test_panel.py`.
