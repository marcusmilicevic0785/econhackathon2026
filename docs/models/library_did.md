# Library access difference-in-differences: design and decision gate

## Current decision: not estimated

This is a prospective methods specification. No verified branch-event panel,
aligned repeated local outcome, or credible comparison sample is currently
established. There are no estimated library effects, event-study coefficients,
standard errors, power results or simulated observations in this document.
The main CLI records `library_did: not_estimated`. A cross-sectional access
regression is not a substitute for this design.

## Question, exposure and estimand

For residents of areas receiving a verified library access expansion, what is
the change in a prespecified directly measured local outcome relative to its
counterfactual without that expansion? The primary estimand would be an
intention-to-treat effect of local access, not the effect of choosing to visit.
Library attendance or circulation would instead define an operational-use
outcome and would not establish an effect on loneliness.

Select one intervention before looking at outcomes: a new branch opening, or
a sustained restoration of opening hours. Define treatment dose, effective
date, an anticipation interval, minimum duration and geographic catchment.
Announcements, construction completion and actual public reopening are different
events. Do not pool openings, temporary closures, renovations and service-hour
changes as interchangeable treatments. Reversible hours/closure treatments do
not satisfy the absorbing-treatment setup described below; use a separate
validated design or restrict to genuinely sustained events.

Use documented network walking catchments and fixed residential areas, not
distance from a tract centroid as if it were every resident's exposure. Fix
areas, population weights and boundaries before treatment; report overlapping
catchments, moves and baseline access. If treatment is assigned to catchment
clusters, tract observations inside a cluster are not independent treatments.

## Required evidence and joins

| Input | Minimum evidence before estimation |
|---|---|
| Event ledger | Stable branch ID; address/coordinates; actual public-service start/end dates; hours/dose; official dated source URL; event type; subsequent reversals and other nearby changes |
| Local outcome | Repeated directly observed survey or administrative measure with consistent unit, period, coverage, denominator and uncertainty; documented access and reuse permission |
| Residential geography | Fixed tract/catchment crosswalk and vintage; baseline population and network access; assessment of demographic turnover |
| Comparison pool | Never-treated or eligible not-yet-treated areas with sufficient pretreatment overlap, no anticipation and no meaningful spillover exposure |
| Confounders | Predetermined outcome histories and baseline covariates; documented simultaneous service changes, local shocks and reasons for library investment |

Potential event-verification sources are the systems' own branch pages and
dated announcements: [NYPL locations](https://www.nypl.org/locations),
[Brooklyn locations](https://www.bklynlibrary.org/locations), and
[Queens locations](https://www.queenslibrary.org/about-us/locations).
Current directories are discovery aids; they do not supply a verified history.
[NYC Facilities Database](https://www.nyc.gov/content/planning/pages/resources/datasets/facilities)
can locate sites, but snapshot differences do not prove openings or treatment dates.

Join branch IDs to dated events, events to fixed catchments, and catchments to
area-period outcomes. Validate unique area-period keys, treatment chronology,
missing periods, geographic vintage and outcome denominators. Never join a
branch's outcomes to all surrounding residents and call them resident outcomes.
Record unmatched cases and attrition without filling missing outcomes with zero.

CDC PLACES is not an intervention-evaluation outcome: it models local prevalence
from survey and demographic inputs and cannot detect effects of local programs.
See the [CDC dataset warning](https://catalog.data.gov/dataset/places-local-data-for-better-health-census-tract-data-2025-release).
Overlapping ACS five-year windows are also not independent annual outcomes;
the current ACS, TPI and FacDB snapshots do not create a pre/post panel.

## Identification and estimator, conditional on the gate passing

For sustained, staggered adoption, define first treatment period `G_i = g` and
estimate cohort-time `ATT(g,t)`, then prespecified event-time and overall
aggregates. Use never-treated controls or not-yet-treated controls outside the
anticipation interval, with documented comparison eligibility in each period.
Do not use already-treated areas as untreated controls. Specify cohort weights
and a common event window so changing cohort support does not masquerade as
dynamic effects. See the authors' [group-time ATT documentation](https://bcallaway11.github.io/did/reference/att_gt.html)
and [Callaway and Sant'Anna paper](https://doi.org/10.1016/j.jeconom.2020.12.001).

Identification requires conditional parallel untreated trends, no anticipation
outside the declared window, overlap, consistent exposure/outcome measurement,
and a defensible account of spillovers. Investment may target changing areas,
and renovations may accompany other improvements: matching on baseline income
does not solve endogenous timing. Adjust only for predetermined covariates;
attendance, post-opening hours and subsequent neighborhood composition can be
mediators, not safe default controls. Avoid interpreting a conventional
staggered two-way fixed-effects event study as the ATT under heterogeneous effects.

Require multiple clean pretreatment observations. A planning target is at least
four annual preperiods and two postperiods, or a comparably informative seasonal
monthly/quarterly panel; actual adequacy depends on outcome noise, treatment
clusters and plausible effect size. Display preperiod estimates and simultaneous
bands, examine meaningful differential trends and assess power. Non-rejection
of a pretrend test does not verify parallel trends. Prespecify sensitivity to
trend violations using the authors' [pretrend tools](https://github.com/jonathandroth/pretrends)
and [HonestDiD](https://github.com/asheshrambachan/HonestDiD), where supported by
the estimator and covariance matrix.

Account for inference at the assignment level, serial correlation and overlapping
catchments; report the number of independent treated/control clusters, not just
tract rows. Consider spatially robust sensitivity and appropriate cluster
bootstrap inference when justified. Few treatment clusters can invalidate usual
asymptotics. Randomization inference requires a credible assignment mechanism;
it is not a generic remedy. Prespecify outcome families and multiplicity.

## Go/no-go gate and future reporting

Proceed only when all of the following have inspectable evidence:

1. Verified service dates/doses, stable treatment units and a compatible treatment
   design, with ambiguous or reversed events resolved.
2. A directly observed, consistently measured local panel with adequate pre/post
   coverage, usable denominators and permitted access.
3. Supported control cohorts, pretreatment overlap and a credible account of
   timing, anticipation, concurrent investments and spillovers.
4. A prespecified outcome/estimand/window, feasible inference at the assignment
   level and a defensible precision assessment.
5. Audited joins and attrition, plus sensitivity plans for trends, catchments,
   controls, composition and alternative timing definitions.

If any condition fails, retain `not_estimated` and document the missing evidence;
do not invent dates, outcomes, treatment histories or comparison groups. If the
gate later passes, report the cohort/event support, sample construction,
estimates with appropriate uncertainty, sensitivity results and limitations.
Limit claims to the intervention, population, period and measured outcome
actually supported. A positive attendance effect would not establish reduced
loneliness, and an imprecise estimate would not establish no effect.
