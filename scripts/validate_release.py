"""Check a release's saved notebooks, files, and test receipt."""

import json
import platform
import re
import subprocess
import xml.etree.ElementTree as ElementTree
from pathlib import Path

import nbformat

from econhack.common import OUTPUTS, ROOT, utc_now, write_json


def main():
    notebook_checks = []
    for path in sorted((ROOT / "notebooks").glob("*.ipynb")):
        notebook = nbformat.read(path, as_version=4)
        nbformat.validate(notebook)
        code = [cell for cell in notebook.cells if cell.cell_type == "code"]
        errors = [output for cell in code for output in cell.outputs if output.output_type == "error"]
        if errors or any(cell.execution_count is None for cell in code):
            raise ValueError(f"Notebook not completely executed: {path.name}")
        if notebook.metadata.get("econhack", {}).get("execution") != "executed top-to-bottom":
            raise ValueError(f"Notebook execution receipt missing: {path.name}")
        notebook_checks.append({"notebook": path.name, "code_cells": len(code), "errors": len(errors)})
    if len(notebook_checks) != 5:
        raise ValueError("Expected five executed companion notebooks")
    for path in [ROOT / "README.md", *(ROOT / "docs").rglob("*.md"),
                 *(ROOT / "data").rglob("README.md")]:
        for target in re.findall(r"\]\(([^)]+)\)", path.read_text()):
            if target.startswith(("https://", "http://", "mailto:", "#")):
                continue
            relative = target.split("#")[0]
            if relative and not (path.parent / relative).exists():
                raise ValueError(f"Broken local documentation link: {path.name}: {target}")
    suite = ElementTree.parse(OUTPUTS / "qa" / "tests.xml").getroot().find("testsuite")
    if suite is None or int(suite.attrib["failures"]) or int(suite.attrib["errors"]):
        raise ValueError("Missing or failing pytest receipt")
    tracked = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).decode().split("\0")
    if any(path.startswith(("data/restricted/", ".venv/", ".env")) for path in tracked):
        raise ValueError("Restricted or environment files are tracked")
    for relative in filter(None, tracked):
        if (ROOT / relative).stat().st_size > 50 * 1024 * 1024:
            raise ValueError(f"Oversized distribution file: {relative}")
    summary = {"verified_utc": utc_now(), "python": platform.python_version(), "platform": platform.system(),
               "tests": int(suite.attrib["tests"]), "failures": 0, "errors": 0, "notebooks": notebook_checks,
               "figures_png": len(list((OUTPUTS / "figures").glob("*.png"))),
               "figures_svg": len(list((OUTPUTS / "figures").glob("*.svg"))),
               "tracked_files": len(list(filter(None, tracked))), "restricted_files_tracked": False,
               "local_documentation_links": "passed"}
    write_json(OUTPUTS / "qa" / "release_validation.json", summary)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
