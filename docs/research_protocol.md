# EconHack 2026 research protocol

**Implementation-aligned methods record, updated 2026-10-20.** This document describes the models actually implemented in `src/econhack/nyc.py` and `src/econhack/panel.py` and the saved run outputs. The code and analysis plan were developed in the same work session, and results are already available. These analyses are **exploratory**, not a registered or prospectively fixed preanalysis plan. Directional hypotheses below describe research questions, not evidence that choices preceded inspection of results.

The provided source notes were reviewed; the exact earlier assistant discussion is unavailable in the supplied material. See the [source review](source_notes_review.md) for research context and unresolved claims, and the [student brief](hackathon_brief.md) for the proposed challenge.

## Implemented scope and current status

| Analysis | Actual unit and sample | Status and interpretation |
| --- | --- | --- |
| NYC access equity | 2,190 NYC census tracts; current selected-facility snapshot and ACS 2019–2023 | Estimated; equal-tract geographic association |
| Access and modeled loneliness | 2,190 NYC tracts; CDC PLACES 2025 crude `LONELINESS`, reference year 2023 | Estimated exploratory association with a modeled area outcome and later facility snapshot |
| Commercial establishments and applications | All 62 New York counties, 2018–2023; 372 county-year rows before lag/sample restrictions | All eight county/year fixed-effects specifications estimated; observational associations |
| Library difference-in-differences | No verified event/outcome/comparison panel | `not_estimated`; conditional future design only |

These statuses and samples come from [model status](../outputs/model_status.json), [NYC equity attrition](../outputs/qa/nyc_equity_attrition.json), [loneliness attrition](../outputs/qa/loneliness_attrition.json), and [panel diagnostics](../outputs/tables/panel_model_diagnostics.csv). They describe the saved run, not a guarantee that a later source refresh will reproduce its coverage.

## Actual inputs and provenance

| Input | Implemented use | Essential distinction |
| --- | --- | --- |
| Census ACS 2019–2023 five-year tables `B01003`, `B19013`, `B17001`, `B01001` | NYC tract population, median household income, poverty, and age composition | Five-year period estimates; negative sentinel values become missing; source margins of error are retained but not propagated into regression uncertainty |
| Census 2023 New York tract Gazetteer | `ALAND_SQMI`, `INTPTLAT`, and `INTPTLONG` | Land area in square miles and geographic internal points, not population-weighted origins or entrances |
| NYC DCP Facilities Database, `ji82-xba5` | Frozen current snapshot; selected facility types and coordinates | A conservative facility inventory, not all commercial/noncommercial third spaces or verified usable access |
| CDC PLACES 2025 tract data, `cwsq-ngmh` | New York `LONELINESS`, crude prevalence, reference year 2023; point estimates and source confidence limits | Modeled adult area prevalence, not an individual survey of each tract or a youth-specific outcome |
| Census CBP annual county files, 2018–2023 | Establishment count `est`/`ESTAB`, NAICS `722515`, 2017 NAICS vintage | Employer snack and nonalcoholic beverage establishments; a stock, not new café openings |
| Census BFS annual county workbook | County business applications, 2018–2023, across the series' industry universe | Applications, not realized startups, formations, employment, or café-specific applications |
| ACS annual five-year `B01003` county releases, 2018–2023 | Each year's population denominator for both county rates | 2018 means 2014–2018 population; 2023 means 2019–2023 population. No annual Population Estimates Program denominator is used |

Exact acquisition URLs, cached-source hashes, and reuse notes are in [the raw manifest](../data/manifest.json) and [data licenses](../DATA_LICENSES.md); processed-file provenance is in [the processed manifest](../data/processed_manifest.json). Detailed model documentation is available for [NYC equity](models/nyc_equity.md), [loneliness](models/loneliness.md), and [the county panel](models/panel.md). The NYC library GIS and parks-acquisition supplements are downloaded and audited separately; they are not added to the FacDB exposure, which avoids cross-source double counting. Park-acquisition geometries are not a verified inventory of distinct park openings.

County FIPS remain five-character strings and tract GEOIDs eleven-character strings. NYC is restricted to its five borough-counties; the panel covers the entire state. ACS/Gazetteer joins and CDC joins are validated one-to-one. County inputs join to an explicit county-year grid. Source status distinguishes missing, suppressed, invalid, and numeric-zero observations; missing outcomes or suppressed counts are not silently filled with zero. An observed zero nearby-facility count means none of the selected valid-coordinate records lies in that radius, not that no usable third space exists.

## Model A: NYC tract access equity

### Exposure and covariate definitions

For tract `i`, let `A_i(r)` count selected, valid-coordinate FacDB sites within `r` meters great-circle distance of its Gazetteer internal point:

```text
A_i(r) = Σ over selected sites s I(great_circle(internal_point_i, site_s) ≤ r)
log_access_i = ln(1 + A_i(800))
log_income_i = ln(median_household_income_i)
population_density_i = population_i / ALAND_SQMI_i
log_density_i = ln(1 + population_density_i)
```

The implemented spherical calculation uses Earth radius 6,371,008.8 meters. The main radius is **800 m**, with **400 m and 1,200 m** equity sensitivity fits. Counts can cross tract boundaries and are not divided by tract population. The auxiliary `within_tract_count` is not the main regression outcome. These are geographic supply measures, not pedestrian routes, 15-minute walking coverage, a TPI percentile, or an all-venue density.

The exact allow-list is in [facility selection QA](../outputs/qa/facility_selection.json). It covers specified public/branch library types, specified parks/playgrounds, recreation-center types, the generic NYCHA community-center type, and senior centers. Specialized/academic libraries and ambiguous NYCHA facility types are excluded. Valid-coordinate sites are deduplicated by category and coordinates rounded to five decimal places; this can merge distinct co-located facilities. Invalid coordinates are excluded from radius counts. Categories are not proof of free entry, current operation, youth eligibility, accessibility, quality, or welcoming conditions.

| Predictor | Actual definition and coefficient scale |
| --- | --- |
| `log_income` | Natural log of ACS median household income in 2023 dollars; nonpositive income becomes missing |
| `poverty_pct` | `100 × B17001_E002 / B17001_E001`; poverty-status universe, not total residents |
| `youth_pct` | Percentage of total residents ages **15–24**, summed across sexes from `B01001` |
| `older_pct` | Percentage of total residents ages **65+**, summed across sexes from `B01001` |
| `log_density` | `ln(1 + population / land square miles)`; not density per square kilometer |
| `C(borough)` | Borough fixed effects, represented by indicators with an intercept/reference borough |

All percentage predictors are on a **0–100 scale**: one unit is one percentage point. Age counts require all constituent cells; incomplete sums do not become observed totals. No education, unemployment, vehicle-access, or other additional control enters this main model.

### Actual fitted model and sample

```text
log_access ~ log_income + poverty_pct + youth_pct + older_pct
             + log_density + C(borough)

ln(1 + A_i(800)) = α + β_income ln(income_i) + β_poverty poverty_pct_i
                    + β_youth youth_pct_i + β_older older_pct_i
                    + β_density ln(1 + population_i / land_sqmi_i)
                    + δ_borough(i) + ε_i
```

The conceptual hypotheses are positive income and negative poverty/youth associations; the older-adult association is examined without assigning an assumed direction. These are exploratory hypotheses, not registered tests. Borough fixed effects absorb borough-level means; they do not remove all neighborhood confounding.

Start with 2,327 matched NYC tracts, retain the 2,225 with **population ≥100**, then remove incomplete/nonfinite model rows. The realized complete-case sample is **n = 2,190**. Unweighted OLS gives each tract equal weight. There is no population-weighted main fit or resident-average estimand.

A percentage-predictor coefficient describes a one-percentage-point difference in the log outcome. For two fitted values differing by `Δ`, `exp(Δ)` is a ratio of fitted `1 + count` values on the transformed scale; it is not automatically a ratio of observed facility counts or an unbiased arithmetic-mean prediction. Do not report a coefficient as a change in the raw count without an explicit justified back-transformation.

### Implemented diagnostics and sensitivities

- **Main uncertainty:** HC3 heteroskedasticity-robust covariance. It does not address residual spatial dependence, ACS sampling error, or measurement error in facility access.
- **Radius sensitivity:** refit the same equity equation on the same complete-case tracts using `ln(1 + nearby_400m)`, `ln(1 + nearby_800m)`, and `ln(1 + nearby_1200m)` as the outcome, with HC3 intervals. See [radius results](../outputs/tables/nyc_equity_radius_sensitivity.csv).
- **Spatial covariance sensitivity:** refit the same 800 m equation with finite-sample-corrected cluster covariance and t inference using approximate **2 km geographic tiles**. The saved sample contains **226 tiles**. The bins are `floor(latitude × 111.2 / 2)` and `floor(longitude × 84.3 / 2)`. This is grid clustering, not Conley/spatial-HAC covariance; dependence across tile borders remains possible. See [tile results](../outputs/tables/nyc_equity_spatial_cluster_sensitivity.csv).
- **Residual Moran diagnostic:** eight directed nearest neighbors based on spherical positions, row-standardized weights, **499 permutations**, and random seed **2026**. For centered residuals `z`, the statistic is `I = z'Wz / z'z`; weights sum to the number of tracts. The two-sided permutation comparison is centered at `-1/(n-1)` and uses `(1 + extreme permutations)/500`. It diagnoses geographic dependence; it is not a covariance correction or a causal test. See [spatial QA](../outputs/qa/nyc_equity_spatial.json).
- **Other saved diagnostics:** correlations/covariances, VIF, design rank/condition number, Breusch–Pagan, and residual/QQ displays. Income-quintile summaries use equal-tract groups from `qcut` and report tract counts plus mean/median **800 m counts**; they are not population-weighted per-capita gaps.

Use the [coefficient table](../outputs/tables/nyc_equity_coefficients.csv) and QA outputs to inspect actual estimates rather than assuming the hypothesized signs. Spatial clustering is a sensitivity, not assurance that uncertainty is fully corrected.

## Model B: access and modeled adult loneliness

The implemented outcome is `loneliness_pct`: **crude modeled adult `LONELINESS` prevalence in percentage points**, CDC PLACES **2025 release**, reference year **2023**. The pipeline joins exact tract GEOIDs, retains the source confidence bounds and year, and uses the same population threshold and complete-case procedure as Model A. The saved sample is **n = 2,190**, with no outcome substitution or missing-to-zero imputation.

### Actual fitted model

```text
loneliness_pct ~ log_access + log_income + poverty_pct + youth_pct
                 + older_pct + log_density + C(borough)

L_i = α + β_access ln(1 + A_i(800)) + θ_income ln(income_i)
        + θ_poverty poverty_pct_i + θ_youth youth_pct_i
        + θ_older older_pct_i + θ_density ln(1 + population_i / land_sqmi_i)
        + δ_borough(i) + u_i
```

Every predictor uses the same definition as Model A, including **ages 15–24** for `youth_pct`; the code does **not** switch to an 18–24 covariate. That area-composition predictor does not make the adult outcome a youth loneliness measure. The exploratory hypothesis is `β_access < 0`, not an assumed result.

The main fit is equal-tract OLS with HC3 covariance. The adjustment comparison is exactly `loneliness_pct ~ log_access + C(borough)` versus the full equation on the same rows; the borough-only model is not a completely unadjusted bivariate regression. The same **2 km tile-cluster sensitivity and 499-permutation residual Moran procedure** are implemented for the full loneliness model. The radius refits described in Model A are equity fits; no loneliness 400/1,200 m fit is claimed here.

`β_access` is a percentage-point difference in modeled tract prevalence per natural-log unit of `1 + selected-facility count`. It is not an individual response to visiting a site or a policy effect. Inspect [coefficients](../outputs/tables/access_loneliness_coefficients.csv), [adjustment sensitivity](../outputs/tables/loneliness_adjustment_sensitivity.csv), [tile sensitivity](../outputs/tables/access_loneliness_spatial_cluster_sensitivity.csv), and [spatial QA](../outputs/qa/access_loneliness_spatial.json).

### Measurement and temporal limits

The **current FacDB snapshot is later than the 2023 outcome reference period**. The model does not reconstruct historical facilities or establish that exposure preceded loneliness. ACS demographic inputs also describe a five-year period rather than a single matching day/year.

PLACES is a generated area outcome incorporating demographic/poverty information. Adjustment with related ACS covariates can partly reproduce its prediction structure. HC3 and tile-cluster intervals do not propagate CDC modeled-outcome uncertainty, source confidence bounds, shared prediction error, or ACS margins of error. Crude prevalence also reflects age composition. These limits apply even if coefficients appear statistically significant.

Earlier social-isolation wording and current loneliness wording are not interchangeable independent outcomes or an automatically comparable time series. The [CDC definition](https://www.cdc.gov/places/measure-definitions/health-related-social-needs.html), [release notes](https://www.cdc.gov/places/current-release-notes/index.html), and [FAQ](https://www.cdc.gov/places/faqs/index.html) govern interpretation. Modeled estimates are unsuitable for evaluating a local third-space or library intervention. Ecological findings cannot identify individual causal effects or outcomes specifically among young people.

## Model C: actual New York county CBP/BFS panel

### Measures, universe, and timing

The implemented grid contains **all 62 New York State counties × 2018–2023 = 372 rows**. All current rows are usable in the saved run. CBP exposure is NAICS **722515, Snack and Nonalcoholic Beverage Bars**, using **2017 NAICS across these six releases**. It is an employer-establishment proxy broader than cafés and omits many nonemployer and noncommercial gathering places. BFS is the county's all-covered-industry application flow, not realized new businesses.

```text
R_ct = 10,000 × proxy_establishments_ct / population_acs5_ct
Y_ct = 10,000 × business_applications_ct / population_acs5_ct
R_c,t-1 = the prior calendar year's R for the same county
```

The denominator for year `t` is that year's ACS **five-year** `B01003` release, covering `t-4` through `t`. The lag uses the **prior year's rate and prior year's denominator**, joined at exactly `year-1`; it does not bridge missing years. Because no 2017 exposure is acquired, 2018 has no lag in this panel.

CBP is a stock and BFS a flow, so contemporaneous timing does not establish precedence. BFS follows IRS processing-year boundaries; the saved panel documentation notes 53 weeks in 2020 versus 52 in other sample years. Disclosure noise and later revisions also limit literal interpretation of application counts, including published zeros.

### Actual equations and eight specifications

Both dependent and explanatory rates are in **levels**, not `log(1 + rate)`:

```text
Current-only:  Y_ct = α_c + λ_t + β_current R_ct + ε_ct
Lag-only:      Y_ct = α_c + λ_t + β_lag R_c,t-1 + ε_ct
Joint:         Y_ct = α_c + λ_t + β_current R_ct + β_lag R_c,t-1 + ε_ct
```

All fits are unweighted OLS with an intercept, **county fixed effects and year fixed effects**. There are **no income, unemployment, education, log-population, or other additional controls**. The positive-association hypothesis is exploratory; neither fixed effects nor a lag removes time-varying confounding or simultaneity.

| Saved specification | Exposure terms | Observed outcome years | n |
| --- | --- | --- | ---: |
| `current_all_years` | Current rate | 2018–2023 | 372 |
| `current_matched_all_years` | Current rate, on common current/lag sample | 2019–2023 | 310 |
| `lag1_matched_all_years` | Lagged rate, same matched sample | 2019–2023 | 310 |
| `joint_matched_all_years` | Current and lagged rates, same matched sample | 2019–2023 | 310 |
| `current_exclude_2020_2021` | Current rate | 2018, 2019, 2022, 2023 | 248 |
| `current_matched_exclude_2020_2021` | Current rate, on restricted matched sample | 2019, 2023 | 124 |
| `lag1_matched_exclude_2020_2021` | Lagged rate, same restricted matched sample | 2019, 2023 | 124 |
| `joint_matched_exclude_2020_2021` | Current and lagged rates, same restricted matched sample | 2019, 2023 | 124 |

Each fitted specification retains all **62 county clusters**. The exclusion sensitivity removes 2020/2021 outcomes and, for every matched specification, also removes observations whose lag exposure is from 2020/2021. This removes 2022 from the matched sensitivity because its lag is 2021. The strict sensitivity leaves only two outcome years; it does not remove pandemic influence from overlapping ACS windows or subsequent conditions. The current-only exclusion model has a different sample from the matched models.

A slope measures applications per 10,000 residents associated with one additional proxy establishment per 10,000 residents, conditional on county/year effects. It is not an elasticity, an additional application per individual venue, a café-opening treatment effect, or an estimate of business births.

### Implemented inference and diagnostics

Standard errors **cluster by county**, with finite-sample sandwich and degrees-of-freedom corrections. The saved run uses t inference and 95% intervals with **G−1 = 61** cluster degrees of freedom. The code checks county/year support, design rank, residual degrees of freedom, within-outcome variation, and finite inference before labeling a fit estimated.

Diagnostics include within-exposure variation, overall/within R², RMSE, condition number, leverage, fitted values, and residuals. Pooled and county/year-residualized correlations/covariances are descriptive; fixed effects are removed by least-squares projection rather than a single double-demeaning shortcut. Results and membership are inspectable in [coefficients](../outputs/tables/panel_coefficients.csv), [diagnostics](../outputs/tables/panel_model_diagnostics.csv), and [model samples](../outputs/tables/panel_model_samples.csv).

County clustering handles within-county serial dependence under its assumptions; it does not correct correlation across counties. No county-panel spatial-HAC fit, state-cluster fit, or two-way county/year-cluster fit is implemented. With only six years, dependence and short-panel sensitivity remain material. Both rates share a population denominator, and overlapping ACS windows smooth changes and share sampling error; denominator uncertainty is not propagated. Endogenous business location, growth expectations, rents, and omitted local investment can affect both variables.

This county analysis does not replicate the neighborhood Starbucks study discussed in the source review: its exposure, application outcome, geography, and identification differ. No coefficient should become a guaranteed local policy payoff.

## Model D: library DiD remains unimplemented

**Status: `not_estimated`.** Downloaded library locations or facility snapshots do not verify treatment dates, untreated comparisons, or repeated local outcomes. No library coefficient, event-study chart, standard error, or power result is available. The controlling future-design specification is [library DiD](models/library_did.md).

The future resident-level policy question concerns areas receiving a verified sustained access expansion, using fixed residential catchments and a directly observed repeated local outcome. Operational branch visits/circulation would answer a separate use question and would not establish resident loneliness effects. A common-date representation, conditional on a valid area-period panel, would be:

```text
Y_it = α_i + λ_t + τ × (Treated_i × Post_t) + ε_it
```

Before estimating anything, verify implemented service dates/doses, a compatible sustained-treatment definition, stable geography, consistent pre/post observations, comparison eligibility, and sufficient independent treatment clusters. Assess parallel untreated trends, anticipation, spillovers, endogenous investment timing, and concurrent changes. For staggered sustained adoption, the future design uses cohort-time `ATT(g,t)` with eligible never-treated/not-yet-treated comparisons, not naive already-treated controls. Specify outcomes, windows, weights, and inference before that future estimation; this does not imply the existing analyses were preregistered. CDC PLACES is not an intervention outcome, and a failure to reject a pretrend test would not prove parallel trends.

## Extensions — UNIMPLEMENTED

The following are possible future work, **not fitted models or completed sensitivity checks in the current outputs**:

- Adding county income, unemployment, education, population controls, or other time-varying adjustment; these would change the current panel specification and require new data/measurement checks.
- Poisson pseudo-maximum likelihood on application counts with a population offset, alternative log-rate equations, or further denominator sensitivities. No PPML coefficient, fit, or inference is claimed.
- Pedestrian-network/entrance-based catchments, population-weighted origins, verified opening hours/fees/eligibility, or resident-weighted regressions. Great-circle counts cannot be relabeled as these access measures.
- Conley/spatial-HAC covariance or alternative spatial partitions beyond the implemented 2 km tile check. Tiles do not establish robustness to all spatial dependence.
- TPI-based exposure, education-adjusted NYC regressions, or population-weighted income-quintile gaps. TPI is optional and recorded as `not_downloaded` in the saved run; it is not an input to the actual NYC fits.
- Propagating ACS sampling uncertainty and CDC shared modeled-outcome uncertainty, or completing the gated library evaluation.

Any extension should document its motivation, code/data changes, sample, results, and exploratory status. Do not describe a post-result revision as prespecified.

## Reporting limits and separate ATUS context

Report the actual equation, transformation, units, weights, sample, observation/reference periods, source snapshot, fixed effects, and covariance method alongside every result. Distinguish source confidence bounds from regression intervals. Retain all eight county specifications and declared NYC sensitivities rather than selecting a preferred sign. Facility counts measure supply, not attendance or experienced connection; area correlations do not establish individual outcomes, and fixed effects do not cure simultaneity.

The separate [ATUS specification](models/atus.md) targets 2003–2024 socializing and communicating among ages 15–24 and all ages 15+. The saved status records an unsuccessful official-file download (HTTP 403), so that run supplies no new ATUS estimates. The notes' **61 → 35 minutes, 2003 → 2025, ages 15–24** claim remains unverified, and “face-to-face” is not an established interpretation of that activity series. National time-use context is not a tract covariate or an identification strategy for the implemented NYC/county models.
