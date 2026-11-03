from . import lib_bldg, lib_bridge, lib_furniture, lib_gf, lib_misc, lib_street, lib_wall, lib_win  # noqa: F401  (登録のため)
from .registry import REG, build

_cache = {}


def get(name):
    if name not in _cache:
        _cache[name] = build(name)
    return _cache[name]


def all_names():
    return list(REG)
