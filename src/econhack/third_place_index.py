"""Optional restricted Third Place Index acquisition and aggregate comparison."""

import argparse
import csv
import hashlib
import zipfile
from pathlib import PurePosixPath

import numpy as np
import pandas as pd

from .common import (
    OUTPUTS,
    PROCESSED,
    ROOT,
    fetch,
    record_status,
    save_figure,
    save_table,
)

URL = "https://thirdplaceindex.org/data/third_place_index-main.zip"
SOURCE = "Evan O'Neil, Third Place Index; archive README supplies release-specific metadata"
LICENSE = (
    "Compiled index redistribution permission unresolved. Source identifies OSM ODbL "
    "and public-domain Census inputs, without a separate compiled-index grant. "
    "Restricted local research only; do not redistribute archive or tract-level derivatives."
)
REQUIRED = {
    "geoid", "geoid_2022", "state_fips", "urban_rural_class",
    "third_place_percentile", "total_places",
}
CATEGORIES = (
    "food_beverage_count", "personal_service_count", "traditional_retail_count",
    "civic_educational_count", "public_spaces_count", "cultural_arts_count",
    "commercial_retail_count", "fitness_wellness_count", "work_creation_count",
    "entertainment_gaming_count",
)
ACCESS_COLUMNS = ("within_tract_count", "nearby_400m", "nearby_800m", "nearby_1200m")
NYC_PATTERN = r"36(?:005|047|061|081|085)[0-9]{6}"
MIN_COMPARISON = 100
MAX_MEMBERS = 128
MAX_UNCOMPRESSED = 512 * 1024 * 1024


def sha256(path):
    checksum = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            checksum.update(chunk)
    return checksum.hexdigest()


def read_archive(path):
    with zipfile.ZipFile(path) as archive:
        members = archive.infolist()
        if len(members) > MAX_MEMBERS or sum(member.file_size for member in members) > MAX_UNCOMPRESSED:
            raise ValueError("TPI archive exceeds inspection limits")
        inventory = []
        candidates = []
        for member in members:
            parts = PurePosixPath(member.filename).parts
            ignored = member.is_dir() or "__MACOSX" in parts or any(part.startswith(".") for part in parts)
            if member.flag_bits & 1:
                raise ValueError("TPI archive contains an encrypted member")
            if not ignored and member.file_size > 1000 * max(member.compress_size, 1):
                raise ValueError("TPI archive exceeds compression-ratio limit")
            inventory.append({"member": member.filename, "bytes": member.file_size, "ignored": ignored})
            if ignored or not member.filename.lower().endswith(".csv"):
                continue
            with archive.open(member) as handle:
                header_line = handle.readline(65537)
            if len(header_line) > 65536:
                raise ValueError("TPI CSV header exceeds inspection limit")
            header = next(csv.reader([header_line.decode("utf-8-sig").strip()]))
            if len(set(header)) != len(header):
                raise ValueError("TPI CSV has duplicate column names")
            if REQUIRED.issubset(header):
                candidates.append(member)
        if len(candidates) != 1:
            raise ValueError("TPI archive must contain exactly one CSV with the required schema")
        selected = candidates[0]
        with archive.open(selected) as handle:
            frame = pd.read_csv(handle, dtype=str, encoding="utf-8-sig")
    return frame, inventory, selected.filename


def validate_index(frame):
    if frame.empty or not REQUIRED.issubset(frame.columns):
        raise ValueError("TPI data are empty or missing required columns")
    frame = frame.copy()
    for column in ("geoid", "geoid_2022", "state_fips", "urban_rural_class"):
        frame[column] = frame[column].astype("string").str.strip()
    if not frame.geoid.str.fullmatch(r"[0-9]{11}", na=False).all():
        raise ValueError("TPI geoid must contain complete 11-digit text identifiers")
    if frame.geoid.duplicated().any():
        raise ValueError("TPI geoid is not unique")
    if not frame.state_fips.str.fullmatch(r"[0-9]{2}", na=False).all():
        raise ValueError("TPI state_fips must contain complete two-digit text identifiers")
    if not frame.state_fips.eq(frame.geoid.str[:2]).all():
        raise ValueError("TPI state_fips disagrees with geoid")
    crosswalk_present = frame.geoid_2022.notna()
    if not frame.loc[crosswalk_present, "geoid_2022"].str.fullmatch(r"[0-9]{11}", na=False).all():
        raise ValueError("TPI geoid_2022 contains malformed identifiers")
    outside_connecticut = frame.state_fips.ne("09")
    if not frame.loc[outside_connecticut, "geoid_2022"].eq(frame.loc[outside_connecticut, "geoid"]).fillna(False).all():
        raise ValueError("TPI GEOID vintages differ or are missing outside Connecticut")
    if not frame.urban_rural_class.isin(["Urbanized Area", "Urban Cluster", "Rural"]).all():
        raise ValueError("TPI urban/rural class is missing or unrecognized")
    numeric_columns = {"third_place_percentile", "total_places"}
    numeric_columns.update(column for column in frame if column.endswith("_count"))
    numeric_columns.update(column for column in (
        "total_population", "median_income", "pct_bachelors", "pop_under_18",
        "pct_under_18", "area_sq_miles", "total_places_per_sqmi",
    ) if column in frame)
    schema = []
    for column in frame:
        missing = int(frame[column].isna().sum())
        invalid = 0
        negative = 0
        if column in numeric_columns:
            original = frame[column]
            values = pd.to_numeric(original, errors="coerce").astype(float)
            invalid = int((original.notna() & ~np.isfinite(values)).sum())
            negative = int(values.lt(0).sum())
            frame[column] = values
            if (column == "total_places" or column.endswith("_count")) and (
                missing or invalid or negative or values.mod(1).ne(0).any()
            ):
                raise ValueError(f"TPI {column} must contain complete finite nonnegative integers")
            if column == "third_place_percentile" and (
                missing or invalid or not values.between(0, 1).all()
            ):
                raise ValueError("TPI score must contain complete finite values on the documented 0–1 scale")
        schema.append({"column": column, "required": column in REQUIRED,
                       "kind": "numeric" if column in numeric_columns else "text",
                       "missing_rows": missing, "invalid_numeric_rows": invalid,
                       "negative_numeric_rows": negative})
    reconciliation = None
    if set(CATEGORIES).issubset(frame.columns):
        reconciliation = int(frame[list(CATEGORIES)].sum(axis=1).ne(frame.total_places).sum())
        if reconciliation:
            raise ValueError("TPI category counts do not reconcile to total_places")
    qa = {"source_rows": len(frame), "source_columns": len(frame.columns),
          "duplicate_geoid_rows": 0, "category_total_mismatches": reconciliation,
          "missing_category_columns": len(set(CATEGORIES).difference(frame.columns)),
          "missing_geoid_2022_rows": int((~crosswalk_present).sum()),
          "nyc_tpi_tracts": int(frame.geoid.str.fullmatch(NYC_PATTERN).sum())}
    return frame, pd.DataFrame(schema), qa


def compare_access(frame, path):
    header = pd.read_csv(path, nrows=0).columns
    if not {"geoid", "within_tract_count", "nearby_800m"}.issubset(header):
        raise ValueError("Official NYC access file is missing required comparison columns")
    columns = [column for column in ACCESS_COLUMNS if column in header]
    official = pd.read_csv(path, usecols=["geoid"] + columns, dtype={"geoid": str})
    official["geoid"] = official.geoid.astype("string").str.strip()
    if not official.geoid.str.fullmatch(NYC_PATTERN, na=False).all() or official.geoid.duplicated().any():
        raise ValueError("Official NYC access file has invalid or duplicated NYC tract identifiers")
    for column in columns:
        values = pd.to_numeric(official[column], errors="coerce").astype(float)
        if not (np.isfinite(values) & values.ge(0) & values.mod(1).eq(0)).all():
            raise ValueError(f"Official access {column} must contain complete finite nonnegative integers")
        official[column] = values
    nyc = frame.loc[frame.geoid.str.fullmatch(NYC_PATTERN), ["geoid_2022", "total_places"]]
    matched = official.merge(nyc, left_on="geoid", right_on="geoid_2022", how="inner", validate="one_to_one")
    matched_count = len(matched)
    qa = {"official_nyc_tracts": len(official), "matched_tracts": matched_count,
          "official_unmatched_tracts": len(official) - matched_count,
          "tpi_nyc_unmatched_tracts": len(nyc) - matched_count}
    correlations = []
    for column in columns:
        publishable = (matched_count >= MIN_COMPARISON and matched.total_places.nunique() >= 3
                       and matched[column].nunique() >= 3)
        coefficient = None
        if publishable:
            coefficient = float(matched.total_places.rank().corr(matched[column].rank()))
            publishable = bool(np.isfinite(coefficient))
        correlations.append({"tpi_measure": "total_places", "official_measure": column,
                             "matched_tracts": matched_count,
                             "spearman_rho": round(coefficient, 3) if publishable and coefficient is not None else None,
                             "status": "descriptive" if publishable else "suppressed_insufficient_support"})
    return qa, pd.DataFrame(correlations)


def aggregate_figure(comparison):
    valid = comparison.loc[comparison.status.eq("descriptive")]
    if valid.empty:
        return False
    import matplotlib.pyplot as plt

    figure, axis = plt.subplots(figsize=(10, 5))
    axis.barh(valid.official_measure, valid.spearman_rho)
    axis.axvline(0, color="#777", linewidth=1)
    axis.set(xlim=(-1, 1), xlabel="Spearman correlation with TPI total venue count",
             title="NYC tract measures: aggregate rank agreement")
    figure.text(.02, .01, "Matched NYC tracts only; broad OSM venues vs selected official facilities.\n"
                "Straight-line nearby supply differs from within-tract supply; descriptive, not causal.", fontsize=9)
    figure.tight_layout(rect=(0, .09, 1, 1))
    save_figure(figure, "third_place_index_aggregate_comparison")
    return True


def run(download=False, make_figure=False):
    restricted = ROOT / "data" / "restricted"
    archive_path = restricted / "third_place_index.zip"
    resolved_restricted = restricted.resolve()
    if not resolved_restricted.is_relative_to(ROOT.resolve()) or not archive_path.resolve().is_relative_to(resolved_restricted):
        raise ValueError("TPI archive must stay inside the repository restricted directory")
    ignored = ROOT / ".gitignore"
    if not ignored.exists() or "data/restricted/" not in {line.strip() for line in ignored.read_text().splitlines()}:
        raise ValueError("Repository must ignore data/restricted/ before TPI acquisition")
    if not download and not archive_path.exists():
        record_status("third_place_index", "not_downloaded", "Optional restricted source absent; explicitly pass --download to acquire.", source_url=URL)
        return None
    try:
        path = fetch(URL, "../restricted/third_place_index.zip", SOURCE, LICENSE)
        if path.resolve() != archive_path.resolve():
            raise ValueError("Common fetch returned an unexpected restricted archive path")
        record_status("third_place_index", "downloaded_not_redistributed", LICENSE,
                      source_url=URL, archive_sha256=sha256(path), qa_status="pending")
        try:
            frame, inventory, member = read_archive(path)
        except (ValueError, UnicodeError, zipfile.BadZipFile, csv.Error, pd.errors.ParserError, EOFError):
            raise ValueError("TPI archive/schema could not be read; no row contents exported") from None
        frame, schema, qa = validate_index(frame)
        official_path = PROCESSED / "nyc_access.csv"
        comparison = None
        comparison_status = "not_available_run_nyc_first"
        official_hash = None
        if official_path.exists():
            additional, comparison = compare_access(frame, official_path)
            qa.update(additional)
            official_hash = sha256(official_path)
            comparison_status = "descriptive" if comparison.status.eq("descriptive").any() else "insufficient_support"
        summary = pd.DataFrame([{"metric": metric, "value": value} for metric, value in qa.items()])
        save_table(pd.DataFrame(inventory), "third_place_index_archive_inventory")
        save_table(schema, "third_place_index_schema")
        save_table(summary, "third_place_index_qa_summary")
        if comparison is not None:
            save_table(comparison, "third_place_index_comparison")
        chart_written = make_figure and comparison is not None and aggregate_figure(comparison)
        record_status(
            "third_place_index", "downloaded_not_redistributed", LICENSE,
            source_url=URL, archive_sha256=sha256(path), csv_member=member,
            qa_status="passed", comparison_status=comparison_status,
            official_input_sha256=official_hash, aggregate_figure_written=bool(chart_written),
            public_output_directory=str((OUTPUTS / "tables").relative_to(ROOT)),
            output_policy="Schema, inventory, QA counts and pooled correlations only; no GEOIDs or tract-level values.",
        )
        return {"qa": qa, "comparison_status": comparison_status}
    except Exception as exc:
        record_status("third_place_index", "incomplete_not_redistributed",
                      "Restricted acquisition or validation failed; no tract-level output written.",
                      failure_type=type(exc).__name__, source_url=URL, qa_status="failed")
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--download", action="store_true", help="Acquire restricted ZIP through the common verified fetch cache")
    parser.add_argument("--aggregate-figure", action="store_true", help="Plot pooled correlations only when at least 100 tracts match")
    arguments = parser.parse_args()
    run(download=arguments.download, make_figure=arguments.aggregate_figure)


if __name__ == "__main__":
    main()
