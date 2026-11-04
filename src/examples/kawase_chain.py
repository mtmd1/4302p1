"""Kawase 3b: chaining gaussians stays gaussian, and chaining boxes becomes one.

    uv run render kawase_chain

Every curve is a real kernel. The bell is kawase_convolve's last kernel, with a dashed
gaussian of the same variance and scale over it, and any misfit would show.
"""

from style import *

from kawase_convolve import PASSES, matching_gaussian, middle_row, offsets

# The two equations: a shared height, with a wider slot for each result
SLOT_WIDTH, SLOT_HEIGHT = 1.5, 1.25
RESULT_WIDTH = 2.7
ROW_NAME_X, FIRST_SLOT_X = -FILL_WIDTH / 2, -2.43
BOX_WIDTH, BOX_STEP = 0.9, 1.2
BOX_LEFT = -2.73  # Centre of the first box
GAUSSIAN_Y, BOX_Y = 1.25, -1.1
PEAK_HEADROOM = 1.12
DASHES = 30
SAMPLES = 120
# The top row's kernels: real samples of a gaussian, on the one scale so "wider" is literal
SIGMA = 2.0
REACH = 9
BOX_REACH = 3  # Each box's axis runs this many cells either side


class Slot:
    """Bare axes for one kernel in an equation, centred on (x, y)."""

    def __init__(self, x: float, y: float, reach: float, peak: float, width: float = SLOT_WIDTH):
        self.origin = np.array([x, y - SLOT_HEIGHT / 2, 0.0])
        self.reach, self.peak, self.width = reach, peak, width

    def point(self, x: float, y: float) -> np.ndarray:
        return self.origin + np.array([x / self.reach * self.width / 2, y / self.peak / PEAK_HEADROOM * SLOT_HEIGHT, 0.0])

    def base(self) -> Line:
        return Line(self.point(-self.reach, 0), self.point(self.reach, 0), color=MUTED, stroke_width=STROKE)

    def trace(self, xs, ys, color) -> VGroup:
        line = VMobject(color=color, stroke_width=STROKE)
        line.set_points_as_corners([self.point(x, y) for x, y in zip(xs, ys)])
        return VGroup(self.base(), line)


def gaussian_row(sigma: float) -> np.ndarray:
    """A gaussian's samples, summing to 1, over offsets -REACH to REACH."""
    row = np.exp(-(np.arange(-REACH, REACH + 1) ** 2) / (2 * sigma**2))
    return row / row.sum()


def box_trace(slot: Slot) -> VGroup:
    """A 3-tap box, with its hard edges."""
    return slot.trace((-BOX_REACH, -1, -1, 1, 1, BOX_REACH), (0, 0, 1, 1, 0, 0), BOX)


def bell_trace(slot: Slot) -> VGroup:
    """kawase_convolve's final kernel, and over it the true gaussian on the same scale."""
    row = middle_row(PASSES)
    kernel = slot.trace(offsets(PASSES), row / row.max(), BOX)
    xs = np.linspace(-PASSES, PASSES, SAMPLES)
    heights, _ = matching_gaussian(PASSES, xs)
    true = VMobject(color=GAUSSIAN, stroke_width=STROKE_BOLD)
    true.set_points_smoothly([slot.point(x, y) for x, y in zip(xs, heights)])
    return VGroup(kernel, DashedVMobject(true, num_dashes=DASHES))


def operator(tex: str, x: float, y: float) -> MathTex:
    return MathTex(tex, font_size=TEXT_LG, color=TEXT).move_to([x, y, 0.0])


class Chain(ClipScene):
    def construct(self):
        result_x = FILL_WIDTH / 2 - RESULT_WIDTH / 2
        bell_slot = Slot(result_x, BOX_Y, PASSES, 1.0, width=RESULT_WIDTH)

        # Nothing yet: the clip is placed here, and the first chain waits for its words
        self.cue("as it turns out")

        # Gaussian after gaussian: one wider gaussian, on the one scale, so lower too
        self.cue("chaining gaussian blurs")
        once = gaussian_row(SIGMA)
        twice = np.convolve(once, once)[REACH:-REACH]
        spots = FIRST_SLOT_X + (SLOT_WIDTH + SPACE_3 + SPACE_2) * np.arange(2)
        row_name = Text("gaussian", font_size=TEXT_BASE, color=GAUSSIAN)
        row_name.move_to([ROW_NAME_X, GAUSSIAN_Y, 0.0], aligned_edge=LEFT)
        xs = np.arange(-REACH, REACH + 1)
        first = Slot(spots[0], GAUSSIAN_Y, REACH, once.max()).trace(xs, once, GAUSSIAN)
        second = Slot(spots[1], GAUSSIAN_Y, REACH, once.max()).trace(xs, once, GAUSSIAN)
        times = operator(r"\ast", (spots[0] + spots[1]) / 2, GAUSSIAN_Y)
        equals_x = result_x - RESULT_WIDTH / 2 - SPACE_3
        equals = operator("=", equals_x, GAUSSIAN_Y)
        wider = Slot(result_x, GAUSSIAN_Y, REACH, once.max(), width=RESULT_WIDTH).trace(xs, twice, GAUSSIAN)
        self.play(
            FadeIn(row_name), FadeIn(first), FadeIn(times), FadeIn(second),
            run_time=MOVE, rate_func=EASE,
        )
        self.play(FadeIn(equals), FadeIn(wider), run_time=MOVE, rate_func=EASE)

        # Box after box after box, in the order they chain, and only then the bell they make
        self.cue("but chaining box blurs")
        box_name = Text("box", font_size=TEXT_BASE, color=BOX)
        box_name.move_to([ROW_NAME_X, BOX_Y, 0.0], aligned_edge=LEFT)
        boxes = [box_trace(Slot(BOX_LEFT + i * BOX_STEP, BOX_Y, BOX_REACH, 1.0, width=BOX_WIDTH)) for i in range(3)]
        stars = [operator(r"\ast", BOX_LEFT + (i + 0.5) * BOX_STEP, BOX_Y) for i in range(3)]
        dots = operator(r"\cdots", BOX_LEFT + 2.5 * BOX_STEP + SPACE_3, BOX_Y)
        result_name = Text("gaussian", font_size=TEXT_SM, color=GAUSSIAN)
        result_name.next_to(bell_slot.point(0, 0), DOWN, buff=SPACE_1)
        self.play(FadeIn(box_name), FadeIn(boxes[0]), run_time=BEAT, rate_func=EASE)
        for i in (1, 2):
            self.play(FadeIn(stars[i - 1]), FadeIn(boxes[i]), run_time=BEAT, rate_func=EASE)
        self.play(
            FadeIn(stars[2]), FadeIn(dots), FadeIn(operator("=", equals_x, BOX_Y)), FadeIn(result_name),
            FadeIn(bell_trace(bell_slot)),
            run_time=BEAT, rate_func=EASE,
        )

        # Both rows hold until the next graphic
        self.cue("When a GPU looks up")
