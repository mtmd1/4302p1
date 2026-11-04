"""Intro: three everyday blurs, each made from sands.jpg with blur.py.

    uv run render intro_montage

One tile per cue, each naming its effect, holding until "Today I will explain".
"""

from functools import lru_cache

from PIL import Image

from style import *

import blur
from components import photo_still
from sample import photo

# The same part of the photo in every tile, in source pixels, so the viewer sees
# one scene three ways: the town, its lamps, and the beach's reflection.
CROP = (690, 480, 1730, 1040)  # Left, top, right, bottom
TILE_WIDTH = (FILL_WIDTH - 2 * SPACE_2) / 3
SUPERSAMPLE = 2  # Tile pixels per screen pixel; manim's bilinear aliases beyond this

# Frosted glass: a sheet over the buildings, with the tower rising out of it
PANEL = (950, 610, 1470, 930)  # Left, top, right, bottom
PANEL_CORNER = 28  # Source pixels
PANEL_LEVELS = 4  # Dual Kawase levels behind the glass
PANEL_TINT = 0.16  # Fraction of white mixed into the blur
PANEL_EDGE = 0.35  # Fraction of white on the rim
PANEL_RIM = 3.0  # Rim thickness, source pixels

# Bloom: everything over the threshold is blurred at growing sizes and added back
BLOOM_THRESHOLD = 0.75  # Linear luminance
BLOOM_LEVELS = (3, 4, 5, 6)
BLOOM_GAIN = 1.2

# Depth of field: an ellipse of focus on the buildings, blur outside it
FOCUS_CENTRE = (1210, 690)
FOCUS_RADII = (380, 210)
FOCUS_FEATHER = 0.35  # Fraction of the radius over which focus falls away
DEPTH_LEVELS = 4


def _smoothstep(edge0: float, edge1: float, x: np.ndarray) -> np.ndarray:
    t = np.clip((x - edge0) / (edge1 - edge0), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def _rounded_box_distance(height: int, width: int, box, corner: float) -> np.ndarray:
    """Signed distance in pixels to a rounded rectangle, negative inside."""
    left, top, right, bottom = box
    ys, xs = np.mgrid[0:height, 0:width] + 0.5
    qx = np.abs(xs - (left + right) / 2) - (right - left) / 2 + corner
    qy = np.abs(ys - (top + bottom) / 2) - (bottom - top) / 2 + corner
    return np.hypot(np.maximum(qx, 0), np.maximum(qy, 0)) + np.minimum(np.maximum(qx, qy), 0) - corner


def frosted(image: np.ndarray) -> np.ndarray:
    rgb = image[..., :3]
    behind = blur.dual_kawase(image, levels=PANEL_LEVELS).image[..., :3]
    glass = behind + (1 - behind) * PANEL_TINT
    distance = _rounded_box_distance(*rgb.shape[:2], PANEL, PANEL_CORNER)
    inside = np.clip(0.5 - distance, 0.0, 1.0)[..., None]
    rim = (np.clip(0.5 - np.abs(distance + PANEL_RIM / 2) + PANEL_RIM / 2, 0.0, 1.0) * PANEL_EDGE)[..., None]
    glass = glass + (1 - glass) * rim
    return rgb * (1 - inside) + glass * inside


def bloom(image: np.ndarray) -> np.ndarray:
    linear = blur.srgb_to_linear(image[..., :3])
    luminance = linear @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
    bright = linear * _smoothstep(BLOOM_THRESHOLD * 0.8, BLOOM_THRESHOLD, luminance)[..., None]
    glow = sum(blur.dual_kawase(bright, levels=n, linear=False).image[..., :3] for n in BLOOM_LEVELS)
    return blur.linear_to_srgb(linear + glow * BLOOM_GAIN)


def depth_of_field(image: np.ndarray) -> np.ndarray:
    rgb = image[..., :3]
    soft = blur.dual_kawase(image, levels=DEPTH_LEVELS).image[..., :3]
    ys, xs = np.mgrid[0 : rgb.shape[0], 0 : rgb.shape[1]] + 0.5
    reach = np.hypot((xs - FOCUS_CENTRE[0]) / FOCUS_RADII[0], (ys - FOCUS_CENTRE[1]) / FOCUS_RADII[1])
    focus = (1 - _smoothstep(1 - FOCUS_FEATHER, 1 + FOCUS_FEATHER, reach))[..., None]
    return rgb * focus + soft * (1 - focus)


def _crop(image: np.ndarray) -> np.ndarray:
    """The shared crop, shrunk ahead of time so the tile stays clean at any quality."""
    left, top, right, bottom = CROP
    pixels = blur.to_uint8(image[top:bottom, left:right])
    width = round(TILE_WIDTH * config.pixel_width / config.frame_width * SUPERSAMPLE)
    height = round(width * (bottom - top) / (right - left))
    return np.asarray(Image.fromarray(pixels).resize((width, height), Image.LANCZOS))


@lru_cache(maxsize=None)
def effects() -> dict[str, np.ndarray]:
    """Label to finished tile image, in the order they appear."""
    image = photo()
    return {
        "frosted glass": _crop(frosted(image)),
        "bloom": _crop(bloom(image)),
        "depth of field": _crop(depth_of_field(image)),
    }


def tile(pixels: np.ndarray, name: str) -> Group:
    still = photo_still(pixels, width=TILE_WIDTH)
    outline = SurroundingRectangle(still, buff=0, color=MUTED, stroke_width=STROKE_THIN)
    label = Text(name, font_size=TEXT_BASE, color=TEXT).next_to(still, DOWN, buff=SPACE_2)
    return Group(still, outline, label)


class IntroMontage(ClipScene):
    def construct(self):
        tiles = Group(*(tile(pixels, name) for name, pixels in effects().items()))
        tiles.arrange(RIGHT, buff=SPACE_2, aligned_edge=UP).move_to(ORIGIN)

        cues = ("the frosted glass", "bloom around", "the background of a depth-of-field")
        for phrase, shown in zip(cues, tiles):
            self.cue(phrase)
            self.play(FadeIn(shown), run_time=MOVE, rate_func=EASE)
        self.cue("Today I will explain")
