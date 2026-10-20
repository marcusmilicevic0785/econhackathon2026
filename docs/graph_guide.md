# How these graphs help students do research

The graphs help students move from a policy idea to a question they can test, check what their data measure, compare explanations, and communicate uncertainty. They are evidence for a research argument, not illustrations that automatically prove a preferred policy.

Start with the [student worksheet](student_worksheet.md). No coding is needed to read the PNG images or open the CSV tables in a spreadsheet. The [executed notebooks](../notebooks) expose the calculations for students who want to go further. Each image also has an SVG version in the same folder for clear presentation slides.

## Choose a graph for the question

| Student question | Start with | What it teaches |
|---|---|---|
| Has time spent socializing changed? | [Socializing trend](../outputs/figures/atus_published_trend.png) | Time trends, units, missing years, and the difference between describing change and explaining it |
| Which neighborhoods have more selected nearby facilities? | [NYC access equity](../outputs/figures/nyc_access_equity.png) | Distributions, income groups, medians, and checking an assumption against observed data |
| Does the association remain after adjustment? | [NYC coefficients](../outputs/figures/nyc_equity_coefficients.png) | Regression coefficients, comparison groups, control variables, and uncertainty |
| Are facilities associated with loneliness? | [Loneliness scatter](../outputs/figures/access_loneliness_scatter.png) and [coefficients](../outputs/figures/access_loneliness_coefficients.png) | Raw versus adjusted relationships, confounding, ecological inference, and modeled outcomes |
| Are commercial venues associated with economic activity? | [County trends](../outputs/figures/panel_annual_trends.png), [within-county relationships](../outputs/figures/panel_within_associations.png), and [coefficients](../outputs/figures/panel_coefficients.png) | Rates, fixed effects, lags, matching samples, and robustness |
| Can we trust the coverage and model fit? | [County coverage](../outputs/figures/panel_coverage.png) and the three diagnostic figures below | Missingness, residuals, outliers, and model limitations |
| Would a different definition of third spaces change the story? | [Index comparison](../outputs/figures/third_place_index_aggregate_comparison.png) | Measurement choices and agreement between sources |

## 1. Socializing trend: describe a problem before explaining it

**Read:** [atus_published_trend.png](../outputs/figures/atus_published_trend.png). The horizontal axis is diary year; the vertical axis is average minutes per person per day. The series describes all persons age 15+, including people reporting zero time in the activity. It is not the requested age-15–24 series and is not a measure of every face-to-face interaction.

**Learn:** distinguish an endpoint difference from a steady annual change. The published values imply 46.8 minutes/day in 2003 and 35.4 in 2024: a difference of −11.4 minutes, approximately −24.4%. These are conversions of rounded hours. The line has fluctuations, and 2020 is intentionally missing.

**Use in research:** motivate a question about opportunities to connect, then investigate competing explanations. Neither the decline nor its timing establishes that third-space closures caused it. The graph contains no venue-history variable and cannot establish a youth-specific trend.

**Try:** calculate the absolute and percentage changes in a spreadsheet. Explain why the gap must not be filled with zero or connected as if a comparable 2020 estimate existed.

**Evidence:** [annual values](../outputs/tables/atus_published_annual.csv), [descriptive regression](../outputs/tables/atus_published_regression.csv), [notebook 04](../notebooks/04_socializing_trend.ipynb), [methods](models/atus_published.md).

## 2. NYC access equity: test whether the expected pattern exists

**Read:** [nyc_access_equity.png](../outputs/figures/nyc_access_equity.png). Each point in the left panel is a tract in the analysis sample. The vertical axis counts selected facilities within 800 metres of its Census internal point. The right panel groups the same 2,190 tracts into income quintiles and shows medians, not total sites or person-weighted averages.

**Learn:** individual points show variation that a group average can hide. A median describes the middle tract in its group; it does not describe every resident or neighborhood. The displayed quintile medians are 8, 5, 4, 3, and 5 from lowest to highest income. That is not a simple increasing income gradient.

**Use in research:** check a claim such as “richer neighborhoods always have more public gathering places.” If the evidence does not match the claim, revise the claim or investigate the measurement. The inventory emphasizes selected parks, libraries, senior centers, and generic community centers; it is not an inventory of every café or welcoming place.

**Try:** compare the median with the mean for each quintile. Identify how a few well-supplied tracts can affect the mean. Discuss how population, density, hours, public eligibility, and walking barriers could change the interpretation.

**Evidence:** [quintile table](../outputs/tables/nyc_equity_income_quintiles.csv), [tract inputs](../data/processed/nyc_access.csv), [notebook 01](../notebooks/01_nyc_access_equity.ipynb), [methods](models/nyc_equity.md).

## 3. NYC coefficient plot: understand conditional associations

**Read:** [nyc_equity_coefficients.png](../outputs/figures/nyc_equity_coefficients.png). A dot is an estimated regression coefficient. The horizontal line is a 95% HC3 interval. The vertical reference at zero helps show which intervals include zero. The model adjusts for borough and the other included variables.

**Learn:** a conditional association can differ from the raw pattern. “Holding included variables constant” describes a model comparison; it does not mean researchers randomly assigned neighborhoods to income or age composition.

**Use in research:** explain why an age, poverty, or income relationship may partly reflect neighborhood density or borough differences. Consult the [spatial-cluster sensitivity](../outputs/tables/nyc_equity_spatial_cluster_sensitivity.csv) alongside the plotted HC3 intervals. Nearby tracts are not independent just because they have different identifiers.

**Try:** find the income term in both interval tables. Explain why a coefficient with an interval crossing zero does not prove that the population association is exactly zero. Compare the [400/800/1,200 m results](../outputs/tables/nyc_equity_radius_sensitivity.csv) to ask whether the definition of “nearby” matters.

**Important:** the outcome is ln(1+facility count), not a raw count. Shares are measured in percentage points, while income and density are logged. Do not rank the importance of predictors by their plotted coefficient magnitudes: their units differ. Borough effects are in the table but omitted from the coefficient figure.

**Evidence:** [coefficients](../outputs/tables/nyc_equity_coefficients.csv), [model formula and units](models/nyc_equity.md).

## 4. Loneliness scatter: separate the observation from the explanation

**Read:** [access_loneliness_scatter.png](../outputs/figures/access_loneliness_scatter.png). Each dot is a tract, not a person. The vertical axis is CDC's modeled crude adult loneliness prevalence. The horizontal axis is selected nearby facility supply.

**Learn:** a scatterplot can show clusters, overlap, spread, and possible nonlinear patterns without establishing why they occur. Many dots at the same integer facility count form vertical columns; this is not a time trend.

**Use in research:** propose and compare explanations: age composition, poverty, residential selection, facility placement, measurement, or other neighborhood conditions. Current facility supply is paired with an earlier 2023 outcome, so the graph cannot establish exposure before outcome.

**Try:** write two explanations that could produce the same pattern. For each, name one additional variable or research design needed to distinguish it from the other explanation. Do not infer that a particular library user is less lonely from a tract-level pattern.

**Evidence:** [matched tract data](../data/processed/nyc_loneliness.csv), [notebook 02](../notebooks/02_access_loneliness.ipynb), [methods](models/loneliness.md).

## 5. Loneliness coefficients: communicate uncertainty honestly

**Read:** [access_loneliness_coefficients.png](../outputs/figures/access_loneliness_coefficients.png). The outcome is in percentage points. The access coefficient is per natural-log unit of (1+nearby facilities), not per additional facility.

**Learn:** adjustment changes the question. The [comparison table](../outputs/tables/loneliness_adjustment_sensitivity.csv) contrasts a borough-only specification with the fuller model on the same rows. The plotted access estimate is negative, but its HC3 interval crosses zero; the spatial sensitivity is wider.

**Use in research:** practice saying, “This specification has an imprecise adjusted association,” rather than “Third spaces do not work” or “More parks reduce loneliness.” CDC estimates already use demographic/contextual inputs, so apparent associations with similar covariates can partly reflect the outcome's construction. Regression intervals do not propagate all CDC or ACS uncertainty.

**Try:** write a 30-word results sentence giving the direction, uncertainty, unit of analysis, and one limitation. Use the [spatial sensitivity](../outputs/tables/access_loneliness_spatial_cluster_sensitivity.csv) to check whether the same sentence remains defensible.

**Evidence:** [coefficient table](../outputs/tables/access_loneliness_coefficients.csv), [methods](models/loneliness.md).

## 6. County annual trends: choose the right denominator

**Read:** [panel_annual_trends.png](../outputs/figures/panel_annual_trends.png). The two panels show snack/nonalcoholic beverage employer establishments and business applications per 10,000 residents. Read each panel's scale separately. The shading identifies 2020–2021; it does not estimate a pandemic effect.

**Learn:** rates make differently sized populations more comparable. Both rates share the ACS population denominator, which can also create a relationship mechanically. Annual ACS five-year releases overlap, so these are smoothed period denominators rather than independent annual population measurements.

**Use in research:** describe changes in the paired observed counties before fitting a model. Two statewide series moving together cannot establish a within-county relationship or a causal mechanism.

**Try:** reconstruct a rate as 10,000 × count / population. Explain why the county's number of business applications is not a count of successful new businesses, and why NAICS 722515 is broader than cafés.

**Evidence:** [annual summary](../outputs/tables/panel_annual_summary.csv), [county-year inputs](../data/processed/panel_county_year.csv), [notebook 03](../notebooks/03_county_panel.ipynb), [methods](models/panel.md).

## 7. County coverage: missing data can change the answer

**Read:** [panel_coverage.png](../outputs/figures/panel_coverage.png). The lines count counties with observed usable source values; 62 is the intended NY county universe. This snapshot has complete current-model coverage across 2018–2023.

**Learn:** complete coverage is a finding to verify, not an assumption. Missing, suppressed, and observed-zero values mean different things. The first year's missing lag is expected and does not mean that source coverage failed.

**Use in research:** check whether a changing sample, rather than changing conditions, could explain a trend. Complete coverage does not establish that the measures are perfectly accurate or suitable for a different research question.

**Try:** compare 372 current-model observations with 310 matched current/lag observations. Explain the difference using 62 counties and the exact prior-year requirement.

**Evidence:** [coverage table](../outputs/tables/panel_coverage.csv), [model diagnostics and samples](../outputs/tables/panel_model_diagnostics.csv).

## 8. Within-county scatterplots: learn what fixed effects remove

**Read:** [panel_within_associations.png](../outputs/figures/panel_within_associations.png). Both axes contain values after projecting out county and year effects. They are not raw rates: a negative plotted value is a negative residual, not a negative number of applications or establishments.

**Learn:** counties can differ in stable ways, and statewide annual shocks can move many counties together. These graphs ask about the remaining relationship after removing those modeled differences. The current and lagged panels use the same matched sample.

**Use in research:** compare a pooled relationship with a within-county relationship. Fixed effects do not remove time-varying local confounding, and lagging an exposure does not make its variation random.

**Try:** explain what the origin means and why a point far from it deserves investigation. Consult the [pooled and residualized correlations](../outputs/tables/panel_correlations_covariance.csv).

## 9. County coefficient comparison: test robustness, not preferred signs

**Read:** [panel_coefficients.png](../outputs/figures/panel_coefficients.png). Each row corresponds to a model term. Bars are 95% county-clustered t intervals, not the observed spread of counties. “Matched” means the current/lag comparison uses identical observations. “Joint” includes current and lagged exposure together.

**Learn:** estimates can change when the sample or model changes. The pandemic-excluded matched models retain only 2019 and 2023 outcome years because they also exclude pandemic exposure years. This makes that sensitivity especially short and imprecise.

**Use in research:** report all declared comparisons, not just the row with a favored sign or smallest p-value. The plotted intervals cross zero in this snapshot. A positive point estimate does not establish that subsidizing cafés will create businesses.

**Try:** compare current and lagged estimates on the matched sample. State the coefficient's units: applications per 10,000 residents per additional proxy establishment per 10,000 residents. Explain why a high overall R-squared can coexist with little additional within-county explanatory power.

**Evidence:** [coefficients](../outputs/tables/panel_coefficients.csv), [diagnostics](../outputs/tables/panel_model_diagnostics.csv), [methods](models/panel.md).

## 10–12. Diagnostic figures: ask whether the model leaves structure behind

| Figure | Read it this way | Research response |
|---|---|---|
| [NYC equity diagnostics](../outputs/figures/nyc_equity_diagnostics.png) | Left: residual versus fitted transformed supply. Right: residual quantiles against a normal reference. | Look for curvature, changing spread, and extreme points; consider specification and measurement explanations. |
| [Loneliness diagnostics](../outputs/figures/access_loneliness_diagnostics.png) | The same checks, now for modeled prevalence residuals. | Consider shared demographic inputs and spatial dependence; a smooth fit is not independent validation of CDC estimates. |
| [County panel diagnostics](../outputs/figures/panel_residual_diagnostics.png) | Residuals from the matched contemporaneous FE model. | Investigate influential observations and serial/spatial dependence using the exported diagnostics. |

**Learn:** a residual is observed outcome minus fitted outcome. Patterns around zero can reveal aspects the model did not capture. A QQ departure does not by itself invalidate OLS coefficients; a straight QQ line does not establish causality, independence, or a correct model. Robust or clustered standard errors address specified dependence problems, not every misspecification.

**Try:** sketch the residual pattern you would expect if a linear model missed a curved relationship. Then explain why deleting unusual observations simply to improve the picture would be inappropriate. Any alternative sample or model must have a stated reason and be reported alongside the original.

## 13. Index comparison: definitions are part of the research

**Read:** [third_place_index_aggregate_comparison.png](../outputs/figures/third_place_index_aggregate_comparison.png). Bars are Spearman rank correlations between the independent index's broad within-tract venue count and several official selected-facility measures, across 2,327 matched NYC tracts. They are not counts, effect sizes, or confidence intervals.

**Learn:** sources can rank neighborhoods differently because they measure different constructs. The 800 m comparison is 0.240. That is rank agreement; it is not “24% of access explained,” and it is not proof that either dataset is wrong.

**Use in research:** justify whether “third spaces” means public facilities, commercial venues, nearby supply, within-tract supply, or usable places. Treat alternative definitions as a measurement sensitivity. Do not redistribute row-level TPI data from the local restricted folder without resolving the source terms.

**Try:** list three reasons the measures could disagree: category scope, geographic catchment, source coverage, or observation period. Explain what a site audit or resident consultation could add.

**Evidence:** [aggregate comparison](../outputs/tables/third_place_index_comparison.csv), [source audit](models/third_place_index.md).

## Correlations and covariances alongside the graphs

The notebooks and CSVs include both. Covariance records how variables vary together and depends on their units; Pearson correlation standardizes covariance and ranges from −1 to 1. Neither proves causation, and a weak linear correlation can miss a curved pattern. Spearman correlation compares ranks rather than raw distances between values. Always state the sample and whether variables are pooled or residualized.

## Build a defensible research argument

1. **Question:** define the population, place, period, exposure, and outcome.
2. **Measurement:** explain what the variables capture and miss.
3. **Description:** show one central pattern and the observations behind it.
4. **Explanation:** compare plausible mechanisms and potential confounders.
5. **Robustness:** ask whether the conclusion survives another sample, definition, or covariance method.
6. **Policy:** explain what the evidence supports now and how a proposed intervention would be evaluated.

For a six-slide hackathon presentation, use one descriptive graph, one uncertainty or robustness graph, and an evidence appendix. Select the graphs that answer your question; using every plot does not make the argument stronger. Credit the original sources, state the sample and units, and label any proposed targets or scenarios separately from observed results. No library event-study figure exists because the required credible event/outcome panel has not been established.
