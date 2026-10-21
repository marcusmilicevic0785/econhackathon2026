# Graph guide

The figures are in [outputs/figures](../outputs/figures), as PNGs and SVGs. Each section below links to the data and results behind the graph.

## 1. Socializing time

[View graph](../outputs/figures/atus_published_trend.png)

Average daily socializing time in the published BLS series fell from 46.8 minutes in 2003 to 35.4 in 2024. Those values cover people age 15+, including people who reported no time in the activity. They come from rounded published hours. The category doesn't capture every face-to-face interaction.

There is no comparable 2020 annual observation. The graph shows a national trend, not a youth-specific trend or an explanation for the decline.

[Data](../data/processed/atus_published_annual.csv) · [Trend table](../outputs/tables/atus_published_regression.csv) · [Notebook](../notebooks/04_socializing_trend.ipynb) · [Methods](models/atus_published.md)

## 2. NYC access and income

[View graph](../outputs/figures/nyc_access_equity.png)

Each dot is one of the 2,190 tracts in the model sample. Income is on the horizontal axis; the vertical axis counts selected facilities within 800 metres of the tract's Census internal point. The bars show the median count in each income fifth: **8, 5, 4, 3 and 5**, from lowest to highest income.

This selected public-facility inventory doesn't show a simple increasing income gradient. It includes selected libraries, parks/playgrounds, senior centres and community facilities, not every third space. Distance is straight-line, and entry rules and opening hours haven't been verified. Each tract has equal weight.

[Data](../data/processed/nyc_access.csv) · [Income-group table](../outputs/tables/nyc_equity_income_quintiles.csv) · [Notebook](../notebooks/01_nyc_access_equity.ipynb) · [Methods](models/nyc_equity.md)

## 3. NYC access regression

[View graph](../outputs/figures/nyc_equity_coefficients.png)

The dots are regression estimates after accounting for the other included variables and borough differences. The lines are 95% HC3 confidence intervals. The outcome is $\ln(1+A_i)$, where $A_i$ is the nearby-facility count. Income and population density are also transformed; age and poverty shares are in percentage points. Coefficient sizes aren't directly comparable across those units.

The income interval includes zero. The [spatial-cluster results](../outputs/tables/nyc_equity_spatial_cluster_sensitivity.csv) give a second uncertainty estimate because nearby tracts can share conditions. The [radius comparison](../outputs/tables/nyc_equity_radius_sensitivity.csv) uses 400, 800 and 1,200 metres.

[Data](../data/processed/nyc_access.csv) · [Coefficients](../outputs/tables/nyc_equity_coefficients.csv) · [Notebook](../notebooks/01_nyc_access_equity.ipynb) · [Equation and units](models/nyc_equity.md)

## 4. Access and loneliness

[View graph](../outputs/figures/access_loneliness_scatter.png)

Each dot is a tract, not a person. The graph pairs selected nearby facilities with CDC's modeled adult loneliness prevalence. It shows the raw relationship before the fuller regression adjustment.

The outcome refers to 2023; the facilities come from a later snapshot. Demographics, facility placement and other neighbourhood differences could contribute to the pattern. This isn't evidence that an individual using a facility becomes less lonely.

[Data](../data/processed/nyc_loneliness.csv) · [Notebook](../notebooks/02_access_loneliness.ipynb) · [Methods](models/loneliness.md)

## 5. Loneliness regression

[View graph](../outputs/figures/access_loneliness_coefficients.png)

The access estimate is negative, but its 95% HC3 interval includes zero. The [spatial-cluster interval](../outputs/tables/access_loneliness_spatial_cluster_sensitivity.csv) is wider and also includes zero. That leaves considerable uncertainty about the adjusted association.

The outcome is in percentage points, and access is $\ln(1+A_i)$, not a raw facility count. CDC's area estimates already use demographic/contextual inputs, some related to the regression predictors. The regression intervals don't include all CDC modeling or ACS sampling uncertainty.

[Data](../data/processed/nyc_loneliness.csv) · [Coefficients](../outputs/tables/access_loneliness_coefficients.csv) · [Adjustment comparison](../outputs/tables/loneliness_adjustment_sensitivity.csv) · [Notebook](../notebooks/02_access_loneliness.ipynb) · [Methods](models/loneliness.md)

## 6. County trends

[View graph](../outputs/figures/panel_annual_trends.png)

The panels show snack/nonalcoholic beverage establishments and business applications per 10,000 residents across New York counties. The establishment category is broader than cafés. Applications aren't confirmed business openings.

Both rates use the same population denominator from overlapping ACS five-year estimates. That affects how their movement together can be interpreted. The shaded 2020–2021 period marks the pandemic years; it isn't an estimated pandemic effect.

[Data](../data/processed/panel_county_year.csv) · [Annual summary](../outputs/tables/panel_annual_summary.csv) · [Notebook](../notebooks/03_county_panel.ipynb) · [Methods](models/panel.md)

## 7. County coverage

[View graph](../outputs/figures/panel_coverage.png)

All 62 New York counties have usable current-model values in each year, 2018–2023: 372 county-year rows. The matched current/lag sample has 310 rows because the first year has no prior-year exposure in this dataset. That expected lag gap isn't a failed download.

[Data](../data/processed/panel_county_year.csv) · [Coverage table](../outputs/tables/panel_coverage.csv) · [Sample diagnostics](../outputs/tables/panel_model_diagnostics.csv) · [Notebook](../notebooks/03_county_panel.ipynb)

## 8. Within-county relationships

[View graph](../outputs/figures/panel_within_associations.png)

These plots remove county and year effects from both variables. A negative axis value is a negative residual, not a negative number of establishments or applications. The current and lagged panels use the same matched rows.

The plots show the relationship left after those modeled differences are removed. Changing local conditions can still affect both variables, and a lag doesn't make facility availability random.

[Data](../data/processed/panel_county_year.csv) · [Correlations and covariances](../outputs/tables/panel_correlations_covariance.csv) · [Notebook](../notebooks/03_county_panel.ipynb) · [Methods](models/panel.md)

## 9. County regression comparison

[View graph](../outputs/figures/panel_coefficients.png)

The graph compares current, lagged and joint specifications, including a pandemic-year exclusion. Lines are 95% county-clustered t intervals; the plotted intervals include zero. A coefficient measures applications per 10,000 residents per additional proxy establishment per 10,000 residents.

“Matched” models use the same current/lag sample. The pandemic-excluded matched models retain only 2019 and 2023, because pandemic exposure years are also excluded. Those short comparisons are especially imprecise. County and year effects don't establish a causal effect of café openings.

[Data](../data/processed/panel_county_year.csv) · [Coefficients](../outputs/tables/panel_coefficients.csv) · [Diagnostics](../outputs/tables/panel_model_diagnostics.csv) · [Notebook](../notebooks/03_county_panel.ipynb) · [Methods](models/panel.md)

## 10–12. Model diagnostics

| Figure | What it shows | Inputs and notebook |
| --- | --- | --- |
| [NYC access diagnostics](../outputs/figures/nyc_equity_diagnostics.png) | Residuals against fitted log facility counts, plus a normal-quantile comparison | [NYC access data](../data/processed/nyc_access.csv) · [Notebook 01](../notebooks/01_nyc_access_equity.ipynb) |
| [Loneliness diagnostics](../outputs/figures/access_loneliness_diagnostics.png) | The same checks for the modeled loneliness regression | [NYC loneliness data](../data/processed/nyc_loneliness.csv) · [Notebook 02](../notebooks/02_access_loneliness.ipynb) |
| [County diagnostics](../outputs/figures/panel_residual_diagnostics.png) | Residual checks for the matched current-exposure fixed-effects model | [County data](../data/processed/panel_county_year.csv) · [Notebook 03](../notebooks/03_county_panel.ipynb) |

A residual is the observed outcome minus the fitted value. Curvature, changing spread and extreme points describe what the model leaves unexplained. A straight normal-quantile plot doesn't establish independence or causality. NYC residuals also show spatial dependence, recorded in [access QA](../outputs/qa/nyc_equity_spatial.json) and [loneliness QA](../outputs/qa/access_loneliness_spatial.json).

## 13. Third Place Index comparison

[View graph](../outputs/figures/third_place_index_aggregate_comparison.png)

The bars show Spearman rank correlations across 2,327 matched NYC tracts. They compare the independent index's broad within-tract venue count with several official selected-facility measures. The correlation for nearby facilities within 800 metres is **0.240**. That isn't “24% explained.”

The sources count different categories over different areas and periods. Neither is a complete measure of usable access. The TPI archive also flags area/density issues; those fields aren't used in these models. Row-level TPI data remain outside the public repository because redistribution permission is unclear.

[Aggregate comparison](../outputs/tables/third_place_index_comparison.csv) · [Aggregate QA](../outputs/tables/third_place_index_qa_summary.csv) · [Official facility input](../data/processed/nyc_selected_facilities.csv) · [Source details](models/third_place_index.md)

There is no library event-study graph: the required verified treatment history, comparison areas and repeated outcomes weren't established.
