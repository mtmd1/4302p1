"""Box blur 3: the full photo, a 41x41 kernel to scale, a spinner, then the blur.

    uv run render box_41

Ends on the blurred image; the TADA is added in Resolve, so the blur lands
TADA_ROOM ahead of "Wow".
"""

from style import *

import blur
from components import FIGURES, credit, grey, photo_still
from sample import photo

SPIN_SPEED = TAU * 1.2  # Radians per second
SPINNER_RADIUS = 0.45
SPINNER_SWEEP = 1.5 * PI  # How much of the circle the spinner's arc covers
LOADING_GREY = 0.3  # Value of the grey laid over the whole photo while it loads
LOADING_OPACITY = 0.75

KERNEL = 2 * FIGURES.radius_box + 1
SKY = (1600, 200)  # Centre of the kernel, in source pixels: clear sky, top right
KERNEL_OPACITY = 0.7
TADA_ROOM = 0.7  # Seconds between the blur landing and "Wow"

IMAGE = photo()
BLURRED = blur.box(IMAGE, FIGURES.radius_box).image


class FortyOne(ClipScene):
    def construct(self):
        sharp = photo_still(IMAGE)
        blurred = photo_still(BLURRED)
        source = credit("Blur ported from Acerola, youtube.com")
        self.add(sharp, source)
        self.cue("Let's try a 41 by 41")

        # Drawn to scale, solid so its size reads, on empty sky
        unit = sharp.width / IMAGE.shape[1]
        origin = sharp.get_corner(UL)
        centre = origin + RIGHT * (SKY[0] + 0.5) * unit + DOWN * (SKY[1] + 0.5) * unit
        kernel = Square(KERNEL * unit, stroke_width=0, fill_color=HIGHLIGHT, fill_opacity=KERNEL_OPACITY).move_to(centre)
        size = Mono(f"{KERNEL} x {KERNEL}", font_size=TEXT_SM, color=TEXT).next_to(kernel, LEFT, buff=SPACE_1)
        self.cue("forty-one by forty-one")
        self.play(FadeIn(kernel), FadeIn(size), run_time=BEAT, rate_func=EASE)

        # Loading: the whole photo greys, with only the white spinner on it
        loading = Rectangle(
            width=sharp.width, height=sharp.height, stroke_width=0, fill_color=grey(LOADING_GREY), fill_opacity=LOADING_OPACITY
        ).move_to(sharp)
        arc = Arc(radius=SPINNER_RADIUS, start_angle=0, angle=SPINNER_SWEEP, color=TEXT, stroke_width=STROKE_BOLD)
        arc.move_to(sharp)
        arc.add_updater(lambda m, dt: m.rotate(SPIN_SPEED * dt, about_point=sharp.get_center()))
        self.cue("box blur on this image")
        self.play(FadeIn(loading), FadeIn(arc), run_time=QUICK, rate_func=EASE)

        # Hold so the change below ends TADA_ROOM before "Wow", wherever the cut puts it
        landing = cue_time("Wow, that took") - self._cue_origin - TADA_ROOM
        self.wait(landing - QUICK - self.renderer.time)

        arc.clear_updaters()
        self.play(
            FadeIn(blurred),
            FadeOut(VGroup(loading, arc, kernel, size)),
            run_time=QUICK,
            rate_func=EASE,
        )
        self.cue("the roughly 4.5 milliseconds")
