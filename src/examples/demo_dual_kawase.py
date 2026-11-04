"""Demo: every intermediate image of a Dual Kawase blur, down then back up.

    uv run render demo_dual_kawase                                        # clip for Resolve
    uv run manim -pql src/examples/demo_dual_kawase.py DualKawasePyramid  # quick preview
"""

from style import *

import blur
from sample import test_card

LEVELS = 4
WIDTH = 2.3  # Every level is drawn the same size, so the low resolutions show


def tile(pixels):
    image = ImageMobject(blur.to_uint8(pixels)).set_resampling_algorithm(RESAMPLING_ALGORITHMS["nearest"])
    image.width = WIDTH
    return Group(image, SurroundingRectangle(image, buff=0, color=MUTED, stroke_width=STROKE_THIN))


class DualKawasePyramid(ClipScene):
    def construct(self):
        source = test_card()
        result = blur.dual_kawase(source, levels=LEVELS, steps=True, repeat=20)
        down, up = result.steps[:LEVELS], result.steps[LEVELS:]

        top = Group(*(tile(p) for p in [source, *down])).arrange(RIGHT, buff=SPACE_3).to_edge(UP, buff=SPACE_4)
        # Each upscale lands under the downscale level of the same size
        bottom = Group(*(tile(p) for p in up))
        for i, t in enumerate(bottom):
            t.next_to(top[LEVELS - 1 - i], DOWN, buff=SPACE_4)

        for i, t in enumerate(top):
            label = MathTex(rf"\tfrac{{1}}{{{2**i}}}" if i else "1", font_size=TEXT_SM).next_to(t, UP, buff=SPACE_1)
            t.add(label)

        title = Text("Dual Kawase", font_size=TEXT_LG).to_edge(UP, buff=SPACE_1)
        self.play(FadeIn(title), FadeIn(top[0]))

        for i in range(1, LEVELS + 1):
            arrow = Arrow(top[i - 1].get_right(), top[i].get_left(), buff=SPACE_1, stroke_width=STROKE)
            self.play(GrowArrow(arrow), FadeIn(top[i], shift=RIGHT * SPACE_2), run_time=BEAT)

        arrow = Arrow(top[LEVELS].get_bottom(), bottom[0].get_top(), buff=SPACE_1, stroke_width=STROKE)
        self.play(GrowArrow(arrow), FadeIn(bottom[0], shift=DOWN * SPACE_2), run_time=BEAT)
        for i in range(1, LEVELS):
            arrow = Arrow(bottom[i - 1].get_left(), bottom[i].get_right(), buff=SPACE_1, stroke_width=STROKE)
            self.play(GrowArrow(arrow), FadeIn(bottom[i], shift=LEFT * SPACE_2), run_time=BEAT)

        stats = Mono(
            f"{result.taps_per_pixel:.1f} taps per pixel  ·  {result.gpu_ms:.3f} ms on the GPU",
            font_size=TEXT_SM,
        ).to_edge(DOWN, buff=SPACE_3)
        self.play(Write(stats))
        self.wait()
