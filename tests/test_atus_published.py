"""Synthetic offline parser and fallback checks; no fixture is a research result."""

import copy
import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest

from econhack import atus_published as published


def response(start, end):
    return {"status": "REQUEST_SUCCEEDED", "message": [], "Results": {"series": [{
        "seriesID": published.SERIES_ID,
        "data": [{"year": str(year), "period": "A01", "value": f"{1.25 - .01 * (year - 2003):.2f}",
                  "footnotes": [{"text": "Synthetic test fixture"}]}
                 for year in reversed(range(start, end + 1)) if year != 2020],
    }]}}


@pytest.fixture
def annual():
    return published.combine_windows([published.parse_response(response(start, end), start, end)
                                      for start, end in published.WINDOWS])


def test_ten_year_windows_and_strict_series():
    assert "startyear=2003&endyear=2012" in published.api_url(2003, 2012)
    with pytest.raises(ValueError, match="ten years"):
        published.api_url(2003, 2013)
    frame = published.parse_response(response(2003, 2012), 2003, 2012)
    assert frame.year.tolist() == list(range(2003, 2013))
    assert frame.age_group.eq("15+").all()
    assert frame.footnotes.str.contains("Synthetic").all()
    np.testing.assert_allclose(frame.minutes_per_day, frame.hours_per_day * 60)


@pytest.mark.parametrize("fault", ["api_error", "wrong_series", "wrong_period", "duplicate", "missing", "nonfinite", "negative"])
def test_rejects_bad_or_truncated_api_responses(fault):
    payload = response(2003, 2012)
    series = payload["Results"]["series"][0]
    if fault == "api_error":
        payload["status"] = "REQUEST_NOT_PROCESSED"
    elif fault == "wrong_series":
        series["seriesID"] = "not-the-requested-series"
    elif fault == "wrong_period":
        series["data"][0]["period"] = "M01"
    elif fault == "duplicate":
        series["data"].append(copy.deepcopy(series["data"][0]))
    elif fault == "missing":
        series["data"].pop()
    else:
        series["data"][0]["value"] = "NaN" if fault == "nonfinite" else "-0.1"
    with pytest.raises(ValueError):
        published.parse_response(payload, 2003, 2012)


def test_missing_2020_is_preserved_and_descriptive_fit_has_no_inference(annual):
    assert len(annual) == 22
    assert annual.loc[annual.year.eq(2020), ["hours_per_day", "minutes_per_day"]].isna().all().all()
    assert not annual.loc[annual.year.eq(2020), "included_in_trend"].any()
    coefficients, fitted = published.fit_trends(annual)
    assert len(coefficients) == 2
    np.testing.assert_allclose(coefficients.estimate, [75, -0.6])
    assert coefficients.n_years.eq(21).all()
    assert not any(column.startswith("ci_") or column in {"p_value", "std_error"} for column in coefficients)
    assert not fitted.year.eq(2020).any()
    np.testing.assert_allclose(fitted.residual, 0, atol=1e-10)
    with pytest.raises(ValueError, match="coverage"):
        published.fit_trends(annual.loc[annual.year.ne(2008)])


def test_processed_replay_rejects_youth_relabeling_and_imputed_2020(annual, tmp_path):
    path = tmp_path / "annual.csv"
    annual.to_csv(path, index=False)
    assert len(published.read_processed(path)) == 22
    altered = annual.copy()
    altered.loc[0, "age_group"] = "15-24"
    altered.to_csv(path, index=False)
    with pytest.raises(ValueError, match="population"):
        published.read_processed(path)
    altered = annual.copy()
    altered.loc[altered.year.eq(2020), ["hours_per_day", "minutes_per_day"]] = 0
    altered.to_csv(path, index=False)
    with pytest.raises(ValueError, match="2020"):
        published.read_processed(path)


def test_plot_has_real_2020_gap_without_confidence_band(annual):
    figure = published.plot_trends(annual)
    try:
        axis = figure.axes[0]
        line = axis.lines[0]
        gap = list(line.get_xdata()).index(2020)
        assert np.isnan(line.get_ydata()[gap])
        assert not axis.collections
        assert "published aggregate" in axis.get_title()
    finally:
        plt.close(figure)


def test_definition_check_reconciles_official_table_endpoints(annual):
    for year, hours, reference in published.DEFINITION_ANCHORS:
        annual.loc[annual.year.eq(year), "hours_per_day"] = hours
    checks = published.verify_definition_anchors(annual)
    assert len(checks) == 2
    np.testing.assert_allclose(checks.api_hours_per_day, checks.official_table_hours_per_day)
    annual.loc[annual.year.eq(2024), "hours_per_day"] = 2
    with pytest.raises(ValueError, match="definition check failed"):
        published.verify_definition_anchors(annual)


def test_run_acquires_only_official_windows_then_replays_offline(monkeypatch, tmp_path):
    from econhack import common

    calls, tables, figures, statuses = [], {}, [], []
    paths = {}
    for start, end in published.WINDOWS:
        path = tmp_path / f"{start}_{end}.json"
        payload = response(start, end)
        for observation in payload["Results"]["series"][0]["data"]:
            for year, hours, reference in published.DEFINITION_ANCHORS:
                if int(observation["year"]) == year:
                    observation["value"] = str(hours)
        path.write_text(json.dumps(payload))
        paths[published.api_url(start, end)] = path

    def fake_fetch(url, relative_path, source, license_note):
        calls.append((url, relative_path))
        assert relative_path.startswith("atus_published/")
        return paths[url]

    def fake_figure(figure, name):
        figures.append(name)
        plt.close(figure)

    monkeypatch.delenv("ECONHACK_OFFLINE", raising=False)
    monkeypatch.setattr(common, "PROCESSED", tmp_path / "processed")
    monkeypatch.setattr(common, "fetch", fake_fetch)
    monkeypatch.setattr(common, "save_table", lambda frame, name: tables.update({name: frame.copy()}))
    monkeypatch.setattr(common, "save_figure", fake_figure)
    monkeypatch.setattr(common, "record_status", lambda *args, **kwargs: statuses.append((args, kwargs)))
    status = published.run()
    assert len(calls) == 3
    assert len(tables["atus_published_annual"]) == 22
    assert len(tables["atus_published_fitted"]) == 21
    assert status["youth_microdata_complete"] is False
    assert all(arguments[0] == "atus_published" for arguments, metadata in statuses)
    monkeypatch.setenv("ECONHACK_OFFLINE", "1")
    replay = published.run()
    assert len(calls) == 3
    assert replay["input_mode"] == "processed_aggregate_offline_replay"
    assert figures == ["atus_published_trend", "atus_published_trend"]
