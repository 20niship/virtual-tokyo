"""Overpass APIからお台場周辺のOSMを取得してdata/osm/にキャッシュする。"""
import json
import sys
import time
from pathlib import Path

import requests

# 南, 西, 北, 東
BBOX = (35.610, 139.715, 35.675, 139.800)
CACHE = Path(__file__).resolve().parents[2] / f"data/osm/odaiba_{'_'.join(map(str, BBOX))}.osm.json"  # bbox変更で自動再取得
ENDPOINTS = ["https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter"]

HEADERS = {"User-Agent": "virtual-tokyo/0.1 (OSM procedural city project)", "Accept": "*/*"}

QUERY = """[out:json][timeout:300];
(
  way["highway"]({b});
  way["building"]({b});  way["building:part"]({b});
  way["railway"]({b});
  way["natural"~"water|coastline|bay"]({b});
  way["landuse"]({b});  way["leisure"]({b});
  way["man_made"~"pier|bridge"]({b});  way["bridge"]({b});
  relation["building"]({b});
  relation["natural"="water"]({b});
  relation["type"="multipolygon"]["landuse"]({b});
  relation["type"="multipolygon"]["leisure"]({b});
  node["railway"="station"]({b});
);
out geom;"""


def fetch(force: bool = False) -> dict:
    if CACHE.exists() and not force:
        return json.loads(CACHE.read_text())
    q = QUERY.format(b=",".join(map(str, BBOX)))
    for attempt in range(4):
        for url in ENDPOINTS:
            try:
                r = requests.post(url, data={"data": q}, headers=HEADERS, timeout=400)
                r.raise_for_status()
                break
            except requests.RequestException as e:
                print(f"{url}: {e}", file=sys.stderr)
        else:
            time.sleep(30 * (attempt + 1))
            continue
        break
    else:
        raise RuntimeError("all Overpass endpoints failed")
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(r.text)
    return r.json()


if __name__ == "__main__":
    d = fetch(force="--force" in sys.argv)
    print(len(d["elements"]), "elements ->", CACHE)
