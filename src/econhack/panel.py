"""New York county panel: employer snack/beverage establishments and applications."""

import logging
import os
import re
from itertools import combinations
from pathlib import Path
from zipfile import ZipFile

import numpy as np
import pandas as pd
import statsmodels.api as sm

from .common import PROCESSED, ROOT, fetch, record_status, save_figure, save_table

logger = logging.getLogger(__name__)

YEARS = tuple(range(2018, 2024))
NY_COUNTIES = tuple(f"36{county:03d}" for county in range(1, 124, 2))
NAICS = "722515"
NAICS_VINTAGE = 2017
COVID_YEARS = (2020, 2021)
BFS_URL = "https://www.census.gov/econ/bfs/xlsx/bfs_county_apps_annual.xlsx"
LICENSE = "U.S. Census Bureau public data; cite Census and retain disclosure/measurement caveats."
OUTCOME = "applications_per_10k"
CURRENT = "proxy_establishments_per_10k"
LAGGED = "proxy_establishments_per_10k_lag1"


def acs_url(year):
    folder = "prototype" if year <= 2020 else "table-based-SF/data"
    return (f"https://www2.census.gov/programs-surveys/acs/summary_file/{year}/"
            f"{folder}/5YRData/acsdt5y{year}-b01003.dat")


def cbp_url(year):
    return (f"https://www2.census.gov/programs-surveys/cbp/datasets/{year}/"
            f"cbp{year % 100:02d}co.zip")


def _column(value):
    return re.sub(r"[^a-z0-9]", "", str(value).strip().lower())


def _fips(values, width):
    return values.astype("string").str.strip().str.replace(r"\.0$", "", regex=True).str.zfill(width)


def _counts(values, flags=None):
    raw = values.astype("string").fillna("").str.strip()
    numeric = pd.to_numeric(raw.str.replace(",", "", regex=False), errors="coerce")
    suppressed = raw.str.upper().isin(["D", "S", "N", "(D)", "(S)", "(N)"])
    if flags is not None:
        suppressed |= flags.astype("string").str.strip().str.upper().isin(["D", "S", "N"])
    valid = numeric.notna() & np.isfinite(numeric) & numeric.ge(0) & numeric.mod(1).eq(0) & ~suppressed
    status = pd.Series("invalid", index=values.index, dtype="string")
    status.loc[raw.isin(["", "NA", "N/A", "null", "-", "--", "."])] = "missing"
    status.loc[suppressed] = "suppressed"
    status.loc[valid & numeric.gt(0)] = "observed"
    status.loc[valid & numeric.eq(0)] = "observed_zero"
    return numeric.where(valid).astype(float), status, raw


def _unique(frame, label):
    if frame.duplicated(["county_fips", "year"]).any():
        raise ValueError(f"{label}: duplicate county-year keys; refusing an ambiguous merge")
    return frame


def parse_cbp(path, year):
    """Read county totals, using EST/ESTAB rather than employment or size bins."""
    pieces = []
    with ZipFile(path) as archive:
        members = [name for name in archive.namelist() if name.lower().endswith((".txt", ".csv"))]
        if len(members) != 1:
            raise ValueError("CBP ZIP must contain exactly one county data file")
        with archive.open(members[0]) as handle:
            for chunk in pd.read_csv(handle, dtype=str, keep_default_na=False, chunksize=100_000):
                chunk.columns = [_column(name) for name in chunk.columns]
                required = {"fipstate", "fipscty", "naics"}
                if not required.issubset(chunk.columns):
                    raise ValueError("Unexpected CBP county file schema")
                selected = chunk.loc[(_fips(chunk.fipstate, 2) == "36") &
                                     (chunk.naics.str.strip() == NAICS)].copy()
                for name in ["lfo", "empszes"]:
                    if name in selected:
                        selected = selected.loc[_fips(selected[name], 3) == "001"]
                pieces.append(selected)
    data = pd.concat(pieces, ignore_index=True)
    measure = next((name for name in ["est", "estab"] if name in data), None)
    if measure is None:
        raise ValueError("CBP lacks the establishment count EST/ESTAB")
    data["county_fips"] = _fips(data.fipstate, 2) + _fips(data.fipscty, 3)
    data = data.loc[data.county_fips.isin(NY_COUNTIES)].copy()
    flag = next((name for name in ["estflag", "estabf", "estabflag", "estf"] if name in data), None)
    values, status, raw = _counts(data[measure], data[flag] if flag else None)
    result = pd.DataFrame({"county_fips": data.county_fips, "year": year,
                           "proxy_establishments": values, "cbp_status": status,
                           "cbp_estab_raw": raw, "cbp_estab_flag": data[flag] if flag else "",
                           "cbp_source_url": cbp_url(year)})
    if result.empty:
        raise ValueError("CBP file contains no New York NAICS 722515 records")
    return _unique(result, "CBP")


def parse_bfs(path, years=YEARS):
    """Locate the documented wide BAyyyy header, including workbook title rows."""
    with pd.ExcelFile(path, engine="openpyxl") as workbook:
        for sheet in workbook.sheet_names:
            preview = pd.read_excel(workbook, sheet_name=sheet, header=None, nrows=40, dtype=str)
            for position, (_, row) in enumerate(preview.iterrows()):
                names = {_column(value) for value in row.dropna()}
                if "countycode" in names and any(re.fullmatch(r"ba\d{4}", name) for name in names):
                    data = pd.read_excel(workbook, sheet_name=sheet, header=int(position), dtype=str,
                                         keep_default_na=False)
                    data.columns = [_column(name) for name in data.columns]
                    data["county_fips"] = _fips(data.countycode, 5)
                    data = data.loc[data.county_fips.isin(NY_COUNTIES)].copy()
                    if "statefips" in data and not (_fips(data.statefips, 2) == "36").all():
                        raise ValueError("BFS state and county FIPS disagree")
                    pieces = []
                    for year in years:
                        if f"ba{year}" not in data:
                            raise ValueError(f"BFS workbook lacks BA{year}")
                        values, status, raw = _counts(data[f"ba{year}"])
                        pieces.append(pd.DataFrame({
                            "county_fips": data.county_fips, "year": year,
                            "county_name": data.get("county", data.county_fips),
                            "business_applications": values, "bfs_status": status,
                            "bfs_applications_raw": raw, "bfs_source_url": BFS_URL,
                        }))
                    result = _unique(pd.concat(pieces, ignore_index=True), "BFS")
                    if result.empty:
                        raise ValueError("BFS workbook contains no New York county rows")
                    return result
    raise ValueError("BFS workbook lacks documented County Code / BAyyyy header")


def parse_population(path, year):
    """Filter national table B01003 to exact NY county summary-level GEO_IDs."""
    with Path(path).open(encoding="utf-8-sig") as handle:
        header = handle.readline()
    separator = "|" if "|" in header else ","
    pieces = []
    for chunk in pd.read_csv(path, sep=separator, dtype=str, keep_default_na=False, chunksize=100_000):
        chunk.columns = [_column(name) for name in chunk.columns]
        estimate = next((name for name in ["b01003e001", "b01003001e"] if name in chunk), None)
        margin = next((name for name in ["b01003m001", "b01003001m"] if name in chunk), None)
        if "geoid" not in chunk or estimate is None:
            raise ValueError("ACS bulk file lacks GEO_ID / B01003 population estimate")
        selected = chunk.loc[chunk.geoid.str.fullmatch(r"0500000US36\d{3}")].copy()
        values, status, raw = _counts(selected[estimate])
        status.loc[values.eq(0)] = "invalid_denominator"
        values = values.where(values.gt(0))
        margins = (
            pd.to_numeric(selected[margin], errors="coerce")
            if margin else pd.Series(np.nan, index=selected.index)
        )
        pieces.append(pd.DataFrame({
            "county_fips": selected.geoid.str[-5:], "year": year,
            "population_acs5": values, "population_status": status, "population_raw": raw,
            "population_moe90": margins.where(margins.ge(0)),
            "population_source_url": acs_url(year),
        }))
    result = _unique(pd.concat(pieces, ignore_index=True), "ACS")
    if result.empty:
        raise ValueError("ACS bulk file contains no New York county population rows")
    return result


def build_panel(cbp, bfs, population, years=YEARS, counties=NY_COUNTIES):
    """Retain the explicit geography-year grid; absent records never imply zero."""
    grid = pd.MultiIndex.from_product([counties, years], names=["county_fips", "year"]).to_frame(index=False)
    for data, label in [(cbp, "CBP"), (bfs, "BFS"), (population, "ACS")]:
        grid = grid.merge(_unique(data, label), on=["county_fips", "year"], how="left", validate="one_to_one")
    for name in ["cbp_status", "bfs_status", "population_status"]:
        grid[name] = grid[name].fillna("missing_row")
    grid["state_fips"] = "36"
    grid["state"] = "New York"
    grid["naics"] = NAICS
    grid["naics_vintage"] = NAICS_VINTAGE
    grid["acs_period_start"] = grid.year - 4
    grid["acs_period_end"] = grid.year
    denominator = grid.population_acs5.where(grid.population_acs5.gt(0))
    grid[CURRENT] = 10_000 * grid.proxy_establishments / denominator
    grid[OUTCOME] = 10_000 * grid.business_applications / denominator
    grid = grid.sort_values(["county_fips", "year"]).reset_index(drop=True)
    previous = grid[["county_fips", "year", CURRENT]].rename(columns={CURRENT: LAGGED})
    previous["year"] += 1
    grid = grid.merge(previous, on=["county_fips", "year"], how="left", validate="one_to_one")
    grid["lag_source_year"] = (grid.year - 1).where(grid[LAGGED].notna()).astype("Int64")
    grid["complete_current"] = grid[[OUTCOME, CURRENT]].notna().all(axis=1)
    grid["complete_comparison"] = grid[[OUTCOME, CURRENT, LAGGED]].notna().all(axis=1)
    return grid


def coverage_table(panel):
    rows = []
    for year, data in panel.groupby("year", sort=True):
        row = {"year": int(year), "expected_counties": len(NY_COUNTIES), "grid_counties": len(data),
               "complete_current": int(data.complete_current.sum()),
               "complete_comparison": int(data.complete_comparison.sum())}
        for status in ["cbp_status", "bfs_status", "population_status"]:
            for value in ["observed", "observed_zero", "suppressed", "missing", "missing_row", "invalid", "invalid_denominator"]:
                row[f"{status}_{value}"] = int(data[status].eq(value).sum())
        rows.append(row)
    return pd.DataFrame(rows)


def _fixed_effects(data) -> pd.DataFrame:
    categories = data[["county_fips", "year"]].astype(str)
    effects = pd.get_dummies(categories, columns=["county_fips", "year"], drop_first=True, dtype=float)
    return pd.DataFrame(sm.add_constant(effects, has_constant="add")).astype(float)


def residualize(data, columns):
    effects = _fixed_effects(data).to_numpy()
    values = data[columns].to_numpy(dtype=float)
    coefficients = np.linalg.lstsq(effects, values, rcond=None)[0]
    return pd.DataFrame(values - effects @ coefficients, columns=columns, index=data.index)


def model_samples(panel):
    """Matched current/lag models share rows; COVID drops lag exposures too."""
    specifications = [("current", [CURRENT], [OUTCOME, CURRENT]),
                      ("current_matched", [CURRENT], [OUTCOME, CURRENT, LAGGED]),
                      ("lag1_matched", [LAGGED], [OUTCOME, CURRENT, LAGGED]),
                      ("joint_matched", [CURRENT, LAGGED], [OUTCOME, CURRENT, LAGGED])]
    for sensitivity in ["all_years", "exclude_2020_2021"]:
        for specification, predictors, required in specifications:
            data = panel.loc[np.isfinite(panel[required].astype(float)).all(axis=1)].copy()
            if sensitivity != "all_years":
                data = data.loc[~data.year.isin(COVID_YEARS)]
                if specification != "current":
                    data = data.loc[~(data.year - 1).isin(COVID_YEARS)]
            yield f"{specification}_{sensitivity}", predictors, data


def fit_models(panel):
    coefficient_rows, diagnostic_rows, covariance_rows, residual_rows, sample_rows = [], [], [], [], []
    for model, predictors, data in model_samples(panel):
        for row in data[["county_fips", "year"]].to_dict("records"):
            sample_rows.append({"model": model, **row})
        diagnostic = {"model": model, "nobs": len(data), "counties": data.county_fips.nunique(),
                      "years": ",".join(str(year) for year in sorted(data.year.unique())),
                      "status": "not_estimable", "reason": "Insufficient counties or years"}
        if diagnostic["counties"] < 2 or data.year.nunique() < 2:
            diagnostic_rows.append(diagnostic)
            continue
        effects = _fixed_effects(data)
        design = pd.concat([effects, data[predictors].astype(float)], axis=1)
        rank = int(np.linalg.matrix_rank(design))
        within = residualize(data, [OUTCOME, *predictors])
        diagnostic.update(design_rank=rank, design_columns=design.shape[1], residual_df=len(data) - rank,
                          singleton_counties=int(data.groupby("county_fips").size().eq(1).sum()))
        for predictor in predictors:
            diagnostic[f"within_sd_{predictor}"] = float(within[predictor].std())
        if rank != design.shape[1] or len(data) <= rank or within[OUTCOME].std() < 1e-10:
            diagnostic["reason"] = "Rank deficient design, no residual degrees of freedom, or no within outcome variation"
            diagnostic_rows.append(diagnostic)
            continue
        result = sm.OLS(data[OUTCOME].astype(float), design).fit(
            cov_type="cluster", cov_kwds={"groups": data.county_fips, "use_correction": True,
                                          "df_correction": True}, use_t=True)
        intervals = result.conf_int()
        finite = np.isfinite(result.bse[predictors]).all() and np.isfinite(intervals.loc[predictors]).all().all()
        diagnostic.update(status="estimated" if finite else "invalid_inference",
                          reason="County and year fixed effects; county-clustered t inference" if finite else "Nonfinite clustered inference",
                          r_squared=float(result.rsquared),
                          within_r_squared=float(1 - np.square(result.resid).sum() / np.square(within[OUTCOME]).sum()),
                          rmse=float(np.sqrt(np.mean(np.square(result.resid)))),
                          condition_number=float(result.condition_number), cluster_df=diagnostic["counties"] - 1,
                          max_leverage=float(result.get_influence().hat_matrix_diag.max()))
        diagnostic_rows.append(diagnostic)
        if not finite:
            continue
        for predictor in predictors:
            coefficient_rows.append({"model": model, "term": predictor, "coefficient": result.params[predictor],
                                     "std_error": result.bse[predictor], "p_value": result.pvalues[predictor],
                                     "ci_lower": intervals.loc[predictor, 0], "ci_upper": intervals.loc[predictor, 1],
                                     "nobs": len(data), "county_clusters": diagnostic["counties"],
                                     "cluster_df": diagnostic["counties"] - 1, "covariance": "cluster_county",
                                     "outcome": OUTCOME, "county_fe": True, "year_fe": True})
            for other in predictors:
                covariance_rows.append({"model": model, "term": predictor, "other_term": other,
                                        "cluster_covariance": result.cov_params().loc[predictor, other]})
        for position, (_, row) in enumerate(data.iterrows()):
            residual_rows.append({"model": model, "county_fips": row.county_fips, "year": row.year,
                                  "fitted": float(result.fittedvalues.iloc[position]),
                                  "residual": float(result.resid.iloc[position])})
    return {"panel_coefficients": pd.DataFrame(coefficient_rows, columns=[
                "model", "term", "coefficient", "std_error", "p_value", "ci_lower", "ci_upper",
                "nobs", "county_clusters", "cluster_df", "covariance", "outcome", "county_fe", "year_fe"]),
            "panel_model_diagnostics": pd.DataFrame(diagnostic_rows),
            "panel_coefficient_covariance": pd.DataFrame(covariance_rows, columns=[
                "model", "term", "other_term", "cluster_covariance"]),
            "panel_residuals": pd.DataFrame(residual_rows, columns=[
                "model", "county_fips", "year", "fitted", "residual"]),
            "panel_model_samples": pd.DataFrame(sample_rows, columns=["model", "county_fips", "year"])}


def association_statistics(panel):
    rows = []
    variables = ["proxy_establishments", "business_applications", "population_acs5", CURRENT, OUTCOME, LAGGED]
    for first, second in combinations(variables, 2):
        data = panel.loc[np.isfinite(panel[[first, second]].astype(float)).all(axis=1)]
        for adjustment in ["pooled", "county_year_residuals"]:
            values = data[[first, second]] if adjustment == "pooled" else residualize(data, [first, second]) if len(data) else data[[first, second]]
            varying = len(values) >= 2 and values.std().gt(1e-10).all()
            rows.append({"first": first, "second": second, "adjustment": adjustment, "n_pairs": len(data),
                         "pearson": values[first].corr(values[second]) if varying else np.nan,
                         "spearman": values[first].corr(values[second], method="spearman") if varying else np.nan,
                         "sample_covariance_ddof1": values[first].cov(values[second]) if len(values) >= 2 else np.nan})
    return pd.DataFrame(rows)


def annual_summary(panel):
    rows = []
    for year, data in panel.groupby("year"):
        matched = data.loc[data.complete_current]
        population = matched.population_acs5.sum(min_count=1)
        establishments = matched.proxy_establishments.sum(min_count=1)
        applications = matched.business_applications.sum(min_count=1)
        rows.append({"year": year, "matched_counties": len(matched), "population_acs5": population,
                     "proxy_establishments": establishments, "business_applications": applications,
                     CURRENT: 10_000 * establishments / population if population > 0 else np.nan,
                     OUTCOME: 10_000 * applications / population if population > 0 else np.nan})
    return pd.DataFrame(rows)


def _coefficient_label(model, term):
    specification = model.removesuffix("_all_years").removesuffix("_exclude_2020_2021")
    labels = {"current": "Current · full", "current_matched": "Current · matched",
              "lag1_matched": "Prior year · matched",
              "joint_matched": "Joint current" if term == CURRENT else "Joint lag"}
    return labels[specification] + (" · pandemic excluded" if model.endswith("_exclude_2020_2021") else "")


def make_figures(panel, coverage, annual, models):
    import matplotlib.pyplot as plt

    figure, axes = plt.subplots(1, 2, figsize=(12, 5))
    for axis, variable, title in zip(axes, [CURRENT, OUTCOME],
                                     ["Snack/beverage employer establishments", "Business applications (all covered industries)"]):
        axis.plot(annual.year, annual[variable], marker="o")
        axis.axvspan(2019.5, 2021.5, color="#c37926", alpha=.12)
        axis.set(title=title, xlabel="Reference year", ylabel="Per 10,000 ACS 5-year residents")
    figure.suptitle("New York counties, 2018–2023 • paired observed county totals")
    figure.text(.5, -.02, "County coverage can vary; ACS releases overlap. Proxy is broader than cafes; applications are not formations.", ha="center", fontsize=9)
    figure.tight_layout()
    save_figure(figure, "panel_annual_trends")

    figure, axis = plt.subplots(figsize=(10, 5))
    for name, label in [("cbp_status", "CBP proxy"), ("bfs_status", "BFS applications"), ("population_status", "ACS population")]:
        observed = coverage[f"{name}_observed"] + coverage[f"{name}_observed_zero"]
        axis.plot(coverage.year, observed, marker="o", label=label)
    axis.axhline(62, color="#777", linestyle="--", label="62 NY counties")
    axis.set(xlabel="Reference year", ylabel="Counties with observed usable values", ylim=(0, 65), title="Coverage: missing or suppressed values remain missing")
    axis.legend()
    figure.tight_layout()
    save_figure(figure, "panel_coverage")

    figure, axes = plt.subplots(1, 2, figsize=(12, 5))
    for axis, predictor, title in zip(axes, [CURRENT, LAGGED], ["Contemporaneous proxy", "Prior-year proxy"]):
        sample = panel.loc[panel.complete_comparison]
        if len(sample):
            within = residualize(sample, [OUTCOME, predictor])
            axis.scatter(within[predictor], within[OUTCOME], s=18, alpha=.5)
        axis.axhline(0, color="#888", linewidth=.7)
        axis.axvline(0, color="#888", linewidth=.7)
        axis.set(title=title, xlabel="Proxy per 10,000 residents, FE residual", ylabel="Applications per 10,000 residents, FE residual")
    figure.suptitle("County and year effects removed • identical current/lag sample • descriptive")
    figure.tight_layout()
    save_figure(figure, "panel_within_associations")

    coefficients = models["panel_coefficients"]
    if not coefficients.empty:
        figure, axis = plt.subplots(figsize=(12, max(5, .45 * len(coefficients))))
        positions = np.arange(len(coefficients))
        axis.errorbar(coefficients.coefficient, positions,
                      xerr=[coefficients.coefficient - coefficients.ci_lower, coefficients.ci_upper - coefficients.coefficient], fmt="o", capsize=3)
        labels = [_coefficient_label(row.model, row.term) for row in coefficients.itertuples()]
        axis.set_yticks(positions, labels)
        axis.axvline(0, color="#777", linewidth=1)
        axis.set(title="Applications and snack/beverage establishment density: county/year FE",
                 xlabel="Applications per 10,000 per additional proxy establishment per 10,000\n95% county-clustered t intervals; observational associations")
        figure.tight_layout()
        save_figure(figure, "panel_coefficients")

    residuals = models["panel_residuals"]
    selected_model = "current_matched_all_years"
    if not residuals.empty and (residuals.model == selected_model).any():
        data = residuals.loc[residuals.model == selected_model]
        figure, axes = plt.subplots(1, 2, figsize=(12, 5))
        axes[0].scatter(data.fitted, data.residual, s=16, alpha=.5)
        axes[0].axhline(0, color="#777", linewidth=1)
        axes[0].set(title="Residual pattern", xlabel="Fitted applications per 10,000", ylabel="Residual")
        sm.qqplot(data.residual, line="s", ax=axes[1], markersize=3)
        axes[1].set_title("Residual quantiles")
        figure.suptitle("Matched contemporaneous county/year FE model diagnostics")
        figure.tight_layout()
        save_figure(figure, "panel_residual_diagnostics")


def _source_requests():
    return [
        ("BFS annual county applications", None, BFS_URL, "panel/bfs_county_apps_annual.xlsx", parse_bfs),
        *[("CBP county establishments", year, cbp_url(year), f"panel/cbp/cbp{year % 100:02d}co.zip", parse_cbp) for year in YEARS],
        *[("ACS 5-year B01003", year, acs_url(year), f"panel/acs/acsdt5y{year}-b01003.dat", parse_population) for year in YEARS],
    ]


def _replay_panel():
    cached = pd.read_csv(PROCESSED / "panel_county_year.csv", dtype=str, keep_default_na=False)
    acquisition = pd.read_csv(PROCESSED / "panel_acquisition.csv", dtype=str, keep_default_na=False)
    sources = [
        (["proxy_establishments", "cbp_status", "cbp_estab_raw", "cbp_estab_flag", "cbp_source_url"], "cbp_status"),
        (["county_name", "business_applications", "bfs_status", "bfs_applications_raw", "bfs_source_url"], "bfs_status"),
        (["population_acs5", "population_status", "population_raw", "population_moe90", "population_source_url"], "population_status"),
    ]
    numeric = ["year", "proxy_establishments", "business_applications", "population_acs5", "population_moe90",
               "naics_vintage", "acs_period_start", "acs_period_end", CURRENT, OUTCOME, LAGGED, "lag_source_year"]
    required = {"county_fips", "state_fips", "state", "naics", "complete_current", "complete_comparison", *numeric}
    required.update(name for columns, _ in sources for name in columns)
    if not required.issubset(cached.columns):
        raise ValueError(f"Processed panel is missing columns: {sorted(required - set(cached.columns))}")
    for name in numeric:
        converted = pd.to_numeric(cached[name], errors="coerce")
        if (cached[name].ne("") & converted.isna()).any() or np.isinf(converted).any():
            raise ValueError(f"Processed panel has invalid numeric values: {name}")
        cached[name] = converted.astype(float)
    _unique(cached, "Processed panel")
    expected = set(pd.MultiIndex.from_product([NY_COUNTIES, YEARS]))
    if set(zip(cached.county_fips, cached.year)) != expected:
        raise ValueError("Processed panel must contain exactly all 62 NY counties and years 2018–2023")
    cached["year"] = cached.year.astype(int)
    cached = cached.sort_values(["county_fips", "year"]).reset_index(drop=True)
    if not (cached.state_fips.eq("36") & cached.state.eq("New York") & cached.naics.eq(NAICS) &
            cached.naics_vintage.eq(NAICS_VINTAGE) & cached.acs_period_start.eq(cached.year - 4) &
            cached.acs_period_end.eq(cached.year)).all():
        raise ValueError("Processed panel geography, NAICS vintage or ACS period metadata disagree")
    for value, status, raw, flag in [
        ("proxy_establishments", "cbp_status", "cbp_estab_raw", "cbp_estab_flag"),
        ("business_applications", "bfs_status", "bfs_applications_raw", None),
        ("population_acs5", "population_status", "population_raw", None),
    ]:
        derived, derived_status, _ = _counts(cached[raw], cached[flag] if flag else None)
        if value == "population_acs5":
            derived_status.loc[derived.eq(0)] = "invalid_denominator"
            derived = derived.where(derived.gt(0))
        absent = cached[status].eq("missing_row")
        derived_status.loc[absent] = "missing_row"
        if (absent & cached[raw].ne("")).any() or not derived_status.eq(cached[status]).all():
            raise ValueError(f"Processed panel source status disagrees with raw values: {status}")
        if not np.allclose(cached[value], derived, rtol=0, atol=0, equal_nan=True):
            raise ValueError(f"Processed panel counts disagree with raw values: {value}")
    if cached.population_moe90.dropna().lt(0).any():
        raise ValueError("Processed panel population MOEs must be nonnegative or missing")
    frames = [cached.loc[cached[status].ne("missing_row"), ["county_fips", "year", *columns]].copy()
              for columns, status in sources]
    rebuilt = build_panel(*frames)
    for name in [CURRENT, OUTCOME, LAGGED, "lag_source_year"]:
        tolerance = 0 if name == "lag_source_year" else 1e-9
        if not np.allclose(cached[name], rebuilt[name].to_numpy(dtype=float, na_value=np.nan),
                           rtol=tolerance, atol=0 if name == "lag_source_year" else 1e-10, equal_nan=True):
            raise ValueError(f"Processed panel rate identity or exact-year lag disagrees: {name}")
    for name in ["complete_current", "complete_comparison"]:
        if not cached[name].isin(["True", "False"]).all() or not cached[name].eq("True").eq(rebuilt[name]).all():
            raise ValueError(f"Processed panel completeness flag disagrees: {name}")
    required_acquisition = {"source", "year", "url", "raw_relative_path", "status", "rows", "reason"}
    if not required_acquisition.issubset(acquisition.columns):
        raise ValueError("Processed panel acquisition log is missing required columns")
    requests = _source_requests()
    seen, records = set(), []
    for row in acquisition.to_dict("records"):
        year = None if row["year"] == "" else float(row["year"])
        matching = [request for request in requests if request[0] == row["source"] and request[1] == year]
        key = (row["source"], year)
        if len(matching) != 1 or key in seen:
            raise ValueError("Processed panel acquisition log has duplicate or unexpected source/year keys")
        seen.add(key)
        source, _, url, relative_path, _ = matching[0]
        if row["url"] != url or row["raw_relative_path"] != relative_path or row["status"] not in {"loaded", "failed"}:
            raise ValueError("Processed panel acquisition source URL, path or status disagrees")
        status, url_column = (("bfs_status", "bfs_source_url") if year is None else
                              ("cbp_status", "cbp_source_url") if source.startswith("CBP") else
                              ("population_status", "population_source_url"))
        selected = cached if year is None else cached.loc[cached.year.eq(year)]
        present = selected[status].ne("missing_row")
        if not selected.loc[present, url_column].eq(url).all() or selected.loc[~present, url_column].ne("").any():
            raise ValueError("Processed panel row source URLs disagree with acquisition log")
        rows = float(row["rows"])
        if not np.isfinite(rows) or rows != int(present.sum()) or (row["status"] == "failed") != (rows == 0):
            raise ValueError("Processed panel acquisition row count or failure status disagrees")
        records.append({**row, "year": None if year is None else int(year), "rows": int(rows)})
    if len(seen) != len(requests):
        raise ValueError("Processed panel acquisition log must cover all 13 source/year requests")
    return rebuilt, records


def _acquire_panel():
    acquisition, cbp_frames, population_frames = [], [], []
    bfs = pd.DataFrame(columns=["county_fips", "year", "county_name", "business_applications", "bfs_status", "bfs_applications_raw", "bfs_source_url"])
    for source, year, url, relative_path, parser in _source_requests():
        try:
            path = fetch(url, relative_path, source, LICENSE)
            data = parser(path) if year is None else parser(path, year)
            acquisition.append({"source": source, "year": year, "url": url, "raw_relative_path": relative_path,
                                "status": "loaded", "rows": len(data), "reason": ""})
            if year is None:
                bfs = data
            elif source.startswith("CBP"):
                cbp_frames.append(data)
            else:
                population_frames.append(data)
        except Exception as error:
            logger.exception("Panel source acquisition failed: %s (%s)", source, year)
            acquisition.append({"source": source, "year": year, "url": url, "raw_relative_path": relative_path,
                                "status": "failed", "rows": 0, "reason": f"{type(error).__name__}: {error}"})
    cbp = pd.concat(cbp_frames, ignore_index=True) if cbp_frames else pd.DataFrame(
        columns=["county_fips", "year", "proxy_establishments", "cbp_status", "cbp_estab_raw", "cbp_estab_flag", "cbp_source_url"])
    population = pd.concat(population_frames, ignore_index=True) if population_frames else pd.DataFrame(
        columns=["county_fips", "year", "population_acs5", "population_status", "population_raw", "population_moe90", "population_source_url"])
    return build_panel(cbp, bfs, population), acquisition


def run():
    """Fit the same analysis from official bulk sources or validated processed replay."""
    replay = os.environ.get("ECONHACK_OFFLINE") == "1"
    input_mode = "processed_panel_offline_replay" if replay else "verified_raw_bulk_sources"
    if replay:
        try:
            panel, acquisition = _replay_panel()
        except (OSError, ValueError) as error:
            record_status("panel", "blocked", f"Processed panel offline replay failed: {error}", input_mode=input_mode)
            raise
    else:
        panel, acquisition = _acquire_panel()
    coverage = coverage_table(panel)
    annual = annual_summary(panel)
    models = fit_models(panel)
    tables = {"panel_county_year": panel, "panel_acquisition": pd.DataFrame(acquisition),
              "panel_coverage": coverage, "panel_annual_summary": annual,
              "panel_correlations_covariance": association_statistics(panel), **models}
    paths = {name: Path(save_table(data, name)).relative_to(ROOT).as_posix() for name, data in tables.items()}
    if not replay:
        PROCESSED.mkdir(parents=True, exist_ok=True)
        panel.to_csv(PROCESSED / "panel_county_year.csv", index=False)
        pd.DataFrame(acquisition).to_csv(PROCESSED / "panel_acquisition.csv", index=False)
    make_figures(panel, coverage, annual, models)
    failed = [row for row in acquisition if row["status"] == "failed"]
    estimated = int(models["panel_model_diagnostics"].status.eq("estimated").sum())
    complete = int(panel.complete_current.sum())
    status = "complete" if not failed and complete == len(panel) and estimated == 8 else "partial" if estimated else "blocked"
    reason = (f"NY 62 counties, 2018–2023: {complete}/{len(panel)} usable current rows; "
              f"{estimated}/8 county/year FE models estimated; {len(failed)} source failures. "
              "NAICS 722515 is a snack/nonalcoholic beverage bar proxy; BFS measures applications, not formations.")
    record_status("panel", status, reason, geography="New York: all 62 counties", years=list(YEARS),
                  expected_rows=len(panel), usable_current_rows=complete, models_estimated=estimated,
                  failed_sources=failed, tables=paths, input_mode=input_mode,
                  processed_inputs=[(PROCESSED / name).relative_to(ROOT).as_posix() for name in
                                    ["panel_county_year.csv", "panel_acquisition.csv"]],
                  caveats=["ACS annual 5-year estimates overlap; population uncertainty is not propagated.",
                           "County BFS counts have disclosure-avoidance noise and IRS processing-year boundaries.",
                           "Observational associations do not identify cafe effects or actual business births."])
    return {"status": status, "reason": reason, "tables": paths, "input_mode": input_mode}
