"""Weighted ATUS socializing/communicating time; see docs/models/atus.md."""

import os
from pathlib import Path
from typing import cast
from zipfile import ZipFile

import numpy as np
import pandas as pd

SOURCE_PAGE = "https://www.bls.gov/tus/data/datafiles-0324.htm"
DATA_URL = "https://www.bls.gov/tus/datafiles/atussum-0324.zip"
RAW_PATH = "atus/atussum-0324.zip"
LICENSE_NOTE = (
    "BLS public-use federal government data; cite BLS American Time Use Survey."
)
ACTIVITY = "T120101"
YEARS = tuple(range(2003, 2025))
AGE_GROUPS = ("15-24", "15+")
COLUMNS = ("TUCASEID", "TUYEAR", "TEAGE", "TUFNWGTP", "TU20FWGT", ACTIVITY)
INFERENCE_NOTE = (
    "No survey-design standard errors or annual confidence intervals: replicate weights "
    "are not loaded. Temporal HAC uncertainty is not survey-design uncertainty or causal evidence."
)


def read_summary(path: Path) -> pd.DataFrame:
    """Read only needed columns, without extracting the BLS ZIP archive."""
    with ZipFile(path) as archive:
        members = [
            name
            for name in archive.namelist()
            if Path(name).name.lower().startswith("atussum")
            and Path(name).suffix.lower() in {".dat", ".csv"}
            and not name.startswith("__MACOSX/")
        ]
        if len(members) != 1:
            raise ValueError(
                "Expected exactly one ATUS activity summary CSV/.dat member"
            )
        with archive.open(members[0]) as stream:
            frame = pd.read_csv(
                stream,
                usecols=lambda name: (
                    isinstance(name, str) and name.strip().upper() in COLUMNS
                ),
                dtype=str,
            )
    return validate_summary(frame)


def validate_summary(frame: pd.DataFrame) -> pd.DataFrame:
    """Fail on schema drift, duplicate diaries, invalid time, or unusable weights."""
    frame = frame.rename(
        columns=lambda name: name.strip().upper() if isinstance(name, str) else name
    ).copy()
    if frame.columns.duplicated().any():
        raise ValueError("Duplicate ATUS column names")
    missing = set(COLUMNS) - set(frame.columns)
    if missing:
        raise ValueError(f"Missing ATUS columns: {sorted(missing)}")
    frame = frame.loc[:, list(COLUMNS)].copy()
    identifiers = frame["TUCASEID"].astype("string").str.strip()
    if (
        identifiers.isna().any()
        or identifiers.eq("").any()
        or identifiers.duplicated().any()
    ):
        raise ValueError(
            "TUCASEID must be present and unique: one diary per respondent"
        )
    frame["TUCASEID"] = identifiers
    for column in COLUMNS[1:]:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    for column, lower, upper in (
        ("TUYEAR", 2003, 2024),
        ("TEAGE", 15, 85),
        (ACTIVITY, 0, 1440),
    ):
        values = frame[column]
        if not (
            np.isfinite(values)
            & values.between(lower, upper)
            & values.eq(values.round())
        ).all():
            raise ValueError(
                f"Invalid {column}: expected integers between {lower} and {upper}"
            )
        frame[column] = values.astype(int)
    frame["weight"] = frame["TUFNWGTP"].where(
        frame["TUYEAR"].ne(2020), frame["TU20FWGT"]
    )
    if not (np.isfinite(frame["weight"]) & frame["weight"].ge(0)).all():
        raise ValueError("Missing, negative, or nonfinite applicable ATUS weight")
    if frame.empty:
        raise ValueError("Empty ATUS activity summary")
    return frame


def annual_estimates(frame: pd.DataFrame) -> pd.DataFrame:
    """Ratio estimates include zero-time diaries and select weights by diary year."""
    frame = validate_summary(frame)
    rows = []
    for year, yearly in frame.groupby("TUYEAR", sort=True):
        year = cast(int, year)  # validate_summary normalizes TUYEAR to integers.
        for age_group in AGE_GROUPS:
            sample = (
                yearly.loc[yearly["TEAGE"].between(15, 24)]
                if age_group == "15-24"
                else yearly
            )
            if sample.empty:
                raise ValueError(f"No respondents for {year}, ages {age_group}")
            positive = sample.loc[sample["weight"].gt(0)]
            weight_sum = float(positive["weight"].sum())
            if not np.isfinite(weight_sum) or weight_sum <= 0:
                raise ValueError(
                    f"No positive total weight for {year}, ages {age_group}"
                )
            minutes = float(np.average(positive[ACTIVITY], weights=positive["weight"]))
            rows.append(
                {
                    "year": int(year),
                    "age_group": age_group,
                    "minutes_per_day": minutes,
                    "hours_per_day": minutes / 60,
                    "n_respondents": len(sample),
                    "n_positive_weight": len(positive),
                    "n_zero_weight": len(sample) - len(positive),
                    "weight_sum": weight_sum,
                    "weight_variable": "TU20FWGT" if year == 2020 else "TUFNWGTP",
                    "is_full_year": year != 2020,
                    "included_in_trend": year != 2020,
                    "coverage": "Jan 1-Mar 17; May 10-Dec 31"
                    if year == 2020
                    else "Full calendar year",
                    "activity_code": ACTIVITY,
                    "source_url": DATA_URL,
                }
            )
    return pd.DataFrame(rows)


def fit_trends(annual: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Full-period descriptive OLS and contiguous pre-pandemic temporal HAC fits."""
    import statsmodels.api as sm

    if annual.duplicated(["year", "age_group"]).any():
        raise ValueError("Duplicate year/age_group annual estimates")
    coefficients = []
    fitted_rows = []
    for age_group in AGE_GROUPS:
        group = annual.loc[annual["age_group"].eq(age_group)].sort_values("year")
        for model, stop, use_hac in (
            ("2003-2024_excluding_2020_descriptive", 2024, False),
            ("2003-2019_temporal_HAC", 2019, True),
        ):
            sample = group.loc[
                group["year"].between(2003, stop) & group["year"].ne(2020)
            ]
            expected = [year for year in range(2003, stop + 1) if year != 2020]
            if sample["year"].tolist() != expected:
                raise ValueError(
                    f"Incomplete calendar-year coverage for {age_group}, {model}"
                )
            if not np.isfinite(sample["minutes_per_day"]).all():
                raise ValueError("Nonfinite annual time estimate")
            design = pd.DataFrame(
                {
                    "intercept": np.ones(len(sample)),
                    "year_since_2003": sample["year"].to_numpy() - 2003,
                },
                index=sample.index,
            )
            result = sm.OLS(sample["minutes_per_day"], design).fit()
            robust = (
                result.get_robustcov_results(
                    cov_type="HAC",
                    maxlags=2,
                    kernel="bartlett",
                    use_correction=True,
                    use_t=True,
                )
                if use_hac
                else None
            )
            interval = robust.conf_int(alpha=0.05) if robust is not None else None
            for position, term in enumerate(design.columns):
                coefficients.append(
                    {
                        "age_group": age_group,
                        "model": model,
                        "term": term,
                        "estimate": float(result.params.iloc[position]),
                        "std_error": float(robust.bse[position])
                        if robust is not None
                        else np.nan,
                        "t_statistic": float(robust.tvalues[position])
                        if robust is not None
                        else np.nan,
                        "p_value": float(robust.pvalues[position])
                        if robust is not None
                        else np.nan,
                        "ci_95_low": float(interval[position, 0])
                        if interval is not None
                        else np.nan,
                        "ci_95_high": float(interval[position, 1])
                        if interval is not None
                        else np.nan,
                        "n_years": int(result.nobs),
                        "df_resid": int(result.df_resid),
                        "r_squared": float(result.rsquared),
                        "start_year": 2003,
                        "end_year": stop,
                        "excluded_years": "2020",
                        "hac_maxlags": 2 if use_hac else np.nan,
                        "covariance": "HAC Bartlett; small-sample correction; t reference"
                        if use_hac
                        else "Not reported",
                        "inference_scope": "Exploratory temporal model only"
                        if use_hac
                        else "Descriptive coefficients; no inference",
                        "units": "minutes/day"
                        if term == "intercept"
                        else "minutes/day per calendar year",
                        "note": INFERENCE_NOTE,
                    }
                )
            for year, observed, predicted, residual in zip(
                sample["year"],
                sample["minutes_per_day"],
                result.fittedvalues,
                result.resid,
            ):
                fitted_rows.append(
                    {
                        "year": int(year),
                        "age_group": age_group,
                        "model": model,
                        "observed_minutes_per_day": float(observed),
                        "fitted_minutes_per_day": float(predicted),
                        "residual": float(residual),
                    }
                )
    return pd.DataFrame(coefficients), pd.DataFrame(fitted_rows)


def read_processed(path: Path) -> pd.DataFrame:
    """Validate the saved aggregate before replaying it without the bulky ZIP."""
    annual = pd.read_csv(path, dtype={"age_group": str})
    required = {
        "year",
        "age_group",
        "minutes_per_day",
        "hours_per_day",
        "n_respondents",
        "n_positive_weight",
        "n_zero_weight",
        "weight_sum",
        "weight_variable",
        "is_full_year",
        "included_in_trend",
        "coverage",
        "activity_code",
        "source_url",
    }
    if not required.issubset(annual.columns):
        raise ValueError("Processed ATUS aggregate is missing required columns")
    keys = set(zip(annual["year"], annual["age_group"]))
    if len(annual) != 44 or keys != {
        (year, group) for year in YEARS for group in AGE_GROUPS
    }:
        raise ValueError(
            "Processed ATUS aggregate must contain 44 distinct year/cohort rows"
        )
    full_year = annual["year"].ne(2020)
    valid = (
        annual["minutes_per_day"].between(0, 1440)
        & np.isclose(annual["hours_per_day"] * 60, annual["minutes_per_day"])
        & annual["weight_sum"].gt(0)
        & np.isfinite(annual["weight_sum"])
        & annual["is_full_year"].eq(full_year)
        & annual["included_in_trend"].eq(full_year)
        & annual["weight_variable"].eq(
            pd.Series(
                np.where(full_year, "TUFNWGTP", "TU20FWGT"),
                index=annual.index,
            )
        )
        & annual["activity_code"].eq(ACTIVITY)
        & annual["source_url"].eq(DATA_URL)
        & annual["n_positive_weight"].gt(0)
        & annual["n_zero_weight"].ge(0)
        & annual["n_respondents"].eq(
            annual["n_positive_weight"] + annual["n_zero_weight"]
        )
    )
    for column in ("n_respondents", "n_positive_weight", "n_zero_weight"):
        valid &= np.isfinite(annual[column]) & annual[column].eq(annual[column].round())
    if not valid.all():
        raise ValueError("Invalid values or provenance in processed ATUS aggregate")
    return annual


def plot_trends(annual: pd.DataFrame):
    """Show the 2020 coverage interruption without joining full-year estimates across it."""
    import matplotlib.pyplot as plt

    figure, axis = plt.subplots(figsize=(10, 5.8))
    colors = {"15-24": "#176B87", "15+": "#B85C38"}
    for age_group in AGE_GROUPS:
        group = (
            annual.loc[annual["age_group"].eq(age_group)]
            .set_index("year")
            .reindex(YEARS)
        )
        full_year = group["minutes_per_day"].copy()
        full_year.loc[full_year.index == 2020] = np.nan
        axis.plot(
            YEARS,
            full_year,
            marker="o",
            markersize=3.5,
            color=colors[age_group],
            label=f"Ages {age_group}",
        )
        partial = (
            group.loc[group.index == 2020, "minutes_per_day"]
            .dropna()
            .to_numpy(dtype=float)
        )
        if partial.size:
            axis.scatter(
                [2020],
                partial,
                marker="D",
                facecolors="none",
                edgecolors=colors[age_group],
                s=48,
                zorder=4,
            )
    axis.axvspan(2019.65, 2020.35, color="#747474", alpha=0.12)
    axis.set(
        title="Time spent socializing and communicating with others",
        xlabel="Diary year",
        ylabel="Weighted minutes per person per day",
        ylim=(0, None),
    )
    axis.set_xticks([2003, 2006, 2009, 2012, 2015, 2018, 2020, 2022, 2024])
    axis.grid(axis="y", alpha=0.2)
    axis.legend(frameon=False)
    figure.text(
        0.11,
        0.035,
        "Source: BLS ATUS, T120101; includes zero-time diaries. No survey confidence intervals.\n"
        "Hollow diamonds: 2020 partial-year estimates; excluded from all trend fits.\n"
        "This activity category does not measure all face-to-face interaction.",
        fontsize=9,
    )
    figure.tight_layout(rect=(0, 0.14, 1, 1))
    return figure


def run():
    """Fetch the official archive and write reproducible tables, figures, and status."""
    from .common import PROCESSED, fetch, record_status, save_figure, save_table

    processed_path = PROCESSED / "atus_socializing_annual.csv"
    replay = os.environ.get("ECONHACK_OFFLINE") == "1" and processed_path.exists()
    if replay:
        annual = read_processed(processed_path)
    else:
        path = fetch(
            DATA_URL,
            RAW_PATH,
            source="BLS ATUS 2003-2024 activity summary",
            license_note=LICENSE_NOTE,
        )
        summary = read_summary(path)
        observed_years = set(summary["TUYEAR"])
        if observed_years != set(YEARS):
            raise ValueError(
                f"Expected ATUS 2003-2024 coverage; found {sorted(observed_years)}"
            )
        annual = annual_estimates(summary)
        PROCESSED.mkdir(parents=True, exist_ok=True)
        annual.to_csv(processed_path, index=False, float_format="%.12g")
    coefficients, fitted = fit_trends(annual)
    save_table(annual, "atus_socializing_annual")
    save_table(coefficients, "atus_socializing_regression")
    save_table(fitted, "atus_socializing_fitted")
    figure = plot_trends(annual)
    try:
        save_figure(figure, "atus_socializing_trend")
    finally:
        import matplotlib.pyplot as plt

        plt.close(figure)
    status = {
        "source": SOURCE_PAGE,
        "data_url": DATA_URL,
        "activity": ACTIVITY,
        "years": [2003, 2024],
        "age_groups": list(AGE_GROUPS),
        "annual_rows": len(annual),
        "respondents": int(
            annual.loc[annual["age_group"].eq("15+"), "n_respondents"].sum()
        ),
        "input_mode": "processed_aggregate_offline_replay"
        if replay
        else "verified_raw_archive",
        "caveats": [
            "T120101 is an activity category, not a measure of all face-to-face interaction.",
            "2020 is partial-year only, uses TU20FWGT, and is excluded from every regression.",
            INFERENCE_NOTE,
            "Full-period OLS is descriptive. Exploratory HAC inference uses only 2003-2019.",
        ],
    }
    record_status(
        "atus",
        "completed",
        "Weighted official BLS estimates and temporal models generated",
        **status,
    )
    return status


if __name__ == "__main__":
    run()
