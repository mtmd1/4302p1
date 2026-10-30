"""Demo: every intermediate image of a Dual Kawase blur, down then back up.

    uv run manim -pql src/examples/demo_dual_kawase.py DualKawasePyramid
"""

from manim import *

import blur
from sample import test_card

LEVELS = 4
WIDTH = 2.4  # Every level is drawn the same size, so the low resolutions show


def tile(pixels):
    image = ImageMobject(blur.to_uint8(pixels)).set_resampling_algorithm(RESAMPLING_ALGORITHMS["nearest"])
    image.width = WIDTH
    return Group(image, SurroundingRectangle(image, buff=0, color=GREY, stroke_width=1))


class DualKawasePyramid(Scene):
    def construct(self):
        source = test_card()
        result = blur.dual_kawase(source, levels=LEVELS, steps=True, repeat=20)
        down, up = result.steps[:LEVELS], result.steps[LEVELS:]

        top = Group(*(tile(p) for p in [source, *down])).arrange(RIGHT, buff=0.4).to_edge(UP, buff=1.0)
        # Each upscale lands under the downscale level of the same size
        bottom = Group(*(tile(p) for p in up))
        for i, t in enumerate(bottom):
            t.next_to(top[LEVELS - 1 - i], DOWN, buff=1.4)

        for i, t in enumerate(top):
            label = MathTex(rf"\tfrac{{1}}{{{2**i}}}" if i else "1", font_size=30).next_to(t, UP, buff=0.15)
            t.add(label)

        title = Text("Dual Kawase", font_size=36).to_edge(UP, buff=0.2)
        self.play(FadeIn(title), FadeIn(top[0]))

        for i in range(1, LEVELS + 1):
            arrow = Arrow(top[i - 1].get_right(), top[i].get_left(), buff=0.05, stroke_width=3)
            self.play(GrowArrow(arrow), FadeIn(top[i], shift=RIGHT * 0.3), run_time=0.6)

        arrow = Arrow(top[LEVELS].get_bottom(), bottom[0].get_top(), buff=0.1, stroke_width=3)
        self.play(GrowArrow(arrow), FadeIn(bottom[0], shift=DOWN * 0.3), run_time=0.6)
        for i in range(1, LEVELS):
            arrow = Arrow(bottom[i - 1].get_left(), bottom[i].get_right(), buff=0.05, stroke_width=3)
            self.play(GrowArrow(arrow), FadeIn(bottom[i], shift=LEFT * 0.3), run_time=0.6)

        stats = Text(
            f"{result.taps_per_pixel:.1f} taps per pixel  ·  {result.gpu_ms:.3f} ms on the GPU",
            font_size=28,
        ).to_edge(DOWN, buff=0.4)
        self.play(Write(stats))
        self.wait()
