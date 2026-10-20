# EconHack 2026 · Third spaces, measured carefully

A research and teaching repository for investigating neighborhood facility supply, social connection, and local economic activity. Every estimate comes from downloaded source records. Hypotheses are allowed to fail; missing data never become invented observations.

![NYC access equity](outputs/figures/nyc_access_equity.png)

## Start here

- **Students:** start with the [graph-reading guide](docs/graph_guide.md) and [research worksheet](docs/student_worksheet.md), read the [two-day challenge and policy objectives](docs/hackathon_brief.md), then choose a model notebook.
- **Researchers:** read the [research protocol](docs/research_protocol.md), [data dictionary](docs/data_dictionary.md), and [findings](docs/findings.md).
- **Reviewers:** inspect [source checksums](data/manifest.json), [processed-data checksums](data/processed_manifest.json), [realized model status](outputs/model_status.json), and [QA records](outputs/qa).
- **Organizers:** the brief includes proposed deliverables, a scoring rubric, implementation/evaluation requirements, and a comparison with earlier Pace EconHacks. It is a proposed 2026 teaching plan, not an official event announcement.

## Learn with the graphs

Use the time trend to describe change, the NYC scatterplots and income groups to challenge assumptions about access, and the coefficient plots to distinguish an estimated association from its uncertainty. County comparisons introduce denominators, fixed effects, lags, and robustness. Coverage and residual plots help students question the evidence before proposing policy.

The [graph guide](docs/graph_guide.md) explains all 13 figures: how to read them, what they teach, how to use them in a research argument, what they cannot establish, and an exercise linked to the actual CSV. The [worksheet](docs/student_worksheet.md) offers starter, intermediate, and advanced routes plus instructor checkpoints. Students can begin with images and spreadsheets; coding is optional.

## Analyses

| Question | Data and unit | Implementation and outputs | Interpretation |
|---|---|---|---|
| Who has nearby third-space supply in NYC? | ACS 2019–2023, Census Gazetteer, current NYC FacDB; census tract | [Methods](docs/models/nyc_equity.md), [notebook](notebooks/01_nyc_access_equity.ipynb), [coefficients](outputs/tables/nyc_equity_coefficients.csv) | Exploratory association; 400/800/1,200 m sensitivity, HC3 and spatial-grid clustered intervals |
| Is access associated with modeled loneliness? | CDC PLACES 2025, 2023 adult outcome; NYC tract | [Methods](docs/models/loneliness.md), [notebook](notebooks/02_access_loneliness.ipynb), [coefficients](outputs/tables/access_loneliness_coefficients.csv) | Ecological, generated outcome; exposure is later than outcome; no causal effect |
| Are café-like establishments associated with business applications? | CBP NAICS 722515, BFS annual county applications, ACS population; all 62 NY counties, 2018–2023 | [Methods](docs/models/panel.md), [notebook](notebooks/03_county_panel.ipynb), [coefficients](outputs/tables/panel_coefficients.csv) | Eight county/year FE specifications with county-clustered uncertainty; applications are not business births |
| How has socializing time changed? | BLS ATUS official series; national time trend | [Microdata design](docs/models/atus.md), [published-series fallback](docs/models/atus_published.md), [notebook](notebooks/04_socializing_trend.ipynb) | Published all-person series can run when archive access fails; age 15–24 microdata remains explicitly incomplete in that case |
| How does an independent index compare? | Third Place Index and official NYC supply; matched tracts | [Methods/rights](docs/models/third_place_index.md), [aggregate QA](outputs/tables/third_place_index_qa_summary.csv) | Local-only index archive; public schema/aggregate comparisons only |
| Did a library intervention cause a change? | Requires credible treatment dates and aligned pre/post direct outcomes | [Design and evidence gate](docs/models/library_did.md) | **Not estimated**; no invented event-study chart |

The NYC exposure is a conservative selected-facility count within straight-line distance of each tract's Census internal point. It does not measure walking access, capacity, welcome, prices, opening hours, or actual social participation. Separate library/park geometry supplements are audited and retained without double-counting them in FacDB.

## Reproduce in five steps

Use Python 3.13 for the tested lock. Python ≥3.11 is allowed by the package declaration, but other runtimes require revalidation. Tested locally on macOS; a GitHub workflow is configured to check Linux.

```sh
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.lock
python -m pip install --no-deps -e .
econhack verify
python -m pytest -q
econhack run --offline
python scripts/build_notebooks.py --execute
```

The public repository includes small official raw responses plus processed extracts for replay. Large nationwide ACS files and CBP/ATUS archives are omitted from Git; URLs, timestamps, sizes, SHA-256 hashes, parsers, and extraction rules remain available. `econhack verify` checks all files present plus every required distributed processed extract and reports omitted large inputs separately.

For source acquisition/rebuild, run `econhack run` with internet access. This fetches absent raw inputs, validates source types and hashes, and estimates each model independently. **A blocked source is reported in the status registry**, and the BLS published-series fallback does not masquerade as a completed youth microdata analysis. Data needing redistribution clarification remain in ignored `data/restricted/`. See [data rights](DATA_LICENSES.md).

Run one module with `econhack run --model nyc`, `--model panel`, `--model atus`, `--model supplements`, or `--model third_place_index`. `--offline` disables downloads. Model estimation and notebook execution need no Census API key. The source API returned HTML “Missing Key” in this session; official ACS/CBP bulk downloads avoid that dependency. Credentials are never written to manifests.

### If the installed command cannot find the project

Some macOS environments mark the editable-install `.pth` registration file as hidden, which Python can skip. If `econhack` reports `ModuleNotFoundError: econhack` despite a successful installation, run from this repository's root with an explicit source path:

```sh
PYTHONPATH=src .venv/bin/python -m econhack.cli verify
PYTHONPATH=src .venv/bin/python -m econhack.cli run --offline
PYTHONPATH=src .venv/bin/python scripts/build_notebooks.py --execute
```

These commands use the repository's code and the same pinned environment. The notebook setup also selects the repository source explicitly.

### Refreshing data

Cached inputs are immutable and hash-checked. Keep raw files and manifests together. For a fresh vintage, use a new checkout or archive the existing data/manifests/results before removing caches; rerun acquisition and review QA/definition changes. To force ACS extraction from existing bulk sources, archive/remove only the corresponding `data/processed/acs2023_nyc_*.csv` and processed manifest as a deliberate regeneration step. Never hand-edit datasets to make a model pass.

## Repository map

```text
src/econhack/       Acquisition, cleaning, QA, estimation, charts, CLI
data/raw/          Official source snapshots; large downloads stay local
data/processed/    Distributable extracts and model inputs
data/restricted/   Ignored Third Place Index archive; not part of the repo
data/*manifest*   Provenance and integrity hashes
docs/models/       Variables, hypotheses, formulas, diagnostics, limitations
docs/              Protocol, source-note review, findings, student brief
notebooks/         Executed, portable research companions
scripts/           Notebook builder and bounded source-discovery utility
tests/             Source parsing, sentinel handling, joins, weights, lags, estimability
outputs/tables/    Regression tables, correlations, covariances, coverage
outputs/figures/   Reproducible PNG and SVG charts
outputs/qa/        Missingness, exclusions, uniqueness, diagnostics
.github/workflows/ Offline reproduction and testing
```

## Research standards

- Distinguish a location, accessible space, actual use, social connection, and a health/economic outcome.
- Preserve geographic strings, source universes, observation periods, missing/suppressed values, and margins of error.
- Report exact estimation samples, FE/weighting choices, covariance estimators, intervals, residual diagnostics, and sensitivity results.
- Do not call an observational association causal or an imprecise estimate evidence of no effect. Multiple exploratory specifications are not a registered confirmatory analysis.
- CDC estimates and ACS five-year periods carry shared modeling/sampling error. Spatial and temporal dependence, reverse causality, and denominator-driven correlation remain material limitations.
- The original attachment is summarized in [source-note review](docs/source_notes_review.md). Private organizer logistics are excluded. Prior assistant replies were inaccessible reference placeholders; no missing recommendations are claimed to have been recovered.

Official source links and source-specific caveats are in the model guides and manifests. No agency endorsement is implied. No software license has been selected; source data retain their own terms.
