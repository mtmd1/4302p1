"""Kawase 3: a box kernel convolved with itself, again and again, becomes a gaussian.

    uv run render kawase_convolve

Every kernel on screen is computed by convolve() below. The clip stops dead on the
last kernel: the presenter cuts away to a gag there, and kawase_chain picks it up.
"""

from style import *

from components import NumberGrid

PASSES = 20  # Box kernels convolved together by the end: 41 x 41
BOX_KERNEL = np.ones((3, 3))
GRID_SIDE = 3.3  # The kernel's width on screen, whatever its size
PLOT_WIDTH, PLOT_HEIGHT = 4.5, 2.9
GRID_X, PLOT_X, BODY_Y = -2.75, 2.45, -0.55
EQUATION_Y = 2.35
PEAK_HEADROOM = 1.12  # Plot height, in units of the normalised peak
DOT_RADIUS = 0.05
TICK = 0.08
SPARSE_ABOVE = 4  # Past this range, the axis labels only its ends and centre
STAMP_OPACITY = 0.35  # The 3 x 3 kernel as it moves over the result
COUNT_OPACITY = 0.6  # Result cells, at the most overlaps
# All nine stamps in reading order: the first row slowly, so the method is clear
FIRST_ROW = 3
LATER_STAMP = 0.36
BURST = 1.2  # Seconds from "keep convolving" to the fastest sweep, as the gag's wipe opens
BURST_FIRST = 2  # Boxes in the kernel the burst starts from
BURST_RATIO = 0.85  # Each sweep's time as a share of the one before
GRID_PIXELS = 900  # Across the heatmap image at most
GRID_LINE_PIXELS = 3  # About STROKE_THIN at that size
GRID_LINES_GONE = 31  # Cells across at which the grid lines have faded out, leaving pure heat


def convolve(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Discrete 2D convolution: a copy of a stamped at every cell of b, scaled by it."""
    out = np.zeros((a.shape[0] + b.shape[0] - 1, a.shape[1] + b.shape[1] - 1))
    for (r, c), weight in np.ndenumerate(b):
        out[r : r + a.shape[0], c : c + a.shape[1]] += weight * a
    return out


KERNELS = {1: BOX_KERNEL}
for _n in range(2, PASSES + 1):
    KERNELS[_n] = convolve(KERNELS[_n - 1], BOX_KERNEL)


def middle_row(n: int) -> np.ndarray:
    kernel = KERNELS[n]
    return kernel[n]  # Radius n, so row n is the middle


def offsets(n: int) -> np.ndarray:
    return np.arange(-n, n + 1)


def matching_gaussian(n: int, xs: np.ndarray) -> tuple[np.ndarray, float]:
    """The gaussian with the variance of kernel n's middle row, scaled as that row is plotted.

    Row and gaussian both have unit area, then both divide by the row's peak, so any
    misfit shows. Returns the heights and sigma.
    """
    row = middle_row(n)
    weights = row / row.sum()
    sigma = float(np.sqrt(np.sum(weights * offsets(n) ** 2)))
    density = np.exp(-(xs**2) / (2 * sigma**2)) / (sigma * np.sqrt(TAU))
    return density / weights.max(), sigma


class Plot:
    """Axes for a kernel's middle row, normalised so its peak is 1."""

    def __init__(self, x_max: int):
        self.x_max = x_max
        self.origin = np.array([PLOT_X, BODY_Y - PLOT_HEIGHT / 2, 0.0])

    def point(self, x: float, y: float) -> np.ndarray:
        return self.origin + np.array([x / self.x_max * PLOT_WIDTH / 2, y / PEAK_HEADROOM * PLOT_HEIGHT, 0.0])

    def axes(self) -> VGroup:
        base = Line(self.point(-self.x_max, 0), self.point(self.x_max, 0), color=MUTED, stroke_width=STROKE)
        # At the left end rather than x = 0, clear of the curve at any scale
        spine = Line(self.point(-self.x_max, 0), self.point(-self.x_max, PEAK_HEADROOM), color=MUTED, stroke_width=STROKE)
        top = self.point(-self.x_max, 1)
        peak = Line(top + LEFT * TICK, top + RIGHT * TICK, color=MUTED, stroke_width=STROKE)
        one = Mono("1", font_size=TEXT_XS, color=MUTED).next_to(peak, LEFT, buff=SPACE_1)
        ticks, labels = VGroup(), VGroup()
        for x in range(-self.x_max, self.x_max + 1):
            at = self.point(x, 0)
            ticks.add(Line(at + DOWN * TICK, at + UP * TICK, color=MUTED, stroke_width=STROKE))
            if self.x_max <= SPARSE_ABOVE or x in (-self.x_max, 0, self.x_max):
                labels.add(Mono(f"{x}", font_size=TEXT_XS, color=MUTED).next_to(at, DOWN, buff=SPACE_1))
        return VGroup(base, spine, peak, one, ticks, labels)

    def curve(self, n: int) -> VMobject:
        if n == 1:
            # The box's hard edges
            return self.line_through([(-1, 0), (-1, 1), (0, 1), (1, 1), (1, 0)])
        return self.row_curve(middle_row(n))

    def row_curve(self, row: np.ndarray) -> VMobject:
        """Straight lines through a row's samples, falling to zero just past them."""
        n = len(row) // 2
        return self.line_through([(-n - 1, 0), *zip(offsets(n), row / row.max()), (n + 1, 0)])

    def line_through(self, points: list[tuple[float, float]]) -> VMobject:
        line = VMobject(color=BOX, stroke_width=STROKE)
        line.set_points_as_corners([self.point(x, y) for x, y in points])
        return line

    def dots(self, n: int) -> VGroup:
        return self.row_dots(middle_row(n))

    def row_dots(self, row: np.ndarray) -> VGroup:
        return VGroup(*(
            Dot(self.point(x, y), radius=DOT_RADIUS, color=BOX)
            for x, y in zip(offsets(len(row) // 2), row / row.max())
        ))


def heatmap(n: int) -> VGroup:
    kernel = KERNELS[n]
    cell = GRID_SIDE / kernel.shape[0]
    centre = np.array([GRID_X, BODY_Y, 0.0])
    half = (kernel.shape[0] - 1) / 2
    return VGroup(*(
        Square(cell, stroke_color=MUTED, stroke_width=STROKE_THIN, fill_color=magma(value / kernel.max()), fill_opacity=1)
        .move_to(centre + np.array([(c - half) * cell, (half - r) * cell, 0.0]))
        for (r, c), value in np.ndenumerate(kernel)
    ))


def magma_table() -> np.ndarray:
    """magma() as a lookup table, since the burst repaints the whole heatmap every frame."""
    return np.array([magma(t).to_rgb() for t in np.linspace(0, 1, 256)]) * 255


def heat_pixels(values: np.ndarray, table: np.ndarray) -> np.ndarray:
    """A heatmap of normalised values as an RGBA image, with grid lines while cells are big."""
    side = values.shape[0]
    cell = GRID_PIXELS // side
    rgb = table[np.round(values * 255).astype(int)]
    rgb = rgb.repeat(cell, axis=0).repeat(cell, axis=1)
    lines = 1 - min((side - BURST_FIRST * 2 - 1) / (GRID_LINES_GONE - BURST_FIRST * 2 - 1), 1)
    if lines > 0:
        grey = np.array(MUTED.to_rgb()) * 255
        along = np.arange(rgb.shape[0]) % cell < GRID_LINE_PIXELS
        mask = along[:, None] | along[None, :]
        rgb[mask] += (grey - rgb[mask]) * lines
    alpha = np.full((*rgb.shape[:2], 1), 255.0)
    return np.concatenate((rgb, alpha), axis=2).astype(np.uint8)


def sweep_schedule() -> np.ndarray:
    """When each sweep of the burst ends: a geometric series adding up to BURST."""
    times = BURST_RATIO ** np.arange(PASSES - BURST_FIRST)
    return np.cumsum(times / times.sum() * BURST)


def swept(n: int, progress: float) -> tuple[np.ndarray, int, int]:
    """The heatmap's values part way through convolving kernel n once more, read as a sweep.

    Normalised per kernel. Cells before the head hold the new kernel and cells after it
    the old one, padded to the new size. Returns the values and the head's row and column.
    """
    old, new = KERNELS[n], KERNELS[n + 1]
    side = new.shape[0]
    shown = np.pad(old / old.max(), 1)
    head = min(int(progress * side * side), side * side - 1)
    row, col = divmod(head, side)
    shown[:row] = (new / new.max())[:row]
    shown[row, : col + 1] = (new / new.max())[row, : col + 1]
    return shown, row, col


def size_label(n: int) -> Mono:
    side = 2 * n + 1
    return Mono(f"{side}x{side}", font_size=TEXT_BASE, color=TEXT).move_to(
        [GRID_X, BODY_Y - GRID_SIDE / 2 - SPACE_3 + SPACE_1, 0.0]
    )


class Convolve(ClipScene):
    def construct(self):
        equation = MathTex(r"(I * W) * W", "=", r"I *", r"(W * W)", font_size=TEXT_LG, color=TEXT)
        self.cue("Convolution is associative")
        self.play(FadeIn(equation), run_time=MOVE, rate_func=EASE)

        # What the right-hand side asks for, and the empty kernel it will fill
        self.cue("one pass with the kernel")
        target = KERNELS[2]
        cell = GRID_SIDE / target.shape[0]
        result = NumberGrid([[None] * 5 for _ in range(5)], cell=cell).move_to([GRID_X, BODY_Y, 0.0])
        stamp = NumberGrid(BOX_KERNEL.tolist(), cell=cell, decimals=0, fill=lambda v: BOX).move_to(result.point(1, 1))
        for square in stamp.squares:
            square.set_stroke(BOX, STROKE_THIN).set_fill(BOX, opacity=STAMP_OPACITY)
        stamp.squares.set_z_index(1)
        stamp.labels.set_color(TEXT).set_z_index(3)
        name = size_label(2)
        plot = Plot(3)
        axes = plot.axes()
        curve, dots = plot.curve(1), plot.dots(1)
        caption = Text("middle row", font_size=TEXT_SM, color=MUTED).move_to([PLOT_X, name.get_y(), 0.0])
        equation.generate_target().move_to(UP * EQUATION_Y)
        equation.target[3].set_color(HIGHLIGHT)
        self.play(
            MoveToTarget(equation),
            FadeIn(result),
            FadeIn(stamp),
            FadeIn(name),
            FadeIn(axes),
            FadeIn(curve),
            FadeIn(dots),
            FadeIn(caption),
            run_time=MOVE,
            rate_func=EASE,
        )

        # Stamp the box at each of its own nine cells, in reading order. Each stamp is
        # one change: it moves as the cells under it count the overlap and the plot
        # redraws the row
        self.cue("with itself")
        counts = np.zeros((5, 5), dtype=int)
        numbers = {}
        for index, (r, c) in enumerate(np.ndindex(3, 3)):
            changes = [FadeOut(stamp.labels) if index == 0 else stamp.squares.animate.move_to(result.point(r + 1, c + 1))]
            counts[r : r + 3, c : c + 3] += 1
            for row, col in np.ndindex(3, 3):
                at = r + row, c + col
                shown = counts[at] / target.max() * COUNT_OPACITY
                changes.append(result.square(*at).animate.set_fill(BOX, opacity=shown))
                number = Mono(f"{counts[at]}", font_size=TEXT_SM, color=text_on(BOX, shown))
                number.move_to(result.point(*at)).set_z_index(2)
                changes.append(FadeIn(number))
                if at in numbers:
                    changes.append(FadeOut(numbers[at]))
                numbers[at] = number
            self.play(
                *changes,
                Transform(curve, plot.row_curve(counts[2].astype(float))),
                Transform(dots, plot.row_dots(counts[2].astype(float))),
                run_time=BEAT if index < FIRST_ROW else LATER_STAMP,
                rate_func=EASE,
            )
        assert (counts == target).all()

        # A triangle already. The cells take their heights as heat, digits still on them
        self.cue("Already, it's no longer")
        heat = heatmap(2)
        recoloured = VGroup(*(
            Mono(f"{target[key]:.0f}", font_size=TEXT_SM, color=text_on(magma(target[key] / target.max())))
            .move_to(number)
            .set_z_index(2)
            for key, number in numbers.items()
        ))
        self.play(
            FadeOut(stamp.squares),
            Transform(result.squares, heat),
            *(Transform(number, new) for number, new in zip(numbers.values(), recoloured)),
            run_time=MOVE,
            rate_func=EASE,
        )

        # The axis makes room for what's coming, and the grid is about to be too fine for digits
        wide = Plot(PASSES + 1)
        wide_axes = wide.axes()
        self.play(
            *(FadeOut(number) for number in numbers.values()),
            FadeTransform(axes, wide_axes),
            Transform(curve, wide.curve(2)),
            Transform(dots, wide.dots(2)),
            run_time=MOVE,
            rate_func=EASE,
        )

        # The burst: every convolution one reading-order sweep, each faster than the last.
        # The kernel's outline visits every cell; the cell under its centre takes its new
        # value. One play, so the last sweep lands exactly on the cut to the gag
        self.cue("And if we keep convolving")
        table = magma_table()
        ends = sweep_schedule()
        kernels = range(BURST_FIRST, PASSES)
        names = {n + 1: size_label(n + 1) for n in kernels}
        image = ImageMobject(heat_pixels(np.pad(KERNELS[2] / KERNELS[2].max(), 1), table))
        image.set_resampling_algorithm(RESAMPLING_ALGORITHMS["nearest"])
        image.width = GRID_SIDE
        image.move_to([GRID_X, BODY_Y, 0.0])
        head = Square(1.0, color=HIGHLIGHT, stroke_width=STROKE_BOLD).set_z_index(3)
        # A play freezes which leaves it draws when it begins, by calling step once, so
        # these must still be empty then. After that they can swap freely
        begun = []
        label, row_dots = VGroup(), VGroup()
        self.remove(result, name, dots)
        live = Group(image, head, label, curve, row_dots)

        def step(mob, alpha):
            if not begun:
                begun.append(True)
                return
            at = int(np.searchsorted(ends, alpha * BURST, side="right"))
            if alpha >= 1 or at >= len(kernels):
                image.pixel_array = heat_pixels(KERNELS[PASSES] / KERNELS[PASSES].max(), table)
                head.set_stroke(opacity=0)
                label.submobjects = [names[PASSES]]
                curve.become(wide.curve(PASSES))
                row_dots.submobjects = wide.dots(PASSES).submobjects
                return
            start = ends[at - 1] if at else 0.0
            n = kernels[at]
            values, row, col = swept(n, (alpha * BURST - start) / (ends[at] - start))
            image.pixel_array = heat_pixels(values, table)
            side = values.shape[0]
            cell = GRID_SIDE / side
            head.width = head.height = 3 * cell
            head.move_to(image.get_center() + np.array([(col - (side - 1) / 2) * cell, ((side - 1) / 2 - row) * cell, 0.0]))
            label.submobjects = [names[n + 1]]
            middle = values[side // 2]
            curve.become(wide.row_curve(middle))
            row_dots.submobjects = wide.row_dots(middle).submobjects

        self.play(UpdateFromAlphaFunc(live, step), run_time=BURST, rate_func=linear)

        # Nothing moves from here: the meme goes over this in Resolve
        self.cue("as it turns out")
