"""Official published all-15+ ATUS fallback, separate from T120101 microdata."""

import json
import os
from pathlib import Path
from urllib.parse import urlencode

import numpy as np
import pandas as pd


SERIES_ID = "TUU10101AA01013951"
SERIES_PAGE = f"https://data.bls.gov/timeseries/{SERIES_ID}"
SERIES_DICTIONARY = "https://download.bls.gov/pub/time.series/TU/tu.series"
API_BASE = f"https://api.bls.gov/publicAPI/v2/timeseries/data/{SERIES_ID}"
WINDOWS = ((2003, 2012), (2013, 2022), (2023, 2024))
YEARS = tuple(range(2003, 2025))
LABEL = "Socializing and communicating (BLS published aggregate)"
POPULATION = "U.S. civilian noninstitutional population age 15 and over; all persons; all days"
LICENSE_NOTE = "US federal government public data; cite BLS American Time Use Survey."
MODEL = "2003-2024_excluding_2020_descriptive"
DEFINITION_ANCHORS = (
    (2003, 0.78, "https://www.bls.gov/news.release/archives/atus_09142004.pdf"),
    (2024, 0.59, "https://www.bls.gov/news.release/archives/atus_06262025.htm"),
)


def api_url(start, end):
    """Stay within the unregistered API's ten-year request window."""
    if start < 2003 or end < start or end - start >= 10:
        raise ValueError("ATUS API windows must span at most ten years, beginning in 2003 or later")
    return API_BASE + "?" + urlencode({"startyear": start, "endyear": end})


def parse_response(payload, start, end):
    """Reject API error envelopes, wrong series, periods, duplicates, and truncation."""
    if payload.get("status") != "REQUEST_SUCCEEDED":
        raise ValueError(f"BLS API did not succeed: {payload.get('message', payload.get('status'))}")
    series = payload.get("Results", {}).get("series", [])
    if len(series) != 1 or series[0].get("seriesID") != SERIES_ID:
        raise ValueError("BLS API response does not contain exactly the requested ATUS series")
    rows = []
    for observation in series[0].get("data", []):
        if observation.get("period") != "A01":
            raise ValueError("Expected annual ATUS period A01, not a monthly/quarterly series")
        year = int(observation["year"])
        if not start <= year <= end:
            raise ValueError("BLS API returned a year outside the requested window")
        raw = str(observation.get("value", "")).strip()
        if year == 2020 and raw in {"", "-", "--", "N/A"}:
            continue
        try:
            hours = float(raw)
        except ValueError as error:
            raise ValueError(f"Invalid published ATUS hours for {year}: {raw}") from error
        if year == 2020 or not np.isfinite(hours) or not 0 <= hours <= 24:
            raise ValueError(f"Invalid annual ATUS estimate for {year}")
        notes = observation.get("footnotes", [])
        rows.append({
            "year": year, "age_group": "15+", "hours_per_day": hours,
            "minutes_per_day": hours * 60, "published_value": raw,
            "period": "A01", "series_id": SERIES_ID, "activity_label": LABEL,
            "population": POPULATION, "is_full_year": True, "included_in_trend": True,
            "data_status": "published", "source_url": api_url(start, end),
            "footnotes": " | ".join(str(note["text"]) for note in notes if note.get("text")),
        })
    frame = pd.DataFrame(rows)
    expected = {year for year in range(start, end + 1) if year != 2020}
    if frame.empty or frame.year.duplicated().any() or set(frame.year) != expected:
        found = sorted(frame.year.tolist()) if not frame.empty else []
        raise ValueError(f"Incomplete/duplicate ATUS API years: expected {sorted(expected)}, found {found}")
    return frame.sort_values("year").reset_index(drop=True)


def combine_windows(frames):
    annual = pd.concat(frames, ignore_index=True)
    if annual.year.duplicated().any() or set(annual.year) != set(YEARS) - {2020}:
        raise ValueError("Published fallback requires all 2003-2024 annual estimates except 2020")
    missing = {column: np.nan for column in annual.columns}
    missing.update({
        "year": 2020, "age_group": "15+", "period": "A01", "series_id": SERIES_ID,
        "activity_label": LABEL, "population": POPULATION, "published_value": "",
        "is_full_year": False, "included_in_trend": False,
        "data_status": "not_published_pandemic_gap", "source_url": SERIES_PAGE,
        "footnotes": "No annual estimate; ATUS collection was suspended March 18-May 9, 2020.",
    })
    return pd.concat([annual, pd.DataFrame([missing])], ignore_index=True).sort_values("year").reset_index(drop=True)


def read_processed(path: Path):
    """Validate distributed annual results before an entirely offline replay."""
    annual = pd.read_csv(path, dtype={"age_group": str, "series_id": str})
    required = {"year", "age_group", "hours_per_day", "minutes_per_day", "series_id",
                "activity_label", "population", "is_full_year", "included_in_trend", "data_status"}
    if not required.issubset(annual.columns) or len(annual) != len(YEARS):
        raise ValueError("Invalid processed published-ATUS schema/coverage")
    if annual.year.duplicated().any() or set(annual.year) != set(YEARS):
        raise ValueError("Invalid processed published-ATUS year coverage")
    available = annual.year.ne(2020)
    valid = (
        annual.age_group.eq("15+") & annual.series_id.eq(SERIES_ID)
        & annual.activity_label.eq(LABEL) & annual.population.eq(POPULATION)
        & annual.is_full_year.eq(available) & annual.included_in_trend.eq(available)
    )
    if not valid.all() or not annual.loc[available, "hours_per_day"].between(0, 24).all():
        raise ValueError("Invalid population, definition, flags, or values in published ATUS aggregate")
    if not np.isclose(annual.loc[available, "hours_per_day"] * 60,
                      annual.loc[available, "minutes_per_day"]).all():
        raise ValueError("Published ATUS minute/hour units disagree")
    if not annual.loc[~available, ["hours_per_day", "minutes_per_day"]].isna().all().all():
        raise ValueError("2020 must remain missing, not imputed or treated as a full-year observation")
    return annual.sort_values("year").reset_index(drop=True)


def fit_trends(annual):
    """Describe rounded published levels with OLS; deliberately report no inference."""
    sample = annual.loc[annual.year.ne(2020)].sort_values("year")
    if sample.year.tolist() != [year for year in YEARS if year != 2020]:
        raise ValueError("Descriptive trend requires complete non-2020 calendar-year coverage")
    values = sample.minutes_per_day.to_numpy(dtype=float)
    if not np.isfinite(values).all():
        raise ValueError("Nonfinite published annual minutes")
    design = np.column_stack([np.ones(len(sample)), sample.year.to_numpy() - 2003])
    parameters = np.linalg.lstsq(design, values, rcond=None)[0]
    prediction = design @ parameters
    residual = values - prediction
    total_variation = np.square(values - values.mean()).sum()
    explained = 1 - np.square(residual).sum() / total_variation if total_variation > 0 else np.nan
    coefficients = pd.DataFrame([{
        "model": MODEL, "age_group": "15+", "term": term, "estimate": float(parameters[position]),
        "units": "minutes/day" if position == 0 else "minutes/day per calendar year",
        "n_years": len(sample), "df_resid": len(sample) - 2, "r_squared": explained,
        "rmse_minutes_per_day": float(np.sqrt(np.mean(np.square(residual)))),
        "start_year": 2003, "end_year": 2024, "excluded_years": "2020",
        "inference_scope": "Descriptive only; no standard errors, p-values, or confidence intervals",
        "series_id": SERIES_ID, "activity_label": LABEL,
    } for position, term in enumerate(("intercept", "year_since_2003"))])
    fitted = pd.DataFrame({
        "year": sample.year.to_numpy(), "age_group": "15+", "model": MODEL,
        "observed_minutes_per_day": values, "fitted_minutes_per_day": prediction, "residual": residual,
    })
    return coefficients, fitted


def verify_definition_anchors(annual):
    """Reconcile API endpoints against independently inspected official Table 1 values."""
    rows = []
    for year, official_hours, reference in DEFINITION_ANCHORS:
        values = annual.loc[annual.year.eq(year), "hours_per_day"]
        if len(values) != 1 or not np.isclose(values.iloc[0], official_hours, rtol=0, atol=1e-9):
            raise ValueError(f"BLS series/table definition check failed for {year}; reconcile source vintage before using the fallback")
        rows.append({"year": year, "series_id": SERIES_ID, "api_hours_per_day": float(values.iloc[0]),
                     "official_table_hours_per_day": official_hours, "table_category": "Socializing and communicating",
                     "table_population": "Total population, age 15 and over", "official_reference": reference})
    return pd.DataFrame(rows)


def plot_trends(annual):
    import matplotlib.pyplot as plt

    series = annual.set_index("year").reindex(YEARS)
    minutes = series.minutes_per_day.copy()
    minutes.loc[2020] = np.nan
    figure, axis = plt.subplots(figsize=(10, 5.8))
    axis.plot(YEARS, minutes, marker="o", color="#176b87", label="All persons ages 15+")
    axis.axvspan(2019.65, 2020.35, color="#777777", alpha=0.12)
    axis.text(2020, 0.97, "2020: no annual estimate", transform=axis.get_xaxis_transform(),
              ha="center", va="top", fontsize=9)
    axis.set(title="Socializing and communicating: BLS published aggregate",
             xlabel="Diary year", ylabel="Published average minutes per person per day", ylim=(0, None))
    axis.set_xticks([2003, 2006, 2009, 2012, 2015, 2018, 2020, 2022, 2024])
    axis.grid(axis="y", alpha=0.2)
    axis.legend(frameon=False, loc="lower left")
    figure.text(0.1, 0.035,
                f"Source: BLS ATUS {SERIES_ID}; published rounded hours × 60. No survey confidence intervals.\n"
                "Includes zero-time diaries. Broader published category; not detailed T120101 or all face-to-face time.\n"
                "Fallback covers all ages 15+ only; the requested ages 15–24 microdata series remains unavailable.", fontsize=9)
    figure.tight_layout(rect=(0, 0.14, 1, 1))
    return figure


def run():
    """Acquire official API JSON only; never overwrite the microdata model's status."""
    from .common import PROCESSED, fetch, record_status, save_figure, save_table

    processed_path = PROCESSED / "atus_published_annual.csv"
    replay = os.environ.get("ECONHACK_OFFLINE") == "1" and processed_path.exists()
    if replay:
        annual = read_processed(processed_path)
    else:
        frames = []
        for start, end in WINDOWS:
            path = fetch(api_url(start, end), f"atus_published/{SERIES_ID}_{start}_{end}.json",
                         "BLS ATUS official published socializing/communicating series, all persons 15+", LICENSE_NOTE)
            frames.append(parse_response(json.loads(path.read_text()), start, end))
        annual = combine_windows(frames)
        PROCESSED.mkdir(parents=True, exist_ok=True)
    definition_check = verify_definition_anchors(annual)
    if not replay:
        annual.to_csv(processed_path, index=False, float_format="%.12g")
    coefficients, fitted = fit_trends(annual)
    save_table(annual, "atus_published_annual")
    save_table(coefficients, "atus_published_regression")
    save_table(fitted, "atus_published_fitted")
    save_table(definition_check, "atus_published_definition_check")
    save_figure(plot_trends(annual), "atus_published_trend")
    reason = ("Official published all-15+ socializing/communicating series only, 2003-2024; "
              "no 2020 annual estimate. This does not complete the ages 15-24/T120101 microdata analysis.")
    metadata = {
        "series_id": SERIES_ID, "series_page": SERIES_PAGE, "series_dictionary": SERIES_DICTIONARY,
        "activity_label": LABEL, "population": POPULATION, "age_groups": ["15+"],
        "years": [2003, 2024], "observed_years": 21, "missing_years": [2020],
        "input_mode": "processed_aggregate_offline_replay" if replay else "verified_official_api_json",
        "youth_microdata_complete": False,
        "definition_verification": "API endpoints reconciled to independently inspected 2003 and 2024 official BLS Table 1 total-population values; no API catalog title is assumed.",
        "caveats": ["Published aggregate is not equivalent to detailed T120101 or total face-to-face interaction.",
                    "Published hours are rounded; minutes are a unit conversion, not additional precision.",
                    "No annual survey confidence intervals or regression inference are supplied.",
                    "All-15+ results cannot establish the trend for ages 15-24."],
    }
    record_status("atus_published", "complete_published_only", reason, **metadata)
    return {"status": "complete_published_only", "reason": reason, **metadata}


if __name__ == "__main__":
    run()
