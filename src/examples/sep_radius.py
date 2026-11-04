"""Separation 3: a 95 percent saving, but the cost still grows with the radius.

    uv run render sep_radius

First the saving: one pass and two passes side by side, from blur.py, the same
image for far fewer taps. Then one result becomes the preview beside a graph.
One value drives that: r moves the end of the line along taps = 2(2r + 1) and sets
the real blur beside it. That cost is linear, 4r + 2, so the line is straight, and
at r = 20 it's the 82 taps of the last clip.
"""

import functools

from style import *

import blur
from components import FIGURES, TapPoint, photo_still
from sample import photo

# The 2 x 2
FRAME_WIDTH = 3.95
FRAME_HEIGHT = FRAME_WIDTH * 9 / 16
ROW_GAP = FILL_HEIGHT - 2 * FRAME_HEIGHT  # Between the rows, for the -95% arrow
COLUMN_GAP = FILL_WIDTH - 2 * FRAME_WIDTH  # Between source and result, for the arrows and kernels
KERNEL_SIZE = 0.9  # Each kernel's long side
ARROW_DROP = 0.2  # Arrows sit this far below a row's centre, so kernel and arrow centre on it
ARROW_STYLE = dict(  # The same stroke and tip whatever an arrow's length
    color=HIGHLIGHT, stroke_width=STROKE, tip_length=0.2, max_tip_length_to_length_ratio=1, max_stroke_width_to_length_ratio=20,
)
STRIP_CELLS = 4  # How many cells thick a 1D kernel is drawn, so it stays visible

# The preview and graph
R_START = FIGURES.radius_box
R_TOP = 80  # Where the radius ends up
SIGMA_PER_R = FIGURES.sigma_gaussian / FIGURES.radius_box  # So r = 20 is the same sigma = 7 blur as before
IMAGE_WIDTH = 5.6
GRAPH_WIDTH = FILL_WIDTH - IMAGE_WIDTH - SPACE_3
GRAPH_HEIGHT = 2.3
R_AXIS = 88  # Far end of the x axis, past R_TOP so the point stays on the graph
TAPS_AXIS = 360  # Far end of the y axis
LINE_WIDTH = TapPoint().width * 100  # Stroke widths are in hundredths of a unit, so the line is as thick as the point
GROW = 2.4  # Seconds for the point to run out to R_TOP


def taps(r: int) -> int:
    return 2 * (2 * r + 1)


@functools.lru_cache(maxsize=2)
def blurred(r: int) -> np.ndarray:
    """The real separated blur at radius r. Too large to keep them all, and quick to redo."""
    return blur.to_uint8(blur.gaussian(photo(), r * SIGMA_PER_R, r, separable=True).image)


def one_pass() -> np.ndarray:
    """The real unseparated blur, which must match the separated one on screen."""
    result = blur.to_uint8(blur.gaussian(photo(), FIGURES.sigma_gaussian, FIGURES.radius_box).image)
    if np.abs(result.astype(int) - blurred(R_START)).max() > 1:
        raise ValueError("Separated blur differs visibly from the unseparated one")
    return result


def heat_image(weights: np.ndarray, length: float) -> ImageMobject:
    """Kernel weights as a magma image whose longest side is length, every cell crisp."""
    pixels = np.array([[magma(w / weights.max()).to_int_rgba() for w in row] for row in weights], dtype=np.uint8)
    still = ImageMobject(pixels).set_resampling_algorithm(RESAMPLING_ALGORITHMS["nearest"])
    return still.scale_to_fit_width(length) if pixels.shape[1] >= pixels.shape[0] else still.scale_to_fit_height(length)


def kernels() -> tuple[Group, Group, Group]:
    """The 41 x 41 kernel, its row and its column, framed, each KERNEL_SIZE long."""
    x = np.arange(-R_START, R_START + 1)
    line = np.exp(-(x**2) / (2 * FIGURES.sigma_gaussian**2))
    full = heat_image(np.outer(line, line), KERNEL_SIZE)
    row = heat_image(np.tile(line, (STRIP_CELLS, 1)), KERNEL_SIZE)
    column = heat_image(np.tile(line[:, None], (1, STRIP_CELLS)), KERNEL_SIZE)
    return tuple(
        Group(still, SurroundingRectangle(still, buff=0, color=MUTED, stroke_width=STROKE_THIN))
        for still in (full, row, column)
    )


def framed(image: np.ndarray, x: float, y: float) -> Group:
    still = photo_still(image, width=FRAME_WIDTH).move_to([x, y, 0])
    return Group(still, SurroundingRectangle(still, buff=0, color=MUTED, stroke_width=STROKE_THIN))


def operation(y: float, kernel_groups: list[Group]) -> tuple[VGroup, Group]:
    """Source to result across the gap at height y: one arrow per kernel, end to end, each
    kernel on its arrow."""
    reach = COLUMN_GAP - 2 * SPACE_1
    step = reach / len(kernel_groups)
    arrows = VGroup()
    for i, kernel in enumerate(kernel_groups):
        x = -reach / 2 + i * step
        arrow = Arrow([x, y - ARROW_DROP, 0], [x + step, y - ARROW_DROP, 0], buff=0, **ARROW_STYLE)
        kernel.next_to(arrow, UP, buff=SPACE_1)
        arrows.add(arrow)
    return arrows, Group(*kernel_groups)


class SepRadius(ClipScene):
    def construct(self):
        radius = ValueTracker(R_START)

        def r() -> int:
            return round(radius.get_value())

        # The saving: source to result, one pass above and two passes below
        source = photo()
        column_x = (FRAME_WIDTH + COLUMN_GAP) / 2
        row_y = (FRAME_HEIGHT + ROW_GAP) / 2
        full, row_kernel, column_kernel = kernels()

        top_source = framed(source, -column_x, row_y)
        top_result = framed(one_pass(), column_x, row_y)
        top_arrows, top_kernels = operation(row_y, [full])

        bottom_source = framed(source, -column_x, -row_y)
        bottom_result = framed(blurred(R_START), column_x, -row_y)
        bottom_arrows, bottom_kernels = operation(-row_y, [row_kernel, column_kernel])

        percent = 100 - round(100 * FIGURES.taps_separated / FIGURES.taps_box)
        saving_arrow = Arrow(UP * ROW_GAP / 2, DOWN * ROW_GAP / 2, buff=SPACE_1, **ARROW_STYLE)
        saving_label = VGroup(
            Mono(f"-{percent}%", font_size=TEXT_LG, color=TEXT),
            Text("taps", font_size=TEXT_LG, color=TEXT),
        ).arrange(RIGHT, buff=SPACE_1).next_to(saving_arrow, RIGHT, buff=SPACE_2)

        self.cue("That's 95 percent")
        self.play(
            FadeIn(top_source), FadeIn(top_kernels), *map(GrowArrow, top_arrows), FadeIn(top_result),
            run_time=MOVE, rate_func=EASE,
        )
        self.play(
            FadeIn(bottom_source), FadeIn(bottom_kernels), *map(GrowArrow, bottom_arrows),
            FadeIn(bottom_result),
            run_time=MOVE, rate_func=EASE,
        )
        self.cue("percent decrease")
        self.play(GrowArrow(saving_arrow), FadeIn(saving_label), run_time=MOVE, rate_func=EASE)

        # The two-pass result becomes the preview, with the graph's cell beside it
        image_at = LEFT * (GRAPH_WIDTH + SPACE_3) / 2
        cell_x = (IMAGE_WIDTH + SPACE_3) / 2

        axes = Axes(
            x_range=[0, R_AXIS, R_AXIS],
            y_range=[0, TAPS_AXIS, TAPS_AXIS],
            x_length=GRAPH_WIDTH,
            y_length=GRAPH_HEIGHT,
            tips=False,
            axis_config={"color": MUTED, "stroke_width": STROKE, "include_ticks": False},
        )
        axes.set_x(cell_x)

        # Each axis names itself and its current value: taps atop y, radius at the end of x.
        # Templates fix where they sit, so the digits hold still.
        taps_slot = Mono("taps = 000", font_size=TEXT_SM).next_to(axes.y_axis, UP, buff=SPACE_1)
        taps_slot.align_to(axes.y_axis, LEFT)
        radius_slot = Mono("radius = 00", font_size=TEXT_SM).next_to(axes.x_axis, DOWN, buff=SPACE_1)
        radius_slot.align_to(axes.x_axis, RIGHT)

        def readout() -> VGroup:
            return VGroup(
                Mono(f"taps = {taps(r())}", font_size=TEXT_SM, color=TEXT).move_to(taps_slot, aligned_edge=LEFT),
                Mono(f"radius = {r()}", font_size=TEXT_SM, color=TEXT).move_to(radius_slot, aligned_edge=LEFT),
            )

        def line_end() -> np.ndarray:
            value = radius.get_value()
            return axes.c2p(value, 2 * (2 * value + 1))

        # One point; its far end travels, leaving a line as thick as itself behind it
        start = axes.c2p(R_START, taps(R_START))
        point = TapPoint().move_to(start)
        head = TapPoint().move_to(start)
        head.add_updater(lambda m: m.move_to(line_end()))
        line = always_redraw(
            lambda: VMobject(stroke_color=POINT, stroke_width=LINE_WIDTH).set_points_as_corners([start, line_end()])
        )

        leaving = Group(
            top_source, top_kernels, top_arrows, top_result,
            bottom_source, bottom_kernels, bottom_arrows,
            saving_arrow, saving_label,
        )
        self.cue("but the cost still grows")
        self.play(
            FadeOut(leaving), bottom_result.animate.scale_to_fit_width(IMAGE_WIDTH).move_to(image_at),
            run_time=MOVE, rate_func=EASE,
        )
        # The cost arrives whole: the graph, its readouts and the point together
        self.play(FadeIn(axes), FadeIn(always_redraw(readout)), FadeIn(point), run_time=BEAT, rate_func=EASE)

        image = bottom_result[0]
        image.add_updater(lambda m: setattr(m, "pixel_array", blurred(r())))
        self.add(line, head)
        self.play(radius.animate.set_value(R_TOP), run_time=GROW, rate_func=EASE)
        self.cue("In his 2003 GDC talk")
