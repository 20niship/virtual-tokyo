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


EXTRA_CACHE = CACHE.with_name(CACHE.name.replace("odaiba_", "odaiba_extra_"))
EXTRA_QUERY = """[out:json][timeout:300];
(
  node["highway"~"street_lamp|bus_stop|crossing|traffic_signals|stop|speed_camera"]({b});
  node["amenity"~"bench|vending_machine|waste_basket|waste_disposal|post_box|bicycle_parking|bicycle_rental|shelter|telephone|toilets|drinking_water|fountain|charging_station|clock"]({b});
  node["barrier"]({b});
  way["barrier"~"guard_rail|fence|wall|handrail|jersey_barrier|chain|cable_barrier|retaining_wall|kerb"]({b});
  node["power"~"pole|tower|portal|transformer|substation"]({b});
  way["power"~"line|minor_line|cable"]({b});
  node["man_made"~"street_cabinet|utility_pole|mast|flagpole|pole|surveillance|monitoring_station"]({b});
  node["advertising"]({b});
  way["advertising"]({b});
  node["tourism"~"information|artwork"]({b});
  node["emergency"~"fire_hydrant|phone|defibrillator"]({b});
  node["traffic_calming"]({b});
  node["natural"="tree"]({b});
  way["barrier"="hedge"]({b});
  way["natural"~"tree_row|scrub|shrub"]({b});
  node["natural"="shrub"]({b});
  way["leisure"="garden"]({b});
  way["landuse"~"flowerbed|forest"]({b});
  way["natural"="wood"]({b});
  node["amenity"="planter"]({b});
);
out geom;"""


def fetch_extra(force: bool = False) -> dict:
    """道路ファニチャ用のOSM(街灯/バス停/ベンチ/自販機/ガードレール/電柱/広告 など)。bbox別にキャッシュ"""
    if EXTRA_CACHE.exists() and not force:
        return json.loads(EXTRA_CACHE.read_text())
    q = EXTRA_QUERY.format(b=",".join(map(str, BBOX)))
    for attempt in range(5):
        for url in ENDPOINTS:
            try:
                r = requests.post(url, data={"data": q}, headers=HEADERS, timeout=400)
                r.raise_for_status()
                EXTRA_CACHE.parent.mkdir(parents=True, exist_ok=True)
                EXTRA_CACHE.write_text(r.text)
                return r.json()
            except requests.RequestException as e:
                print(f"{url}: {e}", file=sys.stderr)
        time.sleep(30 * (attempt + 1))
    raise RuntimeError("all Overpass endpoints failed")


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
    e = fetch_extra(force="--force" in sys.argv)
    print(len(e["elements"]), "extra elements ->", EXTRA_CACHE)
