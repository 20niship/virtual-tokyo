from __future__ import annotations

import numpy as np
from rasterio import features
from rasterio.transform import from_origin
from shapely.geometry import shape

from ..core.node import Node, node
from ..masks.terrain import slope_aspect
from .flow import flow, twi
from .rivers import lakes, river_lines


@node("hydro.flow")
class Flow(Node):
    """窪地充填 → D8 流向 → 流量(上流面積 m²) → TWI。sea_level 以下は海(出口)"""
    outputs = ("filled", "flow_rcv", "flow_acc", "twi")
    defaults = dict(sea_level=-1e9)

    def run(self, doc, rng):
        filled, rcv, area = flow(doc.height, doc.grid.res, self.params["sea_level"])
        doc.set("filled", filled, keep64=True)     # ε(1e-5m)を float32 で潰さない
        doc.set("flow_rcv", rcv)
        doc.set("flow_acc", area)
        s, _ = slope_aspect(doc.height, doc.grid.res)
        doc.set("twi", twi(area, s, doc.grid.res))


@node("hydro.rivers")
class Rivers(Node):
    """流域面積が min_area_km2 以上のセルを川にして、支流ごとの折れ線(幅・流量・次数)にする。要 hydro.flow"""
    inputs = ("filled", "flow_rcv", "flow_acc")
    outputs = ("river",)
    vec_outputs = ("rivers",)
    defaults = dict(min_area_km2=0.05, runoff_m=1.2, width_k=2.5, width_exp=0.5)

    def run(self, doc, rng):
        p = self.params
        lines, wmap = river_lines(doc.layers["flow_acc"], doc.layers["flow_rcv"], doc.grid, doc.layers["filled"], p["min_area_km2"] * 1e6,
                                  p["runoff_m"], p["width_k"], p["width_exp"])
        doc.vectors["rivers"] = [(ln, {k: v for k, v in pr.items() if k != "cells"}) for ln, pr in lines]
        doc.set("river", wmap)


@node("hydro.lakes")
class Lakes(Node):
    """充填で埋まった窪地(深さ・面積が基準以上)を湖にする。要 hydro.flow"""
    inputs = ("filled",)
    outputs = ("lake", "water_depth")
    vec_outputs = ("lakes",)
    defaults = dict(min_depth=2.0, min_area_m2=2e4)

    def run(self, doc, rng):
        p = self.params
        lake, wd, info = lakes(doc.height, doc.layers["filled"], doc.grid.res, p["min_depth"], p["min_area_m2"])
        doc.set("lake", lake)
        doc.set("water_depth", wd)
        g = doc.grid
        tr = from_origin(g.x0, g.y0 + g.ny * g.res, g.res, g.res)
        polys = []
        for geom, v in features.shapes(np.flipud(lake).astype(np.int32), mask=np.flipud(lake) > 0, transform=tr):
            polys.append((shape(geom), dict(id=int(v), max_depth=info[int(v)][0], area_m2=info[int(v)][1])))
        doc.vectors["lakes"] = polys
