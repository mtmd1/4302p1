"""Shared look for every clip: background, colours, fonts, heatmap, layout, scales.

Scenes subclass ClipScene instead of Scene to get the standard pauses at both
ends, which give DaVinci room to cut. For another scene type, mix Clip in
first: class Zoom(Clip, MovingCameraScene).

Use the scales below rather than literal sizes and timings, so clips made on
different days still match.

Motion: every frame is either state or change. State is something the viewer
reads (a grid of values, a finished blur); change gets them from one state to
the next. Keep each change clearly directed, so the eye knows where to look
before it moves: one thing travels, in one direction, eased at both ends.

But don't rush the change. Viewers tested on faster versions (durations cut by
40%, hard quartic easing) lost track of what had turned into what: the
transformation is the explanation, so they need to watch it happen. The
durations and EASE below are the tested compromise, slightly quicker than
manim's defaults. Hold states with self.wait(), but never buy hold time by
shortening a change below these.
"""

from pathlib import Path

import manimpango
from manim import *

# Near-black, slightly cold. Clips render transparent, so this is the solid
# colour to put under them in DaVinci, or for a scene that draws a backdrop.
BACKGROUND = ManimColor("#0B0E14")

# MARK: Fonts

# Two families. Sans for words: titles, labels, captions. Mono for anything
# technical: numbers, pixel values, timings, tap counts, code. Equations stay in
# MathTex.
FONT = "Figtree"
MONO = "Fragment Mono"  # One weight; its plain zero keeps grids of 0.xx calm

# Fragment Mono ships with the project (SIL OFL), so no system install is needed
_FONTS = Path(__file__).resolve().parents[2] / "assets" / "fonts"
for _font in _FONTS.glob("*.ttf"):
    manimpango.register_font(str(_font))

Text.set_default(font=FONT)
MarkupText.set_default(font=FONT)


class Mono(Text):
    """Text in the mono family. Use it for every number and technical value."""

    def __init__(self, text: str, **kwargs):
        kwargs.setdefault("font", MONO)
        super().__init__(text, **kwargs)


# Counters and readouts in mono rather than LaTeX's Computer Modern. Integer
# inherits this.
DecimalNumber.set_default(mob_class=Mono)
Code.set_default(paragraph_config={"font": MONO})

# One colour per method, used for its bars, kernels and labels throughout.
# Every pair stays apart under red-green colour blindness (CIELAB distance of
# at least 24 when simulated for deuteranopia and protanopia).
BOX = ManimColor("#3D7FD9")
GAUSSIAN = ManimColor("#5FD39A")
KAWASE = ManimColor("#F0625D")
DUAL_KAWASE = ManimColor("#D9B3FF")

TEXT = ManimColor("#E6E8EE")
MUTED = ManimColor("#7D8594")  # Grid lines, axes, secondary labels
HIGHLIGHT = ManimColor("#FFD166")  # The pixel or tap currently in focus

# Colour channels of an image. Only for literal R, G and B values, never for
# methods, so they're purer than the method colours they sit near.
RED_CHANNEL = ManimColor("#FF5A5A")
GREEN_CHANNEL = ManimColor("#45D16A")
BLUE_CHANNEL = ManimColor("#5A8CFF")
CHANNELS = (RED_CHANNEL, GREEN_CHANNEL, BLUE_CHANNEL)

# Matplotlib's magma, sampled at nine evenly spaced stops
_MAGMA = [
    "#000004", "#1C1044", "#4F127B", "#812581", "#B5367A",
    "#E55064", "#FB8761", "#FEC287", "#FCFDBF",
]
# Magma starts at black, which vanishes into the background
HEATMAP_FLOOR = 0.12


def _luminance(colour: ManimColor) -> float:
    rgb = np.asarray(colour.to_rgb())
    linear = np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)
    return float(linear @ (0.2126, 0.7152, 0.0722))


def text_on(fill: ManimColor, opacity: float = 1.0) -> ManimColor:
    """TEXT or BACKGROUND, whichever contrasts more with fill laid over the background."""
    shown = _luminance(interpolate_color(BACKGROUND, ManimColor(fill), float(opacity)))

    def contrast(colour):
        other = _luminance(colour)
        return (max(shown, other) + 0.05) / (min(shown, other) + 0.05)

    return TEXT if contrast(TEXT) >= contrast(BACKGROUND) else BACKGROUND


def magma(t: float) -> ManimColor:
    """Colour for a value in [0, 1], lifted off black so zero stays visible."""
    t = HEATMAP_FLOOR + (1 - HEATMAP_FLOOR) * min(max(t, 0.0), 1.0)
    i = min(int(t * (len(_MAGMA) - 1)), len(_MAGMA) - 2)
    local = t * (len(_MAGMA) - 1) - i
    return interpolate_color(ManimColor(_MAGMA[i]), ManimColor(_MAGMA[i + 1]), local)


# MARK: Layout

# Most graphics should fill about two thirds of the screen, not all of it: the
# margin leaves room for the presenter, captions and DaVinci's own framing.
# Fit a graphic inside FILL_WIDTH x FILL_HEIGHT; only full-bleed moments such as
# title cards or the photo itself before it becomes a graphic go edge to edge.
FILL = 0.7
FILL_WIDTH = FILL * config.frame_width
FILL_HEIGHT = FILL * config.frame_height


# MARK: Scales

# Type, as manim font_size. The frame is 8 units tall, so at 1080p 1 unit = 135 px.
TEXT_XS = 20  # Dense grids of values, several to a cell
TEXT_SM = 28  # Small print, credits
TEXT_BASE = 36  # Labels and readouts
TEXT_LG = 48  # Titles
TEXT_XL = 72  # Big numbers
TEXT_HERO = 120  # The one number a section is about

# Spacing, as buff in manim units
SPACE_1 = 0.15  # Label to its object
SPACE_2 = 0.3  # Between related objects
SPACE_3 = 0.6  # Between groups
SPACE_4 = 1.2  # Frame margins, between sections of a layout

STROKE_THIN = 1  # Grid lines, outlines
STROKE = 3
STROKE_BOLD = 6  # Kernels, the thing in focus

# Durations of change, in seconds: the tested minimums (see Motion, above).
# Lengthen a change if a transformation is hard to follow; don't shorten one.
QUICK = 0.28  # Highlights, small state changes
BEAT = 0.56  # One step of a repeated sequence
MOVE = 0.92  # Most single animations
SLOW = 1.84  # The few big transitions, such as a zoom or a split

# How far EASE leans from manim's smooth (0) towards quartic easing (1), which
# holds still longer at both ends and rushes the middle. Viewers followed
# changes best near smooth, so only a little quartic sharpening is kept.
EASE_STRENGTH = 0.2


def EASE(t: float) -> float:
    """The default rate func. Use linear only for counters and sweeps."""
    return (1 - EASE_STRENGTH) * smooth(t) + EASE_STRENGTH * rate_functions.ease_in_out_quart(t)


SPEED = 4.0  # Units per second for anything that travels
COUNT_SPEED = 1.5  # Decades per second for counters, so 1681 -> 82 matches 82 -> 20


def travel(distance: float) -> float:
    """run_time for a move, so cameras and kernels always travel at one pace."""
    return max(QUICK, abs(distance) / SPEED)


def count(start: float, end: float) -> float:
    """run_time for a counter, at an even pace on a log scale."""
    return max(QUICK, abs(np.log10(max(end, 1e-9) / max(start, 1e-9))) / COUNT_SPEED)


# MARK: Scenes

PAUSE = 1.0  # Seconds held at the start and end of every clip


class Clip:
    """Mixin adding the standard pauses. List it before the scene type."""

    def setup(self):
        super().setup()
        self.wait(PAUSE)

    def tear_down(self):
        self.wait(PAUSE)
        super().tear_down()


class ClipScene(Clip, Scene):
    pass
