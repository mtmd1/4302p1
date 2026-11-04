"""Kawase 4: a bilinear lookup between four pixels, then the single tap at their corner.

    uv run render kawase_bilinear

(u, v) runs 0 to 1 between the pixel centres. Each centre reaches the point by an L: a
horizontal leg to the point's column, then a vertical leg to the point, thick as that
centre's weight. The equation's terms take their corner's colour.
"""

from style import *

from components import TapPoint, grey

VALUES = ((0.10, 0.62), (0.44, 0.28))  # Dark enough that the corner colours read on all
TERMS = ((r"(1-u)(1-v)\,p_{00}", r"u(1-v)\,p_{10}"), (r"(1-u)\,v\,p_{01}", r"u\,v\,p_{11}"))
# One hue per corner, for its L, its centre and its term. Only here: not methods, and
# kept off POINT's red and HIGHLIGHT's yellow, which the tap and the 2 x 2 use
CORNER_COLOURS = ((ManimColor("#56E0F0"), ManimColor("#FF9A3D")), (ManimColor("#FF7AD9"), ManimColor("#B8F15A")))
CELL = 2.1
GRID_X = -FILL_WIDTH / 2 + CELL  # Against the left of the FILL area
PANEL_LEFT = GRID_X + CELL + SPACE_3  # Close to the graphic
COORDINATE_Y, TITLE_Y = 1.85, 1.3
EQUATION_ROWS = (0.2, -0.45, -1.1, -1.75)  # A row per term, all one sum
NEAR = 0.4  # Pixel value labels, outward from the middle where the legs run
DOT_RADIUS = 0.07
LEG_WIDEST = 24  # Stroke of a leg at weight 1
STROKE_UNIT = 0.01  # Manim units per unit of stroke width
WANDER_REACH = 0.45  # From the middle to the wander's limit: stays well between the centres
WANDER_SEED = 4302
WANDER_WAVES = 3
WANDER_SPEED = (0.5, 1.1)  # Radians per second, slowest and fastest wave
BLOCK_OPACITY = 0.14


def weights(u: float, v: float) -> np.ndarray:
    """Bilinear weights of the four pixels, in the shape of VALUES."""
    return np.array(((1 - u) * (1 - v), u * (1 - v), (1 - u) * v, u * v)).reshape(2, 2)


def centre_of(r: int, c: int) -> np.ndarray:
    return np.array([GRID_X + (c - 0.5) * CELL, (0.5 - r) * CELL, 0.0])


def to_point(u: float, v: float) -> np.ndarray:
    return np.array([GRID_X + (u - 0.5) * CELL, (0.5 - v) * CELL, 0.0])


class Wander:
    """A smooth, seeded path around the middle: a few slow sine waves on each axis."""

    def __init__(self):
        rng = np.random.default_rng(WANDER_SEED)
        self.speeds = rng.uniform(*WANDER_SPEED, size=(2, WANDER_WAVES))
        self.phases = rng.uniform(0, TAU, size=(2, WANDER_WAVES))

    def at(self, t: float) -> tuple[float, float]:
        waves = np.sin(self.speeds * t + self.phases).sum(axis=1) / WANDER_WAVES
        u, v = 0.5 + WANDER_REACH * waves
        return float(u), float(v)


def legs(u: float, v: float, widths: np.ndarray, opacity: float) -> VGroup:
    """The four L shapes. Two sharing a vertical leg run side by side, so each keeps its thickness."""
    at = to_point(u, v)
    shapes = VGroup()
    for (r, c), share in np.ndenumerate(widths):
        width = max(share * LEG_WIDEST, STROKE_THIN)
        shift = (1 if c else -1) * width * STROKE_UNIT / 2
        centre = centre_of(r, c)
        path = VMobject(color=CORNER_COLOURS[r][c], stroke_width=width, stroke_opacity=opacity)
        path.set_points_as_corners([centre, [at[0] + shift, centre[1], 0.0], [at[0] + shift, at[1], 0.0]])
        shapes.add(path)
    return shapes.set_z_index(2)


class Bilinear(ClipScene):
    def construct(self):
        wander = Wander()
        clock = ValueTracker(0)
        clock.add_updater(lambda m, dt: m.increment_value(dt))
        # 0 wanders, 1 sits on the corner where the four pixels meet
        settle = ValueTracker(0)

        def uv() -> tuple[float, float]:
            u, v = wander.at(clock.get_value())
            pull = settle.get_value()
            return u + (0.5 - u) * pull, v + (0.5 - v) * pull

        pixels, dots, values = VGroup(), VGroup(), VGroup()
        for (r, c), value in np.ndenumerate(np.array(VALUES)):
            centre = centre_of(r, c)
            fill = grey(value)
            pixels.add(Square(CELL, stroke_color=MUTED, stroke_width=STROKE_THIN, fill_color=fill, fill_opacity=1).move_to(centre))
            dots.add(Dot(centre, radius=DOT_RADIUS, color=CORNER_COLOURS[r][c]))
            values.add(Mono(f"{value:.2f}", font_size=TEXT_BASE, color=text_on(fill)).move_to(centre + UP * (NEAR if r == 0 else -NEAR)))
        dots.set_z_index(3)
        values.set_z_index(3)

        tap = TapPoint().set_z_index(4)
        tap.add_updater(lambda m: m.move_to(to_point(*uv())))
        tap.update()

        self.cue("When a GPU looks up")
        self.play(FadeIn(pixels), FadeIn(values), FadeIn(tap), run_time=MOVE, rate_func=EASE)
        self.add(clock)  # A fade freezes what it fades, so the wander starts once the tap is in

        def entrance() -> tuple[ValueTracker, Animation]:
            """Fades something redrawn every frame, which FadeIn would freeze until it landed."""
            shown = ValueTracker(0)
            return shown, shown.animate.set_value(1)

        # Its coordinates, as they're mentioned
        self.cue("non-integer coordinates")
        coordinate_name = MathTex("(u, v)", font_size=TEXT_BASE, color=MUTED)
        coordinate_name.move_to([PANEL_LEFT, COORDINATE_Y, 0.0], aligned_edge=LEFT)
        coordinate_shown, coordinate_in = entrance()
        coordinate = always_redraw(lambda: Mono(
            "(%.2f, %.2f)" % uv(), font_size=TEXT_BASE, color=POINT
        ).set_opacity(coordinate_shown.get_value()).next_to(coordinate_name, RIGHT, buff=SPACE_2))
        self.add(coordinate)
        self.play(FadeIn(coordinate_name), coordinate_in, run_time=MOVE, rate_func=EASE)

        # The one equation, too long for a line: each term in its corner's colour
        self.cue("The most common method")
        title = Text("bilinear filtering", font_size=TEXT_BASE, color=TEXT)
        title.move_to([PANEL_LEFT, TITLE_Y, 0.0], aligned_edge=LEFT)
        first = MathTex(r"\text{value}", "=", np.ravel(TERMS)[0], font_size=TEXT_BASE, color=TEXT)
        first.move_to([PANEL_LEFT, EQUATION_ROWS[0], 0.0], aligned_edge=LEFT)
        equation = VGroup(first)
        for term, y in zip(np.ravel(TERMS)[1:], EQUATION_ROWS[1:]):
            line = MathTex("+", term, font_size=TEXT_BASE, color=TEXT)
            line.shift(first[1].get_center() - line[0].get_center())  # Under the equals
            line[1].align_to(first[2], LEFT)
            equation.add(line.set_y(y))
        for line, colour in zip(equation, np.ravel(CORNER_COLOURS)):
            line[-1].set_color(colour)
        self.play(FadeIn(title), FadeIn(equation), run_time=MOVE, rate_func=EASE)

        # The weighted average: an L per corner, thick as its weight
        self.cue("a weighted average")
        connections_shown, connections_in = entrance()
        connections = always_redraw(lambda: legs(*uv(), weights(*uv()), connections_shown.get_value()))
        self.add(connections)
        self.play(connections_in, FadeIn(dots), run_time=MOVE, rate_func=EASE)

        # Exactly where the four meet: equal weights, so the 2 x 2 reads as one
        self.cue("So, when we sample")
        self.play(settle.animate.set_value(1), run_time=MOVE, rate_func=EASE)
        self.cue("a two by two box")
        block = Square(2 * CELL, color=HIGHLIGHT, stroke_width=STROKE_BOLD, fill_color=HIGHLIGHT, fill_opacity=BLOCK_OPACITY)
        block.move_to(to_point(0.5, 0.5)).set_z_index(1)
        self.play(FadeIn(block), run_time=BEAT, rate_func=EASE)
        self.cue("Kawase takes four")
