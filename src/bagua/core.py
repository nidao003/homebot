# -*- coding: utf-8 -*-
"""
八宅核心算法：立极 → 八分法 → 房间归宫 → 星曜 → 报告。

术语
----
立极：确定建筑（主结构）中心太极点，以中心向八个正方位引射线，把平面分成九区。
八分法：八个方向区各 45°，分别对应 坎(正北) 艮(东北) 震(正东) 巽(东南)
        离(正南) 坤(西南) 兑(正西) 乾(西北)。
归宫：房间按"与各方向区的重叠面积最大"归入一宫（比质心法稳健，边界房不受影响）。

★ 传统堪舆经验体系，非科学定论。
"""
import math

from .data import (GUA, PALACE_ORDER, BAZHAI_STARS, LUCKY_STARS, EAST_FOUR,
                   WEST_FOUR, SHAN_TO_GUA)

STAR_ORDER = ["伏位", "生气", "延年", "天医", "祸害", "五鬼", "六煞", "绝命"]
LUCKY = set(LUCKY_STARS)

# 方向区 -> 宫位（按真方位角 45° 递增）
#   0-45 艮 / 45-90 震 / 90-135 巽 / 135-180 离
#   180-225 坤 / 225-270 兑 / 270-315 乾 / 315-360 坎
PALACE_BY_BEARING = [8, 3, 4, 9, 2, 7, 6, 1]

DIR_NAME = {8: "东北", 3: "正东", 4: "东南", 9: "正南",
            2: "西南", 7: "正西", 6: "西北", 1: "正北"}

# 房间跨宫判定阈值：单一方向区占比低于此值即视为跨宫，改用重心定宫
SPLIT_THRESHOLD = 0.45


# ----------------------------------------------------------------- 基础几何
def polygon_area(poly):
    """多边形有向面积（鞋带公式，图像坐标系 y 向下时取绝对值）。"""
    if len(poly) < 3:
        return 0.0
    s = 0.0
    for i in range(len(poly)):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % len(poly)]
        s += x1 * y2 - x2 * y1
    return abs(s) / 2.0


def polygon_centroid(poly):
    a = polygon_area(poly)
    if a == 0:
        xs = [p[0] for p in poly]
        ys = [p[1] for p in poly]
        return (sum(xs) / len(xs), sum(ys) / len(ys))
    cx = cy = 0.0
    for i in range(len(poly)):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % len(poly)]
        cross = x1 * y2 - x2 * y1
        cx += (x1 + x2) * cross
        cy += (y1 + y2) * cross
    return (cx / (6 * a), cy / (6 * a))


def signed_area(poly):
    if len(poly) < 3:
        return 0.0
    s = 0.0
    for i in range(len(poly)):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % len(poly)]
        s += x1 * y2 - x2 * y1
    return s / 2.0


def clip_halfplane(poly, origin, normal):
    """Sutherland–Hodgman：保留 dot(normal, p-origin) >= 0 的一侧。"""
    if not poly:
        return []
    out = []
    n = len(poly)
    for i in range(n):
        cur = poly[i]
        nxt = poly[(i + 1) % n]
        dc = (cur[0] - origin[0]) * normal[0] + (cur[1] - origin[1]) * normal[1]
        dn = (nxt[0] - origin[0]) * normal[0] + (nxt[1] - origin[1]) * normal[1]
        if dc >= 0:
            out.append(cur)
        if (dc > 0 and dn < 0) or (dc < 0 and dn > 0):
            t = dc / (dc - dn)
            out.append((cur[0] + t * (nxt[0] - cur[0]), cur[1] + t * (nxt[1] - cur[1])))
    return out


def clip_convex(subject, clip_poly):
    """Sutherland–Hodgman：把 subject 多边形裁剪到凸多边形 clip_poly 内。"""
    if not subject or len(clip_poly) < 3:
        return []
    sign = 1.0 if signed_area(clip_poly) >= 0 else -1.0
    out = list(subject)
    m = len(clip_poly)
    for i in range(m):
        a = clip_poly[i]
        b = clip_poly[(i + 1) % m]
        ex, ey = b[0] - a[0], b[1] - a[1]

        def side(p):
            return sign * (ex * (p[1] - a[1]) - ey * (p[0] - a[0]))

        new = []
        n = len(out)
        for j in range(n):
            cur = out[j]
            nxt = out[(j + 1) % n]
            dc = side(cur)
            dn = side(nxt)
            if dc >= 0:
                new.append(cur)
            if (dc > 0 and dn < 0) or (dc < 0 and dn > 0):
                t = dc / (dc - dn)
                new.append((cur[0] + t * (nxt[0] - cur[0]), cur[1] + t * (nxt[1] - cur[1])))
        out = new
        if not out:
            return []
    return out


def bearing_of(point, center, theta0_deg):
    """图像坐标 -> 真方位角。theta0_deg = 图像"正上方"对应的真方位角(度)。"""
    dx = point[0] - center[0]
    dy = point[1] - center[1]
    if dx == 0 and dy == 0:
        return theta0_deg % 360.0
    # 图像 y 向下：正上方 ψ=0，向右为 ψ=90
    psi = math.degrees(math.atan2(dx, -dy))
    return (theta0_deg + psi) % 360.0


def palace_of_bearing(b):
    return PALACE_BY_BEARING[int((b % 360) // 45) % 8]


# ----------------------------------------------------------------- 八分法
def _vec(center, bearing, R=1e6):
    """真方位角 -> 图像坐标点（图像 y 向下）。"""
    a = math.radians(bearing)
    return (center[0] + R * math.sin(a), center[1] - R * math.cos(a))


def wedge_polygon(center, theta0_deg, k):
    """第 k 个方向区（45° 扇形）的凸多边形：中心 + 两条射线上的远点。"""
    b0 = theta0_deg + 45 * k
    return [center, _vec(center, b0), _vec(center, b0 + 45)]


def sector_bounds(center, theta0_deg, k):
    """返回 (射线k的方向向量, 射线k+1的方向向量)，单位向量（图像坐标）。"""
    out = []
    for j in (k, k + 1):
        ang = math.radians(theta0_deg + 45 * j - theta0_deg)  # 相对图像上方向的角度
        out.append((math.sin(ang), -math.cos(ang)))
    return out


def _norm(b):
    return b % 360.0


def _bisector(b0, b1):
    """两条射线（真方位角）的角平分线方位（取 45° 内的小角）。"""
    d = _norm(b1 - b0)
    if d > 180:
        d -= 360
    return _norm(b0 + d / 2.0)


def grid_regions(center, bounds, theta0_deg):
    """
    米字格八分法（经典法）：以立极中心为太极点，连接中心与立极矩形的
    四角、四边中点，得到 8 个方向区；每个区含一角 + 相邻半条边。

    bounds = (x0, y0, x1, y1)  立极矩形（主结构外接矩形）
    theta0_deg = 图像"正上方"对应的真实方位角

    返回 [{"poly": 三顶点, "palace": 宫位, "bisector": 平分线方位}, ...]
    """
    x0, y0, x1, y1 = bounds
    A = (x0, y0)          # 左上
    B = (x1, y0)          # 右上
    C = (x1, y1)          # 右下
    D = (x0, y1)          # 左下
    N = ((x0 + x1) / 2, y0)   # 上边中
    E = (x1, (y0 + y1) / 2)   # 右边中
    S = ((x0 + x1) / 2, y1)   # 下边中
    W = (x0, (y0 + y1) / 2)   # 左边中
    tris = [(W, A), (A, N), (N, B), (B, E), (E, C), (C, S), (S, D), (D, W)]
    out = []
    for p1, p2 in tris:
        b1 = bearing_of(p1, center, theta0_deg)
        b2 = bearing_of(p2, center, theta0_deg)
        bis = _bisector(b1, b2)
        pal = palace_of_bearing(bis)
        out.append({"poly": [center, p1, p2], "palace": pal, "bisector": bis,
                    "name": GUA[pal]["palace"]})
    return out


def assign_rooms(rooms, center, theta0_deg, bounds=None, method="grid"):
    """
    房间归宫：按与 8 个方向区的重叠面积取最大。
    rooms: [{"id","name","poly":[[x,y],...]}, ...]
    method="grid"   米字格八分法（需 bounds，经典做法）
    method="wedge"  45° 方位扇形法（只需中心，方位为正南北时用）
    返回 {room_id: {"palace": 宫位, "area": 重叠面积, "share": 占比, "by": "overlap"|"centroid"}}
    """
    if method == "grid":
        if bounds is None:
            raise ValueError("method='grid' 需要 bounds=(x0,y0,x1,y1)")
        regions = [(r["palace"], r["poly"]) for r in grid_regions(center, bounds, theta0_deg)]
    else:
        regions = [(PALACE_BY_BEARING[k], wedge_polygon(center, theta0_deg, k))
                   for k in range(8)]

    res = {}
    for r in rooms:
        poly = r["poly"]
        room_area = polygon_area(poly) or 1.0
        scored = []
        for pal, wpoly in regions:
            a = polygon_area(clip_convex(poly, wpoly))
            scored.append((a, pal))
        scored.sort(reverse=True)
        top_area, top_pal = scored[0]
        share = top_area / room_area
        second = scored[1]
        if share < SPLIT_THRESHOLD:
            # 房间跨宫：以重心所在方向区定宫（并记录跨宫情况）
            c = polygon_centroid(poly)
            pal = palace_of_bearing(bearing_of(c, center, theta0_deg))
            by = "centroid"
        else:
            pal = top_pal
            by = "overlap"
        res[r["id"]] = {"palace": pal, "area": top_area, "share": share, "by": by,
                        "runner_up": second[1], "runner_up_share": second[0] / room_area,
                        "split": share < SPLIT_THRESHOLD}
    return res


# ----------------------------------------------------------------- 星曜
def star_table(伏位宫):
    """返回 {宫位: 星名}。"""
    return dict(BAZHAI_STARS[伏位宫])


def lucky(star):
    return star in LUCKY


def home_guā_from_shan(zuo_shan: str):
    """由坐山字取宅卦。"""
    return SHAN_TO_GUA[zuo_shan]


def analyze(cfg):
    """
    主入口。cfg 结构见 examples/*.json 与 README。
    返回一个纯 dict 的报告（可直接 JSON 序列化）。
    """
    site = cfg["site"]
    center = tuple(site["center_px"])
    theta0 = float(site["north_deg"])
    rooms = cfg["rooms"]
    home = int(site["home_palace"])
    door = int(site.get("door_palace") or 0)
    mings = site.get("minggu", [])

    bounds = site.get("bounds_px")
    method = site.get("method", "grid" if bounds else "wedge")
    assign = assign_rooms(rooms, center, theta0, bounds=tuple(bounds) if bounds else None,
                          method=method)
    home_tbl = star_table(home)
    door_tbl = star_table(door) if door else None
    ming_tbls = {m["name"]: star_table(int(m["palace"])) for m in mings}

    out_rooms = []
    for r in rooms:
        a = assign[r["id"]]
        pal = a["palace"]
        entry = {
            "id": r["id"],
            "name": r.get("name", r["id"]),
            "area": r.get("area", ""),
            "palace": pal,
            "palace_name": GUA[pal]["palace"],
            "direction": GUA[pal]["dir"],
            "wx": GUA[pal]["wx"],
            "home_star": home_tbl[pal],
            "home_lucky": lucky(home_tbl[pal]),
            "door_star": door_tbl[pal] if door_tbl else None,
            "assign_share": round(a["share"], 3),
            "assign_by": a["by"],
            "notes": r.get("notes", []),
        }
        for m in mings:
            st = ming_tbls[m["name"]][pal]
            entry[f"ming_{m['name']}"] = st
            entry[f"ming_lucky_{m['name']}"] = lucky(st)
        out_rooms.append(entry)

    return {
        "meta": cfg.get("meta", {}),
        "site": {
            "center_px": list(center),
            "north_deg": theta0,
            "bounds_px": list(bounds) if bounds else None,
            "method": method,
            "home_palace": home,
            "home_palace_name": GUA[home]["palace"],
            "door_palace": door or None,
            "minggu": mings,
        },
        "rooms": out_rooms,
        "home_stars": home_tbl,
        "door_stars": door_tbl,
        "palace_order": PALACE_ORDER,
    }
