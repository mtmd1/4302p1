"""Zooming into an image down to its individual pixels.

Manim's Cairo camera perspective-transforms a whole ImageMobject every frame, so
zooming a 1920-pixel photo until 10 pixels fill the screen would mean
transforming an image some 300,000 pixels wide. PixelView instead redraws only
the visible pixels at screen resolution, nearest-neighbour, so zooming costs
the same at any depth.
"""

import math

import numpy as np
from manim import *

import blur


class PixelView(ImageMobject):
    """A window onto an image: a box on screen, centred on a focus point, some pixels across.

    Coordinates are in source pixels, continuous: pixel (i, j) covers
    [i, i + 1) x [j, j + 1), so its centre is (i + 0.5, j + 0.5). Rows grow
    downwards, as in the image. The box is centred on the origin.

    The box is a hard clip, so its outline holds still while the view zooms
    and pixels are cut wherever its edge falls. Give the final view a box that
    is a whole number of pixels, with the focus on pixel boundaries, and the
    clip lands exactly on cell edges once the zoom settles.
    """

    def __init__(self, image: np.ndarray, box: tuple[float, float], focus=None, across=None, **kwargs):
        self.source = blur.to_uint8(image)
        height, width = self.source.shape[:2]
        if self.source.shape[2] == 3:
            self.source = np.concatenate([self.source, np.full((height, width, 1), 255, np.uint8)], axis=2)
        self.box = np.array(box, float)
        self.focus = np.array(focus if focus is not None else (width / 2, height / 2), float)
        self.across = float(across or width)
        self._drawn = None
        super().__init__(self._draw(), **kwargs)
        self.set_resampling_algorithm(RESAMPLING_ALGORITHMS["nearest"])
        self.width = config.frame_width  # Drawn full-frame; transparent outside the box
        self.add_updater(lambda m: m.refresh())

    def set_view(self, focus, across, box=None):
        self.focus = np.array(focus, float)
        self.across = float(across)
        if box is not None:
            self.box = np.array(box, float)
        return self

    @property
    def unit(self) -> float:
        """Manim units per source pixel at the current zoom."""
        return self.box[0] / self.across

    @property
    def window(self) -> tuple[float, float, float, float]:
        """The box's left, right, top and bottom, in source coordinates."""
        half_w, half_h = self.box / self.unit / 2
        return self.focus[0] - half_w, self.focus[0] + half_w, self.focus[1] - half_h, self.focus[1] + half_h

    def to_point(self, x: float, y: float) -> np.ndarray:
        """The manim point showing source coordinate (x, y)."""
        return np.array([(x - self.focus[0]) * self.unit, (self.focus[1] - y) * self.unit, 0.0])

    def visible_pixels(self) -> tuple[range, range]:
        """Source columns and rows at least partly inside the box, clipped to the image."""
        height, width = self.source.shape[:2]
        left, right, top, bottom = self.window
        cols = range(max(0, math.floor(left)), min(width, math.ceil(right)))
        rows = range(max(0, math.floor(top)), min(height, math.ceil(bottom)))
        return cols, rows

    def refresh(self):
        if self._drawn != (*self.focus, self.across, *self.box):
            self.pixel_array = self._draw()

    def _draw(self) -> np.ndarray:
        self._drawn = (*self.focus, self.across, *self.box)
        out_w, out_h = config.pixel_width, config.pixel_height
        height, width = self.source.shape[:2]
        left, right, top, bottom = self.window

        # Each screen pixel's centre, in source coordinates
        per_screen_pixel = config.frame_width / out_w / self.unit
        sx = self.focus[0] + (np.arange(out_w) + 0.5 - out_w / 2) * per_screen_pixel
        sy = self.focus[1] + (np.arange(out_h) + 0.5 - out_h / 2) * per_screen_pixel
        xs, ys = np.floor(sx).astype(np.int64), np.floor(sy).astype(np.int64)

        # Clip to the box and the image; everything else is transparent
        shown_x = (sx >= left) & (sx < right) & (xs >= 0) & (xs < width)
        shown_y = (sy >= top) & (sy < bottom) & (ys >= 0) & (ys < height)

        out = self.source[np.clip(ys, 0, height - 1)][:, np.clip(xs, 0, width - 1)].copy()
        out[~shown_y] = 0
        out[:, ~shown_x] = 0
        return out


def zoom(view: PixelView, focus, across, box=None, **kwargs) -> Animation:
    """Zoom view to (focus, across), keeping the target steady as it comes to the middle.

    The zoom is even on a log scale, so each halving takes the same time. A new
    box, if given, is reached at the same pace.
    """
    start_focus, start_across, start_box = view.focus.copy(), view.across, view.box.copy()
    target = np.array(focus, float)
    end_box = np.array(box if box is not None else start_box, float)

    def update(mob, alpha):
        current = math.exp((1 - alpha) * math.log(start_across) + alpha * math.log(across))
        # Slide the target's on-screen position to the middle while zooming about it
        offset = (start_focus - target) * (current / start_across) * (1 - alpha)
        mob.set_view(target + offset, current, start_box + (end_box - start_box) * alpha)

    return UpdateFromAlphaFunc(view, update, **kwargs)


def grid_lines(view: PixelView, color, stroke_width, fade_from: float = 16, fade_to: float = 48) -> VGroup:
    """Pixel boundaries inside the box, fading in once pixels reach fade_from screen pixels.

    Clipped to the box like the pixels, so the outer edge appears only once the
    box sits on pixel boundaries.
    """
    size = view.unit * config.pixel_width / config.frame_width
    opacity = min(max((size - fade_from) / (fade_to - fade_from), 0.0), 1.0)
    if opacity == 0:
        return VGroup()
    height, width = view.source.shape[:2]
    left, right, top, bottom = view.window
    left, right, top, bottom = max(left, 0), min(right, width), max(top, 0), min(bottom, height)
    lines = [Line(view.to_point(x, top), view.to_point(x, bottom)) for x in range(math.ceil(left), math.floor(right) + 1)]
    lines += [Line(view.to_point(left, y), view.to_point(right, y)) for y in range(math.ceil(top), math.floor(bottom) + 1)]
    return VGroup(*lines).set_stroke(color, stroke_width, opacity)
