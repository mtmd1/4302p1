"""Demo: crank up sigma at a fixed radius until the box artifacts return.

    uv run manim -pql src/examples/demo_gaussian_sweep.py GaussianSweep
"""

from manim import *

import blur
from sample import test_card

RADIUS = 6


class GaussianSweep(Scene):
    def construct(self):
        source = test_card()
        sigma = ValueTracker(0.5)
        stats = {}

        def render():
            result = blur.gaussian(source, sigma.get_value(), radius=RADIUS, separable=True)
            stats["ms"] = result.gpu_ms
            return blur.to_uint8(result.image)

        # The blur reruns on the GPU every frame, driven by the tracker
        image = ImageMobject(render()).set_resampling_algorithm(RESAMPLING_ALGORITHMS["nearest"])
        image.height = 5.5
        image.add_updater(lambda m: setattr(m, "pixel_array", render()))

        sigma_label = VGroup(MathTex(r"\sigma ="), DecimalNumber(sigma.get_value(), num_decimal_places=1))
        sigma_label.add_updater(lambda g: g[1].set_value(sigma.get_value()))
        sigma_label.arrange(RIGHT).next_to(image, DOWN).align_to(image, LEFT)

        radius_label = MathTex(rf"r = {RADIUS}").next_to(image, DOWN)
        timing = always_redraw(
            lambda: Text(f"{stats['ms']:.3f} ms", font_size=28).next_to(image, DOWN).align_to(image, RIGHT)
        )

        self.add(image)
        self.play(FadeIn(sigma_label), FadeIn(radius_label), FadeIn(timing))
        self.play(sigma.animate.set_value(2.0), run_time=2)
        self.wait(0.5)

        # Past sigma = r / 3 the kernel truncates the Gaussian and squares appear
        self.play(sigma.animate.set_value(12.0), run_time=4, rate_func=linear)
        warning = Text("kernel too small for σ", font_size=32, color=YELLOW).next_to(image, UP)
        self.play(Write(warning))
        self.wait()
