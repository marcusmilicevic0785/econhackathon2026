# Student worksheet: from one graph to a research proposal

Use the [graph guide](graph_guide.md) for explanations and the [student brief](hackathon_brief.md) for the policy task. You can complete the starter route using the published images and a spreadsheet. All routes use the same standard: a clear, checkable claim with a stated limitation.

## Starter route · suggested 45–60 minutes

### 1. Choose a question · 5 minutes

Choose one, or narrow it to a question your team can answer:

- Does selected nearby public-facility supply rise steadily with tract income?
- How has published average socializing time changed for people age 15+?
- What does the available evidence say, and not say, about facilities and modeled adult loneliness?
- Are changes in café-like employer establishments associated with county business applications?

Write your expected answer before inspecting the relevant graph. This is a classroom exercise in making hypotheses explicit, not a preregistration of the repository's completed analyses.

### 2. Make a graph identification card · 10 minutes

| Field | Your answer |
|---|---|
| Graph title and filename | |
| What one dot, bar, or row represents | |
| Horizontal axis and units | |
| Vertical axis and units | |
| Population and geographic scope | |
| Observation period versus release/retrieval date | |
| Source table or dataset | |
| Meaning of any gap, shading, or interval | |

Do not continue until the team agrees on the unit of analysis. A tract is not a person; a business application is not a successful business opening.

### 3. Check one calculation · 10 minutes

Pick one exercise and retain your steps:

1. **Time trend:** use [annual BLS values](../outputs/tables/atus_published_annual.csv) to calculate the 2003–2024 difference in minutes/day and percentage change. Explain why this is not a youth-specific estimate.
2. **Equity:** use [income quintiles](../outputs/tables/nyc_equity_income_quintiles.csv) to compare the lowest- and highest-income medians. Does that comparison capture the middle quintiles or variation within groups?
3. **County rates:** select one row in [county-year inputs](../data/processed/panel_county_year.csv) and reconstruct both per-10,000 rates from their counts and population denominator.
4. **Uncertainty:** use [loneliness coefficients](../outputs/tables/access_loneliness_coefficients.csv) to identify the access estimate and its interval. Explain what it means for the interval to include zero.

Keep geographic identifiers as text if importing CSVs. Do not convert missing or suppressed cells to zero. Preserve the distinction between a fraction, a percentage, and a percentage point.

### 4. Explain the evidence · 10 minutes

Complete these sentences in your own words:

- “The graph shows …” Include a numerical comparison and its unit.
- “Our initial expectation was …; the observed pattern …”
- “One possible explanation is …”
- “A different explanation that could produce the same pattern is …”
- “The graph cannot establish … because …”
- “To distinguish those explanations, we would collect or compare …”

### 5. Connect it to a feasible policy · 10–15 minutes

Define one barrier the graph helps investigate. Propose a change, intended users, service area, delivery partner, and one implementation measure. Then name one outcome that would need direct measurement after the intervention.

Examples of implementation measures are delivered no-purchase hours or verified accessible site-hours. A proposed loneliness improvement is a hypothesis, not an observed result. Cross-sectional CDC PLACES estimates cannot evaluate the pilot's local effect.

## Intermediate route · add a robustness comparison

Choose one of the following and explain why it changes the research question:

| Comparison | Task |
|---|---|
| [NYC 400/800/1,200 m estimates](../outputs/tables/nyc_equity_radius_sensitivity.csv) | Compare one predictor's direction and interval across radii. Does “nearby” change your conclusion? |
| [HC3 loneliness results](../outputs/tables/access_loneliness_coefficients.csv) versus [spatial clusters](../outputs/tables/access_loneliness_spatial_cluster_sensitivity.csv) | Explain what changes in uncertainty and why nearby tracts may have related errors. |
| [County current versus lagged estimates](../outputs/tables/panel_coefficients.csv) | Compare matched-sample models. Explain why using a lag is not a causal identification strategy. |
| [Pooled versus residualized relationships](../outputs/tables/panel_correlations_covariance.csv) | Compare the same variable pair before and after county/year adjustment. Distinguish between-county differences from within-county variation. |
| [Official supply versus independent index](../outputs/tables/third_place_index_comparison.csv) | Explain the definition and geography differences before judging the amount of agreement. |

Record the exact rows used. Report an inconvenient result as carefully as a result that supports your idea. Do not compare coefficient magnitudes across predictors with different units as if they measured the same kind of change.

## Advanced route · reproduce and propose an extension

Run the relevant [notebook](../notebooks) top-to-bottom in the documented environment. Verify its input receipts and reconstruct one central comparison. Read the relevant [model guide](models) before suggesting a change.

Write a short extension plan containing:

1. A question the existing data do not fully answer.
2. The additional source, variables, time period, geography, and access/redistribution requirements.
3. A planned comparison or estimator and why it fits the question.
4. A source-quality check and one sensitivity check.
5. An inference limit that would remain even if the analysis ran successfully.

Possible directions include directly audited opening hours, entrance-based walking access, a resident survey with a defensible sampling plan, or a historical library service ledger. The [library evaluation gate](models/library_did.md) explains why a causal event study requires more than a current branch directory. These are proposed extensions; this worksheet does not claim that their inputs or approvals already exist.

## Presentation evidence card

Copy this structure into the appendix of your slides and fill it with your actual result:

| Item | Team entry |
|---|---|
| Research question | |
| Graph and companion table | |
| Original source, data period, and unit | |
| Exact sample or geographic scope | |
| Main observed comparison | |
| Uncertainty, if available, and what it means | |
| Alternative explanation | |
| Sensitivity check | |
| What this supports for policy | |
| What must still be measured | |

## Instructor check notes

These are checkpoints for the frozen snapshot, not answers students should copy without checking their table:

- BLS endpoint values convert to 46.8 and 35.4 minutes/day; the difference is −11.4 minutes/day, approximately −24.4%. The population is age 15+, and a comparable 2020 annual value is missing.
- NYC quintile medians are 8, 5, 4, 3, and 5; there is no simple increasing income gradient in this selected-supply measure. Neither a median tract nor its internal reference point represents every resident's experience.
- A complete six-year panel has 62 × 6 = 372 county-years. Requiring an observed exact prior-year exposure gives 310 matched rows in this snapshot.
- The adjusted access–loneliness interval includes zero. That does not prove no effect, and the design does not identify an intervention effect.
- Fixed effects remove modeled county/year differences. They do not remove every changing local condition. A high overall R-squared is not evidence of a causal mechanism.

Assess students on correct units, source use, a checkable calculation, treatment of uncertainty, alternative explanations, and feasibility. A careful descriptive project can be stronger than a complex regression that answers the wrong question.
