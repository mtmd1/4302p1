"""Kawase 8: 5 x 4 = 20 taps, beside the 70 of a separated gaussian at the same strength.

    uv run render kawase_taps
"""

from style import *

from components import FIGURES, TapCounter

TOP = 1.2  # Height of the first row
SUM_Y = -0.75
GAUSSIAN_NAME = "gaussian"


class Taps(ClipScene):
    def construct(self):
        counter = TapCounter(FIGURES.taps_separated_matched, top=TOP)
        counter.add_row(GAUSSIAN_NAME, FIGURES.taps_separated_matched, GAUSSIAN)
        # The gaussian's strength, on its bar, the whole time
        bar = counter.rows[GAUSSIAN_NAME].bar
        strength = Mono(f"σ = {FIGURES.sigma_kawase}", font_size=TEXT_BASE, color=GAUSSIAN)
        strength.next_to(bar, UP, buff=SPACE_1).align_to(bar, LEFT)
        self.add(counter, strength)

        self.cue("Five passes of four taps")
        grow = counter.add_row("Kawase", FIGURES.taps_kawase, KAWASE)
        kawase_sum = MathTex(r"5 \times 4 = 20", font_size=TEXT_SM, color=MUTED).move_to(UP * SUM_Y)
        self.play(grow, FadeIn(kawase_sum, run_time=MOVE, rate_func=EASE))

        self.cue("Look closely at")
