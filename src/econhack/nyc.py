"""NYC tract access equity and modeled loneliness associations."""

import json
from urllib.parse import urlencode

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from scipy.spatial import KDTree

from .common import (
    OUTPUTS,
    PROCESSED,
    fetch,
    profile,
    record_status,
    regression_outputs,
    save_figure,
    save_table,
    write_json,
)

FEDERAL = "US federal government data; public domain; attribute originating agency."
NYC_LICENSE = "NYC Open Data terms https://opendata.cityofnewyork.us/overview/#termsofuse; provided as-is."
COUNTIES = {"005": "Bronx", "047": "Brooklyn", "061": "Manhattan", "081": "Queens", "085": "Staten Island"}
BORO_COUNTY = {"1": "061", "2": "005", "3": "047", "4": "081", "5": "085"}
ACS_COLUMNS = {
    "b01003": ["B01003_E001", "B01003_M001"],
    "b19013": ["B19013_E001", "B19013_M001"],
    "b17001": ["B17001_E001", "B17001_E002", "B17001_M001", "B17001_M002"],
    "b01001": [f"B01001_{kind}{cell:03d}" for kind in ["E", "M"] for cell in
               list(range(6, 11)) + list(range(30, 35)) + list(range(20, 26)) + list(range(44, 50))],
}


def clean_acs(series):
    values = pd.to_numeric(series, errors="coerce")
    return values.mask(values < 0)


def load_acs():
    outputs = []
    for table, columns in ACS_COLUMNS.items():
        extract = PROCESSED / f"acs2023_nyc_{table}.csv"
        if extract.exists():
            frame = pd.read_csv(extract, dtype={"GEO_ID": str})
        else:
            url = f"https://www2.census.gov/programs-surveys/acs/summary_file/2023/table-based-SF/data/5YRData/acsdt5y2023-{table}.dat"
            path = fetch(url, f"acs/acsdt5y2023-{table}.dat", "Census ACS 2019–2023 five-year table-based summary file", FEDERAL)
            chunks = []
            for chunk in pd.read_csv(path, sep="|", usecols=["GEO_ID"] + columns, dtype=str, chunksize=50000):
                chunks.append(chunk[chunk.GEO_ID.str.match(r"^1400000US36(005|047|061|081|085)\d{6}$")])
            frame = pd.concat(chunks, ignore_index=True)
            frame.to_csv(extract, index=False)
        frame[columns] = frame[columns].apply(clean_acs)
        outputs.append(frame.set_index("GEO_ID"))
    result = pd.concat(outputs, axis=1, join="inner").reset_index()
    result["geoid"] = result.GEO_ID.str.removeprefix("1400000US")
    result["county"] = result.geoid.str[2:5]
    result["borough"] = result.county.map(COUNTIES)
    result["population"] = result.B01003_E001
    result["income"] = result.B19013_E001
    result["poverty_pct"] = 100 * result.B17001_E002 / result.B17001_E001.replace(0, np.nan)
    youth = [f"B01001_E{cell:03d}" for cell in list(range(6, 11)) + list(range(30, 35))]
    older = [f"B01001_E{cell:03d}" for cell in list(range(20, 26)) + list(range(44, 50))]
    result["youth_pct"] = 100 * result[youth].sum(axis=1, min_count=len(youth)) / result.population.replace(0, np.nan)
    result["older_pct"] = 100 * result[older].sum(axis=1, min_count=len(older)) / result.population.replace(0, np.nan)
    for column in ["poverty_pct", "youth_pct", "older_pct"]:
        if not result[column].dropna().between(0, 100).all():
            raise ValueError(f"Invalid demographic percentage: {column}")
    profile(result, "acs_nyc", ["geoid"])
    return result


def load_facilities():
    query = urlencode({"$limit": 100000, "$order": "uid"})
    path = fetch("https://data.cityofnewyork.us/resource/ji82-xba5.json?" + query,
                 "nyc/facilities.json", "NYC DCP Facilities Database ji82-xba5 live snapshot", NYC_LICENSE)
    frame = pd.DataFrame(json.loads(path.read_text()))
    if len(frame) >= 100000:
        raise ValueError("FacDB query cap reached; paginate before analysis")
    profile(frame, "facdb_raw", ["uid"])
    save_table(frame.groupby(["facsubgrp", "factype"], dropna=False).size().rename("records").reset_index(), "facdb_taxonomy")
    categories = {
        "LIBRARY": "library", "PUBLIC LIBRARY": "library", "BRANCH LIBRARY": "library",
        "COMMUNITY PARK": "park", "NEIGHBORHOOD PARK": "park", "FLAGSHIP PARK": "park",
        "PLAYGROUND": "park", "JOINTLY OPERATED PLAYGROUND": "park", "CITY-STATE PARK": "park",
        "STATE PARK": "park", "RECREATION CENTER": "recreation", "RECREATION CENTERS": "recreation",
        "NYCHA COMMUNITY CENTER": "community", "SENIOR CENTER": "senior",
    }
    frame["category"] = frame.factype.map(categories)
    selected = frame[frame.category.notna()].copy()
    selected["longitude"] = pd.to_numeric(selected.longitude, errors="coerce")
    selected["latitude"] = pd.to_numeric(selected.latitude, errors="coerce")
    selected["county"] = selected.borocode.astype(str).str.replace(r"\.0$", "", regex=True).map(BORO_COUNTY)
    selected["geoid"] = "36" + selected.county.fillna("") + selected.ct2020.fillna("").str.zfill(6)
    selected["valid_coordinate"] = selected.longitude.between(-74.3, -73.6) & selected.latitude.between(40.45, 40.95)
    selected["site_key"] = (selected.category.astype(str) + "|" + selected.latitude.round(5).astype(str) + "|" + selected.longitude.round(5).astype(str))
    duplicate_sites = selected[selected.valid_coordinate].duplicated("site_key").sum()
    selected = pd.concat([selected[selected.valid_coordinate].drop_duplicates("site_key"), selected[~selected.valid_coordinate]])
    write_json(OUTPUTS / "qa" / "facility_selection.json", {"all_records": len(frame), "selected_records": len(selected),
               "duplicate_coordinate_category_removed": int(duplicate_sites), "invalid_coordinates": int((~selected.valid_coordinate).sum()),
               "categories": selected.category.value_counts().to_dict(), "taxonomy": categories})
    selected.to_csv(PROCESSED / "nyc_selected_facilities.csv", index=False)
    return selected


def geographic_data():
    path = fetch("https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2023_Gazetteer/2023_gaz_tracts_36.txt",
                 "nyc/gazetteer2023_ny_tracts.txt", "Census 2023 NY tract Gazetteer", FEDERAL)
    frame = pd.read_csv(path, sep="\t", dtype={"GEOID": str})
    frame.columns = frame.columns.str.strip()
    frame = frame[frame.GEOID.str[2:5].isin(COUNTIES)].rename(columns={"GEOID": "geoid"})
    profile(frame, "gazetteer_nyc", ["geoid"])
    return frame[["geoid", "ALAND_SQMI", "INTPTLAT", "INTPTLONG"]]


def sphere_coordinates(latitude, longitude):
    latitudes = np.radians(np.asarray(latitude, dtype=float))
    longitudes = np.radians(np.asarray(longitude, dtype=float))
    return np.column_stack([np.cos(latitudes) * np.cos(longitudes), np.cos(latitudes) * np.sin(longitudes), np.sin(latitudes)])


def nearby_counts(tracts, facilities, distance_m):
    valid = facilities[facilities.valid_coordinate]
    if valid.empty:
        raise ValueError("No valid facility coordinates")
    tree = KDTree(sphere_coordinates(valid.latitude, valid.longitude), leafsize=16)
    radius = 2 * np.sin(distance_m / (2 * 6371008.8))
    return tree.query_ball_point(sphere_coordinates(tracts.INTPTLAT, tracts.INTPTLONG), radius, return_length=True)


def build_access():
    frame = load_acs().merge(geographic_data(), on="geoid", validate="one_to_one", how="left", indicator=True)
    if (frame._merge != "both").any():
        raise ValueError("ACS/Gazetteer tract mismatch")
    frame = frame.drop(columns="_merge")
    facilities = load_facilities()
    counts = facilities.groupby("geoid").size()
    frame["within_tract_count"] = frame.geoid.map(counts).fillna(0).astype(int)
    for distance in [400, 800, 1200]:
        frame[f"nearby_{distance}m"] = nearby_counts(frame, facilities, distance)
    frame["population_density"] = frame.population / frame.ALAND_SQMI.replace(0, np.nan)
    frame["log_density"] = np.log1p(frame.population_density)
    frame["log_income"] = np.log(frame.income.where(frame.income > 0))
    frame["log_access"] = np.log1p(frame.nearby_800m)
    frame.to_csv(PROCESSED / "nyc_access.csv", index=False)
    profile(frame, "nyc_access", ["geoid"])
    return frame


def model_sample(frame, columns, name):
    eligible = frame[frame.population >= 100].copy()
    sample = eligible.replace([np.inf, -np.inf], np.nan).dropna(subset=columns)
    write_json(OUTPUTS / "qa" / f"{name}_attrition.json", {"all_tracts": len(frame), "population_at_least_100": len(eligible),
               "complete_cases": len(sample), "removed_geoid": frame.loc[~frame.geoid.isin(sample.geoid), "geoid"].tolist()})
    if len(sample) < 100:
        raise ValueError(f"Insufficient sample: {len(sample)}")
    return sample


def spatial_sensitivity(sample, formula, model_name):
    latitude_bins = np.floor(sample.INTPTLAT * 111.2 / 2).astype(int).astype(str)
    longitude_bins = np.floor(sample.INTPTLONG * 84.3 / 2).astype(int).astype(str)
    groups = latitude_bins + "_" + longitude_bins
    fitted = smf.ols(formula, data=sample).fit(cov_type="cluster", cov_kwds={"groups": groups, "use_correction": True}, use_t=True)
    intervals = fitted.conf_int()
    save_table(pd.DataFrame({"term": fitted.params.index, "coefficient": fitted.params.values,
                            "std_error": fitted.bse.values, "p_value": fitted.pvalues.values,
                            "ci_lower": intervals.iloc[:, 0].values, "ci_upper": intervals.iloc[:, 1].values,
                            "spatial_clusters": groups.nunique()}), model_name + "_spatial_cluster_sensitivity")
    positions = sphere_coordinates(sample.INTPTLAT, sample.INTPTLONG)
    _, neighbor_indices = KDTree(positions, leafsize=16).query(positions, k=9)
    neighbors = np.asarray(neighbor_indices, dtype=np.intp)[:, 1:]
    residuals = np.asarray(fitted.resid) - np.mean(fitted.resid)

    def statistic(values):
        return float(np.sum(values * values[neighbors].mean(axis=1)) / np.sum(values ** 2))

    observed = statistic(residuals)
    generator = np.random.default_rng(2026)
    permutations = np.array([statistic(generator.permutation(residuals)) for _ in range(499)])
    expected = -1 / (len(sample) - 1)
    probability = (1 + np.sum(np.abs(permutations - expected) >= abs(observed - expected))) / 500
    write_json(OUTPUTS / "qa" / f"{model_name}_spatial.json", {"moran_i": observed, "expected_i": expected,
               "permutation_p_two_sided": float(probability), "permutations": 499, "seed": 2026,
               "neighbors": 8, "weighting": "row-standardized directed nearest neighbors",
               "grid_cluster_count": int(groups.nunique()),
               "caveat": "Approximate 2 km geographic tiles; grid clustering is sensitivity, not a guarantee of corrected spatial uncertainty."})


def equity(frame):
    predictors = ["log_income", "poverty_pct", "youth_pct", "older_pct", "log_density"]
    sample = model_sample(frame, predictors + ["log_access"], "nyc_equity")
    formula = "log_access ~ log_income + poverty_pct + youth_pct + older_pct + log_density + C(borough)"
    model = smf.ols(formula, data=sample).fit(cov_type="HC3")
    regression_outputs(model, "nyc_equity", sample, ["log_access"] + predictors)
    spatial_sensitivity(sample, formula, "nyc_equity")
    sensitivity = []
    for distance in [400, 800, 1200]:
        altered = sample.assign(log_access=np.log1p(sample[f"nearby_{distance}m"]))
        fitted = smf.ols(formula, data=altered).fit(cov_type="HC3")
        for variable in predictors:
            sensitivity.append({"radius_m": distance, "term": variable, "coefficient": fitted.params[variable],
                                "ci_lower": fitted.conf_int().loc[variable, 0], "ci_upper": fitted.conf_int().loc[variable, 1]})
    save_table(pd.DataFrame(sensitivity), "nyc_equity_radius_sensitivity")
    sample["income_quintile"] = pd.qcut(sample.income, 5, labels=["Lowest", "Q2", "Q3", "Q4", "Highest"])
    summary = sample.groupby("income_quintile", observed=True).agg(tracts=("geoid", "size"), median_nearby=("nearby_800m", "median"), mean_nearby=("nearby_800m", "mean"))
    save_table(summary.reset_index(), "nyc_equity_income_quintiles")
    figure, axes = plt.subplots(1, 2, figsize=(12, 5))
    axes[0].scatter(sample.income / 1000, sample.nearby_800m, s=12, alpha=.25)
    axes[0].set(xlabel="Median household income (2023 $ thousands)", ylabel="Selected facilities within 800 m", title="Income and nearby facility supply")
    axes[1].bar(summary.index.astype(str), summary.median_nearby)
    axes[1].set(xlabel="Tract income quintile", ylabel="Median facilities within 800 m", title="Neighborhood comparison")
    figure.suptitle("NYC third-space supply: a geographic proxy", fontsize=16)
    figure.text(.02, -.01, "Sources: Census ACS 2019–2023 / Gazetteer; NYC FacDB snapshot. Straight-line distance; availability and entry rules unverified.", fontsize=9)
    figure.tight_layout()
    save_figure(figure, "nyc_access_equity")
    record_status("nyc_equity", "estimated", "Exploratory tract association; HC3 intervals do not correct spatial dependence or ACS sampling error.", n=len(sample), formula=formula)


def loneliness(frame):
    query = urlencode({"$where": "stateabbr='NY' AND measureid='LONELINESS'", "$limit": 10000, "$order": "locationid"})
    path = fetch("https://data.cdc.gov/resource/cwsq-ngmh.json?" + query, "cdc/ny_loneliness_2025.json",
                 "CDC PLACES 2025 release, tract long format cwsq-ngmh, 2023 modeled loneliness", FEDERAL)
    source = pd.DataFrame(json.loads(path.read_text()))
    if len(source) >= 10000:
        raise ValueError("CDC query cap reached")
    if source.empty:
        record_status("access_loneliness", "incomplete", "No NY LONELINESS observations returned; no surrogate outcome fitted.")
        return
    required = {"measureid", "year", "data_value_type", "data_value", "locationid", "low_confidence_limit", "high_confidence_limit"}
    if not required.issubset(source.columns) or not source.measureid.eq("LONELINESS").all() or not source.year.astype(str).eq("2023").all():
        raise ValueError("CDC source schema, measure, or reference year changed")
    source = source[source.data_value_type.str.contains("Crude", case=False)].copy()
    source["geoid"] = source.locationid.astype(str).str.zfill(11)
    source["loneliness_pct"] = pd.to_numeric(source.data_value, errors="coerce")
    profile(source, "places_loneliness_ny", ["geoid"])
    if not source.loneliness_pct.dropna().between(0, 100).all():
        raise ValueError("Invalid CDC prevalence")
    for column in ["low_confidence_limit", "high_confidence_limit"]:
        source[column] = pd.to_numeric(source[column], errors="coerce")
    observed = source.dropna(subset=["loneliness_pct", "low_confidence_limit", "high_confidence_limit"])
    if not ((observed.low_confidence_limit <= observed.loneliness_pct) & (observed.loneliness_pct <= observed.high_confidence_limit) &
            observed.low_confidence_limit.ge(0) & observed.high_confidence_limit.le(100)).all():
        raise ValueError("Invalid CDC modeled confidence bounds")
    source.to_csv(PROCESSED / "cdc_ny_loneliness.csv", index=False)
    joined = frame.merge(source[["geoid", "loneliness_pct", "low_confidence_limit", "high_confidence_limit", "year"]], on="geoid", how="left", validate="one_to_one")
    predictors = ["log_access", "log_income", "poverty_pct", "youth_pct", "older_pct", "log_density"]
    sample = model_sample(joined, predictors + ["loneliness_pct"], "loneliness")
    sample.to_csv(PROCESSED / "nyc_loneliness.csv", index=False)
    formula = "loneliness_pct ~ log_access + log_income + poverty_pct + youth_pct + older_pct + log_density + C(borough)"
    result = smf.ols(formula, data=sample).fit(cov_type="HC3")
    regression_outputs(result, "access_loneliness", sample, ["loneliness_pct"] + predictors)
    spatial_sensitivity(sample, formula, "access_loneliness")
    unadjusted = smf.ols("loneliness_pct ~ log_access + C(borough)", data=sample).fit(cov_type="HC3")
    save_table(pd.DataFrame([{"model": label, "coefficient_log_access": fitted.params["log_access"],
                              "ci_lower": fitted.conf_int().loc["log_access", 0], "ci_upper": fitted.conf_int().loc["log_access", 1],
                              "n": fitted.nobs} for label, fitted in [("borough_only", unadjusted), ("adjusted", result)]]), "loneliness_adjustment_sensitivity")
    figure, axis = plt.subplots()
    axis.scatter(sample.nearby_800m, sample.loneliness_pct, alpha=.3, s=15)
    axis.set(xlabel="Selected facilities within 800 m of tract internal point", ylabel="Modeled adult loneliness prevalence (%)",
             title="Facility supply and modeled loneliness in NYC")
    figure.text(.02, -.02, "CDC PLACES 2025 (2023 outcome); current NYC FacDB. Ecological association with temporal mismatch; not a causal estimate.", fontsize=9)
    figure.tight_layout()
    save_figure(figure, "access_loneliness_scatter")
    record_status("access_loneliness", "estimated_exploratory", "2023 CDC modeled outcome vs current facilities; ACS shares overlap model inputs; temporal mismatch and ecological inference prevent causal claims.", n=len(sample), formula=formula)


def run():
    frame = build_access()
    equity(frame)
    loneliness(frame)
