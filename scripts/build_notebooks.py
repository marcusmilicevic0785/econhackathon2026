"""Build offline companion notebooks; use --execute to save real cell outputs.

Run .venv/bin/python scripts/build_notebooks.py --execute from the repository,
or invoke this script by absolute path from another working directory. No
kernel installation is needed: execution uses this process's Python interpreter.
"""

import argparse
import ast
import hashlib
from pathlib import Path
import sys
from textwrap import dedent

import nbformat


SETUP = '''
import hashlib
import importlib
import inspect
import io
import json
import os
from pathlib import Path
import subprocess
import sys

def find_repository():
    explicit = os.environ.get("ECONHACK_REPO")
    candidates = [Path(explicit).expanduser().resolve()] if explicit else [Path.cwd().resolve(), *Path.cwd().resolve().parents]
    for candidate in candidates:
        if (candidate / "src/econhack/cli.py").is_file() and (candidate / "pyproject.toml").is_file():
            return candidate
    raise FileNotFoundError("Open this notebook inside the repository, or set ECONHACK_REPO to its root.")

ROOT = find_repository()
os.environ["ECONHACK_OFFLINE"] = "1"
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".cache/matplotlib"))
sys.path.insert(0, str(ROOT / "src"))
environment = os.environ.copy()
environment["PYTHONPATH"] = str(ROOT / "src") + os.pathsep + environment.get("PYTHONPATH", "")
verification = subprocess.run(
    [sys.executable, "-m", "econhack.cli", "verify"], cwd=ROOT, env=environment,
    capture_output=True, text=True, check=True,
)
print(verification.stdout.strip())
print(f"Repository: {ROOT.name}\\nPython: {sys.version.split()[0]}\\nMode: local files only")

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from IPython.display import Code, Image, Markdown, display

pd.set_option("display.max_columns", 16)
pd.set_option("display.max_rows", 30)
pd.set_option("display.precision", 4)
plt.rcParams.update({"figure.figsize": (10, 5), "font.size": 11, "axes.spines.top": False,
                     "axes.spines.right": False, "axes.prop_cycle": plt.cycler(color=["#176b87", "#b85c38"])})
PROCESSED = ROOT / "data/processed"
TABLES = ROOT / "outputs/tables"
FIGURES = ROOT / "outputs/figures"
input_receipts = []
processed_manifest = json.loads((ROOT / "data/processed_manifest.json").read_text())

def local_file(relative):
    path = (ROOT / relative).resolve()
    if ROOT not in path.parents or not path.is_file():
        raise FileNotFoundError(f"Required local input missing: {relative}. Run the project pipeline and snapshot first.")
    return path

def receipt(path):
    relative = str(path.relative_to(ROOT))
    input_receipts.append({"path": relative, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})

def read_csv(relative, **kwargs):
    path = local_file(relative)
    if str(path.relative_to(ROOT)).startswith("data/processed/") and str(path.relative_to(ROOT)) not in processed_manifest:
        raise ValueError(f"Processed input is not in the verified manifest: {relative}. Run cli snapshot first.")
    receipt(path)
    return pd.read_csv(path, **kwargs)

def read_json(relative):
    path = local_file(relative)
    receipt(path)
    return json.loads(path.read_text())

def show_png(name, required=True):
    path = FIGURES / f"{name}.png"
    if not path.is_file() and not required:
        display(Markdown(f"Figure `{name}.png` was not produced; consult the model status and estimability table."))
        return
    path = local_file(str(path.relative_to(ROOT)))
    receipt(path)
    display(Image(data=path.read_bytes(), format="png", embed=True, width=1000))

def show_figure(figure):
    buffer = io.BytesIO()
    figure.savefig(buffer, format="png", dpi=140, bbox_inches="tight")
    display(Image(data=buffer.getvalue(), format="png", embed=True, width=1000))

def show_source(module_name, names):
    module = importlib.import_module(module_name)
    display(Markdown(f"Source: `src/{module_name.replace('.', '/')}.py`. Functions below are displayed, not invoked."))
    for name in names:
        display(Code(inspect.getsource(getattr(module, name)), language="python"))

def show_status(name):
    statuses = read_json("outputs/model_status.json")
    display(pd.DataFrame([{key: value for key, value in statuses.get(name, {"status": "not_run"}).items()
                           if key in {"status", "reason", "n", "updated_utc", "formula", "input_mode"}}]))
'''


def markdown(source):
    return nbformat.v4.new_markdown_cell(dedent(source).strip())


def code(source):
    return nbformat.v4.new_code_cell(dedent(source).strip())


def companion(title, methods, cells, caveats):
    return [
        markdown(f"# {title}\n\n## Goal\n\nReproduce the displayed results from distributed local inputs, without downloading data. "
                 "Run every cell in order. Numerical statements are computed in the result cells; none are hard-coded.\n\n"
                 "## Setup\n\nUse the project's Python environment. Start Jupyter inside this repository or set "
                 "`ECONHACK_REPO` explicitly. The first cell runs `python -m econhack.cli verify` before reading data. "
                 "The CLI checks source and processed manifests; tables and PNGs receive separate byte-hash receipts below. "
                 "No acquisition functions or model `run()` entrypoints are called."),
        code(SETUP), markdown("## Context and methods\n\n" + methods),
        *cells,
        markdown("## Interpretation and limits\n\n" + caveats),
        markdown("## Inputs used\n\nExact local inputs and SHA-256 hashes for this execution. "
                 "These receipts identify table/figure versions; they are not an independent validation of their statistical content."),
        code('display(pd.DataFrame(input_receipts).drop_duplicates().reset_index(drop=True))'),
    ]


def quality_cells():
    return companion("Data quality and provenance", "Inspect manifest coverage, source lineage, model status, and missingness. "
                     "A successful integrity check establishes byte consistency, not substantive validity. Missing large raw files may be "
                     "allowed by the distribution policy; missing or altered processed files are not.", [
        markdown("### Source inventory"),
        code('''
        raw_manifest = read_json("data/manifest.json")
        source_rows = [{"path": path, "source": entry.get("source"), "url": entry.get("url"),
                        "bytes": entry.get("bytes"), "distributed": (ROOT / path).is_file()}
                       for path, entry in raw_manifest.items()]
        display(pd.DataFrame(source_rows))
        statuses = read_json("outputs/model_status.json")
        display(pd.DataFrame([{"model": name, "status": entry.get("status"), "reason": entry.get("reason")}
                              for name, entry in statuses.items()]))
        '''),
        markdown("### Processed coverage and missing values"),
        code('''
        grain = {"nyc_access": ["geoid"], "nyc_loneliness": ["geoid"],
                 "nyc_selected_facilities": ["site_key"], "cdc_ny_loneliness": ["geoid"],
                 "panel_county_year": ["county_fips", "year"],
                 "atus_socializing_annual": ["year", "age_group"], "atus_published_annual": ["year"]}
        profiles = []
        for relative in sorted(processed_manifest):
            if not relative.endswith(".csv"):
                continue
            frame = read_csv(relative)
            keys = grain.get(Path(relative).stem, ["GEO_ID"] if "GEO_ID" in frame else [])
            profiles.append({"dataset": Path(relative).stem, "rows": len(frame), "columns": len(frame.columns),
                             "key": ", ".join(keys) or "see data dictionary",
                             "duplicate_keys": int(frame.duplicated(keys).sum()) if keys else np.nan,
                             "missing_cells_pct": 100 * frame.isna().to_numpy().mean() if frame.size else np.nan})
        profile_table = pd.DataFrame(profiles)
        display(profile_table)
        print("Duplicate site keys among invalid-coordinate facility records need separate interpretation; see facility_selection QA.")
        '''),
        code('''
        if not profile_table.empty:
            visible = profile_table.sort_values("missing_cells_pct", ascending=True)
            figure, axis = plt.subplots(figsize=(10, max(4, 0.35 * len(visible))))
            axis.barh(visible.dataset, visible.missing_cells_pct, color="#176b87")
            axis.set(xlabel="Missing cells (%) across all retained columns", title="Missingness inventory by processed extract", xlim=(0, 100))
            figure.tight_layout()
            show_figure(figure)
            plt.close(figure)
        '''),
        markdown("### Recorded QA summaries"),
        code('''
        summaries = []
        for path in sorted((ROOT / "outputs/qa").glob("*.json")):
            report = read_json(str(path.relative_to(ROOT)))
            if isinstance(report, dict):
                summaries.append({"check": path.stem, **{key: value for key, value in report.items()
                                   if isinstance(value, (int, float, str, bool)) or value is None}})
        display(pd.DataFrame(summaries))
        '''),
    ], "Inspect incomplete model statuses before using results. Coverage, source vintage, units, suppression, "
       "and ecological interpretation remain substantive checks even when hashes agree. Missing cells can be intentional, "
       "especially ATUS 2020, first-year lags, and unreported inference; they are never filled with invented zeros.")


def equity_cells():
    return companion("NYC access equity", "Unit: NYC census tract. Facility counts use spherical straight-line distance "
                     "from the Census tract internal point to selected facilities, with an 800 m main radius and 400/1200 m sensitivities. "
                     "The model is `log1p(nearby_800m) ~ log(income) + poverty_pct + youth_pct + older_pct + log1p(population_density) "
                     "+ C(borough)`, with HC3 covariance. The sample has population ≥100 and complete model variables. "
                     "ACS 2019–2023 estimates are joined to the current facility snapshot. See `docs/models/nyc_equity.md`.", [
        markdown("### Load tract inputs and verify transformations"),
        code('''
        from econhack.nyc import nearby_counts
        access = read_csv("data/processed/nyc_access.csv", dtype={"geoid": str, "county": str})
        facilities = read_csv("data/processed/nyc_selected_facilities.csv", dtype={"geoid": str, "county": str})
        assert not access.geoid.duplicated().any()
        np.testing.assert_allclose(np.log1p(access.nearby_800m), access.log_access)
        np.testing.assert_array_equal(nearby_counts(access, facilities, 800), access.nearby_800m)
        predictors = ["log_access", "log_income", "poverty_pct", "youth_pct", "older_pct", "log_density"]
        sample = access.loc[access.population.ge(100)].replace([np.inf, -np.inf], np.nan).dropna(subset=predictors).copy()
        display(sample[["geoid", "borough", "population", "income", "nearby_800m", "poverty_pct"]].head(12))
        print(f"Model sample: {len(sample):,} of {len(access):,} tracts; {len(facilities):,} selected facility records.")
        show_status("nyc_equity")
        '''),
        markdown("### Tidy model results and sensitivity"),
        code('''
        coefficients = read_csv("outputs/tables/nyc_equity_coefficients.csv")
        assert not coefficients.term.duplicated().any()
        display(coefficients)
        quintiles = read_csv("outputs/tables/nyc_equity_income_quintiles.csv")
        display(quintiles)
        display(read_csv("outputs/tables/nyc_equity_radius_sensitivity.csv"))
        '''),
        markdown("### Recreate the core plot with native Matplotlib"),
        code('''
        figure, axes = plt.subplots(1, 2, figsize=(12, 4.8))
        axes[0].scatter(sample.income / 1000, sample.nearby_800m, s=12, alpha=0.25)
        axes[0].set(xlabel="Median household income (2023 $ thousands)", ylabel="Selected facilities within 800 m",
                    title="Tract income and nearby supply", ylim=(0, None))
        axes[1].bar(quintiles.income_quintile, quintiles.median_nearby)
        axes[1].set(xlabel="Income quintile", ylabel="Median nearby facilities", title="Same model sample", ylim=(0, None))
        figure.tight_layout()
        show_figure(figure)
        plt.close(figure)
        '''),
        markdown("### Saved chart, diagnostics, correlation, covariance, and VIF"),
        code('''
        show_png("nyc_access_equity")
        show_png("nyc_equity_diagnostics")
        display(pd.DataFrame([read_json("outputs/qa/nyc_equity_diagnostics.json")]))
        display(read_csv("outputs/tables/nyc_equity_vif.csv"))
        display(read_csv("outputs/tables/nyc_equity_correlation.csv"))
        display(read_csv("outputs/tables/nyc_equity_covariance.csv"))
        '''),
        markdown("### Inspect the shared implementation"),
        code('show_source("econhack.nyc", ["nearby_counts", "equity"])'),
    ], "The selected-facility measure describes geographic supply, not verified opening hours, entry eligibility, walking routes, "
       "quality, or actual use. HC3 does not correct spatial dependence or ACS sampling uncertainty. Income associations are "
       "conditional and observational; facilities and tracts are not randomly assigned.")


def loneliness_cells():
    return companion("Access and modeled loneliness", "Unit: NYC tract. CDC PLACES 2025 release provides modeled 2023 crude "
                     "adult loneliness prevalence, joined by 11-digit tract GEOID to facility supply. The model is "
                     "`loneliness_pct ~ log_access + log_income + poverty_pct + youth_pct + older_pct + log_density + C(borough)`, "
                     "with HC3 covariance. The borough-only and adjusted models use the same complete-case sample. "
                     "See `docs/models/loneliness.md`.", [
        markdown("### Inspect the local analysis sample"),
        code('''
        sample = read_csv("data/processed/nyc_loneliness.csv", dtype={"geoid": str, "county": str})
        assert not sample.geoid.duplicated().any()
        assert sample.loneliness_pct.between(0, 100).all()
        display(sample[["geoid", "borough", "year", "population", "nearby_800m", "loneliness_pct"]].head(12))
        print(f"Complete-case tracts: {len(sample):,}; modeled outcome years: {sorted(sample.year.unique())}.")
        show_status("access_loneliness")
        '''),
        markdown("### Read exported estimates without refitting or hard-coded coefficients"),
        code('''
        coefficients = read_csv("outputs/tables/access_loneliness_coefficients.csv")
        assert not coefficients.term.duplicated().any()
        display(coefficients)
        sensitivity = read_csv("outputs/tables/loneliness_adjustment_sensitivity.csv")
        display(sensitivity)
        estimate = coefficients.loc[coefficients.term.eq("log_access")].iloc[0]
        print(f"Adjusted association: {estimate.coefficient:.3f} prevalence percentage points per unit of log1p(access); "
              f"95% HC3 interval [{estimate.ci_lower:.3f}, {estimate.ci_upper:.3f}].")
        '''),
        markdown("### Recreate the descriptive scatter"),
        code('''
        figure, axis = plt.subplots()
        axis.scatter(sample.nearby_800m, sample.loneliness_pct, s=15, alpha=0.3)
        axis.set(xlabel="Selected facilities within 800 m of tract internal point", ylabel="Modeled adult loneliness prevalence (%)",
                 title="NYC facility supply and modeled 2023 loneliness")
        figure.tight_layout()
        show_figure(figure)
        plt.close(figure)
        '''),
        markdown("### Saved charts and model diagnostics"),
        code('''
        show_png("access_loneliness_scatter")
        show_png("access_loneliness_diagnostics")
        display(pd.DataFrame([read_json("outputs/qa/access_loneliness_diagnostics.json")]))
        display(read_csv("outputs/tables/access_loneliness_vif.csv"))
        display(read_csv("outputs/tables/access_loneliness_correlation.csv"))
        display(read_csv("outputs/tables/access_loneliness_covariance.csv"))
        '''),
        markdown("### Inspect the actual model and adjustment comparison"),
        code('show_source("econhack.nyc", ["loneliness"])'),
    ], "CDC values are modeled area estimates, not independent respondent observations. Demographic adjustments overlap inputs "
       "to the CDC model. Facility/outcome timing differs; HC3 does not propagate CDC or ACS uncertainty or handle spatial dependence. "
       "Neither a tract association nor a change after adjustment establishes an individual or causal effect.")


def panel_cells():
    return companion("New York county panel", "Unit: county-year, all 62 New York counties, 2018–2023. Exposure: employer "
                     "establishments in 2017 NAICS 722515 (snack/nonalcoholic beverage bars, broader than cafes). Outcome: BFS business "
                     "applications, not realized formations. Both rates equal `10000 * count / population_acs5`. Lagged rates use the "
                     "exact prior calendar year and its denominator. Models include county/year fixed effects and county-clustered "
                     "t inference. Current/lag comparisons share complete rows. See `docs/models/panel.md`.", [
        markdown("### Verify the county-year grid, rates, and lag alignment"),
        code('''
        from econhack import panel as panel_module
        panel = read_csv("data/processed/panel_county_year.csv", dtype={"county_fips": str, "state_fips": str, "naics": str})
        assert not panel.duplicated(["county_fips", "year"]).any()
        assert len(panel) == len(panel_module.NY_COUNTIES) * len(panel_module.YEARS)
        for numerator, rate in [("proxy_establishments", panel_module.CURRENT), ("business_applications", panel_module.OUTCOME)]:
            np.testing.assert_allclose(panel[rate], 10000 * panel[numerator] / panel.population_acs5, equal_nan=True)
        previous = panel[["county_fips", "year", panel_module.CURRENT]].rename(columns={panel_module.CURRENT: "expected_lag"})
        previous["year"] += 1
        aligned = panel.merge(previous, on=["county_fips", "year"], how="left", validate="one_to_one")
        np.testing.assert_allclose(aligned[panel_module.LAGGED], aligned.expected_lag, equal_nan=True)
        display(panel[["county_fips", "year", "proxy_establishments", "business_applications", "population_acs5", "cbp_status", "bfs_status"]].head(12))
        show_status("panel")
        '''),
        markdown("### Coverage and estimability precede interpretation"),
        code('''
        display(read_csv("outputs/tables/panel_coverage.csv"))
        display(read_csv("outputs/tables/panel_acquisition.csv"))
        diagnostics = read_csv("outputs/tables/panel_model_diagnostics.csv")
        display(diagnostics)
        coefficients = read_csv("outputs/tables/panel_coefficients.csv")
        assert not coefficients.duplicated(["model", "term"]).any()
        display(coefficients)
        '''),
        markdown("### Recreate aggregate rates with the paired observed county totals"),
        code('''
        annual = read_csv("outputs/tables/panel_annual_summary.csv")
        display(annual)
        figure, axes = plt.subplots(1, 2, figsize=(12, 4.8))
        for axis, variable, label in zip(axes, [panel_module.CURRENT, panel_module.OUTCOME],
                                          ["Snack/beverage employer establishments", "Business applications"]):
            axis.plot(annual.year, annual[variable], marker="o")
            axis.axvspan(2019.5, 2021.5, alpha=0.12, color="#b85c38")
            axis.set(title=label, xlabel="Reference year", ylabel="Per 10,000 ACS 5-year residents", ylim=(0, None))
        figure.tight_layout()
        show_figure(figure)
        plt.close(figure)
        '''),
        markdown("### Saved evidence and diagnostics"),
        code('''
        show_png("panel_annual_trends")
        show_png("panel_coverage")
        show_png("panel_within_associations")
        show_png("panel_coefficients", required=not coefficients.empty)
        show_png("panel_residual_diagnostics", required=diagnostics.loc[diagnostics.model.eq("current_matched_all_years"), "status"].eq("estimated").any())
        associations = read_csv("outputs/tables/panel_correlations_covariance.csv")
        display(associations.loc[associations["first"].eq(panel_module.CURRENT)])
        display(read_csv("outputs/tables/panel_coefficient_covariance.csv"))
        '''),
        markdown("### Inspect transformations and model specification"),
        code('show_source("econhack.panel", ["build_panel", "model_samples", "fit_models"])'),
    ], "Suppression and absent records remain missing, not zeros. Adjacent ACS 5-year denominators overlap. Shared denominators, "
       "reverse causality, time-varying confounding, geographic dependence, and measurement error remain. The sensitivity removes "
       "2020/2021 outcomes and matched rows with 2020/2021 lag exposures; it does not remove all pandemic influence. Fixed effects "
       "and lags do not establish causality or out-of-sample predictive accuracy.")


def socializing_cells():
    return companion("ATUS socializing and communicating trends", "The preferred microdata outcome is primary-activity "
                     "T120101 for ages 15–24 and all ages 15+, using final survey weights and including zero-time diaries. "
                     "A separate official published-series fallback covers all persons 15+ and a broader published socializing aggregate. "
                     "It cannot substitute for the youth estimate or the detailed microdata code. The executed cells state which source "
                     "is available. Both exclude 2020 from trend fitting and display no annual survey confidence intervals. "
                     "See `docs/models/atus.md` and, when the published fallback is used, `docs/models/atus_published.md`.", [
        markdown("### Choose the available verified local series"),
        code('''
        micro_path = PROCESSED / "atus_socializing_annual.csv"
        statuses = read_json("outputs/model_status.json")
        micro_ready = micro_path.is_file() and (TABLES / "atus_socializing_regression.csv").is_file() and statuses.get("atus", {}).get("status") in {"completed", "complete"}
        if micro_ready:
            from econhack import atus as socializing_module
            annual = read_csv("data/processed/atus_socializing_annual.csv", dtype={"age_group": str})
            socializing_module.read_processed(micro_path)
            coefficients = read_csv("outputs/tables/atus_socializing_regression.csv")
            fitted = read_csv("outputs/tables/atus_socializing_fitted.csv")
            figure_name = "atus_socializing_trend"
            source_mode = "Weighted microdata: T120101, ages 15–24 and all 15+"
            show_status("atus")
        else:
            from econhack import atus_published as socializing_module
            annual = read_csv("data/processed/atus_published_annual.csv")
            coefficients = read_csv("outputs/tables/atus_published_regression.csv")
            fitted = read_csv("outputs/tables/atus_published_fitted.csv")
            figure_name = "atus_published_trend"
            source_mode = "Official published fallback: broader socializing/communicating aggregate, all ages 15+ only"
            show_status("atus")
            show_status("atus_published")
        print(source_mode)
        display(annual)
        display(coefficients)
        assert not fitted.year.eq(2020).any()
        '''),
        markdown("### Native plot from the shared implementation"),
        code('''
        figure = socializing_module.plot_trends(annual)
        show_figure(figure)
        plt.close(figure)
        show_png(figure_name)
        '''),
        markdown("### Descriptive changes calculated from the loaded series"),
        code('''
        observed = annual.loc[annual.year.ne(2020) & annual.minutes_per_day.notna()].sort_values("year")
        changes = []
        for age_group, series in observed.groupby("age_group", sort=False):
            first, last = series.iloc[0], series.iloc[-1]
            changes.append({"age_group": age_group, "start_year": int(first.year), "end_year": int(last.year),
                            "start_minutes_per_day": first.minutes_per_day, "end_minutes_per_day": last.minutes_per_day,
                            "change_minutes_per_day": last.minutes_per_day - first.minutes_per_day})
        display(pd.DataFrame(changes))
        '''),
        markdown("### Inspect fitted residuals and shared estimation code"),
        code('''
        display(fitted.head(12))
        figure, axis = plt.subplots()
        descriptive = fitted.loc[fitted.model.str.contains("descriptive")]
        for label, series in descriptive.groupby("age_group"):
            series = series.set_index("year").reindex(range(2003, 2025))
            axis.plot(series.index, series.residual, marker="o", label=f"Ages {label}")
        axis.axhline(0, color="#777777", linewidth=1)
        axis.set(xlabel="Diary year", ylabel="Residual (minutes/day)", title="Descriptive linear-trend residuals; gap at 2020")
        axis.legend()
        figure.tight_layout()
        show_figure(figure)
        plt.close(figure)
        show_source(socializing_module.__name__, ["fit_trends", "plot_trends"])
        '''),
    ], "This is primary-activity socializing/communicating, not total face-to-face time or an individual loneliness outcome. "
       "Published levels are rounded by BLS. There is no 2020 full-year estimate. Youth results require actual youth microdata. "
       "The full-period regression is descriptive; any pre-pandemic HAC inference in the microdata model is temporal uncertainty, "
       "not survey-design uncertainty. Do not interpret these trends as effects of a particular technology or policy.")


BUILDERS = {
    "00_data_quality": quality_cells,
    "01_nyc_access_equity": equity_cells,
    "02_access_loneliness": loneliness_cells,
    "03_county_panel": panel_cells,
    "04_socializing_trend": socializing_cells,
}


def build_notebook(name):
    notebook = nbformat.v4.new_notebook(cells=BUILDERS[name]())
    notebook.metadata.update({
        "kernelspec": {"display_name": "Python 3 (project environment)", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": ".".join(map(str, sys.version_info[:3]))},
        "econhack": {"builder": "scripts/build_notebooks.py", "execution": "not executed"},
    })
    for position, cell in enumerate(notebook.cells):
        cell.id = hashlib.sha256(f"{name}:{position}:{cell.source}".encode()).hexdigest()[:16]
        if cell.cell_type == "code":
            ast.parse(cell.source)
    nbformat.validate(notebook)
    return notebook


def execute_notebook(notebook, root, timeout):
    from jupyter_client import KernelManager
    from jupyter_client.kernelspec import KernelSpec
    from nbclient import NotebookClient

    class CurrentPythonKernelManager(KernelManager):
        @property
        def kernel_spec(self):
            return KernelSpec(argv=[sys.executable, "-m", "ipykernel_launcher", "-f", "{connection_file}"],
                              display_name="Current project Python", language="python")

    client = NotebookClient(notebook, timeout=timeout, startup_timeout=90, allow_errors=False,
                            kernel_manager_class=CurrentPythonKernelManager,
                            resources={"metadata": {"path": str(root)}})
    client.execute(cwd=str(root))
    notebook.metadata.econhack.execution = "executed top-to-bottom"
    nbformat.validate(notebook)
    return notebook


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--execute", action="store_true", help="Execute with this Python interpreter and embed real outputs")
    parser.add_argument("--notebooks", nargs="+", choices=tuple(BUILDERS), default=list(BUILDERS))
    parser.add_argument("--timeout", type=int, default=300, help="Maximum seconds per code cell")
    arguments = parser.parse_args(argv)
    root = arguments.repo.expanduser().resolve()
    if not (root / "src/econhack/cli.py").is_file() or not (root / "pyproject.toml").is_file():
        parser.error("--repo must identify the econhack repository")
    if arguments.timeout <= 0:
        parser.error("--timeout must be positive")
    directory = root / "notebooks"
    directory.mkdir(parents=True, exist_ok=True)
    for name in dict.fromkeys(arguments.notebooks):
        notebook = build_notebook(name)
        path = directory / f"{name}.ipynb"
        if arguments.execute:
            print(f"Executing {name} with {sys.executable}", flush=True)
            try:
                execute_notebook(notebook, root, arguments.timeout)
            except Exception:
                notebook.metadata.econhack.execution = "failed; inspect the error output and rerun after fixing local inputs"
                nbformat.write(notebook, path)
                raise
        nbformat.write(notebook, path)
        print(f"Wrote {path.relative_to(root)} ({notebook.metadata.econhack.execution})", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
