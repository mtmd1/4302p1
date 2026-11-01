"""Box blur 1: the photo becomes a grid of numbers, then splits into its channels.

    uv run render box_pixels

Script: "First, let's treat our image as a two-dimensional matrix of floats
between 0 and 1. A colour image has three, one per RGB channel, but we can blur
each one independently, so let's consider just one."

Timed to the read. Each line gets quick transitions, and the rest of its time
holds the state it arrives at.
"""

from style import *

from pixels import PixelView, grid_lines, zoom
from sample import photo

TARGET = (720, 778.5)  # A lit window: warm light, so R, G and B differ a lot
# Whole pixels shown once zoomed in, sized so three values fit a cell. The odd
# row count puts TARGET's y on a pixel centre, so every row is whole.
COLS, ROWS = 8, 5
# Seconds of narration per line of the script
FIRST_LINE = 5.2  # "...a two-dimensional matrix of floats between 0 and 1."
SECOND_LINE = 1.6  # "A colour image has three, one per RGB channel,"
THIRD_LINE = 3.5  # "...but we can blur each one independently..."

ZOOM = 3.2  # Seconds to zoom from the whole photo to the pixels
SWEEP = 1.64  # Seconds for the pixels to become numbers
WAVE = 0.05  # Lag ratio of that sweep, cell to cell in reading order

PLANE_SCALE = 0.7  # Size of the channel planes when pulled apart
KEPT = 0  # The channel that stays: red


def colour(rgb) -> ManimColor:
    # Manim reads float64 as 0-1 but numpy's float32, as in the photo, as 0-255
    return rgb_to_color(np.asarray(rgb, dtype=np.float64))


def grey(value: float) -> ManimColor:
    return colour(np.full(3, value))


def fit(width: float, height: float) -> tuple[float, float]:
    """The largest box of this aspect inside the standard FILL area."""
    scale = min(FILL_WIDTH / width, FILL_HEIGHT / height)
    return width * scale, height * scale


class PixelsToNumbers(ClipScene):
    def construct(self):
        image = photo()
        view = PixelView(image, box=fit(image.shape[1], image.shape[0]))
        live_grid = always_redraw(lambda: grid_lines(view, MUTED, STROKE_THIN))
        self.add(view, live_grid)
        self.play(zoom(view, TARGET, COLS, box=fit(COLS, ROWS), run_time=ZOOM, rate_func=EASE))

        # Swap the image for vector cells that look identical but can animate
        cols, rows = view.visible_pixels()
        values = [image[j, i, :3] for j in rows for i in cols]
        centres = [view.to_point(i + 0.5, j + 0.5) for j in rows for i in cols]
        cells = VGroup(*(
            Square(view.unit, stroke_width=0, fill_color=colour(rgb), fill_opacity=1).move_to(centre)
            for rgb, centre in zip(values, centres)
        ))
        lines = grid_lines(view, MUTED, STROKE_THIN)
        numbers = VGroup(*(
            VGroup(*(Mono(f"{v:.2f}", font_size=TEXT_XS, color=c) for v, c in zip(rgb, CHANNELS)))
            .arrange(DOWN, buff=SPACE_1)
            .move_to(centre)
            for rgb, centre in zip(values, centres)
        ))
        self.remove(view, live_grid)
        self.add(cells, lines)

        # Cell by cell in reading order, each pixel's colour fades out as its values fade in
        self.play(LaggedStart(
            *(
                AnimationGroup(cell.animate.set_fill(opacity=0), FadeIn(triple), rate_func=EASE)
                for cell, triple in zip(cells, numbers)
            ),
            lag_ratio=WAVE,
            run_time=SWEEP,
        ))
        self.wait(max(0, FIRST_LINE - ZOOM - SWEEP))

        # Pull the matrix apart into one plane per channel, red in front
        self.play(VGroup(cells, lines, numbers).animate.scale(PLANE_SCALE), run_time=BEAT, rate_func=EASE)
        offsets = [(c - KEPT) * (RIGHT * SPACE_4 + UP * SPACE_3) for c in range(3)]
        planes = []
        for c, tint in enumerate(CHANNELS):
            squares = VGroup(*(
                cell.copy().set_fill(tint, opacity=rgb[c]).set_stroke(MUTED, STROKE_THIN)
                for cell, rgb in zip(cells, values)
            ))
            digits = VGroup(*(
                Mono(f"{rgb[c]:.2f}", font_size=TEXT_SM, color=text_on(tint, rgb[c])).scale(PLANE_SCALE).move_to(cell)
                for cell, rgb in zip(cells, values)
            ))
            planes.append(VGroup(squares, digits).shift(offsets[c]).set_z_index(len(CHANNELS) - c))

        self.play(
            FadeOut(cells),
            FadeOut(lines),
            *(FadeIn(plane[0], shift=offset) for plane, offset in zip(planes, offsets)),
            *(
                ReplacementTransform(VGroup(*(triple[c] for triple in numbers)), plane[1])
                for c, plane in enumerate(planes)
            ),
            run_time=MOVE,
            rate_func=EASE,
        )
        self.wait(max(0, SECOND_LINE - BEAT - MOVE))

        # Green and blue leave; red returns to the grid's size as one greyscale channel
        kept = planes[KEPT]
        kept.generate_target()
        kept.target.scale(1 / PLANE_SCALE).move_to(ORIGIN)
        for square, digit, rgb in zip(kept.target[0], kept.target[1], values):
            value = rgb[KEPT]
            square.set_fill(grey(value), opacity=1)
            digit.set_color(text_on(grey(value)))
        leaving = [plane for c, plane in enumerate(planes) if c != KEPT]
        self.play(
            *(plane.animate.shift(RIGHT * config.frame_width + UP * config.frame_height) for plane in leaving),
            MoveToTarget(kept),
            run_time=SLOW,
            rate_func=EASE,
        )
        self.wait(max(0, THIRD_LINE - SLOW))
