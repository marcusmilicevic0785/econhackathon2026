"""Shared acquisition, provenance, verification, and output utilities."""

import hashlib
import json
import os
import time
import tempfile
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import numpy as np
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
OUTPUTS = ROOT / "outputs"
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".cache" / "matplotlib"))
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

for directory in [RAW, PROCESSED, OUTPUTS / "tables", OUTPUTS / "figures", ROOT / ".cache"]:
    directory.mkdir(parents=True, exist_ok=True)

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11, "axes.spines.top": False,
                     "axes.spines.right": False, "axes.titleweight": "bold", "axes.titlepad": 16,
                     "figure.figsize": (10, 6), "figure.facecolor": "#fafaf7",
                     "axes.facecolor": "#fafaf7", "axes.labelcolor": "#22313f",
                     "text.color": "#22313f", "axes.prop_cycle": plt.cycler(color=["#176b87", "#c37926", "#537a45", "#9a4d70"]),
                     "savefig.dpi": 180, "svg.hashsalt": "econhack2026"})


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def digest(path):
    checksum = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            checksum.update(chunk)
    return checksum.hexdigest()


def read_json(path, fallback):
    return json.loads(path.read_text()) if path.exists() else fallback


def write_json(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, delete=False) as handle:
        handle.write(json.dumps(content, indent=2, allow_nan=False) + "\n")
        temporary = Path(handle.name)
    temporary.replace(path)


@contextmanager
def manifest_lock():
    import fcntl
    lock_path = ROOT / ".cache" / "provenance.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def public_url(url):
    parts = urlsplit(url)
    query = [(name, value) for name, value in parse_qsl(parts.query) if name.lower() not in {"key", "token", "app_token"}]
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), ""))


def fetch(url, relative_path, source, license_note):
    path = RAW / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path = ROOT / "data" / "manifest.json"
    manifest = read_json(manifest_path, {})
    relative = str(path.relative_to(ROOT))
    if path.exists():
        if relative not in manifest or digest(path) != manifest[relative]["sha256"]:
            raise ValueError(f"Unverified or altered cached input: {relative}; remove it and redownload")
        return path
    if os.environ.get("ECONHACK_OFFLINE") == "1":
        raise FileNotFoundError(f"Offline mode: missing {relative}")
    error = None
    for attempt in range(3):
        try:
            response = requests.get(url, timeout=(15, 120), headers={"User-Agent": "EconHack2026 academic reproducibility project"})
            response.raise_for_status()
            content = response.content
            if not content:
                raise ValueError("Empty response")
            if path.suffix.lower() in {".csv", ".json", ".geojson", ".xlsx", ".zip", ".dat", ".gz", ".txt"} and content.lstrip().lower().startswith((b"<!doctype html", b"<html")):
                raise ValueError("HTML returned instead of data (possible missing API key)")
            if path.suffix in {".zip", ".xlsx"} and content[:2] != b"PK":
                raise ValueError("Invalid ZIP signature")
            if path.suffix in {".json", ".geojson"}:
                response.json()
            received_hash = hashlib.sha256(content).hexdigest()
            if relative in manifest and received_hash != manifest[relative]["sha256"]:
                raise ValueError(f"Source changed from pinned checksum for {relative}; archive the old vintage and manifests before explicitly refreshing")
            path.write_bytes(content)
            entry = {"url": public_url(url), "resolved_url": public_url(response.url),
                                  "source": source, "license": license_note, "retrieved_utc": utc_now(),
                                  "sha256": digest(path), "bytes": len(content),
                                  "content_type": response.headers.get("Content-Type"),
                                  "etag": response.headers.get("ETag"), "last_modified": response.headers.get("Last-Modified")}
            with manifest_lock():
                manifest = read_json(manifest_path, {})
                manifest[relative] = entry
                write_json(manifest_path, manifest)
            print(f"Downloaded {relative}: {len(content):,} bytes", flush=True)
            return path
        except (requests.RequestException, ValueError) as exc:
            error = exc
            if attempt < 2:
                time.sleep(attempt + 1)
    raise RuntimeError(f"Could not download {public_url(url)}: {error}")


def save_table(frame, name):
    path = OUTPUTS / "tables" / f"{name}.csv"
    frame.to_csv(path, index=False, float_format="%.10g")
    return path


def save_figure(figure, name):
    for suffix in ["png", "svg"]:
        metadata = {"Date": None} if suffix == "svg" else {"Software": "EconHack 2026"}
        figure.savefig(OUTPUTS / "figures" / f"{name}.{suffix}", bbox_inches="tight", metadata=metadata)
    plt.close(figure)


def record_status(model, status, reason, **kwargs):
    path = OUTPUTS / "model_status.json"
    with manifest_lock():
        statuses = read_json(path, {})
        statuses[model] = {"status": status, "reason": reason, "updated_utc": utc_now(), **kwargs}
        write_json(path, statuses)


def profile(frame, name, keys):
    duplicates = int(frame.duplicated(keys).sum())
    report = {"rows": len(frame), "columns": len(frame.columns), "key": keys,
              "duplicate_keys": duplicates, "missing": frame.isna().sum().astype(int).to_dict()}
    write_json(OUTPUTS / "qa" / f"{name}.json", report)
    if duplicates:
        raise ValueError(f"{name}: {duplicates} duplicated keys")
    return report


def regression_outputs(result, name, frame, predictors):
    from statsmodels.stats.diagnostic import het_breuschpagan
    from statsmodels.stats.outliers_influence import variance_inflation_factor

    intervals = result.conf_int()
    table = pd.DataFrame({"term": result.params.index, "coefficient": result.params.values,
                          "std_error": result.bse.values, "p_value": result.pvalues.values,
                          "ci_lower": intervals.iloc[:, 0].values, "ci_upper": intervals.iloc[:, 1].values})
    save_table(table, name + "_coefficients")
    (OUTPUTS / "tables" / f"{name}_summary.txt").write_text(result.summary().as_text())
    matrix = result.model.exog
    diagnostics = {"n": int(result.nobs), "r_squared": float(result.rsquared),
                   "condition_number": float(result.condition_number), "covariance": result.cov_type,
                   "design_rank": int(np.linalg.matrix_rank(matrix)), "design_columns": matrix.shape[1],
                   "breusch_pagan_p": float(het_breuschpagan(result.resid, matrix)[1])}
    write_json(OUTPUTS / "qa" / f"{name}_diagnostics.json", diagnostics)
    save_table(pd.DataFrame({"term": result.model.exog_names,
                             "vif": [variance_inflation_factor(matrix, index) for index in range(matrix.shape[1])]}), name + "_vif")
    save_table(frame[predictors].corr().rename_axis("variable").reset_index(), name + "_correlation")
    save_table(frame[predictors].cov().rename_axis("variable").reset_index(), name + "_covariance")
    figure, axes = plt.subplots(1, 2, figsize=(12, 5))
    axes[0].scatter(result.fittedvalues, result.resid, alpha=.35, s=12)
    axes[0].axhline(0, color="#555", linewidth=1)
    axes[0].set(xlabel="Fitted outcome", ylabel="Residual", title="Residual pattern")
    import statsmodels.api as sm
    sm.qqplot(result.resid, line="s", ax=axes[1], markerfacecolor="#176b87", markersize=3)
    axes[1].set_title("Residual quantiles")
    figure.suptitle(name.replace("_", " ").title(), fontsize=15)
    figure.tight_layout()
    save_figure(figure, name + "_diagnostics")
    terms = table[~table.term.str.startswith(("Intercept", "C("))]
    if len(terms):
        figure, axis = plt.subplots(figsize=(10, max(4, .5 * len(terms) + 2)))
        axis.errorbar(terms.coefficient, np.arange(len(terms)),
                      xerr=[terms.coefficient - terms.ci_lower, terms.ci_upper - terms.coefficient], fmt="o", capsize=4)
        labels = {"log_income": "Log household income (per ln dollar)", "poverty_pct": "Poverty share (per percentage point)",
                  "youth_pct": "Age 15–24 share (per percentage point)", "older_pct": "Age 65+ share (per percentage point)",
                  "log_density": "Log population density (per ln unit)", "log_access": "Log nearby supply (per ln unit)"}
        axis.set_yticks(np.arange(len(terms)), [labels.get(term, term) for term in terms.term])
        axis.axvline(0, color="#777", linewidth=1)
        title = {"nyc_equity": "NYC access equity: adjusted associations", "access_loneliness": "Modeled loneliness: adjusted associations"}.get(name, name.replace("_", " ").title())
        axis.set(title=title, xlabel=f"Coefficient with 95% {result.cov_type} interval; predictor units differ")
        figure.tight_layout()
        save_figure(figure, name + "_coefficients")
    return table
