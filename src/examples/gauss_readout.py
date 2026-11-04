"""Gaussian 5: both blurs cost the same, 4.5 ms and 1681 taps per pixel.

    uv run render gauss_readout
"""

from style import *

from components import FIGURES, TapCounter
from gauss_compare import caption_y, captions, divider, half_centre, picture

SHRINK = 0.8  # Of the two lamps once the counter needs the room
SHRUNK_TOP = FILL_HEIGHT / 2
COUNTER_TOP = -1.4  # y of the counter's first row


class GaussReadout(ClipScene):
    def construct(self):
        # Exactly where the last clip left off
        still = picture(zoomed=1.0)
        line = divider()
        left, right = captions()
        self.add(still, line, left, right)
        self.cue("But it's just as slow")

        # One line of narration, so one change: the kernels make way for what they
        # cost, in time under each half and in taps in the counter below
        readouts = [
            Mono(FIGURES.ms_box, font_size=TEXT_BASE, color=BOX),
            Mono(FIGURES.ms_box, font_size=TEXT_BASE, color=GAUSSIAN),
        ]
        readouts[0].move_to(half_centre(-1) + UP * caption_y())
        readouts[1].move_to(half_centre(1) + UP * caption_y())

        # Where the shrunk lamps and their readouts end up
        upper = Group(still, line, *readouts).copy().scale(SHRINK).move_to(UP * SHRUNK_TOP, aligned_edge=UP)
        still.generate_target().replace(upper[0])
        line.generate_target().move_to(upper[1]).scale(SHRINK)
        for readout, landed in zip(readouts, upper[2:]):
            readout.scale(SHRINK).move_to(landed)
            readout.set_y(upper[0].get_bottom()[1] - SPACE_2 - readout.height / 2)

        counter = TapCounter(FIGURES.taps_box, top=COUNTER_TOP)
        title = Text("taps per pixel", font_size=TEXT_SM, color=MUTED)
        counter.add_row("box", FIGURES.taps_box, BOX)
        title.next_to(counter, UP, buff=SPACE_1).align_to(counter.rows["box"].bar, LEFT)
        box_row = VGroup(*counter.submobjects)
        self.play(
            FadeOut(left),
            FadeOut(right),
            MoveToTarget(still),
            MoveToTarget(line),
            *(FadeIn(r) for r in readouts),
            FadeIn(box_row),
            FadeIn(title),
            counter.add_row("gaussian", FIGURES.taps_box, GAUSSIAN),
            run_time=SLOW,
            rate_func=EASE,
        )
        self.cue("it turns out that our kernels")
