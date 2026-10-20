# Review of source notes for EconHack 2026

**Review date: 2026-10-20.** This is an original, selective research review of the provided attachment and linked public sources. It does not reproduce the attachment or third-party prose. Private organizer logistics are excluded. The [brief](hackathon_brief.md) and [research protocol](research_protocol.md) use research context only and mark all new event-design choices as proposed.

The source notes were available and reviewed. Earlier assistant replies were unavailable as readable text. These documents therefore summarize the attachment and verified sources rather than reconstructing a transcript or confirming earlier agreements.

## How to read the status labels

- **Checked:** the identified source was reviewed and supports the narrow statement described here. This does not validate a local replication or a proposed policy effect.
- **Qualified evidence:** a study or synthesis supports a narrower interpretation than the notes suggest; its design and population matter.
- **Unverified:** the exact number, date, definition, or inference has not been established. This is not a finding that the claim is false.
- **Lead only:** potentially useful context, but insufficiently inspected, inaccessible, or unsuitable as primary evidence for the requested claim.

Documentation review is distinct from data validation. No raw tract/county files, completed model results, or verified library intervention panel are certified by this review.

## Official prior EconHacks: checked structural inspiration

| Organizer page | What it supports | Appropriate adaptation |
| --- | --- | --- |
| [Fourth annual EconHack](https://equaleconomics.wordpress.com/econhack4/) | A NYC policy challenge asking teams to address at least two listed objectives, with attention to implementation, stakeholders, data, evaluation, feasibility, and trade-offs | Use a focused question and require a practical policy proposal |
| [Fifth annual EconHack](https://equaleconomics.wordpress.com/5th-annual-pace-university-econhack/) | A food-insecurity challenge asking for at least three objectives and relevant graphs, tables, or regressions | Connect objectives to accessible evidence; make regression optional for beginners |

These pages establish their own historical formats. They do not establish 2026 dates, rules, budget, attendance, judging criteria, or the third-space topic. Earlier pages were unnecessary to resolve the requested design because these two supplied the relevant structure. The four objectives, pilot budget, rubric, and two-day workshop schedule in the brief are newly proposed, not historical facts or organizer commitments.

## Claim-by-claim review

### 1. Definition and access

**Checked conceptual framing; qualified implementation claim.** Third spaces are gathering places outside home and work/school. Public and commercial examples differ in price, eligibility, culture, and opportunities to linger. The notes' implication that all such spaces are free or universally welcoming is too strong. Treat affordability and inclusion as characteristics to investigate and improve. [Finlay et al., third-place research article](https://pmc.ncbi.nlm.nih.gov/articles/PMC6934089/).

The clinical-provider and university explainer links in the notes can introduce the topic; neither substitutes for measured access, longitudinal venue counts, or intervention evidence. Definitions are not proof that every listed café, park, or library functions as an effective third space.

### 2. National decline, chain replacement, distance, and technology

**Unverified as a combined causal narrative.** The research article above raises concern about closures and calls for further study. It does not establish a current nationwide, all-category decline in usable third-space access, nor a NYC trend. A single TPI snapshot cannot establish closures or chain replacement. Pandemic effects, digital communication, transportation, and rising costs are plausible mechanisms to examine, not collectively demonstrated explanations in this packet.

Before publishing a trend, define which venues count and obtain comparable historical observations, population denominators, and coverage diagnostics. Distinguish venue loss from reduced hours, rising prices, changing social use, and incomplete mapping. Claims that free spaces are generally far from residents require local travel-access evidence.

### 3. The ATUS “61 → 35 minutes, 2003 → 2025, ages 15–24” claim

**Unverified; omit the exact claim from promotional problem statements.** Neither endpoint, the combined 15–24 age group, the start year, nor the claim of the largest age-group decline has been reproduced here.

The [BLS 2025 summary](https://www.bls.gov/news.release/atus.nr0.htm), released June 25, 2026, reports 35 versus 41 daily minutes of socializing and communicating in 2025 versus 2015 for the broader surveyed population. That comparison is not verification of the notes' age-specific 2003 comparison. The release also documents a 2025 shutdown-related collection gap and weighting adjustment; do not say that 2025 data are categorically unavailable.

**“Face-to-face” is also unverified as the measure's interpretation.** The repository's [ATUS methodology](models/atus.md) specifies detailed activity `120101`, socializing and communicating with others. A detailed activity code is not automatically identical to a published broader aggregate. It also misses interaction recorded under other primary activities and does not directly measure loneliness or physical co-presence. Consult the [BLS activity lexicon](https://www.bls.gov/tus/lexicons/lexiconnoex0324.pdf) and coding documentation for the exact series.

The repository specification covers 2003–2024; its existence does not prove that a particular result has been generated. A defensible youth estimate needs verified microdata, correct weights, zero-minute diaries, comparable definitions, and uncertainty appropriate to the survey. Treat 2020 separately under its documented partial-year rules. Verify a 2025 extension independently rather than changing a date label.

### 4. Social connectedness and crime

**Qualified study evidence, not a third-space policy estimate.** Stuart and Taylor study US city crime in 1970–2009 using historical variation in Southern Black migration networks and birth-town concentration as a connectedness proxy. The paper reports estimates corresponding to 21% lower murders and 20% lower motor-vehicle thefts for a one-standard-deviation connectedness increase. Those are the authors' estimates in their historical setting, not EconHack findings. [Original study](https://pmc.ncbi.nlm.nih.gov/articles/PMC8460118/).

The authors make a causal argument under their historical identification assumptions; it would be misleading to reduce that paper to a simple café correlation. It would also be misleading to transfer its estimates to adding venues in NYC. It does not establish that a proposed gathering-space pilot reduces drug use, suicide, or crime by any particular amount. Use it as motivation for possible community mechanisms, with external-validity limits.

### 5. Entrepreneurship and local economic activity

**Qualified evidence with a distinct treatment and outcome.** The [NBER research summary](https://www.nber.org/be/20242/third-places-boost-local-economic-activity) describes work by Choi, Guzman, and Small on neighborhood Starbucks entry and business registrations. It discusses comparisons involving planned-but-unopened locations and variation by existing café presence. A working-paper summary is not a universal causal guarantee about all gathering spaces.

The [working paper landing page](https://www.nber.org/papers/w32604) could not be retrieved in this review; detailed identification checks and current-version results are therefore not independently audited here. Do not transfer the summary's effect sizes into a NYC budget forecast. The proposed county CBP/BFS regression uses different geography, exposure, and outcomes and is explicitly observational. Applications are not the same as registrations or actual business formation.

### 6. Loneliness, health, and productivity

**Checked advisory; qualified evidence, without a pilot-effect claim.** The [2023 Surgeon General advisory](https://www.hhs.gov/sites/default/files/surgeon-general-social-connection-advisory.pdf) synthesizes research on social connection and health. It distinguishes objective isolation from subjective loneliness and describes relative mortality risks from prior research. The notes' 29% mortality figure is a cited risk estimate associated with isolation, not an absolute probability, a randomized third-space effect, or a forecast for NYC youth.

Claims that young adults are almost twice as lonely as adults over 65, or that youth loneliness increased in every year from 1976 to 2019, are **unverified in this review**. Any later use needs the original survey, population, wording, period, and uncertainty. Do not blend loneliness, isolation, living alone, and insufficient social support into one indicator.

The [economic-cost evidence brief](https://www.socialconnectionguidelines.org/en/evidence-briefs/what-are-the-economic-costs-of-loneliness) is a synthesis lead, not a local cost-benefit estimate. No productivity gain, avoided healthcare cost, or fiscal return is validated here. Trace any proposed monetary parameter to its original study and assess whether it transfers to the population and intervention.

### 7. Older adults and third spaces

**Qualified review lead; precise numerical claims unresolved.** The citation corresponding to PMID 36512515 is *Third Places for Older Adults' Social Engagement: A Scoping Review and Research Agenda*, associated with a 2023 journal issue and earlier online publication. The [publisher's indexed record](https://academic.oup.com/gerontologist/article-pdf/63/7/1149/51245983/gnac180.pdf) identifies it as a review; full retrieval was unsuccessful. Its individual study designs and findings were not independently checked here. Do not call it one causal intervention study or repeat a precise probability of benefit.

The other PubMed links, [PMID 23749730](https://pubmed.ncbi.nlm.nih.gov/23749730/) and [PMID 25034246](https://pubmed.ncbi.nlm.nih.gov/25034246/), did not return readable abstracts in this review. They remain leads; no design or result is attributed to them. The notes' 28%/13.8-million living-alone figures need an explicit year, age denominator, and original table. Living alone is not a diagnosis of loneliness. Accessibility for older adults is a reasonable policy objective without relying on those unresolved numbers.

### 8. Geographic equity and the Third Place Index

**Checked documentation; no local results validated.** The [TPI methodology](https://thirdplaceindex.org/methodology/) describes OSM-derived tract counts and percentile rankings, with a November 2024 collection snapshot and older ACS demographics. It acknowledges mapping and access limitations. The claim that areas with the most children have the fewest third spaces has not been replicated here; the direction can depend on whether “most” means counts or shares and whether access means counts, density, or travel time.

Use a candidate venue-supply measure with clear denominators. Hours, cost, age restrictions, accessible entrances, and welcoming conditions require separate evidence. Verify the score's scale in the downloaded file, and distinguish the under-18 demographic field from ages 15–24. A high index score does not establish low loneliness, adequate youth access, or improvement over time.

### 9. NYC youth restrictions and park access

**Checked attribution; current venue facts require confirmation.** The [Public Advocate post](https://advocate.nyc.gov/blog/youth-third-spaces-restriction-relaxation), dated September 9, 2026, presents an intern perspective on youth exclusion and discusses specific retail restrictions. It is useful local context, not a representative survey, independent audit of every cited policy, or a causal study. Verify current rules with operators before directing participants to a site. Do not generalize its cited policing statistics to interactions specifically inside third spaces.

The supplied [2026 park-equity URL](https://council.nyc.gov/data/park-equity-2026/) could not be retrieved; its existence, charts, and findings remain unverified. An accessible [Council parks page](https://council.nyc.gov/data/parks-in-nyc/) is a different resource and contains dated material; it is not a replacement verification of the supplied claim. Prefer documented dataset versions for a new analysis.

## Measurement evidence that governs the protocol

| Source | Checked use | Essential limit |
| --- | --- | --- |
| [CDC PLACES release notes](https://www.cdc.gov/places/current-release-notes/index.html) | Documents the change from social-isolation wording to loneliness in the December 2025 release | Do not assume identical wording, IDs, or comparability across releases |
| [CDC measure definition](https://www.cdc.gov/places/measure-definitions/health-related-social-needs.html) | Defines modeled adult loneliness prevalence | An adult area estimate cannot identify youth-specific prevalence or individual experiences |
| [CDC methods](https://www.cdc.gov/places/methodology/index.html) and [FAQ](https://www.cdc.gov/places/faqs/index.html) | Establish model-based small-area estimation and ecological scope | Shared predictors and model uncertainty affect secondary regressions; CDC cautions against local intervention evaluation using modeled estimates |
| [ACS guidance](https://www.census.gov/programs-surveys/acs/guidance/estimates.html) | Establishes the five-year period basis used for tract characteristics | Annual releases overlap; a rolling estimate is not an independent annual observation |
| [NAICS definition](https://www.census.gov/naics/?input=722515&year=2022&details=722515) and [CBP](https://www.census.gov/programs-surveys/cbp/data/datasets.html) | Identify snack/nonalcoholic beverage bars and employer establishment data | Broader than cafés; omits free public-space supply and nonemployers |
| [BFS county source](https://www.census.gov/econ/bfs/data/county.html) | Documents annual county applications; its reviewed release page advertises 2005–2025 | Inspect the actual workbook and dictionary, disclosure treatment, and common panel years before use |

These are documentation-level checks. They do not establish matched NYC tract coverage, complete New York county panels, regression coefficients, or statistical significance. Those checks belong to the execution stage of the protocol.

## Remaining reading leads

The attachment also links to AEI commentary, a newspaper article, Forbes, Blue Zones, Urban Institute, a clinical-provider explainer, a university explainer, and a ResearchGate-hosted review. These are **leads only** for this packet: their full arguments, underlying data, and any numerical claims were not independently audited here. A hosting platform or institutional name is not by itself proof of peer review or causality. Trace quantitative claims to original methods and data before including them in findings.

## Publication decisions

- Use the conceptual definition, public research motivation, and carefully attributed local perspectives.
- Keep the 61-to-35 claim, exact older-adult living-alone counts, unsupported national closure trends, and unverified park findings out of asserted problem facts.
- Present crime and entrepreneurship studies with their actual settings and identification limits; never use their estimates as a guaranteed pilot payoff.
- Describe tract and county models as exploratory associations; retain ecological, simultaneity, rolling-ACS, and spatial-correlation caveats.
- Keep library DiD conditional on verified service history, repeated direct outcomes, credible comparisons, and defensible inference. No event study is available from these notes.
- Label the 2026 challenge design and every budget, target, rubric, and schedule choice as proposed. Do not reproduce private organizer logistics, the complete source notes, or third-party passages.
