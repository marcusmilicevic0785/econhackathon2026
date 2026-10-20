"""Offline checks for source semantics, exact lags and clustered panel models."""

import shutil
from pathlib import Path
from zipfile import ZipFile

import numpy as np
import pandas as pd
import pytest
import statsmodels.api as sm
from scipy.stats import t as student_t

from econhack import panel


def test_cbp_establishment_field_and_suppression(tmp_path):
    path = tmp_path / "cbp23co.zip"
    with ZipFile(path, "w") as archive:
        archive.writestr("cbp23co.txt", 'fipstate,fipscty,naics,empflag,emp,est\n'
                         '36,001,722515,D,999,0\n36,003,722515,,100,D\n'
                         '36,005,722515,,20,12\n36,007,722511,,90,99\n'
                         '35,001,722515,,90,99\n36,009,722515,,20,-999999999\n')
    data = panel.parse_cbp(path, 2023).set_index("county_fips")
    assert len(data) == 4
    assert data.loc["36001", "proxy_establishments"] == 0
    assert data.loc["36001", "cbp_status"] == "observed_zero"
    assert data.loc["36003", "cbp_status"] == "suppressed"
    assert np.isnan(data.loc["36003", "proxy_establishments"])
    assert data.loc["36005", "proxy_establishments"] == 12
    assert data.loc["36009", "cbp_status"] == "invalid"


def test_cbp_duplicate_totals_fail(tmp_path):
    path = tmp_path / "cbp.zip"
    with ZipFile(path, "w") as archive:
        archive.writestr("cbp.txt", "fipstate,fipscty,naics,est\n36,001,722515,1\n36,001,722515,2\n")
    with pytest.raises(ValueError, match="duplicate county-year"):
        panel.parse_cbp(path, 2023)


def test_cbp_only_total_dimensions_and_establishment_flags(tmp_path):
    path = tmp_path / "cbp.zip"
    with ZipFile(path, "w") as archive:
        archive.writestr("cbp.txt", "fipstate,fipscty,naics,estab,estab_f,lfo,empszes\n"
                         "36,001,722515,0,D,001,001\n36,001,722515,15,,001,210\n"
                         "36,001,722515,20,,002,001\n")
    data = panel.parse_cbp(path, 2023)
    assert len(data) == 1
    assert data.cbp_status.iloc[0] == "suppressed"
    assert np.isnan(data.proxy_establishments.iloc[0])


def test_bfs_documented_wide_workbook_with_preamble(tmp_path):
    path = tmp_path / "bfs.xlsx"
    data = pd.DataFrame({"State": ["NY", "NY", "CA"], "County": ["Albany", "Allegany", "Alameda"],
                         "County Code": [36001, 36003, 6001], "state_fips": [36, 36, 6],
                         "county_fips": [1, 3, 1], "BA2018": [0, "D", 999], "BA2019": [23, 25, 999]})
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        pd.DataFrame([["Annual applications"]]).to_excel(writer, index=False, header=False)
        data.to_excel(writer, index=False, startrow=3)
    result = panel.parse_bfs(path, years=(2018, 2019)).set_index(["county_fips", "year"])
    assert len(result) == 4
    assert result.loc[("36001", 2018), "business_applications"] == 0
    assert result.loc[("36003", 2018), "bfs_status"] == "suppressed"
    assert result.loc[("36003", 2019), "business_applications"] == 25
    assert "formations" not in result.columns


@pytest.mark.parametrize("separator,estimate,margin", [("|", "B01003_E001", "B01003_M001"),
                                                      (",", "B01003_001E", "B01003_001M")])
def test_acs_exact_county_geography_and_sentinels(tmp_path, separator, estimate, margin):
    path = tmp_path / "population.dat"
    pd.DataFrame({"GEO_ID": ["0500000US36001", "0500000US36003", "0500000US36005",
                              "1400000US36001000100", "0500000US06001"],
                  estimate: [10000, -666666666, 0, 200, 999], margin: [-555555555, 20, 10, 10, 10]}).to_csv(path, sep=separator, index=False)
    data = panel.parse_population(path, 2023).set_index("county_fips")
    assert len(data) == 3
    assert data.loc["36001", "population_acs5"] == 10000
    assert np.isnan(data.loc["36001", "population_moe90"])
    assert data.loc["36003", "population_status"] == "invalid"
    assert np.isnan(data.loc["36003", "population_acs5"])
    assert data.loc["36005", "population_status"] == "invalid_denominator"


def _inputs():
    cbp = pd.DataFrame({"county_fips": ["36001", "36001", "36003"], "year": [2018, 2020, 2018],
                        "proxy_establishments": [4., 8., 0.], "cbp_status": ["observed", "observed", "observed_zero"]})
    bfs = pd.DataFrame({"county_fips": ["36001", "36001", "36003"], "year": [2018, 2020, 2018],
                        "business_applications": [40., 80., 10.], "bfs_status": ["observed"] * 3})
    population = pd.DataFrame({"county_fips": ["36001", "36001", "36003"], "year": [2018, 2020, 2018],
                               "population_acs5": [10000., 20000., 1000.], "population_status": ["observed"] * 3})
    return cbp, bfs, population


def test_grid_missing_not_zero_and_lag_never_bridges_gaps():
    data = panel.build_panel(*_inputs(), years=(2018, 2019, 2020), counties=("36001", "36003"))
    assert len(data) == 6
    data = data.set_index(["county_fips", "year"])
    assert data.loc[("36001", 2018), panel.CURRENT] == 4
    assert data.loc[("36001", 2020), panel.CURRENT] == 4
    assert data.loc[("36001", 2019), panel.LAGGED] == 4
    assert np.isnan(data.loc[("36001", 2020), panel.LAGGED])
    assert data.loc[("36003", 2018), panel.CURRENT] == 0
    assert data.loc[("36003", 2019), "cbp_status"] == "missing_row"
    assert np.isnan(data.loc[("36003", 2019), panel.CURRENT])
    assert set(data.naics_vintage) == {2017}
    assert data.loc[("36001", 2020), "acs_period_start"] == 2016


def test_nonconsecutive_requested_years_do_not_create_lag():
    data = panel.build_panel(*_inputs(), years=(2018, 2020), counties=("36001",))
    assert data[panel.LAGGED].isna().all()


def test_duplicate_merge_keys_rejected():
    cbp, bfs, population = _inputs()
    with pytest.raises(ValueError, match="duplicate"):
        panel.build_panel(pd.concat([cbp, cbp]), bfs, population)


def _synthetic_panel():
    random = np.random.default_rng(27)
    rows = []
    for county in range(12):
        previous = np.nan
        for year in panel.YEARS:
            exposure = 2 + county / 3 + (year - 2018) / 10 + random.normal()
            outcome = 7 * county + 3 * (year - 2018) + 2.5 * exposure + random.normal(scale=.3)
            rows.append({"county_fips": f"36{2 * county + 1:03d}", "year": year,
                         panel.CURRENT: exposure, panel.LAGGED: previous, panel.OUTCOME: outcome,
                         "proxy_establishments": exposure * 10, "business_applications": outcome * 10,
                         "population_acs5": 100000.})
            previous = exposure
    return pd.DataFrame(rows)


def test_matched_samples_and_strict_covid_lag_exclusion():
    data = _synthetic_panel()
    data.loc[(data.county_fips == "36001") & (data.year == 2019), panel.CURRENT] = np.nan
    samples = {name: sample for name, _, sample in panel.model_samples(data)}
    for sensitivity in ["all_years", "exclude_2020_2021"]:
        current = samples[f"current_matched_{sensitivity}"]
        lagged = samples[f"lag1_matched_{sensitivity}"]
        joint = samples[f"joint_matched_{sensitivity}"]
        assert current.index.equals(lagged.index)
        assert current.index.equals(joint.index)
    assert set(samples["lag1_matched_exclude_2020_2021"].year) == {2019, 2023}
    assert set(samples["current_exclude_2020_2021"].year) == {2018, 2019, 2022, 2023}


def test_fixed_effects_and_county_clustered_inference():
    data = _synthetic_panel()
    results = panel.fit_models(data)
    table = results["panel_coefficients"]
    current = table.loc[table.model == "current_all_years"].iloc[0]
    assert current.coefficient == pytest.approx(2.5, abs=.15)
    assert current.county_clusters == 12
    assert current.cluster_df == 11
    assert current.covariance == "cluster_county"
    expected_lower = current.coefficient - student_t.ppf(.975, 11) * current.std_error
    assert current.ci_lower == pytest.approx(expected_lower)
    design = pd.concat([panel._fixed_effects(data), data[[panel.CURRENT]]], axis=1)
    independent = sm.OLS(data[panel.OUTCOME], design).fit(
        cov_type="cluster", cov_kwds={"groups": data.county_fips, "use_correction": True, "df_correction": True}, use_t=True)
    assert current.std_error == pytest.approx(independent.bse[panel.CURRENT])
    assert set(results["panel_model_diagnostics"].status) == {"estimated"}


def test_time_invariant_exposure_is_not_identified():
    data = _synthetic_panel()
    data[panel.CURRENT] = data.groupby("county_fips")[panel.CURRENT].transform("mean")
    result = panel.fit_models(data)
    row = result["panel_model_diagnostics"].set_index("model").loc["current_all_years"]
    assert row.status == "not_estimable"
    assert "Rank deficient" in row.reason


def test_residualization_handles_unbalanced_panel():
    data = _synthetic_panel().drop(index=[2, 7, 8, 16, 29, 33])
    residuals = panel.residualize(data, [panel.CURRENT, panel.OUTCOME])
    assert np.abs(panel._fixed_effects(data).to_numpy().T @ residuals.to_numpy()).max() < 1e-8
    associations = panel.association_statistics(data)
    row = associations.loc[(associations["first"] == panel.CURRENT) &
                           (associations.second == panel.OUTCOME) &
                           (associations.adjustment == "county_year_residuals")].iloc[0]
    assert row.n_pairs == len(data)
    assert row.sample_covariance_ddof1 == pytest.approx(residuals[panel.CURRENT].cov(residuals[panel.OUTCOME]))


def test_annual_totals_use_the_same_observed_counties():
    data = panel.build_panel(*_inputs(), years=(2018, 2020), counties=("36001", "36003"))
    data.loc[data.county_fips == "36003", "business_applications"] = np.nan
    data["complete_current"] = data[[panel.CURRENT, panel.OUTCOME, "business_applications"]].notna().all(axis=1)
    annual = panel.annual_summary(data).set_index("year")
    assert annual.loc[2018, "matched_counties"] == 1
    assert annual.loc[2018, "population_acs5"] == 10000
    assert annual.loc[2018, panel.CURRENT] == 4


def test_run_offline_failure_reports_full_grid(monkeypatch, tmp_path):
    saved, statuses = {}, []
    def fail_fetch(*args):
        raise FileNotFoundError("fixture unavailable")
    def capture_table(frame, name):
        saved[name] = frame
        return tmp_path / f"{name}.csv"
    monkeypatch.setattr(panel, "fetch", fail_fetch)
    monkeypatch.setattr(panel, "save_table", capture_table)
    monkeypatch.setattr(panel, "make_figures", lambda *args: None)
    monkeypatch.setattr(panel, "record_status", lambda *args, **kwargs: statuses.append((args, kwargs)))
    monkeypatch.delenv("ECONHACK_OFFLINE", raising=False)
    monkeypatch.setattr(panel, "ROOT", tmp_path)
    monkeypatch.setattr(panel, "PROCESSED", tmp_path)
    result = panel.run()
    assert result["status"] == "blocked"
    assert len(saved["panel_county_year"]) == 372
    assert saved["panel_county_year"].county_fips.nunique() == 62
    assert saved["panel_county_year"].proxy_establishments.isna().all()
    assert len(saved["panel_acquisition"]) == 13
    assert statuses[0][1]["models_estimated"] == 0
    assert "coefficient" in saved["panel_coefficients"]
    assert "county_fips" in saved["panel_model_samples"]


def test_complete_pipeline_with_official_schema_fixtures(monkeypatch, tmp_path):
    random = np.random.default_rng(91)
    sources = {}
    bfs = pd.DataFrame({"State": "NY", "County": panel.NY_COUNTIES,
                        "County Code": panel.NY_COUNTIES, "state_fips": "36"})
    for year in panel.YEARS:
        counts = random.integers(2, 80, len(panel.NY_COUNTIES))
        applications = counts * 7 + random.integers(100, 600, len(counts))
        bfs[f"BA{year}"] = applications
        archive_path = tmp_path / f"cbp{year % 100}co.zip"
        with ZipFile(archive_path, "w") as archive:
            data = pd.DataFrame({"fipstate": "36", "fipscty": [code[-3:] for code in panel.NY_COUNTIES],
                                 "naics": panel.NAICS, "est": counts})
            archive.writestr(f"cbp{year % 100}co.txt", data.to_csv(index=False))
        sources[f"panel/cbp/cbp{year % 100:02d}co.zip"] = archive_path
        population_path = tmp_path / f"acsdt5y{year}-b01003.dat"
        pd.DataFrame({"GEO_ID": [f"0500000US{code}" for code in panel.NY_COUNTIES],
                      "B01003_E001": random.integers(20000, 100000, len(counts)),
                      "B01003_M001": 500}).to_csv(population_path, sep="|", index=False)
        sources[f"panel/acs/acsdt5y{year}-b01003.dat"] = population_path
    workbook_path = tmp_path / "bfs.xlsx"
    bfs.to_excel(workbook_path, index=False, engine="openpyxl", startrow=2)
    sources["panel/bfs_county_apps_annual.xlsx"] = workbook_path
    statuses = []
    output_tables = tmp_path / "outputs" / "tables"
    def capture_table(data, name):
        output_tables.mkdir(parents=True, exist_ok=True)
        destination = output_tables / f"{name}.csv"
        data.to_csv(destination, index=False)
        return destination
    def capture_figure(figure, name):
        import matplotlib.pyplot as plt
        for suffix in ["png", "svg"]:
            figure.savefig(tmp_path / f"{name}.{suffix}", bbox_inches="tight")
        plt.close(figure)
    monkeypatch.setattr(panel, "fetch", lambda url, relative, source, license_note: sources[relative])
    monkeypatch.setattr(panel, "save_table", capture_table)
    monkeypatch.setattr(panel, "save_figure", capture_figure)
    monkeypatch.setattr(panel, "record_status", lambda *args, **kwargs: statuses.append((args, kwargs)))
    monkeypatch.delenv("ECONHACK_OFFLINE", raising=False)
    monkeypatch.setattr(panel, "ROOT", tmp_path)
    monkeypatch.setattr(panel, "PROCESSED", tmp_path / "data" / "processed")
    result = panel.run()
    assert result["status"] == "complete"
    assert statuses[0][1]["models_estimated"] == 8
    assert statuses[0][1]["failed_sources"] == []
    assert len(pd.read_csv(panel.PROCESSED / "panel_county_year.csv")) == 372
    assert len(pd.read_csv(panel.PROCESSED / "panel_acquisition.csv")) == 13
    baseline = pd.read_csv(output_tables / "panel_coefficients.csv")
    assert len(baseline) == 10
    assert len(list(tmp_path.glob("*.png"))) == 5
    assert len(list(tmp_path.glob("*.svg"))) == 5
    assert result["tables"]["panel_coefficients"] == "outputs/tables/panel_coefficients.csv"
    for path in set(sources.values()):
        path.unlink()
    student_clone = tmp_path / "student_clone"
    student_processed = student_clone / "data" / "processed"
    shutil.copytree(panel.PROCESSED, student_processed)
    input_bytes = {path.name: path.read_bytes() for path in student_processed.iterdir()}
    monkeypatch.setattr(panel, "ROOT", student_clone)
    monkeypatch.setattr(panel, "PROCESSED", student_processed)
    output_tables = student_clone / "outputs" / "tables"
    def forbidden_fetch(*args):
        pytest.fail("Offline replay must not access raw files or network")
    monkeypatch.setattr(panel, "fetch", forbidden_fetch)
    monkeypatch.setenv("ECONHACK_OFFLINE", "1")
    replay = panel.run()
    assert replay["status"] == "complete"
    assert replay["input_mode"] == "processed_panel_offline_replay"
    assert replay["tables"] == result["tables"]
    assert statuses[-1][1]["models_estimated"] == 8
    assert statuses[-1][1]["processed_inputs"] == ["data/processed/panel_county_year.csv", "data/processed/panel_acquisition.csv"]
    assert all(not Path(path).is_absolute() for path in statuses[-1][1]["tables"].values())
    pd.testing.assert_frame_equal(baseline, pd.read_csv(output_tables / "panel_coefficients.csv"), rtol=1e-10, atol=1e-10)
    assert input_bytes == {path.name: path.read_bytes() for path in student_processed.iterdir()}


def _distributed_inputs(destination, partial=False):
    grid = pd.MultiIndex.from_product([panel.NY_COUNTIES, panel.YEARS], names=["county_fips", "year"]).to_frame(index=False)
    cbp = grid.assign(proxy_establishments=5., cbp_status="observed", cbp_estab_raw="5", cbp_estab_flag="",
                      cbp_source_url=grid.year.map(panel.cbp_url))
    bfs = grid.assign(county_name=grid.county_fips, business_applications=50., bfs_status="observed",
                      bfs_applications_raw="50", bfs_source_url=panel.BFS_URL)
    population = grid.assign(population_acs5=10000., population_status="observed", population_raw="10000",
                             population_moe90=20., population_source_url=grid.year.map(panel.acs_url))
    if partial:
        cbp.loc[1, ["proxy_establishments", "cbp_status", "cbp_estab_raw"]] = [np.nan, "suppressed", "D"]
        bfs.loc[0, ["business_applications", "bfs_status", "bfs_applications_raw"]] = [0., "observed_zero", "0"]
        population = population.drop(index=2)
    distributed = panel.build_panel(cbp, bfs, population)
    acquisition = []
    for source, year, url, raw_path, _ in panel._source_requests():
        frame = bfs if year is None else cbp.loc[cbp.year.eq(year)] if source.startswith("CBP") else population.loc[population.year.eq(year)]
        acquisition.append({"source": source, "year": year, "url": url, "raw_relative_path": raw_path,
                            "status": "loaded", "rows": len(frame), "reason": ""})
    distributed.to_csv(destination / "panel_county_year.csv", index=False)
    pd.DataFrame(acquisition).to_csv(destination / "panel_acquisition.csv", index=False)


def test_processed_replay_preserves_missing_suppressed_and_zero(monkeypatch, tmp_path):
    _distributed_inputs(tmp_path, partial=True)
    monkeypatch.setattr(panel, "PROCESSED", tmp_path)
    data, acquisition = panel._replay_panel()
    assert len(data) == 372
    assert len(acquisition) == 13
    assert data.loc[0, "business_applications"] == 0
    assert data.loc[1, "cbp_status"] == "suppressed"
    assert np.isnan(data.loc[1, panel.CURRENT])
    assert data.loc[2, "population_status"] == "missing_row"
    assert np.isnan(data.loc[2, panel.CURRENT])
    assert np.isnan(data.loc[2, panel.LAGGED])
    assert np.isnan(data.loc[3, panel.LAGGED])


@pytest.mark.parametrize("target,column,position,value,match", [
    ("panel_county_year", "year", 0, "2017", "all 62 NY counties"),
    ("panel_county_year", "year", 0, "2018.5", "all 62 NY counties"),
    ("panel_county_year", "county_fips", 0, "06001", "all 62 NY counties"),
    ("panel_county_year", panel.CURRENT, 0, "99", "rate identity"),
    ("panel_county_year", panel.OUTCOME, 0, "99", "rate identity"),
    ("panel_county_year", panel.LAGGED, 0, "5", "exact-year lag"),
    ("panel_county_year", panel.LAGGED, 1, "99", "exact-year lag"),
    ("panel_county_year", "lag_source_year", 1, "2017", "exact-year lag"),
    ("panel_county_year", "lag_source_year", 1, "2018.000001", "exact-year lag"),
    ("panel_county_year", "population_acs5", 0, "0", "counts disagree"),
    ("panel_county_year", "population_acs5", 0, "inf", "invalid numeric"),
    ("panel_county_year", "cbp_status", 0, "suppressed", "source status"),
    ("panel_county_year", "cbp_estab_raw", 0, "6", "counts disagree"),
    ("panel_county_year", "naics_vintage", 0, "2022", "metadata disagree"),
    ("panel_county_year", "acs_period_start", 0, "2018", "metadata disagree"),
    ("panel_county_year", "complete_current", 0, "False", "completeness flag"),
    ("panel_county_year", "cbp_source_url", 0, "https://example.com", "row source URLs"),
    ("panel_acquisition", "url", 0, "https://example.com", "source URL"),
    ("panel_acquisition", "raw_relative_path", 0, "/original/machine/bfs.xlsx", "source URL, path"),
    ("panel_acquisition", "rows", 0, "62", "row count"),
    ("panel_acquisition", "status", 0, "failed", "failure status"),
])
def test_processed_replay_rejects_inconsistent_inputs(monkeypatch, tmp_path, target, column, position, value, match):
    _distributed_inputs(tmp_path)
    path = tmp_path / f"{target}.csv"
    data = pd.read_csv(path, dtype=str, keep_default_na=False)
    data.loc[position, column] = value
    data.to_csv(path, index=False)
    monkeypatch.setattr(panel, "PROCESSED", tmp_path)
    with pytest.raises(ValueError, match=match):
        panel._replay_panel()


@pytest.mark.parametrize("target,change,match", [
    ("panel_county_year", "drop", "all 62 NY counties"),
    ("panel_county_year", "duplicate", "duplicate county-year"),
    ("panel_acquisition", "drop", "all 13 source/year"),
    ("panel_acquisition", "duplicate", "duplicate or unexpected source/year"),
])
def test_processed_replay_validates_exact_key_universes(monkeypatch, tmp_path, target, change, match):
    _distributed_inputs(tmp_path)
    path = tmp_path / f"{target}.csv"
    data = pd.read_csv(path, dtype=str, keep_default_na=False)
    data = data.iloc[1:] if change == "drop" else pd.concat([data, data.iloc[:1]], ignore_index=True)
    data.to_csv(path, index=False)
    monkeypatch.setattr(panel, "PROCESSED", tmp_path)
    with pytest.raises(ValueError, match=match):
        panel._replay_panel()


def test_offline_replay_missing_acquisition_fails_without_writing_results(monkeypatch, tmp_path):
    _distributed_inputs(tmp_path)
    (tmp_path / "panel_acquisition.csv").unlink()
    input_bytes = (tmp_path / "panel_county_year.csv").read_bytes()
    statuses = []
    monkeypatch.setattr(panel, "PROCESSED", tmp_path)
    monkeypatch.setenv("ECONHACK_OFFLINE", "1")
    monkeypatch.setattr(panel, "fetch", lambda *args: pytest.fail("Offline mode must not fetch"))
    monkeypatch.setattr(panel, "save_table", lambda *args: pytest.fail("Validation must precede output writes"))
    monkeypatch.setattr(panel, "record_status", lambda *args, **kwargs: statuses.append((args, kwargs)))
    with pytest.raises(FileNotFoundError):
        panel.run()
    assert statuses[0][0][1] == "blocked"
    assert statuses[0][1]["input_mode"] == "processed_panel_offline_replay"
    assert (tmp_path / "panel_county_year.csv").read_bytes() == input_bytes


def test_bulk_source_paths_and_years():
    assert len(panel.NY_COUNTIES) == 62
    assert panel.YEARS == (2018, 2019, 2020, 2021, 2022, 2023)
    assert "/2018/prototype/5YRData/" in panel.acs_url(2018)
    assert "/2022/table-based-SF/data/5YRData/" in panel.acs_url(2022)
    assert panel.BFS_URL.endswith("/xlsx/bfs_county_apps_annual.xlsx")


@pytest.mark.parametrize("model,term,label", [
    ("current_all_years", panel.CURRENT, "Current · full"),
    ("current_matched_all_years", panel.CURRENT, "Current · matched"),
    ("lag1_matched_all_years", panel.LAGGED, "Prior year · matched"),
    ("joint_matched_all_years", panel.CURRENT, "Joint current"),
    ("joint_matched_all_years", panel.LAGGED, "Joint lag"),
    ("joint_matched_exclude_2020_2021", panel.LAGGED, "Joint lag · pandemic excluded"),
])
def test_coefficient_chart_labels_are_readable(model, term, label):
    assert panel._coefficient_label(model, term) == label
