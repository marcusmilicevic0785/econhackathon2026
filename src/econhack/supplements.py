"""Official NYC library and park geometry supplements, audited separately."""

import json

import pandas as pd
from shapely.geometry import shape

from .common import OUTPUTS, fetch, write_json, record_status, save_table
from .nyc import NYC_LICENSE


def run():
    summaries = []
    for label, dataset in [("libraries", "feuq-due4"), ("park_acquisitions", "enfh-gkve")]:
        path = fetch(f"https://data.cityofnewyork.us/api/v3/views/{dataset}/query.geojson?accessType=DOWNLOAD",
                     f"nyc/{label}.geojson", f"NYC Open Data {label} {dataset}", NYC_LICENSE)
        source = json.loads(path.read_text())
        if source.get("type") != "FeatureCollection" or not source.get("features"):
            raise ValueError(f"Invalid {label} GeoJSON response")
        features = source["features"]
        geometry_types = {}
        missing = 0
        invalid = 0
        for feature in features:
            geometry = feature.get("geometry")
            if geometry is None:
                missing += 1
                continue
            geometry_types[geometry["type"]] = geometry_types.get(geometry["type"], 0) + 1
            invalid += int(not shape(geometry).is_valid)
        summaries.append({"dataset": label, "socrata_id": dataset, "features": len(features),
                          "missing_geometries": missing, "invalid_geometries": invalid,
                          "geometry_types": str(geometry_types),
                          "used_as_regression_exposure": False})
        write_json(OUTPUTS / "qa" / f"{label}_schema.json", {"features": len(features), "first_record_fields": sorted(features[0]["properties"]),
                   "geometry_types": geometry_types, "missing_geometries": missing, "invalid_geometries": invalid})
    save_table(pd.DataFrame(summaries), "nyc_supplemental_source_qa")
    record_status("nyc_supplements", "downloaded_audited", "Library GIS and Parks acquisition geometries downloaded separately. Not added to FacDB exposure to avoid cross-source duplicates; acquisitions are not distinct parks.")
