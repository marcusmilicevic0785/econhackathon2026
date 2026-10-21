# Methods overview

## Data and samples

| Analysis | Sources | Saved sample |
| --- | --- | --- |
| NYC facility access | ACS 2019–2023, Census 2023 Gazetteer, current NYC FacDB snapshot | 2,190 NYC tracts with population at least 100 and complete model variables |
| Access and loneliness | NYC access data plus CDC PLACES 2025, adult loneliness reference year 2023 | 2,190 matched tracts |
| Establishments and business applications | Census CBP, BFS and annual ACS five-year population estimates | 62 NY counties, 2018–2023; 372 rows before lag restrictions |
| Socializing time | Official BLS published series, age 15+ | 21 annual observations, 2003–2024; 2020 missing |
| Independent-index comparison | Third Place Index and selected official facility measures | 2,327 matched NYC tracts; aggregate rank comparison only |

These analyses are exploratory. They weren't preregistered, and the regressions estimate associations rather than causal effects. Exact run status is in [model status](../outputs/model_status.json).

## NYC access

For tract $i$, $A_i(r)$ counts selected site-category locations within $r$ metres of its Census internal point:

$$
A_i(r)=\sum_{s\in S}\mathbf{1}\{d(p_i,p_s)\le r\}.
$$

$S$ is the set of selected facilities with valid coordinates after deduplication. Distance is great-circle, not a walking route. The main radius is 800 metres, with 400- and 1,200-metre comparisons. Counts can cross tract boundaries and aren't per-capita rates. Facility hours, fees, eligibility and current operation haven't been verified.

The regression is:

$$
\begin{aligned}
\ln(1+A_i(800))={}&\alpha+\beta_1\ln(MHI_i)+\beta_2 P_i\\
&+\beta_3 Y_i+\beta_4 O_i+\beta_5\ln(1+D_i)\\
&+\delta_{b(i)}+\varepsilon_i.
\end{aligned}
$$

$MHI$ is median household income in 2023 dollars; $P$ is poverty percentage; $Y$ and $O$ are the shares ages 15–24 and 65+; $D$ is population per land square mile. Shares are on a 0–100 scale. The $\delta$ terms account for borough differences.

The fit gives each tract equal weight. Main intervals use HC3 robust standard errors; a separate sensitivity clusters tracts into approximate 2 km tiles. Nearby tracts still share conditions, and residual spatial dependence is substantial. ACS margins of error aren't propagated into regression intervals.

[Dataset](../data/processed/nyc_access.csv) · [Full methods and variable definitions](models/nyc_equity.md) · [Coefficients](../outputs/tables/nyc_equity_coefficients.csv)

## Access and loneliness

The outcome $L_i$ is modeled adult loneliness prevalence, in percentage points. The regression uses the same demographic controls as the access model:

$$
\begin{aligned}
L_i={}&\alpha+\beta_A\ln(1+A_i(800))+\theta_1\ln(MHI_i)\\
&+\theta_2 P_i+\theta_3 Y_i+\theta_4 O_i+\theta_5\ln(1+D_i)\\
&+\delta_{b(i)}+u_i.
\end{aligned}
$$

The fit is equal-tract OLS with HC3 intervals and a separate 2 km tile-cluster sensitivity. A borough-only adjustment comparison uses the same rows. The outcome is an adult area estimate, not a youth loneliness measure. CDC's modeled values share demographic/contextual inputs with some predictors, and the facility snapshot is later than the 2023 outcome. The regression can't establish an intervention effect or an individual-level relationship.

[Dataset](../data/processed/nyc_loneliness.csv) · [Full methods](models/loneliness.md) · [Coefficients](../outputs/tables/access_loneliness_coefficients.csv)

## County establishments and applications

For county $c$ and year $t$, both variables are rates per 10,000 residents:

$$
R_{ct}=10{,}000\frac{E_{ct}}{N_{ct}},
\qquad
B_{ct}=10{,}000\frac{Q_{ct}}{N_{ct}}.
$$

$E$ counts employer establishments in NAICS 722515, a category broader than cafés. $Q$ counts business applications, not confirmed openings. $N$ is that release's ACS five-year population estimate; the annual windows overlap.

The current, lagged and joint models are:

$$
\begin{aligned}
B_{ct}&=\alpha_c+\lambda_t+\beta_0 R_{ct}+\varepsilon_{ct},\\
B_{ct}&=\alpha_c+\lambda_t+\beta_1 R_{c,t-1}+\varepsilon_{ct},\\
B_{ct}&=\alpha_c+\lambda_t+\beta_0 R_{ct}+\beta_1 R_{c,t-1}+\varepsilon_{ct}.
\end{aligned}
$$

County and year effects are included; no additional demographic controls enter these fits. The rates stay in levels. OLS is unweighted, with county-clustered t intervals and 61 cluster degrees of freedom.

Eight specifications cover full, matched and pandemic-excluded samples. The matched current/lag sample has 310 rows. Its pandemic-excluded version has 124 rows, covering only 2019 and 2023 after excluding both pandemic outcomes and lag exposures. Both rates share a denominator; fixed effects and lags don't remove changing local confounding or reverse causality.

[Dataset](../data/processed/panel_county_year.csv) · [All specifications and source definitions](models/panel.md) · [Coefficients](../outputs/tables/panel_coefficients.csv)

## Other results and limits

- **Socializing time:** published BLS hours are converted to minutes. The national age-15+ series is descriptive; it isn't the age-15–24 microdata analysis, which remains incomplete after a blocked download. [Details](models/atus_published.md).
- **Third Place Index:** the comparison uses rank correlations, not a fitted exposure model. Categories, catchments and source periods differ from the official facility counts. Row-level index data aren't redistributed while permissions remain unclear. [Details](models/third_place_index.md).
- **Library intervention:** not estimated. Verified treatment dates, credible comparison areas and aligned repeated outcomes weren't established. [Status and methods](models/library_did.md).

## Data checks

Geographic identifiers stay as text. Joins check key uniqueness and expected matches. Negative ACS special values become missing in analysis variables; missing and suppressed values aren't filled with zero. Invalid facility coordinates are excluded from radius counts, and locations are deduplicated by category and rounded coordinates. Supplementary library/park records aren't added to FacDB counts, avoiding cross-source double counting.

[QA outputs](../outputs/qa) record exclusions, coverage and diagnostics. [Source hashes](../data/manifest.json), [processed hashes and lineage](../data/processed_manifest.json), and [reuse notes](../DATA_LICENSES.md) accompany the files. Detailed parser rules, diagnostics and uncertainty limits remain in the linked model notes.
