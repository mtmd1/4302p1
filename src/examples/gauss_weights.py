"""Gaussian 1: the box kernel's 1s become a weight function of each cell's offset.

    uv run render gauss_weights
"""

from types import SimpleNamespace

from style import *

from components import NumberGrid, kernel_box
from sample import photo

CORNER = (712, 776)  # Top-left of the 5 x 5 patch shown: a lit window, so the values vary
SIZE = 5
CELL = 1.08
KERNEL = range(1, 4)  # The rows and columns under the 3 x 3 kernel
GRID_AT = LEFT * 2.28
READOUT_LEFT = 0.72  # x of the readout's left edge, clear of the grid
WEIGHT_DROP = 0.1  # Lowers each cell's main label, making room for its offset
CORNER_INSET = 0.07
WAVE = 0.08  # Lag ratio as a change passes through the kernel, in reading order
SWEEP = 1.2  # Seconds for that change


def offset_label(grid: NumberGrid, r: int, c: int) -> Mono:
    """The cell's (x, y) from the kernel's centre, in the cell's top-left corner."""
    label = Mono(f"{c - KERNEL[1]},{r - KERNEL[1]}", font_size=TEXT_XS, color=MUTED)
    corner = grid.square(r, c).get_corner(UL)
    return label.move_to(corner, aligned_edge=UL).shift(DR * CORNER_INSET)


def weight_label(grid: NumberGrid, r: int, c: int) -> MathTex:
    return MathTex("w(x, y)", font_size=TEXT_SM, color=TEXT).move_to(grid.square(r, c)).shift(DOWN * WEIGHT_DROP)


def build() -> SimpleNamespace:
    """The graphic before any change: pixel values under a kernel outline, no readout yet."""
    x, y = CORNER
    values = photo()[y : y + SIZE, x : x + SIZE, 0].tolist()
    grid = NumberGrid(values, cell=CELL).move_to(GRID_AT)
    cells = [(r, c) for r in KERNEL for c in KERNEL]
    return SimpleNamespace(
        grid=grid,
        cells=cells,
        outline=kernel_box(grid, KERNEL[1], KERNEL[1]),
        sum=Text("sum /", font_size=TEXT_BASE, color=TEXT).move_to([READOUT_LEFT, 0, 0], aligned_edge=LEFT),
    )


def denominator(state: SimpleNamespace, words: str) -> Text:
    """The readout's second half, on the same baseline as "sum /" (first letters, as "/" and "g" descend)."""
    text = Text(words, font_size=TEXT_BASE, color=TEXT).next_to(state.sum, RIGHT, buff=SPACE_1)
    return text.shift(UP * (state.sum[0].get_bottom()[1] - text[0].get_bottom()[1]))


class GaussWeights(ClipScene):
    def construct(self):
        state = build()
        grid = state.grid
        self.cue("Consider our box blur kernel")
        self.play(FadeIn(grid), run_time=MOVE, rate_func=EASE)
        self.play(Create(state.outline), run_time=MOVE, rate_func=EASE)

        # The pixels under the kernel give way to its weights, and the readout says what they mean
        count = denominator(state, "count")
        ones = {
            (r, c): Mono("1", font_size=TEXT_BASE, color=TEXT).move_to(grid.square(r, c))
            for r, c in state.cells
        }
        self.play(
            *(grid.square(r, c).animate.set_fill(BACKGROUND) for r, c in state.cells),
            *(ReplacementTransform(grid.label(r, c), ones[r, c]) for r, c in state.cells),
            FadeIn(state.sum),
            FadeIn(count),
            run_time=MOVE,
            rate_func=EASE,
        )
        self.cue("pass each pixel's")

        # A wave of offsets on "x and y", then one of weights as the function is named
        self.play(
            LaggedStart(
                *(FadeIn(offset_label(grid, r, c)) for r, c in state.cells),
                lag_ratio=WAVE,
                run_time=SWEEP,
                rate_func=EASE,
            )
        )
        self.cue("to a weight function")
        self.play(
            LaggedStart(
                *(ReplacementTransform(ones[r, c], weight_label(grid, r, c)) for r, c in state.cells),
                lag_ratio=WAVE,
                run_time=SWEEP,
                rate_func=EASE,
            )
        )
        self.cue("then divide by the sum")

        self.play(ReplacementTransform(count, denominator(state, "sum of weights")), run_time=MOVE, rate_func=EASE)
        self.cue("For a gaussian blur")
