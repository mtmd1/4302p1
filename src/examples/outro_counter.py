"""Conclusion 1: every method's taps on one linear scale, with the FPS each reaches.

    uv run render outro_counter

One scale throughout, so the small bars are genuinely tiny: that's the payoff.
"""

from style import *

from components import FIGURES, TapCounter

ROW_HEIGHT = 1.05  # Bigger than TapCounter's default: the chart has the screen to itself
FPS_GAP = SPACE_1 / 2  # Bar to its FPS, tighter than to the next row's bar

# Name, taps, FPS and colour of each row, top to bottom
ROWS = (
    ("box", FIGURES.taps_box, FIGURES.fps_box, BOX),
    ("separated", FIGURES.taps_separated, FIGURES.fps_separated, GAUSSIAN),
    ("Kawase", FIGURES.taps_kawase, FIGURES.fps_kawase, KAWASE),
    ("Dual Kawase", FIGURES.taps_dual, FIGURES.fps_dual, DUAL_KAWASE),
)


class OutroCounter(ClipScene):
    def construct(self):
        heading = Text("taps per pixel", font_size=TEXT_SM, color=MUTED)
        top = FILL_HEIGHT / 2 - heading.height - SPACE_1 - ROW_HEIGHT / 4  # Centre of the first bar
        counter = TapCounter(max_taps=FIGURES.taps_box, top=top, row_height=ROW_HEIGHT)
        heading.move_to([counter.left, FILL_HEIGHT / 2, 0], aligned_edge=UL)
        self.add(counter)
        self.cue("Our first naive box blur")

        # Nothing waits on screen: the chart arrives with the first method
        self.cue("box blur took")
        fps_labels = [self._add_row(counter, *ROWS[0], FadeIn(heading), run_time=SLOW)]

        for phrase, row in zip(("Separation took it", "Kawase took it", "And the Dual Kawase"), ROWS[1:]):
            self.cue(phrase)
            fps_labels.append(self._add_row(counter, *row))

        self.cue("does it in twelve")
        self.play(FadeIn(self._sum()), run_time=MOVE, rate_func=EASE)

        self.cue("more than twenty thousand")
        self.play(fps_labels[-1].animate.set_color(HIGHLIGHT), run_time=BEAT, rate_func=EASE)
        self.cue("That is why this technique")

    def _add_row(self, counter: TapCounter, name: str, taps: int, fps: str, color, *also, run_time=MOVE) -> Mono:
        """Grow a method's bar with its FPS beneath it, and return the FPS label."""
        grow = counter.add_row(name, taps, color)
        bar = counter.rows[name].bar
        label = Mono(f"{fps} FPS", font_size=TEXT_SM, color=TEXT)
        label.next_to(bar, DOWN, buff=FPS_GAP).align_to(bar, LEFT)
        self.play(grow, FadeIn(label), *also, run_time=run_time, rate_func=EASE)
        return label

    def _sum(self) -> VGroup:
        """The dual filter's taps, four levels down and four back up, in a line under the chart."""
        terms = MathTex(
            r"5\left(\tfrac{1}{4} + \tfrac{1}{16} + \tfrac{1}{64} + \tfrac{1}{256}\right)"
            r"\ +\ 8\left(1 + \tfrac{1}{4} + \tfrac{1}{16} + \tfrac{1}{64}\right) \approx",
            font_size=TEXT_SM,
            color=MUTED,
        )
        total = Mono("12.3", font_size=TEXT_SM, color=MUTED)
        line = VGroup(terms, total).arrange(RIGHT, buff=SPACE_1)
        line.scale_to_fit_width(min(line.width, FILL_WIDTH))
        return line.move_to(DOWN * FILL_HEIGHT / 2, aligned_edge=DOWN)
