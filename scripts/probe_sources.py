"""Inspect source schemas without storing data outside the provenance system."""
import re
from concurrent.futures import ThreadPoolExecutor

import requests

URLS = [
    "https://data.cityofnewyork.us/resource/ji82-xba5.json?$select=factype,count(*)&$group=factype&$limit=2000",
    "https://data.cityofnewyork.us/resource/weqx-t5xr.json?$limit=1",
    "https://data.cdc.gov/resource/cwsq-ngmh.json?$select=measure,measureid,year&$group=measure,measureid,year&$limit=500",
    "https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2023_Gazetteer/",
    "https://www2.census.gov/programs-surveys/acs/summary_file/2023/table-based-SF/data/5YRData/acsdt5y2023-b01003.dat",
]


def inspect(url):
    with requests.get(url, timeout=60, stream=True) as response:
        if url.endswith("/"):
            value = re.findall('href="([^"]+)"', response.text)
            value = [item for item in value if "tract" in item.lower()]
        elif url.endswith(".dat"):
            value = next(response.iter_content(2000)).decode()
        else:
            value = response.json()
        return url, response.status_code, value


if __name__ == "__main__":
    for result in ThreadPoolExecutor(5).map(inspect, URLS):
        print(result, flush=True)
