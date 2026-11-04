"""WGS84 -> 平面直角座標系IX系(EPSG:6677)、bbox中心を原点(m)にする。"""
from pyproj import Transformer

from .osm_fetch import BBOX

_t = Transformer.from_crs(4326, 6677, always_xy=True)
_ox, _oy = _t.transform((BBOX[1] + BBOX[3]) / 2, (BBOX[0] + BBOX[2]) / 2)
_inv = Transformer.from_crs(6677, 4326, always_xy=True)


def to_local(lon, lat):
    x, y = _t.transform(lon, lat)
    return x - _ox, y - _oy


def to_lonlat(x, y):
    return _inv.transform(x + _ox, y + _oy)
