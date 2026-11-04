"""Pieces shared by the section graphics, so every clip looks and counts alike."""

from types import SimpleNamespace

from style import *

# The numbers as scripted. On-screen values come from here rather than live
# measurement, so they always match the narration; correct them here if the
# recording says otherwise. Measured with blur.py at 1080p, half=True.
FIGURES = SimpleNamespace(
    taps_box=1681,  # 41 x 41
    taps_separated=82,  # 2 x 41
    taps_separated_matched=70,  # Separated gaussian as strong as Kawase, sigma 5.3
    taps_kawase=20,  # 5 passes x 4 taps
    taps_kawase_no_offset=228,  # 57 passes x 4 taps
    taps_dual=12,  # 12.3 rounded, as spoken
    passes_no_offset=57,
    taps_per_frame_1080p=3_485_721_600,
    taps_per_frame_4k=13_942_886_400,
    ms_box="4.5 ms",
    ms_separated="0.2 ms",
    us_dual="50 µs",
    frame_ms=16.6,
    budget_percent=27,
    fps_box="224",
    fps_separated="5,000",
    fps_kawase="11,500",
    fps_dual="21,700",
    sigma_gaussian=7,
    radius_box=20,
    sigma_kawase=5.3,
    sigma_dual_4=9,
    sigma_dual_5=18,
    kawase_offsets=(0, 1, 2, 2, 3),
)

# A bright reflection on the beach in sands.jpg, as (x, y) in source pixels. On a
# dark surround, so a box blur shows a clean square. Use it for every "square vs
# round" moment, so the viewer recognises the same light each time.
LAMP = (789, 991)


def colour(rgb) -> ManimColor:
    # Manim reads float64 as 0-1 but numpy's float32, as in the photo, as 0-255
    return rgb_to_color(np.asarray(rgb, dtype=np.float64))


def grey(value: float) -> ManimColor:
    return colour(np.full(3, value))


def fit(width: float, height: float) -> tuple[float, float]:
    """The largest box of this aspect inside the standard FILL area."""
    scale = min(FILL_WIDTH / width, FILL_HEIGHT / height)
    return width * scale, height * scale


def photo_still(image: np.ndarray, width: float | None = None) -> ImageMobject:
    """An image as a mobject, fitted to the FILL area unless a width is given."""
    import blur

    pixels = blur.to_uint8(image) if image.dtype != np.uint8 else image
    still = ImageMobject(pixels).set_resampling_algorithm(RESAMPLING_ALGORITHMS["bilinear"])
    still.width = width or fit(image.shape[1], image.shape[0])[0]
    return still


def credit(text: str, under: Mobject | None = None) -> Text:
    """A small source line, under a graphic or at the bottom of the FILL area."""
    line = Text(text, font_size=TEXT_SM, color=MUTED)
    if under is not None:
        return line.next_to(under, DOWN, buff=SPACE_1)
    return line.move_to(DOWN * (FILL_HEIGHT / 2 + SPACE_3))


def slot(label: str, source: str, width: float = FILL_WIDTH) -> VGroup:
    """An empty, credited frame for footage placed in Resolve. 16:9, centred."""
    frame = DashedVMobject(Rectangle(width=width, height=width * 9 / 16, color=MUTED, stroke_width=STROKE), num_dashes=60)
    name = Text(label, font_size=TEXT_BASE, color=MUTED)
    return VGroup(frame, name, credit(source, under=frame))


class NumberGrid(VGroup):
    """A grid of values in cells. values is rows of floats; None leaves a cell blank.

    Cells fill grey by value by default, with labels that stay legible on them.
    Rows count down from the top and columns from the left, as in the image.
    """

    def __init__(self, values, cell: float = 1.12, font_size: float = TEXT_SM, decimals: int = 2, fill=grey, **kwargs):
        super().__init__(**kwargs)
        self.rows, self.cols = len(values), len(values[0])
        self.cell = cell
        self.font_size = font_size
        self.decimals = decimals
        self.squares, self.labels = VGroup(), VGroup()
        self._labels = {}
        for r, row in enumerate(values):
            for c, value in enumerate(row):
                square = Square(cell, stroke_color=MUTED, stroke_width=STROKE_THIN).move_to(self._local(r, c))
                if value is not None:
                    square.set_fill(fill(value), opacity=1)
                    self._labels[r, c] = self.label_for(value, fill(value)).move_to(square)
                    self.labels.add(self._labels[r, c])
                self.squares.add(square)
        self.add(self.squares, self.labels)

    def _local(self, r: int, c: int) -> np.ndarray:
        return np.array([(c - (self.cols - 1) / 2) * self.cell, ((self.rows - 1) / 2 - r) * self.cell, 0.0])

    def label_for(self, value: float, background: ManimColor = BACKGROUND) -> Mono:
        return Mono(f"{value:.{self.decimals}f}", font_size=self.font_size, color=text_on(background))

    def point(self, r: int, c: int) -> np.ndarray:
        """Centre of cell (r, c); also works for cells off the edge of the grid."""
        scale = self.squares[0].width / self.cell
        return self.get_center() + self._local(r, c) * scale

    def square(self, r: int, c: int) -> Square:
        return self.squares[r * self.cols + c]

    def label(self, r: int, c: int) -> Mono:
        return self._labels[r, c]

    def in_bounds(self, r: int, c: int) -> bool:
        return 0 <= r < self.rows and 0 <= c < self.cols


def kernel_box(grid: NumberGrid, r: int, c: int, size: int = 3, color=HIGHLIGHT) -> Square:
    """The kernel outline: size x size cells centred on (r, c), overhanging the grid if need be."""
    side = size * grid.squares[0].width
    return Square(side, color=color, stroke_width=STROKE_BOLD).move_to(grid.point(r, c))


class TapCounter(VGroup):
    """The running bars of taps per pixel, one row per method, on a linear scale.

    add_row and update_rows each return an animation to play. Pass max_taps to
    update_rows to rescale the axis once the largest bar has left.
    """

    def __init__(
        self, max_taps: float, width: float = FILL_WIDTH, top: float = FILL_HEIGHT / 2, names_width: float = 3.2,
        row_height: float = 0.8, **kwargs
    ):
        super().__init__(**kwargs)
        self.max_taps = max_taps
        self.names_width = names_width  # Room for method names left of the bars
        self.values_width = 1.4  # Room for the value right of the longest bar
        self.left = -width / 2 + self.names_width
        self.length = width - self.names_width - self.values_width
        self.top = top
        self.row_height = row_height
        self.rows = {}

    def _width(self, taps: float) -> float:
        return max(taps / self.max_taps * self.length, 0.03)  # A hairline stays visible

    def add_row(self, name: str, taps: int, color) -> Animation:
        y = self.top - self.row_height * len(self.rows)
        bar = Rectangle(width=self._width(taps), height=self.row_height / 2, stroke_width=0, fill_color=color, fill_opacity=1)
        bar.move_to([self.left, y, 0], aligned_edge=LEFT)
        label = Text(name, font_size=TEXT_BASE, color=TEXT).next_to(bar, LEFT, buff=SPACE_2)
        label.align_to([self.left - SPACE_2, 0, 0], RIGHT)
        number = Integer(taps, font_size=TEXT_BASE, color=TEXT, group_with_commas=False)
        number.add_updater(lambda m: m.next_to(bar, RIGHT, buff=SPACE_2))
        number.update()
        self.rows[name] = SimpleNamespace(bar=bar, label=label, number=number, taps=taps)
        self.add(bar, label, number)
        return AnimationGroup(GrowFromEdge(bar, LEFT), FadeIn(label), FadeIn(number), run_time=MOVE, rate_func=EASE)

    @staticmethod
    def _count_to(row) -> Animation:
        """Roll a row's number to its new value. An animation suspends the number's
        own updater, so this keeps it at the end of the bar as well."""
        start = row.number.get_value()

        def roll(number, alpha):
            number.set_value(start + (row.taps - start) * alpha)
            number.next_to(row.bar, RIGHT, buff=SPACE_2)

        return UpdateFromAlphaFunc(row.number, roll)

    def update_rows(self, changes: dict[str, int] | None = None, max_taps: float | None = None) -> Animation:
        """Animate rows to new tap counts, and optionally the whole axis to a new scale."""
        changes = changes or {}
        self.max_taps = max_taps or self.max_taps
        moves = []
        for name, row in self.rows.items():
            row.taps = changes.get(name, row.taps)
            target = row.bar.copy().stretch_to_fit_width(self._width(row.taps)).align_to([self.left, 0, 0], LEFT)
            moves.append(Transform(row.bar, target))
            if name in changes:
                moves.append(self._count_to(row))
        return AnimationGroup(*moves, run_time=SLOW, rate_func=EASE)


class BudgetBar(VGroup):
    """One frame's time budget, filled by how much of it a blur takes."""

    def __init__(self, width: float = FILL_WIDTH, color=HIGHLIGHT, **kwargs):
        super().__init__(**kwargs)
        self.full_width = width
        self.outline = Rectangle(width=width, height=0.6, color=MUTED, stroke_width=STROKE)
        self.fill = Rectangle(width=0.001, height=0.6, stroke_width=0, fill_color=color, fill_opacity=1)
        self.fill.set_z_index(1)  # Over the outline, which would hide half of a thin sliver
        self.fill.align_to(self.outline, LEFT)
        caption = VGroup(
            Text("1 frame at", font_size=TEXT_BASE, color=TEXT),
            Mono(f"60 FPS = {FIGURES.frame_ms} ms", font_size=TEXT_BASE, color=TEXT),
        ).arrange(RIGHT, buff=SPACE_1)
        self.caption = caption.next_to(self.outline, UP, buff=SPACE_1).align_to(self.outline, LEFT)
        self.add(self.fill, self.outline, self.caption)

    def fill_to(self, percent: float, color=None, **kwargs) -> Animation:
        target = self.fill.copy().stretch_to_fit_width(max(self.full_width * percent / 100, 0.001))
        target.align_to(self.outline, LEFT)
        if color is not None:
            target.set_fill(color)
        return Transform(self.fill, target, **{"run_time": SLOW, "rate_func": EASE, **kwargs})


class TapPoint(Circle):
    """A texture lookup: where a tap lands, which needn't be on a pixel centre. Solid,
    so it stays readable on any image, and the same size wherever it appears."""

    def __init__(self, size: float = 0.2, color=POINT, **kwargs):
        super().__init__(radius=size / 2, stroke_width=0, fill_color=color, fill_opacity=1, **kwargs)


class DualV(Group):
    """Every level of a real Dual Kawase as a V, all images to one scale.

    Down the left arm from the source to the deepest level, then up the right arm to
    the result: each image sits below and right of the last going down, above and right
    going up. tiles[i] holds each image in pass order; arrows[i] leads into tiles[i + 1].
    labels[i] names the size of tiles[i] on the left arm only, so the right arm has none.
    taps holds each arm's tap count, for a scene that wants it on the V itself.
    """

    LEVELS = 4
    GAP_X, GAP_Y = 0.2, 0.3  # Between one image's corner and the next's
    ARROW_BUFF, ARROW_TIP = 0.03, 0.12
    STROKE_RATIO = 20  # Keeps the short arrows at the full STROKE
    SCREEN_PIXELS = 270  # Per unit, twice 1080p's: images are reduced to this first, so they don't sparkle

    @staticmethod
    def _depths(levels: int) -> list[int]:
        return [*range(levels + 1), *reversed(range(levels))]

    @classmethod
    def width_for(cls, tile_width: float, levels: int = LEVELS) -> float:
        """The width at which a V of this many levels has images of this full size."""
        depths = cls._depths(levels)
        return tile_width * sum(2.0**-d for d in depths) + cls.GAP_X * (len(depths) - 1)

    def __init__(
        self, source: np.ndarray, width: float = FILL_WIDTH, top: float = FILL_HEIGHT / 2,
        levels: int = LEVELS, gap_y: float = GAP_Y, label_size: float = TEXT_SM, **kwargs,
    ):
        import blur

        super().__init__(**kwargs)
        self.levels = levels
        steps = blur.dual_kawase(source, levels=levels, steps=True).steps
        images = [source, *steps]
        depths = self._depths(levels)

        # Widths halve per level and every gap is fixed, so this fills the width exactly
        self.tile_width = (width - self.GAP_X * (len(images) - 1)) / sum(2.0**-d for d in depths)
        self.tile_height = self.tile_width * source.shape[0] / source.shape[1]

        self.tiles, self.labels, self.arrows = [], [], []
        x = -width / 2
        y = top
        for i, (image, depth) in enumerate(zip(images, depths)):
            tile = self._tile(image, self.tile_width / 2**depth)
            if i <= levels:
                tile.move_to([x, y, 0], aligned_edge=UL)
                y -= tile.height + gap_y
                self.labels.append(self._label(depth, tile, i, label_size))
            else:
                # Going up, each image's bottom is where the last one's top was, plus a gap
                below = self.tiles[-1]
                tile.move_to([x, below.get_top()[1] + gap_y, 0], aligned_edge=DL)
            x += tile.width + self.GAP_X
            self.tiles.append(tile)
        for before, after, going_down in zip(self.tiles, self.tiles[1:], [True] * levels + [False] * levels):
            start, end = (before.get_corner(DR), after.get_corner(UL)) if going_down else (before.get_corner(UR), after.get_corner(DL))
            self.arrows.append(Arrow(
                start, end, buff=self.ARROW_BUFF, stroke_width=STROKE, color=MUTED, tip_length=self.ARROW_TIP,
                max_tip_length_to_length_ratio=1, max_stroke_width_to_length_ratio=self.STROKE_RATIO,
            ))
        self.taps = VGroup(
            self._taps("5", self.labels[0], LEFT),
            self._taps("8", self.labels[0], LEFT).align_to(self.tiles[-1], RIGHT),
        )
        self.add(*self.tiles, *self.labels, *self.arrows)

    def _tile(self, image: np.ndarray, width: float) -> Group:
        from PIL import Image

        import blur

        pixels = blur.to_uint8(image)
        wanted = round(width * self.SCREEN_PIXELS)
        if pixels.shape[1] > wanted:
            scale = wanted / pixels.shape[1]
            size = (wanted, max(round(pixels.shape[0] * scale), 1))
            pixels = np.asarray(Image.fromarray(pixels).resize(size, Image.Resampling.BOX))
        still = ImageMobject(pixels).set_resampling_algorithm(RESAMPLING_ALGORITHMS["bilinear"])
        still.width = width
        return Group(still, SurroundingRectangle(still, buff=0, color=MUTED, stroke_width=STROKE_THIN))

    @staticmethod
    def _label(depth: int, tile: Group, index: int, size: float) -> Mono:
        """Left of its image, clear of the arrow arriving at its corner. The source has
        the frame's edge there, so its label goes underneath."""
        label = Mono(f"1/{2**depth}" if depth else "1", font_size=size, color=MUTED)
        if index == 0:
            return label.next_to(tile, DOWN, buff=SPACE_1).align_to(tile, LEFT)
        return label.next_to(tile, LEFT, buff=SPACE_1)

    @staticmethod
    def _taps(count: str, under: Mobject, edge: np.ndarray) -> VGroup:
        line = VGroup(
            Mono(count, font_size=TEXT_BASE, color=DUAL_KAWASE),
            Text("taps", font_size=TEXT_BASE, color=DUAL_KAWASE),
        ).arrange(RIGHT, buff=SPACE_1)
        return line.next_to(under, DOWN, buff=SPACE_2).align_to(under, edge)
