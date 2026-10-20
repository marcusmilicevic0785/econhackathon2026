"""One command for deterministic model runs and source integrity checks."""

import argparse
import importlib
import os
import sys

from .common import ROOT, OUTPUTS, digest, read_json, record_status, write_json, utc_now


def verify():
    manifest = read_json(ROOT / "data" / "manifest.json", {})
    failures = []
    missing = []
    checked = 0
    for relative, entry in manifest.items():
        path = ROOT / relative
        if not path.exists():
            missing.append(relative)
        elif digest(path) != entry["sha256"]:
            failures.append(relative)
        else:
            checked += 1
    processed = read_json(ROOT / "data" / "processed_manifest.json", {})
    for relative, entry in processed.items():
        path = ROOT / relative
        if not path.exists() or digest(path) != entry["sha256"]:
            failures.append(relative)
        else:
            checked += 1
    print(f"Verified {checked} source/extract hashes; {len(missing)} large source files omitted from distribution.")
    if not manifest or failures:
        raise ValueError(f"Integrity check failed: {failures}")
    return 0


def snapshot():
    files = sorted((ROOT / "data" / "processed").glob("*.csv"))
    raw = read_json(ROOT / "data" / "manifest.json", {})
    def source_inputs(path):
        name = path.name
        if name.startswith("acs2023_nyc_"):
            table = name.removeprefix("acs2023_nyc_").removesuffix(".csv")
            return [key for key in raw if key.endswith(f"acsdt5y2023-{table}.dat") and "/panel/" not in key]
        if name.startswith("panel_"):
            return [key for key in raw if "/panel/" in key]
        if name.startswith("atus_published"):
            return [key for key in raw if "/atus_published/" in key and key.endswith(".json")]
        if name.startswith("atus_"):
            return [key for key in raw if "/atus/" in key]
        if name.startswith("cdc_"):
            return [key for key in raw if "/cdc/" in key]
        return [key for key in raw if "/acs/" in key and "/panel/" not in key or "/nyc/" in key or "/cdc/" in key]
    write_json(ROOT / "data" / "processed_manifest.json", {
        str(path.relative_to(ROOT)): {"sha256": digest(path), "bytes": path.stat().st_size,
                                     "generated_utc": utc_now(), "source_manifest_keys": source_inputs(path),
                                     "transformation": "src/econhack; docs/data_dictionary.md"} for path in files})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["run", "verify", "snapshot"], nargs="?", default="run")
    parser.add_argument("--model", choices=["all", "nyc", "atus", "panel", "supplements", "third_place_index"], default="all")
    parser.add_argument("--offline", action="store_true")
    arguments = parser.parse_args()
    if arguments.offline:
        os.environ["ECONHACK_OFFLINE"] = "1"
    if arguments.command == "verify":
        return verify()
    if arguments.command == "snapshot":
        snapshot()
        return 0
    if (ROOT / "data" / "processed_manifest.json").exists():
        verify()
    modules = ["nyc", "atus", "panel", "supplements", "third_place_index"] if arguments.model == "all" else [arguments.model]
    failed = []
    for name in modules:
        print(f"Running {name}", flush=True)
        try:
            module = importlib.import_module(f"econhack.{name}")
            if name == "third_place_index":
                module.run(download=not arguments.offline, make_figure=True)
            else:
                result = module.run()
                if name == "panel" and isinstance(result, dict) and result.get("status") != "complete":
                    failed.append(name)
        except Exception as exc:
            import traceback
            if name == "atus" and isinstance(exc, (RuntimeError, FileNotFoundError)):
                record_status("atus", "incomplete_microdata", "Official multi-year archive unavailable; age 15–24 estimates are not generated. " + str(exc))
                try:
                    importlib.import_module("econhack.atus_published").run()
                except Exception as fallback_error:
                    traceback.print_exc()
                    record_status("atus_published", "failed", str(fallback_error))
                    failed.append("atus_published")
            else:
                traceback.print_exc()
                record_status(name, "failed", str(exc))
                failed.append(name)
    record_status("library_did", "not_estimated", "No verified branch-level treatment dates, matched untreated controls, and aligned repeated pre/post local outcomes. CDC PLACES is unsuitable for intervention evaluation. See docs/models/library_did.md.")
    snapshot()
    write_json(OUTPUTS / "run_status.json", {"completed_utc": utc_now(), "requested": modules, "failed": failed})
    return int(bool(failed))


if __name__ == "__main__":
    sys.exit(main())
