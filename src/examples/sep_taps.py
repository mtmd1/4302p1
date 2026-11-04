"""Separation 2: the same image for far fewer taps.

    uv run render sep_taps

Two bars on one scale, each with its sum and its time: 1681 taps in 4.5 ms, then
the separated blur's 82 taps in 0.2 ms.
"""

from style import *

from components import FIGURES

SIDE = 2 * FIGURES.radius_box + 1  # 41
VALUES_WIDTH = 2.7  # Room right of the longest bar
BAR_LENGTH = FILL_WIDTH - VALUES_WIDTH  # The longest bar, at FIGURES.taps_box
BAR_HEIGHT = 1.2
ROW_SPACING = 2.8  # From one bar's centre to the next, with room for a heading


def bar_row(name: str, sum_tex: str, taps: int, time: str, y: float) -> VGroup:
    """Heading and sum on one line, over a bar with its taps and time beside it. y is the bar's."""
    bar = Rectangle(
        width=taps / FIGURES.taps_box * BAR_LENGTH, height=BAR_HEIGHT,
        stroke_width=0, fill_color=GAUSSIAN, fill_opacity=1,
    )
    bar.move_to([-FILL_WIDTH / 2, y, 0], aligned_edge=LEFT)
    values = VGroup(
        Mono(str(taps), font_size=TEXT_LG, color=TEXT),
        Mono(time, font_size=TEXT_LG, color=TEXT),
    ).arrange(DOWN, buff=SPACE_1, aligned_edge=LEFT)
    values.next_to(bar, RIGHT, buff=SPACE_2)
    heading = Text(name, font_size=TEXT_LG, color=TEXT).next_to(bar, UP, buff=SPACE_2).align_to(bar, LEFT)
    total = MathTex(sum_tex, font_size=TEXT_SM, color=MUTED)
    total.align_to(heading, DOWN).align_to([FILL_WIDTH / 2, 0, 0], RIGHT)
    return VGroup(heading, total, bar, values)


class SepTaps(ClipScene):
    def construct(self):
        first = bar_row("gaussian", f"{SIDE}^2 = {FIGURES.taps_box}", FIGURES.taps_box, FIGURES.ms_box, 0)
        second = bar_row(
            "separated gaussian", rf"2 \cdot {SIDE} = {FIGURES.taps_separated}",
            FIGURES.taps_separated, FIGURES.ms_separated, -ROW_SPACING,
        )
        VGroup(first, second).move_to(ORIGIN)

        self.add(first)
        self.cue("The output is exactly identical")
        self.cue("our taps per pixel drop")

        heading, total, bar, values = second
        self.play(
            GrowFromEdge(bar, LEFT), FadeIn(heading), FadeIn(total), FadeIn(values),
            run_time=MOVE, rate_func=EASE,
        )
        self.cue("That's 95 percent")
