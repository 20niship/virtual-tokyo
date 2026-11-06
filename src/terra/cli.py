"""terra generate / fetch / preview / export"""
from __future__ import annotations

import argparse
from pathlib import Path

from .core import Document, run_recipe
from .core.pipeline import load_recipe
from .export import export_geotiff, export_heightmap


def _export(doc, out, spec, only=None):
    spec = dict(spec or {})
    if only:
        spec.update(only)
    out = Path(out)
    done = []
    if spec.get("heightmap"):
        done += export_heightmap(doc, out, spec["heightmap"] if isinstance(spec["heightmap"], str) else "raw16")
    if spec.get("geotiff"):
        done += export_geotiff(doc, out, ("height",))
    if spec.get("usd"):
        from .export.usd import export_usd
        done += export_usd(doc, out)
    if spec.get("splat"):
        from .export.usd import export_splat
        done += export_splat(doc, out)
    return done


def cmd_generate(a):
    over = {}
    if a.size:
        over["size_m"] = a.size
    if a.res:
        over["res_m"] = a.res
    r = load_recipe(a.recipe)
    doc = run_recipe(r, seed=a.seed, out=a.out, cache=not a.no_cache, grid_over=over)
    doc.save(a.out)
    for p in _export(doc, a.out, r.get("export")):
        print("wrote", p)


def cmd_fetch(a):
    from .source.gsi_dem import fetch_dem
    x0, y0, x1, y1 = (float(v) for v in a.bbox.split(","))
    for s in a.sources.split(","):
        if s == "gsi_dem":
            print("wrote", fetch_dem((x0, y0, x1, y1), a.out, a.zoom))
        else:
            raise SystemExit(f"source {s} は未実装(T6 で対応)")


def cmd_preview(a):
    from .preview import render_top
    doc = Document.load(a.dir)
    box = None
    if a.spot:
        cx, cy = (float(v) for v in a.spot.split(","))
        box = (cx - a.half, cy - a.half, cx + a.half, cy + a.half)
    if a.view == "top":
        out = Path(a.output or Path(a.dir) / "preview_top.png")
        render_top(doc, a.overlay.split(",") if a.overlay else (), box).save(out)
        print("wrote", out)
    else:
        import subprocess
        import sys
        cmd = [sys.executable, str(Path(__file__).resolve().parents[2] / "scripts" / "terra_render.py"), a.dir, "--view", a.view]
        if a.output:
            cmd += ["-o", a.output]
        subprocess.run(cmd, check=True)


def cmd_export(a):
    doc = Document.load(a.dir)
    only = dict(usd=a.usd, splat=a.splat, geotiff=a.geotiff, heightmap=a.heightmap)
    for p in _export(doc, a.dir, {k: v for k, v in only.items() if v}):
        print("wrote", p)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="terra")
    sp = ap.add_subparsers(dest="cmd", required=True)
    g = sp.add_parser("generate")
    g.add_argument("recipe")
    g.add_argument("--out", required=True)
    g.add_argument("--seed", type=int)
    g.add_argument("--size", type=float, help="grid.size_m 上書き")
    g.add_argument("--res", type=float, help="grid.res_m 上書き")
    g.add_argument("--no-cache", action="store_true")
    g.set_defaults(f=cmd_generate)
    f = sp.add_parser("fetch")
    f.add_argument("--bbox", required=True, help="lon0,lat0,lon1,lat1")
    f.add_argument("--sources", default="gsi_dem")
    f.add_argument("--out", default="data/terra")
    f.add_argument("--zoom", type=int, default=15)
    f.set_defaults(f=cmd_fetch)
    p = sp.add_parser("preview")
    p.add_argument("dir")
    p.add_argument("--view", default="top", choices=["top", "oblique", "ground"])
    p.add_argument("--spot", help="ローカル座標 x,y")
    p.add_argument("--half", type=float, default=250)
    p.add_argument("--overlay", default="")
    p.add_argument("-o", "--output")
    p.set_defaults(f=cmd_preview)
    e = sp.add_parser("export")
    e.add_argument("dir")
    e.add_argument("--usd", action="store_true")
    e.add_argument("--splat", action="store_true")
    e.add_argument("--geotiff", action="store_true")
    e.add_argument("--heightmap", choices=["raw16", "png16", "both"])
    e.set_defaults(f=cmd_export)
    a = ap.parse_args(argv)
    a.f(a)


if __name__ == "__main__":
    main()
