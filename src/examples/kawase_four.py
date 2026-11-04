"""Kawase 5: four taps at the corners of a pixel add up to 1 2 1 / 2 4 2 / 1 2 1.

    uv run render kawase_four
"""

from style import *

from components import NumberGrid, TapPoint, credit

CELL = 1.25
BLOCK_OPACITY = 0.3  # One tap's 2 x 2; overlaps build up over one another
CORNERS = ((-1, 1), (1, 1), (-1, -1), (1, -1))  # Reading order, as (x, y) signs
GRID_LEFT_X, PLOT_X = -2.75, 2.55
PLOT_WIDTH, PLOT_HEIGHT = 4.3, 3.0
PLOT_RANGE = 3
HEADROOM = 1.12
TICK = 0.08
DOT_RADIUS = 0.06
BOX_TRIANGLE = np.array([1, 2, 3, 2, 1]) / 3  # The middle row of the box kernel convolved with itself


def tap_counts() -> np.ndarray:
    """How many of the four 2 x 2 blocks cover each cell of the 3 x 3 patch."""
    counts = np.zeros((3, 3), dtype=int)
    for r in range(2):
        for c in range(2):
            counts[r : r + 2, c : c + 2] += 1
    return counts


def layer_opacity(layers: int) -> float:
    return 1 - (1 - BLOCK_OPACITY) ** layers


class Four(ClipScene):
    def construct(self):
        counts = tap_counts()
        grid = NumberGrid([[None] * 3 for _ in range(3)], cell=CELL)
        centre = Square(CELL, color=TEXT, stroke_width=STROKE).move_to(grid.point(1, 1)).set_z_index(2)
        self.cue("Kawase takes four")
        self.play(FadeIn(grid), FadeIn(centre), FadeIn(credit("Kawase, GDC 2003")), run_time=MOVE, rate_func=EASE)

        # One at a time: a tap lands on a corner and its 2 x 2 lights
        blocks, taps = VGroup(), VGroup()
        for x, y in CORNERS:
            at = grid.point(1, 1) + np.array([x, y, 0.0]) * CELL / 2
            tap = TapPoint().move_to(at).set_z_index(3)
            block = Square(2 * CELL, stroke_width=0, fill_color=KAWASE, fill_opacity=BLOCK_OPACITY).move_to(at)
            blocks.add(block)
            taps.add(tap)
            self.play(FadeIn(tap), FadeIn(block), run_time=BEAT, rate_func=EASE)

        # The counts, in the order they're spoken: centre, sides, corners
        self.cue("The centre ends up")
        numbers = VGroup()
        for value, phrase in ((4, "a weight of four"), (2, "the sides two"), (1, "and the corners one")):
            group = VGroup()
            for (r, c), count in np.ndenumerate(counts):
                if count == value:
                    ink = text_on(KAWASE, layer_opacity(count))
                    group.add(Mono(f"{count}", font_size=TEXT_LG, color=ink).move_to(grid.point(r, c)).set_z_index(3))
            numbers.add(group)
            self.cue(phrase)
            self.play(FadeIn(group), run_time=BEAT, rate_func=EASE)

        # Next to the triangle from before: the same shape
        self.cue("looks a lot like")
        patch = VGroup(grid, centre, blocks, taps, numbers)

        origin = np.array([PLOT_X, -PLOT_HEIGHT / 2, 0.0])

        def point(x: float, y: float) -> np.ndarray:
            return origin + np.array([x / PLOT_RANGE * PLOT_WIDTH / 2, y / HEADROOM * PLOT_HEIGHT, 0.0])

        def trace(xs, ys, color) -> VGroup:
            line = VMobject(color=color, stroke_width=STROKE)
            line.set_points_as_corners([point(x, y) for x, y in zip(xs, ys)])
            dots = VGroup(*(Dot(point(x, y), radius=DOT_RADIUS, color=color) for x, y in zip(xs, ys)))
            return VGroup(line, dots)

        axes = VGroup(
            Line(point(-PLOT_RANGE, 0), point(PLOT_RANGE, 0), color=MUTED, stroke_width=STROKE),
            Line(point(0, 0), point(0, HEADROOM), color=MUTED, stroke_width=STROKE),
        )
        for x in range(-PLOT_RANGE, PLOT_RANGE + 1):
            axes.add(Line(point(x, 0) + DOWN * TICK, point(x, 0) + UP * TICK, color=MUTED, stroke_width=STROKE))
            axes.add(Mono(f"{x}", font_size=TEXT_XS, color=MUTED).next_to(point(x, 0), DOWN, buff=SPACE_1))
        one = Line(point(0, 1) + LEFT * TICK, point(0, 1) + RIGHT * TICK, color=MUTED, stroke_width=STROKE)
        axes.add(one, Mono("1", font_size=TEXT_XS, color=MUTED).next_to(one, LEFT, buff=SPACE_1))

        # Both rows drop to zero one step past their last sample
        box_xs = np.arange(-3, 4)
        box_ys = np.concatenate(([0], BOX_TRIANGLE, [0]))
        box = trace(box_xs, box_ys, BOX)
        row = counts[1] / counts.max()
        kawase_xs = np.arange(-2, 3)
        kawase_ys = np.concatenate(([0], row, [0]))
        kawase = trace(kawase_xs, kawase_ys, KAWASE)

        names = VGroup(
            VGroup(
                Text("box", font_size=TEXT_SM, color=BOX),
                MathTex(r"\ast", font_size=TEXT_LG, color=BOX),
                Text("box", font_size=TEXT_SM, color=BOX),
            ).arrange(RIGHT, buff=SPACE_1),
            Text("Kawase", font_size=TEXT_SM, color=KAWASE),
        ).arrange(RIGHT, buff=SPACE_3)
        names.next_to(axes, UP, buff=SPACE_2)
        self.play(
            patch.animate.move_to([GRID_LEFT_X, 0, 0]), FadeIn(axes), FadeIn(box), FadeIn(names[0]),
            run_time=MOVE, rate_func=EASE,
        )
        self.play(Create(kawase[0]), FadeIn(kawase[1]), FadeIn(names[1]), run_time=MOVE, rate_func=EASE)
        self.cue("But repeat this as it is")
