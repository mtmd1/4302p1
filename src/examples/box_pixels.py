"""Box blur 1: the photo becomes a grid of numbers, then splits into its channels.

    uv run render box_pixels

Timed by cues, so each line holds the state it arrives at until the next one.
"""

from style import *

from components import colour, fit, grey
from pixels import PixelView, grid_lines, zoom
from sample import photo

TARGET = (720, 778.5)  # A lit window: warm light, so R, G and B differ a lot
# Whole pixels shown once zoomed in, sized so three values fit a cell. The odd
# row count puts TARGET's y on a pixel centre, so every row is whole.
COLS, ROWS = 8, 5
ZOOM = 3.2  # Seconds to zoom from the whole photo to the pixels
SWEEP = 1.64  # Seconds for the pixels to become numbers
WAVE = 0.05  # Lag ratio of that sweep, cell to cell in reading order

PLANE_SCALE = 0.7  # Size of the channel planes when pulled apart
KEPT = 0  # The channel that stays: red


class PixelsToNumbers(ClipScene):
    def construct(self):
        image = photo()
        view = PixelView(image, box=fit(image.shape[1], image.shape[0]))
        live_grid = always_redraw(lambda: grid_lines(view, MUTED, STROKE_THIN))
        self.add(view, live_grid)
        self.cue("First, let's treat")
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
        self.cue("one per colour channel")

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
        self.cue("so we can look at just one")

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
        self.cue("To blur it")
