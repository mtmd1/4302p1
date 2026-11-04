"""Bjorge 7: on the V, each pass's cost grows as a bar, adding up to about 12 taps per pixel.

    uv run render bjorge_cost

A bar's height is a pass's taps per pixel of the final image: its taps, times the
share of the frame's pixels its level has. Together they're the sum blur.py's
_pyramid runs: 5 (1/4 + ... + 1/256) + 8 (1 + ... + 1/64) = 12.285, spoken as
FIGURES.taps_dual. Bars follow the V, in pass order, so the chart shows why: the
last pass up dominates, and everything near the V's turning point costs next to
nothing. An extra level adds two passes there, too small to see, so a callout
marks them and says what they add.
"""

from types import SimpleNamespace

from style import *

from components import FIGURES, DualV
from sample import photo

DOWN_TAPS, UP_TAPS = 5, 8
TILE_WIDTH = 1.75  # Leaves the deeper V and the chart beneath it inside the frame
V_GAP_Y = 0.2  # Tighter than the DualV default, for the same reason
BASELINE_GAP = SPACE_4 + SPACE_3  # From the deepest V to the chart's baseline
BAR_WIDTH = 0.5
MAX_BAR = 1.7  # Height of the tallest bar, the last pass's 8 taps per pixel
HAIRLINE = 0.015  # The least a bar is drawn, so even the smallest is there
CALLOUT_HEIGHT = 0.45  # Above the baseline, around the new level's bars

# The V tile each pass writes, in the order the V runs, with each pass's time. Tile 0
# is the source: it's read, never written.
PASS_TIMES = ((1, MOVE), (2, BEAT), (3, QUICK), (4, QUICK), (5, QUICK), (6, BEAT), (7, MOVE), (8, SLOW))
EXTRA_LEVEL = 5  # The level the narration adds, below the V's turning point
NEW_SLOT = DualV.LEVELS  # Where its two passes go along the chart


def small_v(levels: int = DualV.LEVELS) -> DualV:
    """The V at this scene's size, in the same place and image size whatever its depth."""
    return DualV(photo(), width=DualV.width_for(TILE_WIDTH, levels), levels=levels, gap_y=V_GAP_Y, label_size=TEXT_XS)


def slot_x(slot: int, slots: int) -> float:
    return FILL_WIDTH * ((slot + 0.5) / slots - 0.5)


def cost_text(cost: float) -> str:
    return f"{cost:.3g}" if cost >= 1 else f"{cost:.2g}"


def column(level: int, taps: int, slot: int, slots: int, baseline: float) -> SimpleNamespace:
    """One pass: its bar, the value above it and the level it writes, below the baseline."""
    cost = taps / 4**level
    bar = Rectangle(
        width=BAR_WIDTH, height=max(cost / UP_TAPS * MAX_BAR, HAIRLINE), stroke_width=0, fill_color=DUAL_KAWASE, fill_opacity=1,
    ).move_to([slot_x(slot, slots), baseline, 0], aligned_edge=DOWN)
    value = Mono(cost_text(cost), font_size=TEXT_XS, color=MUTED).next_to(bar, UP, buff=SPACE_1)
    tick = Mono(f"1/{2**level}" if level else "1", font_size=TEXT_XS, color=MUTED).next_to([bar.get_x(), baseline, 0], DOWN, buff=SPACE_1)
    return SimpleNamespace(cost=cost, bar=bar, value=value, tick=tick, parts=VGroup(bar, value, tick))


def active(tile: Mobject) -> Rectangle:
    return SurroundingRectangle(tile, buff=0, color=HIGHLIGHT, stroke_width=STROKE)


class BjorgeCost(ClipScene):
    def construct(self):
        v = small_v()
        deeper = small_v(EXTRA_LEVEL)
        self.add(v, v.taps)
        baseline = deeper.tiles[EXTRA_LEVEL].get_bottom()[1] - BASELINE_GAP

        slots = len(PASS_TIMES)
        columns = [
            column(
                min(tile, 2 * DualV.LEVELS - tile), DOWN_TAPS if tile <= DualV.LEVELS else UP_TAPS, slot, slots, baseline,
            )
            for slot, (tile, _) in enumerate(PASS_TIMES)
        ]
        # The figure as spoken must be what's about to be drawn
        total = sum(c.cost for c in columns)
        assert round(total) == FIGURES.taps_dual and round(total, 3) == 12.285

        axis = Line([-FILL_WIDTH / 2, baseline, 0], [FILL_WIDTH / 2, baseline, 0], color=MUTED, stroke_width=STROKE)
        name = Text("taps per pixel, per pass", font_size=TEXT_SM, color=MUTED)
        name.next_to(axis, DOWN, buff=SPACE_3 + SPACE_2, aligned_edge=RIGHT)

        self.cue("Each downscale quarters")
        marks = VGroup()
        for i, ((tile, time), c) in enumerate(zip(PASS_TIMES, columns)):
            next_marks = active(v.tiles[tile])
            first = [FadeIn(axis), FadeIn(name)] if i == 0 else []
            self.play(
                *first, FadeOut(marks), FadeIn(next_marks),
                GrowFromEdge(c.bar, DOWN), FadeIn(c.value), FadeIn(c.tick),
                run_time=time, rate_func=EASE,
            )
            marks = next_marks

        self.cue("about twelve taps")
        whole = VGroup(
            Mono(str(FIGURES.taps_dual), font_size=TEXT_LG, color=TEXT),
            Text("taps per pixel", font_size=TEXT_BASE, color=TEXT),
        ).arrange(RIGHT, buff=SPACE_2, aligned_edge=DOWN)
        whole.next_to(axis, DOWN, buff=SPACE_3 + SPACE_2, aligned_edge=LEFT)
        self.play(FadeOut(marks), FadeIn(whole), run_time=BEAT, rate_func=EASE)

        # One more level: the V widens around a new turning point, keeping its images'
        # sizes, and the chart opens two slots there. Going up, every result is blurrier.
        self.cue("And each extra level")
        extra_tiles = 2
        new_at = DualV.LEVELS + 1
        old_new_tiles = [*zip(v.tiles[:new_at], deeper.tiles[:new_at]), *zip(v.tiles[new_at:], deeper.tiles[new_at + extra_tiles:])]
        old_new_arrows = [*zip(v.arrows[:DualV.LEVELS], deeper.arrows[:DualV.LEVELS]), *zip(v.arrows[DualV.LEVELS:], deeper.arrows[DualV.LEVELS + extra_tiles:])]
        wider = slots + extra_tiles
        self.play(
            *(Transform(old, new) for old, new in [*old_new_tiles, *old_new_arrows, *zip(v.labels, deeper.labels)]),
            Transform(v.taps, deeper.taps),
            *(FadeIn(tile) for tile in deeper.tiles[new_at : new_at + extra_tiles]),
            *(GrowArrow(arrow) for arrow in deeper.arrows[DualV.LEVELS : DualV.LEVELS + extra_tiles]),
            FadeIn(deeper.labels[EXTRA_LEVEL]),
            *(
                c.parts.animate.set_x(slot_x(slot if slot < NEW_SLOT else slot + extra_tiles, wider))
                for slot, c in enumerate(columns)
            ),
            run_time=SLOW,
            rate_func=EASE,
        )

        # 5 taps on the new turning point, 8 on the level above coming back up. They're
        # meant to be too small to see, so the callout shows where they are and what they add.
        self.cue("at almost no cost")
        added = [
            column(EXTRA_LEVEL, DOWN_TAPS, NEW_SLOT, wider, baseline),
            column(EXTRA_LEVEL - 1, UP_TAPS, NEW_SLOT + 1, wider, baseline),
        ]
        addition = sum(c.cost for c in added)
        around = Rectangle(
            width=2 * FILL_WIDTH / wider, height=CALLOUT_HEIGHT, color=HIGHLIGHT, stroke_width=STROKE,
        ).move_to([(slot_x(NEW_SLOT, wider) + slot_x(NEW_SLOT + 1, wider)) / 2, baseline, 0], aligned_edge=DOWN)
        callout = Mono(f"+{addition:.2f} taps", font_size=TEXT_BASE, color=HIGHLIGHT).next_to(around, UP, buff=SPACE_1)
        self.play(
            *(GrowFromEdge(c.bar, DOWN) for c in added),
            *(FadeIn(c.tick) for c in added),
            Create(around),
            FadeIn(callout),
            run_time=MOVE,
            rate_func=EASE,
        )

        self.cue("Our first naive box blur")
