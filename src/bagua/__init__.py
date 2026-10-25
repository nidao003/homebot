# -*- coding: utf-8 -*-
"""八宅工具包：立极 · 八分法 · 星曜 · 渲染。"""
from .data import (GUA, BAZHAI_STARS, LUCKY_STARS, EAST_FOUR, WEST_FOUR,
                   SHAN_TO_GUA, SHAN_24, gua_of_shan, star_of, stars_of, is_lucky)
from .core import (analyze, assign_rooms, bearing_of, polygon_area, polygon_centroid,
                   clip_halfplane, palace_of_bearing, PALACE_BY_BEARING)

__all__ = [
    "GUA", "BAZHAI_STARS", "LUCKY_STARS", "EAST_FOUR", "WEST_FOUR",
    "SHAN_TO_GUA", "SHAN_24", "gua_of_shan", "star_of", "stars_of", "is_lucky",
    "analyze", "assign_rooms", "bearing_of", "polygon_area", "polygon_centroid",
    "clip_halfplane", "palace_of_bearing", "PALACE_BY_BEARING",
]
__version__ = "0.1.0"
