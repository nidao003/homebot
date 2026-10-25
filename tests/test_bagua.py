# -*- coding: utf-8 -*-
"""
八宅核心算法测试。

运行：
    PYTHONPATH=src python3 -m unittest discover -s tests -v
"""
import json
import os
import re
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from bagua import (GUA, BAZHAI_STARS, LUCKY_STARS, EAST_FOUR, WEST_FOUR,  # noqa: E402
                   SHAN_TO_GUA, SHAN_24, gua_of_shan, star_of, is_lucky,
                   analyze, assign_rooms, bearing_of, palace_of_bearing,
                   polygon_area, polygon_centroid, clip_halfplane,
                   PALACE_BY_BEARING)
from bagua.core import grid_regions, SPLIT_THRESHOLD  # noqa: E402

NINE = [1, 2, 3, 4, 6, 7, 8, 9]
ALL_STARS = ["伏位", "生气", "延年", "天医", "祸害", "五鬼", "六煞", "绝命"]


class TestStarTable(unittest.TestCase):
    """八宅星曜表 8×8 全量对账。"""

    def test_table_shape(self):
        self.assertEqual(set(BAZHAI_STARS.keys()), set(NINE))
        for fuwei, row in BAZHAI_STARS.items():
            self.assertEqual(set(row.keys()), set(NINE), f"伏位宫 {fuwei} 宫位不全")

    def test_each_row_has_8_distinct_stars(self):
        for fuwei, row in BAZHAI_STARS.items():
            stars = [row[p] for p in NINE]
            self.assertEqual(len(set(stars)), 8, f"伏位宫 {fuwei} 星名重复")
            self.assertEqual(sorted(stars), sorted(ALL_STARS), f"伏位宫 {fuwei} 星名集合错")

    def test_fuwei_star_is_at_own_palace(self):
        """伏位宫自己的位置必须是「伏位」。"""
        for fuwei, row in BAZHAI_STARS.items():
            self.assertEqual(row[fuwei], "伏位", f"伏位宫 {fuwei} 本宫不是伏位")

    def test_lucky_stars_always_present(self):
        """每行都必须恰好含 4 吉 4 凶。"""
        for fuwei, row in BAZHAI_STARS.items():
            lucky = [row[p] for p in NINE if row[p] in LUCKY_STARS]
            self.assertEqual(len(lucky), 4, f"伏位宫 {fuwei} 吉星数不是 4")
            self.assertEqual(sorted(lucky), sorted(LUCKY_STARS))

    def test_is_lucky(self):
        self.assertTrue(is_lucky("伏位"))
        self.assertTrue(is_lucky("生气"))
        self.assertFalse(is_lucky("绝命"))

    def test_star_of_helper(self):
        for fuwei in NINE:
            for p in NINE:
                self.assertEqual(star_of(fuwei, p), BAZHAI_STARS[fuwei][p])


class TestGuaData(unittest.TestCase):
    def test_nine_palaces(self):
        self.assertEqual(sorted(GUA.keys()), sorted(NINE))
        self.assertNotIn(5, GUA)

    def test_east_west_four_partition(self):
        self.assertEqual(sorted(EAST_FOUR + WEST_FOUR), sorted(NINE))
        self.assertEqual(set(EAST_FOUR) & set(WEST_FOUR), set())

    def test_shan_to_gua(self):
        self.assertEqual(len(SHAN_24), 24)
        self.assertEqual(len(SHAN_TO_GUA), 24)
        self.assertEqual(gua_of_shan("乾"), 6)
        self.assertEqual(gua_of_shan("巽"), 4)
        self.assertEqual(gua_of_shan("子"), 1)
        for s in SHAN_24:
            self.assertIn(gua_of_shan(s), NINE)

    def test_shan_to_gua_matches_gua_shan_field(self):
        """每个宫的 24 山字段应与 SHAN_TO_GUA 反查一致。"""
        for pal, g in GUA.items():
            for s in g["shan"]:
                self.assertEqual(SHAN_TO_GUA[s], pal, f"{g['palace']} 的山 {s} 映射不一致")


class TestGeometry(unittest.TestCase):
    def test_polygon_area(self):
        sq = [(0, 0), (10, 0), (10, 10), (0, 10)]
        self.assertAlmostEqual(polygon_area(sq), 100.0)
        self.assertAlmostEqual(polygon_area([(0, 0), (10, 0), (5, 8)]), 40.0)
        self.assertEqual(polygon_area([(0, 0), (1, 1)]), 0.0)

    def test_polygon_centroid_square(self):
        sq = [(0, 0), (10, 0), (10, 10), (0, 10)]
        cx, cy = polygon_centroid(sq)
        self.assertAlmostEqual(cx, 5.0)
        self.assertAlmostEqual(cy, 5.0)

    def test_polygon_centroid_degenerate(self):
        cx, cy = polygon_centroid([(0, 0), (2, 0), (4, 0)])
        self.assertAlmostEqual(cx, 2.0)

    def test_clip_halfplane(self):
        """保留 y <= 5 的一侧。"""
        sq = [(0, 0), (10, 0), (10, 10), (0, 10)]
        out = clip_halfplane(sq, (0, 5), (0, -1))
        self.assertAlmostEqual(polygon_area(out), 50.0)

    def test_clip_halfplane_outside(self):
        """整块在保留侧之外，裁剪结果为空。"""
        sq = [(0, 0), (10, 0), (10, 10), (0, 10)]
        out = clip_halfplane(sq, (0, 50), (0, 1))   # 保留 y >= 50
        self.assertEqual(out, [])


class TestBearing(unittest.TestCase):
    def test_palace_by_bearing_table(self):
        """0-45 艮 / 45-90 震 / 90-135 巽 / 135-180 离 / 180-225 坤 / 225-270 兑 / 270-315 乾 / 315-360 坎。"""
        expect = {0: 8, 44: 8, 45: 3, 89: 3, 90: 4, 134: 4, 135: 9, 179: 9,
                  180: 2, 224: 2, 225: 7, 269: 7, 270: 6, 314: 6, 315: 1, 359: 1}
        for b, pal in expect.items():
            self.assertEqual(palace_of_bearing(b), pal, f"方位角 {b}° 归宫错")
        self.assertEqual(PALACE_BY_BEARING, [8, 3, 4, 9, 2, 7, 6, 1])

    def test_bearing_of_north(self):
        """图像正上方 = 真实正北（theta0=0）。"""
        b = bearing_of((100, 0), (100, 100), 0)
        self.assertAlmostEqual(b, 0.0, places=6)

    def test_bearing_of_east(self):
        """图像正右方 = 真实正东（theta0=0）。"""
        b = bearing_of((200, 100), (100, 100), 0)
        self.assertAlmostEqual(b, 90.0, places=6)

    def test_bearing_of_south(self):
        b = bearing_of((100, 200), (100, 100), 0)
        self.assertAlmostEqual(b, 180.0, places=6)

    def test_bearing_of_west(self):
        b = bearing_of((0, 100), (100, 100), 0)
        self.assertAlmostEqual(b, 270.0, places=6)

    def test_bearing_theta0_shift(self):
        """theta0=45 时，图像正上方对应真实 45°（东北）。"""
        b = bearing_of((100, 0), (100, 100), 45)
        self.assertAlmostEqual(b, 45.0, places=6)

    def test_bearing_wraps(self):
        b = bearing_of((100, 0), (100, 100), 350)
        self.assertAlmostEqual(b, 350.0, places=6)


class TestGridRegions(unittest.TestCase):
    def test_eight_regions(self):
        regs = grid_regions((500, 500), (200, 200, 800, 800), 0)
        self.assertEqual(len(regs), 8)
        self.assertEqual(sorted(r["palace"] for r in regs), sorted(NINE))

    def test_region_contains_center(self):
        for r in grid_regions((500, 500), (200, 200, 800, 800), 0):
            self.assertEqual(r["poly"][0], (500, 500))

    def test_north_region_is_kan(self):
        """覆盖正北（315°-360°）的区应归坎一。"""
        regs = grid_regions((500, 500), (200, 200, 800, 800), 0)
        kan = [r for r in regs if r["palace"] == 1]
        self.assertEqual(len(kan), 1)
        b = kan[0]["bisector"]
        self.assertTrue(315.0 <= b < 360.0, f"坎一平分线应在 315-360，实际 {b}")

    def test_bisector_agrees_with_palace_of_bearing(self):
        """每个区的平分线方位必须落回它自己的宫位。"""
        for th in (0, 30, 45, 90, 137, 180, 225, 270, 315):
            for r in grid_regions((500, 500), (200, 200, 800, 800), th):
                self.assertEqual(palace_of_bearing(r["bisector"]), r["palace"],
                                 f"theta0={th} 宫位与平分线不自洽")

    def test_bisectors_evenly_spaced(self):
        """米字格 8 区的平分线等距分布，相邻差 45°。"""
        regs = grid_regions((500, 500), (200, 200, 800, 800), 0)
        bis = sorted(r["bisector"] % 360 for r in regs)
        for k, b in enumerate(bis):
            self.assertAlmostEqual(b, 22.5 + 45 * k, places=6)

    def test_rotate_90_shifts_palaces(self):
        """theta0 旋转 90°：米字格几何不动，但每个物理区的方位角 +90°，宫位标签随方位走。"""
        a = grid_regions((500, 500), (200, 200, 800, 800), 0)
        b = grid_regions((500, 500), (200, 200, 800, 800), 90)
        key = lambda r: tuple(sorted(tuple(p) for p in r["poly"]))
        bmap = {key(r): r for r in b}
        for r in a:
            k = key(r)
            self.assertIn(k, bmap, "米字格几何应保持不变")
            hit = bmap[k]
            target = (r["bisector"] + 90) % 360
            self.assertAlmostEqual(hit["bisector"] % 360, target, places=6)
            # 宫位由方位决定，故随旋转顺移两位
            self.assertEqual(hit["palace"], palace_of_bearing(target))
            self.assertNotEqual(hit["palace"], r["palace"])


class TestAssignRooms(unittest.TestCase):
    def setUp(self):
        self.rooms = [
            {"id": "kitchen", "name": "厨房", "poly": [(210, 210), (380, 210), (380, 300), (210, 300)]},
            {"id": "living", "name": "客厅", "poly": [(560, 210), (790, 210), (790, 330), (560, 330)]},
            {"id": "bed1", "name": "主卧", "poly": [(700, 340), (790, 340), (790, 560), (700, 560)]},
            {"id": "bed2", "name": "次卧", "poly": [(700, 600), (790, 600), (790, 790), (700, 790)]},
            {"id": "bath", "name": "卫生间", "poly": [(600, 700), (790, 700), (790, 790), (600, 790)]},
            {"id": "study", "name": "书房", "poly": [(210, 700), (400, 700), (400, 790), (210, 790)]},
            {"id": "balcony", "name": "阳台", "poly": [(120, 560), (200, 560), (200, 790), (120, 790)]},
            {"id": "entry", "name": "玄关", "poly": [(120, 210), (200, 210), (200, 420), (120, 420)]},
            {"id": "gate", "name": "大门", "poly": [(560, 200), (600, 200), (600, 210), (560, 210)]},
        ]

    def test_all_rooms_assigned(self):
        res = assign_rooms(self.rooms, (500, 500), 0, bounds=(200, 200, 800, 800))
        self.assertEqual(len(res), len(self.rooms))
        for rid, a in res.items():
            self.assertIn(a["palace"], NINE, f"{rid} 宫位非法")

    def test_share_and_by_fields(self):
        res = assign_rooms(self.rooms, (500, 500), 0, bounds=(200, 200, 800, 800))
        for rid, a in res.items():
            self.assertGreaterEqual(a["share"], 0.0)
            self.assertLessEqual(a["share"], 1.0000001)
            self.assertIn(a["by"], ("overlap", "centroid"))
            if a["by"] == "centroid":
                self.assertLess(a["share"], SPLIT_THRESHOLD)
                self.assertTrue(a["split"])
            else:
                self.assertGreaterEqual(a["share"], SPLIT_THRESHOLD)
                self.assertFalse(a["split"])

    def test_determinism(self):
        a = assign_rooms(self.rooms, (500, 500), 0, bounds=(200, 200, 800, 800))
        b = assign_rooms(self.rooms, (500, 500), 0, bounds=(200, 200, 800, 800))
        self.assertEqual(a, b)

    def test_rooms_outside_bounds_use_centroid(self):
        """落在立极框外的房间（阳台/玄关）应走质心兜底。"""
        res = assign_rooms(self.rooms, (500, 500), 0, bounds=(200, 200, 800, 800))
        self.assertEqual(res["balcony"]["by"], "centroid")
        self.assertEqual(res["entry"]["by"], "centroid")

    def test_grid_requires_bounds(self):
        with self.assertRaises(ValueError):
            assign_rooms(self.rooms, (500, 500), 0, bounds=None, method="grid")

    def test_wedge_method_works_without_bounds(self):
        res = assign_rooms(self.rooms, (500, 500), 0, bounds=None, method="wedge")
        self.assertEqual(len(res), len(self.rooms))
        for a in res.values():
            self.assertIn(a["palace"], NINE)


class TestAnalyze(unittest.TestCase):
    def setUp(self):
        self.cfg_path = os.path.join(ROOT, "examples", "sample_house.json")
        with open(self.cfg_path, encoding="utf-8") as f:
            self.cfg = json.load(f)

    def test_analyze_structure(self):
        rep = analyze(self.cfg)
        self.assertEqual(len(rep["rooms"]), len(self.cfg["rooms"]))
        self.assertEqual(rep["site"]["home_palace"], 6)
        self.assertEqual(rep["site"]["door_palace"], 8)
        self.assertEqual(len(rep["site"]["minggu"]), 3)

    def test_every_room_has_stars_for_all_three_systems(self):
        rep = analyze(self.cfg)
        for r in rep["rooms"]:
            self.assertIn(r["home_star"], ALL_STARS)
            self.assertIn(r["door_star"], ALL_STARS)
            for m in self.cfg["site"]["minggu"]:
                self.assertIn(r[f"ming_{m['name']}"], ALL_STARS)

    def test_report_is_json_serializable(self):
        rep = analyze(self.cfg)
        json.dumps(rep, ensure_ascii=False)

    def test_ming_fuwei_is_fuwei_star(self):
        """命卦伏位宫在本宫应得「伏位」星。"""
        rep = analyze(self.cfg)
        for m in self.cfg["site"]["minggu"]:
            pal = int(m["palace"])
            for r in rep["rooms"]:
                if r["palace"] == pal:
                    self.assertEqual(r[f"ming_{m['name']}"], "伏位")

    def test_privacy_no_personal_data(self):
        """示例数据不得含个人可识别信息（姓名 / 邮箱 / 内网 IP / 本机路径）。"""
        blob = json.dumps(self.cfg, ensure_ascii=False)
        for pat in (r"[\w.+-]+@[\w-]+\.[\w.]+",          # 邮箱
                    r"(?<![\d.])(?:10|192|172)\.(?:\d{1,3}\.){2}\d{1,3}(?![\d.])",  # 内网 IP
                    r"/Users/[A-Za-z]",                      # macOS 家目录绝对路径
                    r"(?i)openclaw|obsidian|knowledgebase"): # 私有工作区痕迹
            m = re.search(pat, blob)
            self.assertIsNone(m, f"示例数据泄漏：{m.group(0) if m else ''}")

    def test_privacy_room_names_are_generic(self):
        """示例房间名只能是通用词，不得含人名。"""
        allowed = {"\u53a8\u623f", "\u5ba2\u5385", "\u4e3b\u5367", "\u6b21\u5367",
                   "\u536b\u751f\u95f4", "\u4e66\u623f", "\u9633\u53f0",
                   "\u7384\u5173", "\u5927\u95e8", "\u9910\u5385", "\u5ba2\u5385"}
        for r in self.cfg["rooms"]:
            self.assertIn(r["name"], allowed, f"示例房间名不合规：{r['name']}")

    def test_privacy_minggu_names_are_placeholders(self):
        """示例命卦名用天干占位（甲乙丙丁…），不得含人名。"""
        heavenly = set("甲乙丙丁戊己庚辛壬癸")
        for m in self.cfg["site"]["minggu"]:
            self.assertTrue(m["name"] and all(ch in heavenly for ch in m["name"]),
                            f"示例命卦名不是天干占位符：{m['name']}")


class TestSvgRender(unittest.TestCase):
    def test_render_produces_valid_svg(self):
        from bagua.svg import render_svg
        cfg_path = os.path.join(ROOT, "examples", "sample_house.json")
        with open(cfg_path, encoding="utf-8") as f:
            cfg = json.load(f)
        rep = analyze(cfg)
        svg = render_svg(cfg, rep)
        self.assertTrue(svg.startswith("<svg") or "<svg" in svg[:400])
        self.assertIn("</svg>", svg)
        self.assertGreater(len(svg), 5000)
        for pat in (r"[\w.+-]+@[\w-]+\.[\w.]+", r"/Users/[A-Za-z]",
                    r"(?i)openclaw|obsidian|knowledgebase"):
            m = re.search(pat, svg)
            self.assertIsNone(m, f"SVG 泄漏：{m.group(0) if m else ''}")


class TestWebPage(unittest.TestCase):
    """网页版单文件：静态检查，不跑浏览器。"""

    def setUp(self):
        self.path = os.path.join(ROOT, "src", "web", "index.html")
        with open(self.path, encoding="utf-8") as f:
            self.html = f.read()

    def test_no_network_calls(self):
        """纯本地：不得出现 fetch / XMLHttpRequest / WebSocket / 外链脚本。"""
        for token in ("fetch(", "XMLHttpRequest", "WebSocket", "navigator.sendBeacon"):
            self.assertNotIn(token, self.html, f"网页版出现网络调用：{token}")

    def test_no_external_resources(self):
        for token in ("http://", "https://"):
            for line in self.html.splitlines():
                if token in line and "svg xmlns" not in line and "w3.org" not in line:
                    self.fail(f"网页版出现外链资源：{line.strip()[:100]}")

    def test_palace_table_matches_python(self):
        """JS 的 PAL_BY_BEARING 必须与 Python 端一致。"""
        self.assertIn("PAL_BY_BEARING = [8,3,4,9,2,7,6,1]", self.html)
        self.assertEqual(PALACE_BY_BEARING, [8, 3, 4, 9, 2, 7, 6, 1])

    def test_star_table_matches_python(self):
        for fuwei, row in BAZHAI_STARS.items():
            for p, star in row.items():
                self.assertIn(f'{p}:"{star}"', self.html, f"JS 缺星曜 {fuwei}->{p}:{star}")

    def test_no_personal_data(self):
        """网页版不得含个人可识别信息。"""
        for pat in (r"[\w.+-]+@[\w-]+\.[\w.]+",
                    r"(?<![\d.])(?:10|192|172)\.(?:\d{1,3}\.){2}\d{1,3}(?![\d.])",
                    r"/Users/[A-Za-z]",
                    r"(?i)openclaw|obsidian|knowledgebase"):
            m = re.search(pat, self.html)
            self.assertIsNone(m, f"网页版泄漏：{m.group(0) if m else ''}")

    def test_split_threshold_matches_python(self):
        self.assertIn(f"const SPLIT={SPLIT_THRESHOLD}", self.html)


if __name__ == "__main__":
    unittest.main(verbosity=2)
