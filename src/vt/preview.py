"""レイヤーの2Dプレビュー画像を out/preview/ に出力。"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection, PatchCollection
from matplotlib.patches import Polygon as MplPoly

from .layers import HIGHWAY_DEFAULT, load

OUT = Path(__file__).resolve().parents[2] / "out/preview"
RAIL_COLOR = {"rail": "#d33", "light_rail": "#0a8", "monorail": "#e80"}


def _polys(g):
    return [g] if g.geom_type == "Polygon" else list(g.geoms)


def _patches(feats, **kw):
    return PatchCollection([MplPoly(list(p.exterior.coords)) for f in feats for p in _polys(f.geom)], **kw)


def _lines(feats, **kw):
    return LineCollection([list(f.geom.coords) for f in feats], **kw)


def draw(L, ax, rail_overground=True):
    ax.set_facecolor("#cfe4f2")
    ax.add_collection(_patches(L["green"], fc="#b9d9a0", ec="none"))
    ax.add_collection(_patches(L["water"], fc="#cfe4f2", ec="none", zorder=1))
    ax.add_collection(_patches(L["buildings"], fc="#c9c3bb", ec="#8a847c", lw=0.2))
    major = [f for f in L["roads"] if HIGHWAY_DEFAULT.get(f.tags["highway"], (0,))[0] >= 2 or "link" in f.tags["highway"]]
    minor = [f for f in L["roads"] if f not in major]
    ax.add_collection(_lines(minor, colors="#aaa", lw=0.4))
    ax.add_collection(_lines(major, colors="#444", lw=1.1))
    for kind, c in RAIL_COLOR.items():
        fs = [f for f in L["rail"] if f.tags["railway"] == kind and f.tags.get("tunnel") not in ("yes", "building_passage")]
        ax.add_collection(_lines(fs, colors=c, lw=1.6, zorder=5))
    ax.set_aspect("equal")
    ax.autoscale_view()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    L = load()
    fig, ax = plt.subplots(figsize=(11, 11), dpi=110)
    draw(L, ax)
    ax.set_title("OSM layers (m, origin=bbox center)  red=rail green=Yurikamome orange=Monorail")
    fig.savefig(OUT / "overview.png", bbox_inches="tight")
    ax.set_xlim(-1500, 3300); ax.set_ylim(-3200, 1500)
    fig.savefig(OUT / "odaiba.png", bbox_inches="tight")
    plt.close(fig)

    # 建物の高さ(推定元別)
    fig, ax = plt.subplots(figsize=(11, 11), dpi=110)
    ax.set_facecolor("#222")
    pc = _patches(L["buildings"], cmap="magma", ec="none")
    pc.set_array([f.tags["_top"] for f in L["buildings"] for _ in _polys(f.geom)])
    pc.set_clim(0, 120)
    ax.add_collection(pc)
    ax.add_collection(_lines(L["roads"], colors="#555", lw=0.3))
    ax.set_aspect("equal"); ax.autoscale_view()
    fig.colorbar(pc, ax=ax, shrink=0.6, label="building top [m] (levels/guess incl.)")
    fig.savefig(OUT / "building_height.png", bbox_inches="tight")
    print("saved", [p.name for p in OUT.glob("*.png")])


if __name__ == "__main__":
    main()
