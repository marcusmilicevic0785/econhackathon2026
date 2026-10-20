# ATUS socializing and communicating, 2003–2024

## Question and estimand

How did average daily minutes in **socializing and communicating with others**
change for people ages **15–24** and **all ages 15+**? The target population is
the U.S. civilian noninstitutional population. These are overlapping groups,
not independent comparison or treatment groups. Each year is a repeated
cross-section, not a panel following the same young people as they age.

The outcome is **T120101**, daily primary-activity minutes in the summary variable for six-digit activity
**120101**. Its official label is “Socializing and communicating with others”
([multi-year activity lexicon, page 7](https://www.bls.gov/tus/lexicons/lexiconnoex0324.pdf)).
Use that label in reporting. This category is **not a direct measure of all
face-to-face interaction**, friendship, loneliness, or social connection. The
summary does not identify interaction mode or who was physically present.
Do not claim that it measures all online communication either. Telephone calls,
texting, and internet voice/video calls have separate coding rules. Social
interaction during work, meals, childcare, and other primary activities can be
recorded outside this code. Parties/events (1202xx), other leisure (1203xx),
and the residual category 120199 are not added to the specified outcome.

[BLS coding rules, category 12](https://www.bls.gov/tus/coderules/tu2016coderules.pdf)
give face-to-face talking as one example, but also include such activities as
giving/opening gifts and accompanying someone on errands. A category containing
face-to-face talking is not equivalent to total face-to-face time. The
[2024 technical notes](https://www.bls.gov/news.release/archives/atus_06262025.htm)
describe broader published socializing aggregates; those are not interchangeable
with the single detailed code used here.

## Source and extraction

- [BLS 2003–2024 multi-year download page](https://www.bls.gov/tus/data/datafiles-0324.htm).
- [Official activity-summary ZIP](https://www.bls.gov/tus/datafiles/atussum-0324.zip),
  approximately 15 MB compressed. Contains CSV-formatted `.dat` data and import programs.
- [2003–2024 interview dictionary](https://www.bls.gov/tus/dictionaries/atusintcodebk0324.pdf):
  `TUCASEID` is the diary/respondent key, `TUYEAR` is diary year, `TEAGE` is age,
  and `TUFNWGTP` is the harmonized final weight. Age topcoding does not affect
  either group's membership.
- [Frequently used variables](https://www.bls.gov/tus/other-documentation/freqvariables.pdf)
  identifies both `TUFNWGTP` and `TU20FWGT` on the activity-summary file.

`python -m econhack.atus` invokes `run()`. With the package uninstalled, run
`PYTHONPATH=src python -m econhack.atus` from the repository root. Downloads go
through `common.fetch` to `atus/atussum-0324.zip` under the common raw-data root,
with source and license metadata. No secondary mirror, hand-entered estimates,
or synthetic fallback is used. Only six required columns are read. Missing
schema, duplicate keys, malformed values, negative/missing applicable weights,
and incomplete year coverage fail explicitly. Zero weights contribute nothing
and their counts are reported. All requested cohorts must have positive total
weight in every observed year.

After acquisition, `data/processed/atus_socializing_annual.csv` stores the tidy,
44-row annual aggregate. `ECONHACK_OFFLINE=1 PYTHONPATH=src python -m econhack.atus`
replays that table without requiring the ZIP or network access, regenerating
regressions and figures. Replay validates cohort/year coverage, units, counts,
weights, provenance fields, and 2020 flags, and is labeled in run status. The
raw-data download manifest remains the acquisition record; aggregate replay
does not independently recheck raw bytes. If the processed table is absent,
offline mode falls back to the common API's verified raw cache or fails if
neither input is available.

## Annual estimator and the 2020 exception

For year y and age group g, compute:

`mean_minutes[y,g] = sum(w[i] * T120101[i]) / sum(w[i])`

The sums include **all eligible diaries, including zero activity minutes**.
Hours per day equal minutes divided by 60. Final weights incorporate diary-day
and sampling adjustments; do not add a second weekend/weekday reweighting.
Weight sums are person-day calibration totals, not respondent sample sizes or
an estimate of the number of people. The tables report unweighted diary counts
separately. Annual point estimates have no fabricated standard errors or bands.

Use **TUFNWGTP** for 2003–2019 and 2021–2024. This multi-year variable applies
the comparable 2006 weighting methodology even to 2003–2005. Never substitute
the original early-year final weights.

Use **TU20FWGT for 2020 only**. It represents January 1–March 17 and May 10–
December 31; the missing interval is March 18–May 9. Although TU20FWGT also
exists for some 2019 diaries, it must not replace the full-year 2019 weight.
The 2020 value is **partial-year**, not an annual estimate comparable to other
years. It is retained for auditability and shown as a hollow diamond, with a
break in the full-year line and a shaded warning. It is excluded from every
trend regression. See [BLS pandemic technical guidance](https://www.bls.gov/tus/notices/2021/covid19tech.htm).

## Regression and uncertainty

The runnable model is `annual_mean_minutes = intercept + beta * (year - 2003) + error`,
estimated separately for each group. Each annual estimate has equal weight;
microdata weights have already been used inside its annual mean. Weight sums
are not precision weights. The slope is minutes per person per day per calendar
year. The intercept is fitted daily minutes in 2003.

Two specifications are exported, with **both coefficients**, sample size,
degrees of freedom, R-squared, units, period, exclusions, covariance method,
and uncertainty scope:

1. **2003–2024, excluding 2020:** 21 annual observations, descriptive OLS.
   No standard errors, p-values, or confidence intervals are reported. This fit
   summarizes an overall direction; pandemic shifts and nonlinear changes can
   make a constant slope a poor description. Blank inferential fields are intentional.
2. **2003–2019:** 17 consecutive pre-pandemic annual observations, exploratory
   OLS with Bartlett HAC covariance, maximum lag 2, small-sample covariance
   correction, and Student-t reference with 15 residual degrees of freedom.
   Export coefficient standard errors, t statistics, p-values, and 95% temporal
   model intervals. Restricting HAC to consecutive calendar years avoids treating
   2019 and 2021 as adjacent annual observations after removing 2020. These
   results describe the pre-pandemic period, not the entire 2003–2024 change.

[Statsmodels robust covariance documentation](https://www.statsmodels.org/stable/generated/statsmodels.regression.linear_model.RegressionResults.get_robustcov_results.html)
documents these HAC settings. The short time series makes temporal inference
exploratory. HAC addresses temporal residual dependence under model assumptions;
it does **not** implement the ATUS survey design or propagate replicate-weight
uncertainty. Replicate weights are not downloaded in this module, so annual
survey confidence intervals and tests of endpoint differences are unavailable.
Model intervals must never be presented as annual survey intervals. Do not use
the number of respondents as the regression sample size or infer that the
trend identifies a causal effect of technology or any other exposure. Composition,
coding, nonresponse, recall, and simultaneous changes remain potential explanations.

## Outputs and checks

- `outputs/tables/atus_socializing_annual.csv`: 44 year/group rows, weighted
  minutes/hours, diary counts, weight sums, weight variable, coverage, source,
  and flags excluding 2020 from annual trend analysis.
- `data/processed/atus_socializing_annual.csv`: the same aggregate for offline replay.
- `outputs/tables/atus_socializing_regression.csv`: eight coefficient rows
  across two cohorts and two specifications; complete inferential fields only
  for the explicitly labeled pre-pandemic temporal HAC specification.
- `outputs/tables/atus_socializing_fitted.csv`: observed/fitted values and
  residuals for every model observation; no 2020 fitted observation.
- `outputs/figures/atus_socializing_trend.png` and `.svg`: weighted levels,
  no annual confidence bands, and an explicit 2020 discontinuity.
- Common run status records provenance, coverage, and substantive limitations.

`PYTHONPATH=src pytest -q tests/test_atus.py` uses small, explicitly synthetic
fixtures exclusively for testing. It checks unequal weights, zero-time inclusion,
cohort boundaries and overlap, 2019/2020 weight selection, zero/invalid weights,
duplicate diaries, archive/schema handling, complete regression coverage, known
linear slopes, pre-pandemic HAC metadata, and a real gap in plotted lines.
Tests do not access the network or substitute fixture data into research outputs.
