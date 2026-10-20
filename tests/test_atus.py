"""Offline synthetic checks; fixtures are never used as research data."""

from zipfile import ZipFile

import numpy as np
import pandas as pd
import pytest

from econhack import atus


@pytest.fixture
def diaries():
    return pd.DataFrame({
        "TUCASEID": ["a", "b", "c", "d", "e"],
        "TUYEAR": [2019] * 5, "TEAGE": [15, 24, 25, 85, 20],
        "TUFNWGTP": [1.0, 3.0, 2.0, 4.0, 0.0],
        "TU20FWGT": [999.0] * 5, "T120101": [0, 60, 120, 30, 1440],
    })


@pytest.fixture
def annual():
    rows = []
    for year in atus.YEARS:
        for age_group, baseline in (("15-24", 70.0), ("15+", 40.0)):
            rows.append({
                "year": year, "age_group": age_group,
                "minutes_per_day": baseline - 0.5 * (year - 2003),
            })
    return pd.DataFrame(rows)


def test_weighted_means_include_zeros_and_age_boundaries(diaries):
    result = atus.annual_estimates(diaries).set_index("age_group")
    assert result.loc["15-24", "minutes_per_day"] == pytest.approx(45)
    assert result.loc["15+", "minutes_per_day"] == pytest.approx(54)
    assert result.loc["15-24", "hours_per_day"] == pytest.approx(0.75)
    assert result.loc["15-24", "n_respondents"] == 3
    assert result.loc["15-24", "n_positive_weight"] == 2
    assert result.loc["15-24", "n_zero_weight"] == 1
    assert result.loc["15+", "weight_sum"] == 10
    assert result["weight_variable"].eq("TUFNWGTP").all()


def test_2020_uses_only_pandemic_weight_and_is_partial_year(diaries):
    pandemic = diaries.iloc[:2].copy()
    pandemic["TUYEAR"] = 2020
    pandemic["TUCASEID"] = ["p", "q"]
    pandemic["TUFNWGTP"] = -1
    pandemic["TU20FWGT"] = [3, 1]
    result = atus.annual_estimates(pd.concat([diaries, pandemic], ignore_index=True))
    assert result.loc[result.year.eq(2020), "minutes_per_day"].tolist() == [15, 15]
    assert result.loc[result.year.eq(2019) & result.age_group.eq("15-24"), "minutes_per_day"].item() == 45
    partial = result.loc[result.year.eq(2020)]
    assert partial["weight_variable"].eq("TU20FWGT").all()
    assert not partial["is_full_year"].any()
    assert not partial["included_in_trend"].any()


@pytest.mark.parametrize("value", [-1, np.nan, np.inf, "invalid"])
def test_rejects_invalid_applicable_weight(diaries, value):
    diaries["TUFNWGTP"] = diaries["TUFNWGTP"].astype(object)
    diaries.loc[0, "TUFNWGTP"] = value
    with pytest.raises(ValueError, match="applicable ATUS weight"):
        atus.annual_estimates(diaries)


def test_rejects_no_positive_weight(diaries):
    diaries["TUFNWGTP"] = 0
    with pytest.raises(ValueError, match="positive total weight"):
        atus.annual_estimates(diaries)


@pytest.mark.parametrize("column,value", [("TEAGE", 14), ("TEAGE", 24.5),
                                         ("TUYEAR", 2025), ("T120101", -1),
                                         ("T120101", 1441), ("T120101", np.nan)])
def test_rejects_invalid_measurements(diaries, column, value):
    diaries[column] = diaries[column].astype(object)
    diaries.loc[0, column] = value
    with pytest.raises(ValueError, match=f"Invalid {column}"):
        atus.annual_estimates(diaries)


def test_rejects_duplicate_respondents(diaries):
    with pytest.raises(ValueError, match="unique"):
        atus.annual_estimates(pd.concat([diaries, diaries.iloc[:1]], ignore_index=True))


def test_rejects_missing_age_cohort(diaries):
    with pytest.raises(ValueError, match="No respondents"):
        atus.annual_estimates(diaries.loc[diaries.TEAGE.ge(25)])


def test_archive_lowercase_time_field_and_leading_zero_id(tmp_path, diaries):
    diaries["TUCASEID"] = ["0001", "0002", "0003", "0004", "0005"]
    diaries = diaries.rename(columns={"T120101": "t120101"})
    diaries["unneeded_activity"] = 888
    path = tmp_path / "summary.zip"
    with ZipFile(path, "w") as archive:
        archive.writestr("atussum_0324.dat", diaries.to_csv(index=False))
        archive.writestr("atussum_0324.sas", "not a data file")
    result = atus.read_summary(path)
    assert result.TUCASEID.iloc[0] == "0001"
    assert atus.ACTIVITY in result.columns
    assert "unneeded_activity" not in result.columns


def test_archive_rejects_ambiguous_data_members(tmp_path):
    path = tmp_path / "summary.zip"
    with ZipFile(path, "w") as archive:
        archive.writestr("atussum_a.dat", "unused")
        archive.writestr("atussum_b.csv", "unused")
    with pytest.raises(ValueError, match="exactly one"):
        atus.read_summary(path)


def test_missing_schema_fails(diaries):
    with pytest.raises(ValueError, match="TU20FWGT"):
        atus.annual_estimates(diaries.drop(columns="TU20FWGT"))


def test_estimates_are_invariant_to_weight_scale_and_row_order(diaries):
    expected = atus.annual_estimates(diaries)
    changed = diaries.sample(frac=1, random_state=7).copy()
    changed["TUFNWGTP"] *= 1e8
    actual = atus.annual_estimates(changed)
    np.testing.assert_allclose(actual.minutes_per_day, expected.minutes_per_day)
    assert not any("ci" in column or "std_error" in column for column in actual.columns)


def test_full_table_slopes_and_no_2020_in_any_fit(annual):
    annual.loc[annual.year.eq(2020), "minutes_per_day"] = 10000
    coefficients, fitted = atus.fit_trends(annual)
    assert len(coefficients) == 8
    slope = coefficients.loc[coefficients.term.eq("year_since_2003")]
    np.testing.assert_allclose(slope.estimate, -0.5)
    intercept = coefficients.loc[coefficients.term.eq("intercept")]
    np.testing.assert_allclose(intercept.estimate, [70, 70, 40, 40])
    assert not fitted.year.eq(2020).any()
    assert coefficients.groupby("model").n_years.first().to_dict() == {
        "2003-2019_temporal_HAC": 17,
        "2003-2024_excluding_2020_descriptive": 21,
    }
    inferential = ["std_error", "t_statistic", "p_value", "ci_95_low", "ci_95_high"]
    descriptive = coefficients.loc[coefficients.model.str.endswith("descriptive")]
    assert descriptive[inferential].isna().all().all()
    np.testing.assert_allclose(fitted.residual, 0, atol=1e-10)


def test_hac_is_pre_pandemic_only_and_has_full_metadata(annual):
    annual["minutes_per_day"] += np.sin(annual.year.to_numpy())
    coefficients, fitted = atus.fit_trends(annual)
    robust = coefficients.loc[coefficients.model.eq("2003-2019_temporal_HAC")]
    assert robust.n_years.eq(17).all()
    assert robust.df_resid.eq(15).all()
    assert robust.hac_maxlags.eq(2).all()
    assert robust.std_error.gt(0).all()
    assert robust.p_value.between(0, 1).all()
    assert robust.ci_95_low.lt(robust.estimate).all()
    assert robust.ci_95_high.gt(robust.estimate).all()
    assert robust.covariance.str.contains("Bartlett").all()
    changed = annual.copy()
    changed.loc[changed.year.ge(2020), "minutes_per_day"] += 100
    changed_coefficients, _ = atus.fit_trends(changed)
    pd.testing.assert_frame_equal(
        robust.reset_index(drop=True),
        changed_coefficients.loc[changed_coefficients.model.eq("2003-2019_temporal_HAC")].reset_index(drop=True),
    )
    assert fitted.loc[fitted.model.eq("2003-2019_temporal_HAC"), "year"].max() == 2019


def test_regression_rejects_calendar_gaps_and_duplicates(annual):
    with pytest.raises(ValueError, match="Incomplete calendar-year coverage"):
        atus.fit_trends(annual.loc[annual.year.ne(2010)])
    with pytest.raises(ValueError, match="Duplicate"):
        atus.fit_trends(pd.concat([annual, annual.iloc[:1]]))


def test_plot_breaks_lines_at_2020_and_labels_partial_year(annual):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    figure = atus.plot_trends(annual)
    try:
        axis = figure.axes[0]
        for line in axis.lines:
            gap = np.flatnonzero(np.asarray(line.get_xdata()) == 2020).item()
            assert np.isnan(np.asarray(line.get_ydata())[gap])
        assert len(axis.collections) == 2
        assert "partial-year" in " ".join(text.get_text() for text in figure.texts)
        assert axis.get_ylim()[0] == 0
    finally:
        plt.close(figure)


def test_run_uses_common_fetch_and_writes_expected_outputs(monkeypatch, tmp_path):
    from econhack import common

    rows = []
    for year in atus.YEARS:
        for age in (15, 24, 25):
            rows.append({
                "TUCASEID": f"{year}{age}", "TUYEAR": year, "TEAGE": age,
                "TUFNWGTP": -1 if year == 2020 else 1,
                "TU20FWGT": 1 if year == 2020 else -1, "T120101": 50 - (year - 2003) + (age == 25),
            })
    path = tmp_path / "atussum.zip"
    with ZipFile(path, "w") as archive:
        archive.writestr("atussum_0324.dat", pd.DataFrame(rows).to_csv(index=False))
    fetch_calls, tables, figures, statuses = [], {}, [], []

    def fake_fetch(url, relative_path, source, license_note):
        fetch_calls.append((url, relative_path, source, license_note))
        return path

    monkeypatch.setattr(common, "fetch", fake_fetch)
    monkeypatch.setattr(common, "PROCESSED", tmp_path / "processed")
    monkeypatch.delenv("ECONHACK_OFFLINE", raising=False)
    monkeypatch.setattr(common, "save_table", lambda frame, name: tables.update({name: frame.copy()}))
    monkeypatch.setattr(common, "save_figure", lambda figure, name: figures.append(name))
    monkeypatch.setattr(common, "record_status", lambda *args, **kwargs: statuses.append((args, kwargs)))
    status = atus.run()
    assert fetch_calls == [(atus.DATA_URL, atus.RAW_PATH,
                            "BLS ATUS 2003-2024 activity summary", atus.LICENSE_NOTE)]
    assert set(tables) == {"atus_socializing_annual", "atus_socializing_regression", "atus_socializing_fitted"}
    assert len(tables["atus_socializing_annual"]) == 44
    assert figures == ["atus_socializing_trend"]
    assert status["respondents"] == 66
    assert statuses[0][0][:2] == ("atus", "completed")
    processed_path = common.PROCESSED / "atus_socializing_annual.csv"
    assert len(atus.read_processed(processed_path)) == 44
    monkeypatch.setenv("ECONHACK_OFFLINE", "1")
    replay_status = atus.run()
    assert len(fetch_calls) == 1
    assert replay_status["input_mode"] == "processed_aggregate_offline_replay"
    corrupt = pd.read_csv(processed_path)
    corrupt.loc[corrupt.year.eq(2020), "included_in_trend"] = True
    corrupt.to_csv(processed_path, index=False)
    with pytest.raises(ValueError, match="Invalid values or provenance"):
        atus.read_processed(processed_path)
