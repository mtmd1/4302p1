"""Gaussian 3: sigma outgrows a fixed kernel and boxes appear; the kernel catches up, at a price.

    uv run render gauss_sigma

A banner of the town's lights over two panels: the kernel, and later its cost.
Blurs are real and redone per frame from the trackers, so the sigma and r shown
are the ones used. The photo is at half resolution, so r = 6 is big enough on
screen for the squares to read.
"""

from style import *

import blur
from components import LAMP, photo_still
from sample import photo

CROP = (540, 660, 1080, 360)  # x, y, width, height in source pixels; halved below. Keeps LAMP and the bright lights
RADIUS = 6
SIGMA_START = 1.0
SIGMA_MIDDLE = 3.0
SIGMA_END = 7.0
RADIUS_END = 21  # 3 sigma, so the kernel is at least 6 sigma wide

CLIMB = 2.0  # Seconds for sigma to reach SIGMA_MIDDLE
OVERTAKE = 4.2  # Seconds for sigma to run past the window
GROW = 3.0  # Seconds for the window to catch up

GRAPHIC_WIDTH = 8.4  # With a 3:1 banner, as wide as still leaves room for the panels inside FILL_HEIGHT
BANNER_TOP = FILL_HEIGHT / 2
PANEL_WIDTH = (GRAPHIC_WIDTH - SPACE_2) / 2
PANEL_BOTTOM = -FILL_HEIGHT / 2
PLOT_HEIGHT = 1.4
SQUARE_SIDE = 1.45  # Of the square at the final kernel width; true to scale below that
EXTENT = 24  # Pixels either side of centre on the plot
TOP = 1.15  # Top of the y axis, with the bell's peak at 1
SAMPLES = 121
WINDOW_FILL = 0.18
TAIL_FILL = 0.75
LAMP_AT = ((LAMP[0] - CROP[0]) // 2, (LAMP[1] - CROP[1]) // 2)  # In the halved crop
INSET_PIXELS = (32, 18)  # Crop pixels magnified in the inset
INSET_WIDTH = 1.7


def source() -> np.ndarray:
    x, y, width, height = CROP
    patch = photo()[y : y + height, x : x + width]
    return patch.reshape(height // 2, 2, width // 2, 2, 4).mean(axis=(1, 3)).astype(np.float32)


class GaussSigma(ClipScene):
    def construct(self):
        image = source()
        sigma = ValueTracker(SIGMA_START)
        radius = ValueTracker(RADIUS)
        last = {}

        def render() -> np.ndarray:
            key = (sigma.get_value(), round(radius.get_value()))
            if last.get("key") != key:
                result = blur.gaussian(image, key[0], radius=key[1], separable=True)
                last.update(key=key, pixels=blur.to_uint8(result.image))
            return last["pixels"]

        still = photo_still(render(), width=GRAPHIC_WIDTH)
        still.move_to(UP * BANNER_TOP, aligned_edge=UP)
        still.add_updater(lambda m: setattr(m, "pixel_array", render()))

        left_x, right_x = (side * (PANEL_WIDTH + SPACE_2) / 2 for side in (-1, 1))

        # Left panel, top to bottom: name, plot and its bounds, parameters
        kernel = Text("kernel", font_size=TEXT_XS, color=TEXT)
        kernel.next_to(still, DOWN, buff=SPACE_2).set_x(left_x)
        axes = Axes(
            x_range=[-EXTENT, EXTENT, EXTENT],
            y_range=[0, TOP, TOP],
            x_length=PANEL_WIDTH,
            y_length=PLOT_HEIGHT,
            tips=False,
            axis_config={"color": MUTED, "stroke_width": STROKE_THIN, "include_ticks": False},
        )
        axes.y_axis.set_opacity(0)  # It would run up the middle of the bell
        axes.next_to(kernel, DOWN, buff=SPACE_1).set_x(left_x)

        def weight(x):
            return np.exp(-(x**2) / (2 * sigma.get_value() ** 2))

        def area(start: float, end: float, color, opacity: float) -> VMobject:
            xs = np.linspace(start, end, SAMPLES)
            points = [axes.c2p(start, 0), *(axes.c2p(x, weight(x)) for x in xs), axes.c2p(end, 0)]
            return Polygon(*points, stroke_width=0, fill_color=color, fill_opacity=opacity)

        def tails() -> VGroup:
            r = radius.get_value()
            shapes = VGroup()
            if r < EXTENT:
                shapes.add(area(-EXTENT, -r, HIGHLIGHT, TAIL_FILL), area(r, EXTENT, HIGHLIGHT, TAIL_FILL))
            return shapes

        def window() -> VGroup:
            r = radius.get_value()
            return VGroup(
                area(-r, r, GAUSSIAN, WINDOW_FILL),
                Line(axes.c2p(-r, 0), axes.c2p(-r, TOP), color=TEXT, stroke_width=STROKE),
                Line(axes.c2p(r, 0), axes.c2p(r, TOP), color=TEXT, stroke_width=STROKE),
                Mono("-r", font_size=TEXT_XS, color=TEXT).next_to(axes.c2p(-r, 0), DOWN, buff=SPACE_1),
                Mono("r", font_size=TEXT_XS, color=TEXT).next_to(axes.c2p(r, 0), DOWN, buff=SPACE_1),
            )

        def curve() -> VMobject:
            xs = np.linspace(-EXTENT, EXTENT, SAMPLES)
            line = VMobject(stroke_color=GAUSSIAN, stroke_width=STROKE)
            return line.set_points_as_corners([axes.c2p(x, weight(x)) for x in xs])

        # Invisible templates that fix where the live readouts sit, left-aligned so they hold still
        parameters = VGroup(
            Mono("σ = 0.0", font_size=TEXT_SM),
            Mono("r = 00", font_size=TEXT_SM),
        ).arrange(RIGHT, buff=SPACE_3)
        parameters.move_to([left_x, PANEL_BOTTOM, 0], aligned_edge=DOWN)

        def sigma_value() -> Mono:
            text = f"σ = {sigma.get_value():.1f}"
            return Mono(text, font_size=TEXT_SM, color=GAUSSIAN).move_to(parameters[0], aligned_edge=LEFT)

        def radius_value() -> Mono:
            text = f"r = {round(radius.get_value())}"
            return Mono(text, font_size=TEXT_SM, color=TEXT).move_to(parameters[1], aligned_edge=LEFT)

        # Right panel, bottom to top: taps, and the square it describes
        def width() -> int:
            return 2 * round(radius.get_value()) + 1

        readout = Mono("taps = 0000", font_size=TEXT_SM)
        readout.move_to([right_x, PANEL_BOTTOM, 0], aligned_edge=DOWN)

        labelled = ValueTracker(0)  # Its opacity: it fades in while its digits are still changing

        def taps_value() -> Mono:
            label = Mono(f"taps = {width() ** 2}", font_size=TEXT_SM, color=TEXT).move_to(readout, aligned_edge=LEFT)
            return label.set_opacity(labelled.get_value())

        def cost() -> Square:
            side = SQUARE_SIDE * width() / (2 * RADIUS_END + 1)
            square = Square(side, stroke_width=0, fill_color=GAUSSIAN, fill_opacity=1)
            return square.next_to(readout, UP, buff=SPACE_2).set_x(right_x)

        drawn = [always_redraw(f) for f in (window, tails, curve, radius_value)]
        self.add(still, axes, kernel, *drawn)
        self.cue("This gives us a second parameter")

        self.cue("the standard deviation sigma")
        self.play(FadeIn(always_redraw(sigma_value)), run_time=MOVE, rate_func=EASE)

        self.cue("Increasing it makes")
        self.play(sigma.animate.set_value(SIGMA_MIDDLE), run_time=CLIMB, rate_func=EASE)
        self.cue("until boxes reappear")

        # A magnified lamp over the dark beach, where the square is easy to see
        def lamp_pixels() -> np.ndarray:
            x, y = LAMP_AT
            half_w, half_h = INSET_PIXELS[0] // 2, INSET_PIXELS[1] // 2
            return render()[y - half_h : y + half_h, x - half_w : x + half_w]

        unit = still.width / image.shape[1]
        marker = Rectangle(width=INSET_PIXELS[0] * unit, height=INSET_PIXELS[1] * unit, color=TEXT, stroke_width=STROKE_THIN)
        marker.move_to(still.get_corner(UL) + unit * np.array([LAMP_AT[0], -LAMP_AT[1], 0.0]))
        inset = ImageMobject(lamp_pixels()).set_resampling_algorithm(RESAMPLING_ALGORITHMS["nearest"])
        inset.width = INSET_WIDTH
        inset.next_to(marker, RIGHT, buff=SPACE_3).align_to(still, DOWN).shift(UP * SPACE_1)
        inset.add_updater(lambda m: setattr(m, "pixel_array", lamp_pixels()))
        frame = SurroundingRectangle(inset, buff=0, color=TEXT, stroke_width=STROKE_THIN)
        link = Line(marker.get_right(), frame.get_left(), color=TEXT, stroke_width=STROKE_THIN)
        self.play(FadeIn(marker), FadeIn(link), FadeIn(inset), FadeIn(frame), run_time=BEAT, rate_func=EASE)

        self.play(sigma.animate.set_value(SIGMA_END), run_time=OVERTAKE, rate_func=EASE)
        self.cue("To fix this")

        # What the fix will cost: for now just the kernel's area, as its taps are yet to be counted
        self.play(FadeIn(always_redraw(cost)), run_time=MOVE, rate_func=EASE)
        self.cue("the width of our kernel")

        self.add(always_redraw(taps_value))
        self.play(
            labelled.animate(run_time=MOVE, rate_func=EASE).set_value(1),
            radius.animate(run_time=GROW, rate_func=EASE).set_value(RADIUS_END),
        )
        self.cue("At roughly the same kernel size")
