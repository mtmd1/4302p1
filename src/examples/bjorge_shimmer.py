"""Bjorge 2: shrink and stretch brings the boxes back, and they crawl when the scene moves.

    uv run render bjorge_shimmer

The pan moves a crop of the photo under a fixed panel and blurs each position
for real, so the low-res grid stays put while the picture slides under it, as in
a game. Positions between whole pixels cross-fade two neighbouring results, which
keeps the motion the same at any frame rate without resampling the source.

panel() is also used by bjorge_dual, for the side-by-side with Dual Kawase.
"""

from functools import lru_cache

from style import *

import blur
from components import photo_still
from sample import photo

LEVELS = 4

# Each halving's time, by how much area it changes. Halving a side takes away 3/4
# of the area, then 3/4 of what's left, so each level changes a quarter as much as
# the one before; each gets half the time, so the speed of the image's edges stays
# level. Longest step sized so the shrink and stretch just fill their narration.
FIRST_STEP = 1.5


def step_time(level: int) -> float:
    """Seconds for the step between level and level + 1, where 0 is full size."""
    return max(QUICK, FIRST_STEP / 2**level)


# The close-up's crop, 16:9 to fill the frame: the town's windows and the bright lamp,
# which have the most detail for the low-res grid to catch. Whole multiples of 16,
# margin included, keep every level's size exact and its blocks on the photo's own.
CROP = (1024, 592, 512, 288)
MARGIN = 64  # Blurred but not shown, so the crop's edges never reach the panel

PAN_RATE = 16.0  # Source pixels per second. One 16-pixel block regroups every second
PAN_TIME = 2.6  # Between two and three regroupings
METHODS = {"naive": blur.downscale_upscale, "dual": blur.dual_kawase}


@lru_cache(maxsize=None)
def _source() -> np.ndarray:
    return photo()


@lru_cache(maxsize=None)
def _blurred(method: str, crop: tuple, position: int) -> np.ndarray:
    """One whole-pixel pan position, blurred, as uint8 RGBA."""
    x, y, w, h = crop
    x += position
    area = _source()[y - MARGIN : y + h + MARGIN, x - MARGIN : x + w + MARGIN]
    return blur.to_uint8(METHODS[method](area, levels=LEVELS).image[MARGIN:-MARGIN, MARGIN:-MARGIN])


def frame(method: str, crop: tuple, position: float) -> np.ndarray:
    whole = int(position)
    part = position - whole
    if part == 0:
        return _blurred(method, crop, whole)
    mix = (1 - part) * _blurred(method, crop, whole) + part * _blurred(method, crop, whole + 1)
    return (mix + 0.5).astype(np.uint8)


def panel(method: str, tracker: ValueTracker, width: float, crop: tuple = CROP, ink: ValueTracker | None = None) -> ImageMobject:
    """A crop panning with tracker. ink, if given, is its opacity: an animation of the
    panel itself would stop its updater, and the pan would freeze for the fade."""

    def draw(mob):
        pixels = frame(method, crop, tracker.get_value())
        if ink is not None:
            pixels = pixels.copy()
            pixels[..., 3] = round(ink.get_value() * 255)
        mob.pixel_array = pixels

    image = ImageMobject(frame(method, crop, 0.0)).set_resampling_algorithm(RESAMPLING_ALGORITHMS["bilinear"])
    image.width = width
    draw(image)
    image.add_updater(draw)
    return image


class BjorgeShimmer(ClipScene):
    def construct(self):
        source = _source()
        steps = blur.downscale_upscale(source, levels=LEVELS, steps=True).steps
        full = config.frame_width  # The problem, as large as it goes

        current = photo_still(source, full)
        self.add(current)
        self.cue("So let's shrink the image")

        # Each level fades in over the last as both change size together. Slowest where
        # the most area changes, at the top of the pyramid, on the way down and back up.
        size = full
        for i, step in enumerate(steps):
            shrinking = i < LEVELS
            level = i if shrinking else len(steps) - i - 1
            size = size / 2 if shrinking else size * 2
            next_image = photo_still(step, size)
            self.play(
                current.animate.set(width=size),
                FadeIn(next_image, scale=current.width / size),
                run_time=step_time(level),
                rate_func=EASE,
            )
            self.remove(current)
            current = next_image

        # Closer in as the boxes are named, ready to pan on "Worse". The zoom lands the
        # crop exactly where it sits in the whole picture, so nothing but scale changes.
        self.cue("boxy artefacts are")
        x, y, w, h = CROP
        height, width = source.shape[:2]
        zoom = width / w
        crop_centre = np.array([x + w / 2 - width / 2, height / 2 - y - h / 2, 0]) * full / width
        tracker = ValueTracker(0)
        close = panel("naive", tracker, full)
        self.play(
            FadeOut(current, scale=zoom, target_position=-zoom * crop_centre),
            FadeIn(close, scale=1 / zoom, target_position=crop_centre),
            run_time=MOVE,
            rate_func=EASE,
        )
        self.cue("Worse, when the scene moves")
        self.play(tracker.animate.set_value(PAN_RATE * PAN_TIME), run_time=PAN_TIME, rate_func=linear)
        self.cue("So as we shrink")
