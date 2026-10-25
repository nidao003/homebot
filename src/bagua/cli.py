# -*- coding: utf-8 -*-
"""
命令行工具。

用法：
  python3 -m bagua.cli render <config.json> [-o out.svg] [--png out.png]
  python3 -m bagua.cli stars            # 打印八宅星曜表
  python3 -m bagua.cli demo [-o demo.svg]  # 用内置示例生成
"""
import argparse
import json
import os
import sys

from .core import analyze
from .svg import render_svg


def cmd_stars(args):
    from .data import BAZHAI_STARS, GUA
    print("八宅星曜表（伏位宫 → 九宫星名）")
    for gua in [1, 2, 3, 4, 6, 7, 8, 9]:
        row = BAZHAI_STARS[gua]
        s = "  ".join(f'{GUA[p]["palace"]}:{row[p]}' for p in [1, 2, 3, 4, 6, 7, 8, 9])
        print(f'{GUA[gua]["palace"]} 伏位  {s}')


def cmd_render(args):
    cfg = json.load(open(args.config, encoding="utf-8"))
    rep = analyze(cfg)
    svg = render_svg(cfg, rep, width=args.width, height=args.height)
    out = args.out or (os.path.splitext(args.config)[0] + ".svg")
    open(out, "w", encoding="utf-8").write(svg)
    print("SVG ->", out, os.path.getsize(out), "bytes")
    if args.png:
        _svg_to_png(svg, args.png)
        print("PNG ->", args.png)
    if args.json:
        open(args.json, "w", encoding="utf-8").write(
            json.dumps(rep, ensure_ascii=False, indent=2))
        print("JSON ->", args.json)
    for r in rep["rooms"]:
        print(f'  {r["name"]:<8} {r["palace_name"]} {r["direction"]:<3} 宅卦{r["home_star"]}')


def cmd_demo(args):
    from . import data as _d
    demo = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__)))), "examples", "sample_house.json")
    cfg = json.load(open(demo, encoding="utf-8"))
    rep = analyze(cfg)
    svg = render_svg(cfg, rep, width=args.width, height=args.height)
    out = args.out or "demo.svg"
    open(out, "w", encoding="utf-8").write(svg)
    print("SVG ->", out, os.path.getsize(out), "bytes")


def _svg_to_png(svg, path, scale=2):
    """用 Chrome headless 把 SVG 转 PNG（无第三方依赖）。"""
    import subprocess
    import tempfile
    chrome = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    if not os.path.exists(chrome):
        print("! 未找到 Chrome，跳过 PNG", file=sys.stderr)
        return
    with tempfile.TemporaryDirectory() as td:
        sp = os.path.join(td, "t.svg")
        open(sp, "w", encoding="utf-8").write(svg)
        cmd = [chrome, "--headless", "--disable-gpu", "--hide-scrollbars",
               f"--screenshot={path}", "--window-size=1600,1100",
               "--force-device-scale-factor=%d" % scale, "file://" + sp]
        subprocess.run(cmd, capture_output=True, timeout=120)
    print("PNG ->", path)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="bagua", description="八宅定盘工具")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("render", help="由配置 JSON 生成 SVG")
    p.add_argument("config")
    p.add_argument("-o", "--out", dest="out")
    p.add_argument("--png")
    p.add_argument("--json")
    p.add_argument("--width", type=int, default=1600)
    p.add_argument("--height", type=int, default=1100)
    p.set_defaults(func=cmd_render)

    p = sub.add_parser("stars", help="打印星曜表")
    p.set_defaults(func=cmd_stars)

    p = sub.add_parser("demo", help="用示例配置生成")
    p.add_argument("-o", "--out", dest="out")
    p.add_argument("--width", type=int, default=1600)
    p.add_argument("--height", type=int, default=1100)
    p.set_defaults(func=cmd_demo)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    main()
