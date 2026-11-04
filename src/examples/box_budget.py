"""Box blur 4: what 4.5 ms costs out of one frame at 60 FPS.

    uv run render box_budget
"""

from style import *

from components import FIGURES, BudgetBar


class Budget(ClipScene):
    def construct(self):
        readout = Mono(FIGURES.ms_box, font_size=TEXT_HERO, color=TEXT)
        bar = BudgetBar(color=BOX).next_to(readout, DOWN, buff=SPACE_4)
        VGroup(readout, bar).move_to(ORIGIN)
        share = Mono(f"{FIGURES.budget_percent}%", font_size=TEXT_BASE, color=text_on(BOX))
        share.move_to(bar.outline.get_left() + RIGHT * bar.full_width * FIGURES.budget_percent / 200)
        share.set_z_index(bar.fill.z_index + 1)  # The fill sits above its outline, and would hide this

        self.cue("the roughly 4.5 milliseconds")
        self.play(FadeIn(readout), run_time=MOVE, rate_func=EASE)
        self.play(FadeIn(bar), run_time=MOVE, rate_func=EASE)
        self.cue("more than a quarter")
        self.play(bar.fill_to(FIGURES.budget_percent), FadeIn(share, run_time=SLOW, rate_func=EASE))
        self.cue("every pixel still reads")
