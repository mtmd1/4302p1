"""Bjorge 6: every level of a real Dual Kawase, down then back up, with its two tap patterns.

    uv run render bjorge_dual

The images and panels are blur.py's shaders. Going down, offsets of half a
destination texel are one source pixel, so the grid is source pixels. Going up,
the grid is destination pixels, centred on the one being written.

The clip ends back on the V, in the smaller layout bjorge_cost opens on.
"""

from style import *

from bjorge_cost import small_v
from bjorge_shimmer import PAN_RATE, panel
from components import DualV, TapPoint, credit
from sample import photo

INSET_CELL_DOWN = 0.36  # 4 source pixels across
INSET_CELL_UP = 0.48  # 3 destination pixels across

# The comparison's crop, closer than the V's, so the blocks are big enough to see crawl
SIDE_CROP = (1120, 620, 320, 240)
PANEL_GAP = 0.35  # Fills FILL_WIDTH with the two panels
TITLE_ROOM = 0.45 + SPACE_2  # Above the V, kept free from the start so nothing moves for the title


def cells(n: int, size: float) -> VGroup:
    return VGroup(*(
        Square(size, stroke_color=MUTED, stroke_width=STROKE_THIN).move_to(
            np.array([(c - (n - 1) / 2) * size, ((n - 1) / 2 - r) * size, 0])
        )
        for r in range(n)
        for c in range(n)
    ))


def down_pattern() -> VGroup:
    """Centre x4, four diagonals of one source pixel, all on pixel corners."""
    size = INSET_CELL_DOWN
    marks = VGroup(TapPoint())
    for dx, dy in ((-1, 1), (1, 1), (-1, -1), (1, -1)):
        marks.add(TapPoint().move_to(np.array([dx * size, dy * size, 0])))
    return VGroup(cells(4, size), marks)


def up_pattern() -> VGroup:
    """Four on the axes at one destination texel, four diagonals at half, weighted 2."""
    size = INSET_CELL_UP
    marks = VGroup()
    for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        marks.add(TapPoint().move_to(np.array([dx * size, dy * size, 0])))
    for dx, dy in ((-0.5, 0.5), (0.5, 0.5), (-0.5, -0.5), (0.5, -0.5)):
        marks.add(TapPoint().move_to(np.array([dx * size, dy * size, 0])))
    return VGroup(cells(3, size), marks)


def captioned(pattern: VGroup, count: str, direction: str, weights: str) -> VGroup:
    text = VGroup(
        VGroup(
            Mono(count, font_size=TEXT_BASE, color=DUAL_KAWASE),
            Text(direction, font_size=TEXT_BASE, color=DUAL_KAWASE),
        ).arrange(RIGHT, buff=SPACE_1),
        Mono(weights, font_size=TEXT_XS, color=MUTED),
    ).arrange(DOWN, aligned_edge=LEFT, buff=SPACE_1)
    return VGroup(pattern, text).arrange(RIGHT, buff=SPACE_2)


class BjorgeDual(ClipScene):
    def construct(self):
        v = DualV(photo(), top=FILL_HEIGHT / 2 - TITLE_ROOM)

        # Each arm's pattern in the corner the V leaves free beneath it
        down_inset = captioned(down_pattern(), "5", "down", "centre ×4")
        up_inset = captioned(up_pattern(), "8", "up", "diagonals ×2")
        down_inset.move_to([-FILL_WIDTH / 2, -FILL_HEIGHT / 2, 0], aligned_edge=DL)
        up_inset.move_to([FILL_WIDTH / 2, -FILL_HEIGHT / 2, 0], aligned_edge=DR)

        name = Text("dual filter", font_size=TEXT_LG, color=DUAL_KAWASE)
        name.move_to(UP * FILL_HEIGHT / 2, aligned_edge=UP)
        source_credit = credit("Marius Bjørge, ARM, SIGGRAPH 2015")

        self.add(v.tiles[0], v.labels[0])
        self.cue("That's exactly what Marius")
        self.play(FadeIn(source_credit), run_time=QUICK)

        # Only the left arm carries size labels
        for i, (arrow, tile) in enumerate(zip(v.arrows, v.tiles[1:]), start=1):
            label = [FadeIn(v.labels[i])] if i < len(v.labels) else []
            self.play(GrowArrow(arrow), FadeIn(tile), *label, run_time=BEAT, rate_func=EASE)

        self.cue("Five taps going down")
        self.play(FadeIn(down_inset), run_time=MOVE, rate_func=EASE)
        self.cue("eight in a ring")
        self.play(FadeIn(up_inset), run_time=MOVE, rate_func=EASE)

        self.cue("He called it the dual filter")
        self.play(FadeIn(name, shift=UP * SPACE_2), run_time=MOVE, rate_func=EASE)

        # The problem from earlier beside what fixes it, panning from the moment they show
        self.cue("Nowadays, we call it")
        pan, ink = ValueTracker(0), ValueTracker(0)
        pan.add_updater(lambda m, dt: m.increment_value(PAN_RATE * dt))
        width = (FILL_WIDTH - PANEL_GAP) / 2
        naive = panel("naive", pan, width, SIDE_CROP, ink)
        dual = panel("dual", pan, width, SIDE_CROP, ink)
        Group(naive, dual).arrange(RIGHT, buff=PANEL_GAP)
        # The title stays above the visual: it becomes the heading of its own panel
        naive_label = Text("naive", font_size=TEXT_LG, color=TEXT).next_to(naive, UP, buff=SPACE_2)
        dual_label = Text("Dual Kawase", font_size=TEXT_LG, color=DUAL_KAWASE).next_to(dual, UP, buff=SPACE_2)
        Group(naive, dual, naive_label, dual_label).move_to(ORIGIN)
        self.add(pan, naive, dual)
        self.play(
            FadeOut(v), FadeOut(down_inset), FadeOut(up_inset), FadeOut(source_credit),
            ink.animate.set_value(1),
            FadeTransform(name, dual_label),
            FadeIn(naive_label),
            run_time=MOVE,
            rate_func=EASE,
        )

        # Back on the V just as the talk returns to it, for the costs that follow
        # Timed to land on the closing cue exactly, in bjorge_cost's layout, where it opens
        self.wait(cue_time("Each downscale quarters") - cue_time("Nowadays, we call it") - MOVE - BEAT)
        closing = small_v()
        self.play(
            ink.animate.set_value(0),
            FadeOut(naive_label), FadeOut(dual_label),
            FadeIn(closing), FadeIn(closing.taps),
            run_time=BEAT,
            rate_func=EASE,
        )
        self.remove(pan, naive, dual)
        self.cue("Each downscale quarters")
