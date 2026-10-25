# -*- coding: utf-8 -*-
"""
通用 SVG 渲染器：把 analyze() 的结果画成黑金风格「八宅定盘图」。

配置示例见 examples/*.json。纯标准库，无第三方依赖。
"""
import math
from .data import GUA
from .core import (grid_regions, polygon_centroid, bearing_of,
                   palace_of_bearing, PALACE_BY_BEARING)

GOLD, GOLDL, GOLDD = "#d4af37", "#f6d365", "#8a6d1f"
BG = "#070a12"
TXT, MUTE = "#e8e4d8", "#8b93a7"
RED, GRN, BLU = "#ef4444", "#3ddc84", "#38bdf8"
LUCKY_SET = {"伏位", "生气", "延年", "天医"}


def esc(t):
    return str(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def txt(x, y, s, size=14, fill=TXT, anchor="middle", weight="700", ls=None, op=None):
    a = f' text-anchor="{anchor}"' if anchor else ""
    l = f' letter-spacing="{ls}"' if ls is not None else ""
    o = f' opacity="{op}"' if op is not None else ""
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" fill="{fill}" '
            f'font-family="\'Noto Sans SC\',\'PingFang SC\',\'Hiragino Sans GB\',\'Microsoft YaHei\',sans-serif" '
            f'font-weight="{weight}"{a}{l}{o}>{esc(s)}</text>')


def poly(pts, fill="none", stroke=None, sw=1, op=None, dash=None):
    p = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    s = f' stroke="{stroke}" stroke-width="{sw}"' if stroke else ""
    o = f' opacity="{op}"' if op is not None else ""
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return f'<polygon points="{p}" fill="{fill}"{s}{o}{d}/>'


def ln(x1, y1, x2, y2, stroke, sw=1, dash=None, op=None):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    o = f' opacity="{op}"' if op is not None else ""
    return (f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
            f'stroke="{stroke}" stroke-width="{sw}"{d}{o}/>')


def circ(cx, cy, r, fill="none", stroke=None, sw=1, op=None):
    s = f' stroke="{stroke}" stroke-width="{sw}"' if stroke else ""
    o = f' opacity="{op}"' if op is not None else ""
    return f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" fill="{fill}"{s}{o}/>'


def _fit(bbox, vp):
    """把 bbox 装进视口 vp=(x,y,w,h)，返回 (k, ox, oy)。"""
    minx, miny, maxx, maxy = bbox
    bw, bh = max(1e-6, maxx - minx), max(1e-6, maxy - miny)
    k = min(vp[2] / bw, vp[3] / bh)
    ox = vp[0] + (vp[2] - bw * k) / 2 - minx * k
    oy = vp[1] + (vp[3] - bh * k) / 2 - miny * k
    return k, ox, oy


def render_svg(cfg, report=None, width=1600, height=1100):
    """cfg: 见 examples/*.json。返回 SVG 字符串。"""
    from .core import analyze
    rep = report or analyze(cfg)
    site = cfg["site"]
    center = tuple(site["center_px"])
    theta0 = float(site["north_deg"])
    bounds = site.get("bounds_px")
    rooms = cfg["rooms"]
    home = int(site["home_palace"])
    ming = site.get("minggu", [])
    meta = cfg.get("meta", {})

    # ---------------- 视口 ----------------
    panel_w = 400
    vp = (56, 116, width - panel_w - 96, height - 176)
    xs = [p[0] for r in rooms for p in r["poly"]]
    ys = [p[1] for r in rooms for p in r["poly"]]
    if bounds:
        xs += [bounds[0], bounds[2]]
        ys += [bounds[1], bounds[3]]
    pad = 34
    k, ox, oy = _fit((min(xs) - pad, min(ys) - pad, max(xs) + pad, max(ys) + pad), vp)

    def P(p):
        return (p[0] * k + ox, p[1] * k + oy)

    o = []
    o.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
             f'width="{width}" height="{height}">')
    o.append(f'''<defs>
 <linearGradient id="gold" x1="0" y1="0" x2="1" y2="1">
  <stop offset="0%" stop-color="#f6d365"/><stop offset="50%" stop-color="#d4af37"/><stop offset="100%" stop-color="#8a6d1f"/></linearGradient>
 <radialGradient id="bgGlow" cx="42%" cy="32%" r="80%">
  <stop offset="0%" stop-color="#111a2e"/><stop offset="100%" stop-color="{BG}"/></radialGradient>
 <pattern id="hatch" width="120" height="120" patternTransform="rotate(45)" patternUnits="userSpaceOnUse">
  <line x1="0" y1="0" x2="0" y2="120" stroke="#d4af37" stroke-width="2" opacity="0.05"/></pattern>
</defs>''')
    o.append(f'<rect width="{width}" height="{height}" fill="url(#bgGlow)"/>')
    o.append(f'<rect width="{width}" height="{height}" fill="url(#hatch)"/>')

    o.append(txt(56, 50, meta.get("title", "八宅定盘图"), 29, GOLDL, "start", "800", ls=2))
    o.append(txt(56, 80, meta.get("subtitle", ""), 14.5, MUTE, "start", "500"))
    o.append(txt(width - 56, 50, meta.get("stamp", ""), 13.5, GOLDD, "end", "600"))
    o.append(ln(56, 98, width - 56, 98, GOLDD, 1.2, op=0.45))

    # ---------------- 房间 ----------------
    o.append('<g id="layer-rooms">')
    for r in rooms:
        pts = [P(p) for p in r["poly"]]
        o.append(poly(pts, fill=r.get("fill", "#10141c"), stroke=GOLDD, sw=2.0))
    o.append('</g>')

    # ---------------- 八分法（米字格） ----------------
    o.append('<g id="layer-sectors">')
    home_tbl = rep["home_stars"]
    regions = grid_regions(center, tuple(bounds), theta0) if bounds else []
    for reg in regions:
        pts = [P(p) for p in reg["poly"]]
        star = home_tbl[reg["palace"]]
        good = star in LUCKY_SET
        o.append(poly(pts, fill=(GOLD if good else RED), stroke=GOLDD, sw=1.1,
                      op=0.16 if good else 0.13))
    o.append('</g>')

    # 立极矩形
    if bounds:
        bp = [P((bounds[0], bounds[1])), P((bounds[2], bounds[1])),
              P((bounds[2], bounds[3])), P((bounds[0], bounds[3]))]
        o.append(poly(bp, fill="none", stroke=GOLD, sw=1.4, dash="10 6", op=0.75))

    # 八宫卦名：贴在外墙外侧（沿平分线方向）
    for reg in regions:
        star = home_tbl[reg["palace"]]
        good = star in LUCKY_SET
        c = P(center)
        bis = math.radians(reg["bisector"] - theta0)
        # 沿平分线推到立极矩形边界外侧（射线-矩形求交）
        dx, dy = math.sin(bis), -math.cos(bis)
        tmax = 0.0
        for (ax, ay), (bx2, by2) in zip(bp, bp[1:] + bp[:1]):
            ex, ey = bx2 - ax, by2 - ay
            den = dx * ey - dy * ex
            if abs(den) < 1e-9:
                continue
            t = ((ax - c[0]) * ey - (ay - c[1]) * ex) / den
            u = ((ax - c[0]) * dy - (ay - c[1]) * dx) / den
            if -1e-9 <= u <= 1 + 1e-9 and t > 0:
                tmax = max(tmax, t)
        if tmax <= 0:
            tmax = max(math.hypot(b[0] - c[0], b[1] - c[1]) for b in bp)
        R = tmax + 22
        lx = c[0] + R * dx
        ly = c[1] + R * dy
        o.append(circ(lx, ly, 17, fill="#0a0e18", stroke=(GOLD if good else RED), sw=1.5))
        o.append(txt(lx, ly + 6, GUA[reg["palace"]]["name"], 17, (GOLDL if good else "#f08a80")))
        o.append(txt(lx, ly + 32, f'{GUA[reg["palace"]]["dir"]} {star}', 11,
                     (GRN if good else RED)))

    # ---------------- 房间标注 ----------------
    o.append('<g id="layer-labels">')
    for r, ri in zip(rooms, rep["rooms"]):
        c = polygon_centroid(r["poly"])
        cp = P(c)
        cp = (min(max(cp[0], vp[0] + 62), vp[0] + vp[2] - 62),
              min(max(cp[1], vp[1] + 52), vp[1] + vp[3] - 40))
        good = ri["home_lucky"]
        o.append(txt(cp[0], cp[1] - 26, f'{r.get("name","")}'
                     + (f' {r["area"]}' if r.get("area") else ""), 18, GOLDL))
        o.append(txt(cp[0], cp[1] - 6, f'{ri["palace_name"]} · {ri["direction"]}', 14, MUTE))
        o.append(txt(cp[0], cp[1] + 13, f'宅卦 {ri["home_star"]} {"✅" if good else "❌"}', 14,
                     (GRN if good else RED)))
        dy = 32
        for m in ming:
            st = ri.get(f'ming_{m["name"]}')
            if st is None:
                continue
            ok = ri.get(f'ming_lucky_{m["name"]}')
            o.append(txt(cp[0], cp[1] + dy, f'{m["name"]} {st} {"✅" if ok else "❌"}', 13,
                         (GRN if ok else RED)))
            dy += 17
    o.append('</g>')

    # ---------------- 立极中心 / 坐向轴 ----------------
    o.append('<g id="layer-axis">')
    c = P(center)
    o.append(circ(c[0], c[1], 6, fill=GOLDL))
    o.append(circ(c[0], c[1], 11, fill="none", stroke=GOLDL, sw=1, op=0.5))
    for r in rooms:
        if r.get("zuo") or r.get("xiang"):
            cp = P(polygon_centroid(r["poly"]))
            o.append(ln(c[0], c[1], cp[0], cp[1], GOLD, 1.3, dash="6 5", op=0.8))
            o.append(txt((c[0] + cp[0]) / 2, (c[1] + cp[1]) / 2 - 6,
                         "坐" if r.get("zuo") else "向", 13, GOLDL))
    o.append('</g>')

    # ---------------- 右栏 ----------------
    px = width - panel_w - 32
    o.append('<g id="layer-panel">')
    o.append(f'<rect x="{px:.0f}" y="116" width="{panel_w}" height="{height-176}" rx="10" '
             f'fill="#0a0e18" stroke="{GOLDD}" stroke-width="1.2"/>')
    # 面板顶部：罗盘
    cr_x, cr_y, cr_r = px + panel_w / 2, 196, 70
    o.append(circ(cr_x, cr_y, cr_r, fill="#0a0e18", stroke=GOLD, sw=1.6))
    o.append(circ(cr_x, cr_y, cr_r - 9, fill="none", stroke=GOLDD, sw=0.8, op=0.7))
    for k8 in range(8):
        ang = math.radians(theta0 + 45 * k8 - 90)
        lx = cr_x + cr_r * math.cos(ang)
        ly = cr_y + cr_r * math.sin(ang)
        o.append(txt(lx, ly + 5, GUA[PALACE_BY_BEARING[k8]]["name"], 15, GOLDL))
    for k24 in range(24):
        ang = math.radians(theta0 + 15 * k24 - 90)
        lx = cr_x + (cr_r - 5) * math.cos(ang)
        ly = cr_y + (cr_r - 5) * math.sin(ang)
        o.append(txt(lx, ly + 3, "·", 9, GOLDD))
    ang = math.radians(theta0 - 90)
    tipx = cr_x + (cr_r + 17) * math.cos(ang)
    tipy = cr_y + (cr_r + 17) * math.sin(ang)
    bx = cr_x + cr_r * 0.45 * math.cos(ang)
    by = cr_y + cr_r * 0.45 * math.sin(ang)
    o.append(f'<path d="M{tipx:.1f},{tipy:.1f} L{bx-5:.1f},{by-3:.1f} L{bx+5:.1f},{by+3:.1f} Z" fill="{BLU}"/>')
    o.append(txt(cr_x, cr_y + 4, "立极", 12, MUTE))
    o.append(txt(cr_x, cr_y + cr_r + 30,
                 f'正上方真方位 {theta0:.0f}°　（拖动可调）', 12, MUTE))

    y = 336
    o.append(txt(px + 18, y, "一、八宫星曜（宅卦口径）", 17, GOLDL, "start", "800"))
    y += 24
    order = [1, 2, 3, 4, 6, 7, 8, 9]
    for i, p in enumerate(order):
        col = i % 2
        row = i // 2
        cx = px + 18 + col * (panel_w - 36) / 2
        cy = y + row * 42
        st = home_tbl[p]
        good = st in LUCKY_SET
        o.append(txt(cx, cy, f'{GUA[p]["palace"]} · {GUA[p]["dir"]}', 12.5, MUTE, "start", "500"))
        o.append(txt(cx, cy + 17, st, 15, (GRN if good else RED), "start", "700"))
    y += 4 * 42 + 20
    o.append(txt(px + 18, y, "二、房间 × 命卦", 17, GOLDL, "start", "800"))
    y += 10
    # 表头
    usable = panel_w - 40
    name_w = usable * 0.34
    colx = [px + 18]
    cw = (usable * 0.66) / max(1, len(ming))
    for j in range(len(ming)):
        colx.append(colx[0] + usable * 0.34 + j * cw)
    o.append(txt(colx[0], y + 16, "房间 / 宫位", 12, MUTE, "start", "500"))
    for j, m in enumerate(ming):
        o.append(txt(colx[j + 1] + 6, y + 16, m["name"], 12, MUTE, "start", "500"))
    y += 26
    for ri in rep["rooms"]:
        o.append(txt(colx[0], y, f'{ri["name"]} {ri["palace_name"]}', 12.5, TXT, "start", "500"))
        for j, m in enumerate(ming):
            st = ri.get(f'ming_{m["name"]}')
            ok = ri.get(f'ming_lucky_{m["name"]}')
            if st is None:
                continue
            o.append(txt(colx[j + 1] + 6, y, f'{st}{"✅" if ok else "❌"}', 12,
                         (GRN if ok else RED), "start", "500"))
        y += 20
        if y > height - 130:
            break
    o.append('</g>')

    o.append(txt(56, height - 26,
                 meta.get("footer", "八宅与五行属传统堪舆经验体系，非科学定论；仅作居家布局参考。"),
                 12, MUTE, "start", "500"))
    o.append("</svg>")
    return "\n".join(o)
