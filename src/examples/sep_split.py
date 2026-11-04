"""Separation 1: the 2D kernel is a column times a row, so one pass becomes two.

    uv run render sep_split

The identity and the kernel split into column x row, then two buffers: the photo
in ping, its horizontal-only blur written row by row to pong, and the final image
written column by column back to ping.
"""

import functools

from style import *

import blur
from components import FIGURES, NumberGrid, photo_still
from sample import photo

COLUMN = np.array([1, 2, 1])
KERNEL = np.outer(COLUMN, COLUMN)  # Computed, so the grid really is column x row
CELL = 0.8  # Side of a kernel cell
BUFFER_WIDTH = 5.5  # Each of ping and pong: past FILL, so the blur can be seen
BUFFERS_SPAN = 11.95  # Both, with the gap for the arrows between them
ARROW_GAP = 1.0  # How far above and below centre the two arrows run, by the images' edges so the labels clear them


@functools.cache
def passes() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """The photo, the horizontal pass alone, and the finished blur, as 8-bit RGBA."""
    image = photo()
    result = blur.gaussian(image, FIGURES.sigma_gaussian, FIGURES.radius_box, separable=True, steps=True)
    horizontal, final = result.steps
    return blur.to_uint8(image), blur.to_uint8(horizontal), blur.to_uint8(final)


def heat(weight: float) -> ManimColor:
    return magma(weight / KERNEL.max())


def weights(values) -> NumberGrid:
    return NumberGrid(values.tolist(), cell=CELL, font_size=TEXT_BASE, decimals=0, fill=heat)


def wipe(still: ImageMobject, new: np.ndarray, axis: int, **kwargs) -> Animation:
    """Overwrite still with new one line at a time: axis 0 down its rows, axis 1 across its columns."""
    old = still.pixel_array.copy()

    def update(mob, alpha):
        edge = round(alpha * new.shape[axis])
        written = old.copy()
        if axis == 0:
            written[:edge] = new[:edge]
        else:
            written[:, :edge] = new[:, :edge]
        mob.pixel_array = written

    return UpdateFromAlphaFunc(still, update, **kwargs)


class SepSplit(ClipScene):
    def construct(self):
        source, horizontal, final = passes()

        # The identity over the kernel it describes
        identity = MathTex(r"e^{-x^2 - y^2} = e^{-x^2} \cdot e^{-y^2}", font_size=TEXT_LG, color=TEXT)
        kernel = weights(KERNEL)
        VGroup(identity, kernel).arrange(DOWN, buff=SPACE_3).move_to(ORIGIN)

        self.cue("it turns out that our kernels")
        self.play(FadeIn(identity), FadeIn(kernel), run_time=MOVE, rate_func=EASE)
        self.cue("That means")

        # Where the split lands: column x row = kernel
        column, row = weights(COLUMN[:, None]), weights(COLUMN[None, :])
        times, equals = MathTex(r"\times", font_size=TEXT_LG, color=TEXT), MathTex("=", font_size=TEXT_LG, color=TEXT)
        landed = VGroup(column.copy(), times, row.copy(), equals, kernel.copy()).arrange(RIGHT, buff=SPACE_3)
        landed.move_to([0, kernel.get_y(), 0])
        column_at, row_at, kernel_at = landed[0].get_center(), landed[2].get_center(), landed[4].get_center()
        column_name = Text("column", font_size=TEXT_SM, color=MUTED).next_to(landed[0], DOWN, buff=SPACE_1)
        row_name = Text("row", font_size=TEXT_SM, color=MUTED).next_to(landed[2], DOWN, buff=SPACE_1)
        row_name.align_to(column_name, DOWN)

        # The kernel makes room, then its left column and top row each peel off
        self.play(kernel.animate.move_to(kernel_at), run_time=MOVE, rate_func=EASE)
        column.move_to(kernel.get_left(), aligned_edge=LEFT)
        row.move_to(kernel.get_top(), aligned_edge=UP)
        self.cue("a column of weights")
        self.add(column)
        self.play(column.animate.move_to(column_at), FadeIn(column_name), run_time=MOVE, rate_func=EASE)
        self.cue("a row of weights")
        self.add(row)
        # The row completes the equation, so its signs come with it
        self.play(
            row.animate.move_to(row_at), FadeIn(row_name), FadeIn(times), FadeIn(equals),
            run_time=MOVE, rate_func=EASE,
        )
        self.cue("Instead of one pass")

        # The kernel leaves as two buffers take its place
        split = VGroup(identity, column, column_name, times, row, row_name, equals, kernel)

        ping = photo_still(source, width=BUFFER_WIDTH)
        pong = photo_still(np.zeros_like(source), width=BUFFER_WIDTH)
        ping.move_to(LEFT * (BUFFERS_SPAN - BUFFER_WIDTH) / 2)
        pong.move_to(RIGHT * (BUFFERS_SPAN - BUFFER_WIDTH) / 2)
        frames = VGroup(*(
            SurroundingRectangle(still, buff=0, color=MUTED, stroke_width=STROKE_THIN) for still in (ping, pong)
        ))
        names = VGroup(
            Text("Ping", font_size=TEXT_BASE, color=TEXT).next_to(ping, UP, buff=SPACE_1),
            Text("Pong", font_size=TEXT_BASE, color=TEXT).next_to(pong, UP, buff=SPACE_1),
        )
        self.play(FadeOut(split), FadeIn(ping), FadeIn(frames), FadeIn(names), run_time=MOVE, rate_func=EASE)
        self.cue("we can blur every row")

        # Every row of ping is blurred into pong, top to bottom
        there = Arrow(
            ping.get_right() + UP * ARROW_GAP, pong.get_left() + UP * ARROW_GAP,
            buff=SPACE_1, color=HIGHLIGHT, stroke_width=STROKE,
        )
        rows = Text("rows", font_size=TEXT_SM, color=TEXT).next_to(there, UP, buff=SPACE_1)
        rows.set_y(ping.get_top()[1] + rows.height / 2 + SPACE_1)
        self.play(
            GrowArrow(there), FadeIn(rows), wipe(pong, horizontal, axis=0),
            run_time=SLOW, rate_func=EASE,
        )
        self.cue("then blur every column")

        # Every column of pong is blurred back into ping, left to right
        back = Arrow(
            pong.get_left() + DOWN * ARROW_GAP, ping.get_right() + DOWN * ARROW_GAP,
            buff=SPACE_1, color=HIGHLIGHT, stroke_width=STROKE,
        )
        columns = Text("columns", font_size=TEXT_SM, color=TEXT).next_to(ping, DOWN, buff=SPACE_1).set_x(0)
        self.play(
            there.animate.set_color(MUTED), GrowArrow(back), FadeIn(columns), wipe(ping, final, axis=1),
            run_time=SLOW, rate_func=EASE,
        )
        self.cue("The output is exactly identical")
