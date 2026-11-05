"""植栽の配置: OSMの natural=tree / 生垣 / 並木 / 庭・森 と、道路の歩道・中央分離帯・公園/緑地ポリゴンから、
樹木・低木・生垣・花壇・壁面緑化・ツリーサークルの Inst を作る(PointInstancer方式)。信号/街灯/標識等(avoid)とは干渉しない。"""
import math
import random

from shapely.geometry import LineString, MultiPolygon, Point, Polygon
from shapely.prepared import prep

from .assemble import Inst
from .modules.library import REG

SIZES = ("s", "m", "l")
# 樹種→(サイズ別の既定重み)。OSM種名キーワード→樹種
KEYWORDS = [("ginkgo", "ichou"), ("イチョウ", "ichou"), ("zelkova", "keyaki"), ("ケヤキ", "keyaki"), ("platanus", "platanus"), ("プラタナス", "platanus"), ("スズカケ", "platanus"),
            ("prunus", "sakura"), ("サクラ", "sakura"), ("桜", "sakura"), ("cinnamomum", "kusunoki"), ("クスノキ", "kusunoki"), ("castanopsis", "shii"), ("シイ", "shii"),
            ("タブ", "shii"), ("machilus", "shii"), ("lithocarpus", "shii"), ("fagaceae", "shii"), ("acer", "tokaikaede"), ("カエデ", "tokaikaede"), ("cornus", "hanamizuki"),
            ("ハナミズキ", "hanamizuki"), ("pinus", "kuromatsu"), ("マツ", "kuromatsu"), ("松", "kuromatsu"), ("salix", "yanagi"), ("ヤナギ", "yanagi"), ("柳", "yanagi"),
            ("phoenix", "yashi_canary"), ("washingtonia", "yashi_washingtonia"), ("trachycarpus", "shuro"), ("シュロ", "shuro")]


class Occ:
    """空間ハッシュ(中心・半径)。ポイント同士が近すぎないか"""

    def __init__(self, cell=6.0):
        self.cell = cell
        self.g = {}

    def add(self, x, y, r):
        self.g.setdefault((int(x // self.cell), int(y // self.cell)), []).append((x, y, r))

    def free(self, x, y, r):
        k = (int(x // self.cell), int(y // self.cell))
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for (px, py, pr) in self.g.get((k[0] + dx, k[1] + dy), ()):
                    if (px - x) ** 2 + (py - y) ** 2 < (r + pr) ** 2:
                        return False
        return True


class Veg:
    def __init__(self, L, X, world, edges, info, cfg, seed, avoid):
        self.rng = random.Random(seed)
        self.cfg = cfg
        self.zf = world["zf"]
        self.area = world["area"]
        self.land = prep(world["land"])
        self.landg = world["land"]
        self.cw = prep(info["cw"].buffer(0.3))
        self.sw = info["sw"]
        self.swp = prep(info["sw"]) if not info["sw"].is_empty else None
        self.info = info
        self.edges = edges
        self.season = cfg.get("veg_season", "summer")
        self.out = []
        self.occ = Occ()
        self.coast = world["land"].boundary
        for a in avoid or ():
            if a.name.startswith(("pole_", "light_", "sign_", "sigv", "sigp", "signal", "bus_stop", "utility", "street_cabinet", "bollard", "guard", "curve_mirror", "bench", "hydrant", "post_box", "vending", "bike")):
                self.occ.add(a.x, a.y, 0.6)
        self.n_tree = 0

    # ---- 部品 ----
    def mod(self, sp, sz, seed=None):
        seed = self.rng.randint(0, 1) if seed is None else seed
        for se in (self.season, "summer"):
            n = f"veg_{sp}_{sz}_{seed}_{se}"
            if n in REG:
                return n
            n = f"veg_{sp}_{sz}_0_{se}"
            if n in REG:
                return n
        return None

    def z(self, x, y):
        on = self.swp is not None and self.swp.contains(Point(x, y))
        return self.zf(x, y) + (0.14 if on else 0.0)

    def put(self, name, x, y, rot=None, jitter=True, scale=None):
        if name is None or name not in REG or not self.area.contains(Point(x, y)):
            return False
        s = scale or (self.rng.uniform(0.88, 1.15) if jitter else 1.0)
        self.out.append(Inst(name, x, y, self.z(x, y), self.rng.uniform(0, 6.28) if rot is None else rot, s, s, s))
        return True

    def tree(self, sp, sz, x, y, r_clear, scale=None, pit=False):
        if not self.occ.free(x, y, r_clear) or self.cw.contains(Point(x, y)):
            return False
        if not (self.land.contains(Point(x, y)) or (self.swp is not None and self.swp.contains(Point(x, y)))):
            return False
        if self.put(self.mod(sp, sz), x, y, scale=scale):
            self.occ.add(x, y, r_clear)
            self.n_tree += 1
            self.litter(sp, x, y, r_clear)
            if pit:
                self.put("veg_tree_pit_grating" if self.rng.random() < 0.55 else "veg_tree_pit_curb", x, y, 0.0, jitter=False)
            return True
        return False

    LITTER = {"ichou": "y", "keyaki": "y", "platanus": "y", "sakura": "r", "tokaikaede": "r", "hanamizuki": "r", "kusunoki": "b", "shii": "b", "kuromatsu": "b"}
    # 季節 → 1本あたりの落ち葉デカール数(秋〜冬に多い。春は花びら/新芽の殻で少なめ、夏は青葉がわずか)
    LITTER_N = {"autumn_y": 4, "autumn_r": 4, "winter": 3, "spring": 1, "summer": 0.5}

    def litter(self, sp, x, y, r):
        """樹下(歩道・地面)に落ち葉デカールをインスタンス配置。道路上には置かない"""
        k = self.LITTER.get(sp)
        n = self.LITTER_N.get(self.season, 0.5)
        if k is None or not n:
            return
        k = "b" if self.season == "winter" else ("g" if self.season == "summer" else k)
        for _ in range(int(n) + (1 if self.rng.random() < n % 1 else 0)):
            a, d = self.rng.uniform(0, 6.28), self.rng.uniform(0.2, 0.9) * r
            px, py = x + math.cos(a) * d, y + math.sin(a) * d
            if not self.cw.contains(Point(px, py)) and (self.land.contains(Point(px, py)) or (self.swp is not None and self.swp.contains(Point(px, py)))):
                self.put(f"veg_litter_{k}", px, py, scale=self.rng.uniform(0.8, 1.5))

    def species_for(self, tags, ctx):
        t = " ".join(str(tags.get(k, "")) for k in ("genus", "species", "species:ja", "name", "taxon")).lower()
        for kw, sp in KEYWORDS:
            if kw.lower() in t:
                return sp
        lt = tags.get("leaf_type")
        if lt == "needleleaved":
            return "kuromatsu"
        r = self.rng
        if ctx == "street_major":
            return r.choices(["ichou", "keyaki", "platanus", "sakura"], [3, 3, 2, 1])[0]
        if ctx == "street":
            return r.choices(["keyaki", "sakura", "tokaikaede", "hanamizuki", "shii"], [3, 3, 2, 2, 1])[0]
        if ctx == "coast":
            return r.choices(["kuromatsu", "yashi_canary", "yashi_washingtonia", "shuro", "kusunoki", "shii"], [4, 2, 1, 1, 1, 2])[0]
        if ctx == "water":
            return r.choices(["yanagi", "sakura", "kuromatsu", "keyaki"], [3, 2, 1, 2])[0]
        return r.choices(["keyaki", "kusunoki", "shii", "sakura", "platanus", "ichou", "tokaikaede", "kuromatsu", "hanamizuki"], [3, 3, 3, 2, 1, 1, 1, 1, 1])[0]

    def size_for(self, tags, ctx):
        h = tags.get("height")
        try:
            h = float(str(h).split()[0])
        except (TypeError, ValueError):
            h = None
        if h is not None:
            return "s" if h < 6.5 else ("m" if h < 11.5 else "l")
        r = self.rng
        return r.choices(SIZES, {"street_major": (1, 3, 2), "street": (2, 3, 1), "coast": (1, 3, 2), "water": (1, 3, 2)}.get(ctx, (2, 4, 2)))[0]


def _clear_ends(info):
    c = {}
    for a in info["arms"]:
        _, node, e, is_start, arm, D, fr = a
        c[(e.id, is_start)] = D + 10.0
    return c


def osm_trees(V, X):
    """natural=tree ノード: 歩道上なら街路樹(+ツリーグレーチング)、岸沿いなら海岸樹、他は公園樹"""
    n = 0
    for f in X["pois"]:
        if f.tags.get("natural") != "tree" or not V.area.contains(f.geom):
            continue
        x, y = f.geom.x, f.geom.y
        on_sw = V.swp is not None and V.swp.contains(f.geom)
        d_coast = V.coast.distance(f.geom)
        ctx = "street" if on_sw else ("coast" if d_coast < 10 else "park")
        sp = V.species_for(f.tags, ctx)
        sz = V.size_for(f.tags, ctx)
        if V.tree(sp, sz, x, y, {"s": 1.2, "m": 1.8, "l": 2.6}[sz], pit=on_sw and f.tags.get("natural") == "tree"):
            n += 1
    return n


def street_trees(V, X):
    """歩道/植栽帯に沿った街路樹: 6〜12m間隔。OSMの街路樹が既にある道路は省く。交差点付近・信号柱/街灯とは避ける。中央分離帯(planter)には低木帯。"""
    rng = V.rng
    clear = _clear_ends(V.info)
    tree_pts = [f.geom for f in X["pois"] if f.tags.get("natural") == "tree"]
    n = 0
    for e in V.edges:
        if e.kind != "drive" or e.level != 0 or e.prof is None or e.line.length < 25:
            continue
        p = e.prof
        hw = e.tags["highway"]
        if hw in ("service", "motorway", "motorway_link") or "link" in hw:
            continue
        major = hw in ("trunk", "primary", "secondary")
        near_osm = sum(1 for g in tree_pts if e.line.distance(g) < 8)
        if near_osm and e.line.length / near_osm < 22:
            continue
        sp = V.species_for({}, "street_major" if major else "street")
        s0 = clear.get((e.id, True), 8.0)
        s1 = e.line.length - clear.get((e.id, False), 8.0)
        for side, sw in ((1, p.sw_l), (-1, p.sw_r)):
            if sw < 2.6 or rng.random() < 0.25:
                continue
            gap = rng.uniform(7, 11) if major else rng.uniform(8, 13)
            s = s0 + rng.uniform(0, gap * 0.6)
            while s < s1:
                q, q2 = e.line.interpolate(s), e.line.interpolate(min(e.line.length, s + 1.0))
                tx, ty = q2.x - q.x, q2.y - q.y
                d = math.hypot(tx, ty) or 1
                nx, ny = -ty / d, tx / d
                off = p.half + min(1.3, sw * 0.45)
                x, y = q.x + nx * side * off, q.y + ny * side * off
                sz = "m" if sw < 4.5 else "l"
                if V.tree(sp, sz, x, y, 1.8 if sz == "m" else 2.4, pit=True):
                    n += 1
                s += gap * rng.uniform(0.9, 1.1)
        # 中央分離帯(植栽帯)の低木帯
        if p.median >= 1.4 and p.median_kind == "planter":
            s = s0
            while s < s1 - 2:
                q, q2 = e.line.interpolate(s + 1), e.line.interpolate(min(e.line.length, s + 1.8))
                ang = math.atan2(q2.y - q.y, q2.x - q.x)
                if V.occ.free(q.x, q.y, 0.7):
                    V.put(f"veg_hedge_low_{rng.randint(0, 1)}", q.x, q.y, ang, jitter=False)
                    if rng.random() < 0.3:
                        V.put(f"veg_azalea_{rng.randint(0, 2)}_r8", q.x, q.y, None)
                s += 2.0
    return n


def park_vegetation(V, L, X):
    """緑地/庭/森ポリゴン: ポアソンディスク風に樹木を、縁取りに低木と花壇を。水際には柳。"""
    rng = V.rng
    polys = [f.geom for f in L["green"]] + [f.geom for f in X["vegareas"]]
    for f in L["landuse"]:
        if f.tags.get("landuse") in ("grass", "recreation_ground", "village_green") or f.tags.get("leisure") == "park":
            polys.append(f.geom)
    n = 0
    for g in polys:
        gg = [g] if g.geom_type == "Polygon" else [x for x in getattr(g, "geoms", []) if x.geom_type == "Polygon"]
        for poly in gg:
            if not poly.intersects(V.area) or poly.area < 60:
                continue
            poly = poly.intersection(V.area)
            if poly.is_empty or poly.geom_type not in ("Polygon", "MultiPolygon"):
                continue
            inner = poly.buffer(-1.6)
            if inner.is_empty:
                continue
            dens = 1 / 170.0 if poly.area > 4000 else 1 / 260.0
            tries = int(poly.area * dens * 3)
            x0, y0, x1, y1 = inner.bounds
            ip = prep(inner)
            placed = 0
            for _ in range(min(tries, 400)):
                x, y = rng.uniform(x0, x1), rng.uniform(y0, y1)
                if not ip.contains(Point(x, y)):
                    continue
                dc = V.coast.distance(Point(x, y))
                ctx = "water" if dc < 8 else ("coast" if dc < 30 else "park")
                sp = V.species_for({}, ctx)
                sz = V.size_for({}, ctx)
                if V.tree(sp, sz, x, y, {"s": 1.6, "m": 2.6, "l": 3.6}[sz]):
                    n += 1
                    placed += 1
                    if placed > dens * poly.area:
                        break
            # 縁取りの低木帯(つつじ/つげ/あじさい)と花壇
            ring = inner.exterior if inner.geom_type == "Polygon" else max(inner.geoms, key=lambda q: q.area).exterior
            s = rng.uniform(0, 8)
            kinds = ["veg_azalea_0_r8", "veg_azalea_1_r8", "veg_azalea_2_r8", "veg_tsuge_dome_r8", "veg_hydrangea_0_r75", "veg_hydrangea_1_r75", "veg_azalea_green_r8"]
            while s < ring.length and ring.length < 600:
                q = ring.interpolate(s)
                if V.occ.free(q.x, q.y, 0.8) and V.land.contains(q) and not V.cw.contains(q):
                    k = rng.choice(kinds[:3]) if rng.random() < 0.5 else rng.choice(kinds)
                    if V.put(k, q.x, q.y, None):
                        V.occ.add(q.x, q.y, 0.7)
                s += rng.uniform(1.4, 2.4)
            if poly.area > 300 and rng.random() < 0.5:
                x, y = rng.uniform(x0, x1), rng.uniform(y0, y1)
                if ip.contains(Point(x, y)) and V.occ.free(x, y, 1.3):
                    V.put(f"veg_flowerbed_{rng.randint(0, 2)}", x, y, rng.uniform(0, 3.14), jitter=False)
                    V.occ.add(x, y, 1.2)
    return n


def hedges_and_rows(V, X):
    """OSM barrier=hedge の線に沿って生垣を2m間隔で。natural=tree_row は一定間隔で並木。"""
    rng = V.rng
    nh = 0
    for f in X["hedges"]:
        g = f.geom.intersection(V.area)
        if g.is_empty:
            continue
        parts = [g] if g.geom_type == "LineString" else [x for x in getattr(g, "geoms", []) if x.geom_type == "LineString" and not x.is_empty]
        h = f.tags.get("height")
        try:
            hh = float(str(h).split()[0])
        except (TypeError, ValueError):
            hh = rng.choice([0.6, 1.2, 1.2, 1.8])
        nm = "tall" if hh > 1.5 else ("mid" if hh > 0.8 else "low")
        for ln in parts:
            n = max(1, int(round(ln.length / 2.0)))
            for i in range(n):
                a, b = ln.interpolate((i + 0.5) / n, normalized=True), ln.interpolate(min(1.0, (i + 0.5) / n + 0.01), normalized=True)
                ang = math.atan2(b.y - a.y, b.x - a.x)
                s = ln.length / n / 2.0
                if V.put(f"veg_hedge_{nm}_{rng.randint(0, 1)}", a.x, a.y, ang, scale=1.0):
                    V.out[-1].sx = s
                    nh += 1
    nr = 0
    for f in X["tree_rows"]:
        ln = f.geom.intersection(V.area)
        if ln.is_empty:
            continue
        parts = [ln] if ln.geom_type == "LineString" else [x for x in getattr(ln, "geoms", []) if x.geom_type == "LineString" and not x.is_empty]
        sp = V.species_for(f.tags, "street")
        for ln in parts:
            s = rng.uniform(0, 4)
            while s < ln.length:
                q = ln.interpolate(s)
                if V.tree(sp, "m", q.x, q.y, 1.8):
                    nr += 1
                s += rng.uniform(7, 10)
    return nh, nr


def wall_ivy(V, L, frac=0.03):
    """道路に面した建物の長い外壁の一部に壁面緑化(アイビー)"""
    rng = V.rng
    n = 0
    for f in L["buildings"]:
        g = f.geom
        if not V.area.contains(g.centroid) or g.geom_type != "Polygon" or g.area < 120 or rng.random() > frac:
            continue
        cs = list(g.exterior.coords)
        best = max(zip(cs, cs[1:]), key=lambda s: math.dist(*s))
        (x0, y0), (x1, y1) = best
        Ld = math.dist((x0, y0), (x1, y1))
        if Ld < 5:
            continue
        tx, ty = (x1 - x0) / Ld, (y1 - y0) / Ld
        nx, ny = ty, -tx
        mx, my = (x0 + x1) / 2, (y0 + y1) / 2
        if g.contains(Point(mx + nx * 0.2, my + ny * 0.2)):
            nx, ny = -nx, -ny
        nm = rng.choice(["veg_ivy_wall_2x3", "veg_ivy_wall_2x2", "veg_ivy_wall_1x2"])
        yaw = math.atan2(ny, nx) - math.pi / 2          # モジュールの+y(葉の張出し側)を外向きへ
        if V.put(nm, mx, my, yaw, jitter=False, scale=1.0):
            n += 1
    return n


def build_vegetation(L, X, world, edges, info, cfg, seed=3, avoid=None):
    """植栽Instのリストと件数内訳。avoid=ファニチャのInst(信号柱/街灯等)を渡すと干渉を避ける。"""
    V = Veg(L, X, world, edges, info, cfg, seed, avoid)
    stats = {}
    stats["osm_trees"] = osm_trees(V, X)
    stats["street_trees"] = street_trees(V, X)
    stats["park_trees"] = park_vegetation(V, L, X)
    stats["hedges"], stats["tree_rows"] = hedges_and_rows(V, X)
    stats["wall_ivy"] = wall_ivy(V, L)
    stats["total_inst"] = len(V.out)
    build_vegetation.stats = stats
    return V.out
