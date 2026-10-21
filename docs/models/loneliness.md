# Access versus modeled adult loneliness

## Measurement and estimand

CDC PLACES 2025 tract dataset `cwsq-ngmh` supplies crude modeled adult `LONELINESS` prevalence, survey reference year 2023. Retain the release, year, label, raw point estimate, and CDC lower/upper confidence bounds. Confirm actual returned measure/year/type; do not replace absent loneliness with depression. The measure is not an individual loneliness survey of each tract and does not specifically describe young people. CDC renamed the earlier social-isolation measure in its December 2025 release; read the current definition before comparing releases.

Question: do NYC tracts with more selected nearby facilities have different modeled prevalence after adjustment? Hypothesis: a negative coefficient on access. The coefficient is descriptive and subject to confounding and reverse causality.

$$
Loneliness_i=\alpha+\beta\log(1+A_i)+\theta_1\log(MHI_i)+\theta_2 Poverty_i+
\theta_3 Youth_i+\theta_4 Older_i+\theta_5\log(1+Density_i)+\gamma_{borough(i)}+u_i.
$$

The outcome is percentage points; `β` is the change per natural-log unit of (1+selected-site count). This is equal-tract OLS, with HC3 uncertainty conditional on the modeled outcome. A borough-only specification shows how adjustment changes the association. Join exact 11-character Census GEOIDs one-to-one and publish model attrition; missing estimates never become zero.

## Essential caveats

PLACES estimates use multilevel regression and poststratification, including demographic/poverty information. Regressing these estimates on related ACS covariates can partly reproduce the construction of the outcome. The reported regression intervals are not CDC confidence intervals, and do not propagate CDC modeled-outcome uncertainty or shared model error. Crude estimates are influenced by age composition. The facilities snapshot is later than the 2023 outcome, so exposure cannot be treated as preceding outcome. These limitations preclude a causal interpretation even if the coefficient is statistically significant.

Ecological fallacy, spatial dependence, omitted neighborhood characteristics, endogenous facility placement, coverage errors, and entry/quality barriers remain. CDC cautions against using PLACES to evaluate local interventions; this project does not use it for the library event study.

Outputs: regression coefficient/summary tables, adjustment sensitivity, correlations/covariances, residual/VIF diagnostics, and a labeled scatterplot. Consult `outputs/model_status.json` for realized coverage.

Sources: [CDC release](https://data.cdc.gov/resource/cwsq-ngmh.json), [definition](https://www.cdc.gov/places/measure-definitions/health-related-social-needs.html), [FAQ](https://www.cdc.gov/places/faqs/index.html), and the ACS/FacDB sources in the manifest.
