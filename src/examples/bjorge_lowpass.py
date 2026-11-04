"""Bjorge 1: zoomed in far enough, a blurred image's neighbouring pixels are nearly identical,
then what follows from that as a list.

    uv run render bjorge_lowpass
"""

from style import *

import blur
from components import colour
from pixels import PixelView, grid_lines, zoom
from sample import photo

TARGET = (720, 778)  # Beside the lit window of box_pixels, where the blur leaves a soft gradient
COLS, ROWS = 6, 4  # Even counts, so a TARGET on whole numbers puts the box on pixel edges
CELL = 1.15  # Fits three values to a pixel, leaving room for the label under the grid
PAIR = (1, 2), (1, 3)  # The two neighbouring pixels (row, column) read out
ZOOM = 3.2  # Seconds to zoom from the whole photo to the pixels
LEAD = 0.26  # Line spacing of the values, tighter than SPACE_1 so three fit a cell
BULLET = 0.07  # Radius of a list marker


def bullet(text: str) -> VGroup:
    words = Text(text, font_size=TEXT_BASE, color=TEXT)
    return VGroup(Dot(radius=BULLET, color=DUAL_KAWASE), words).arrange(RIGHT, buff=SPACE_2)


class BjorgeLowpass(ClipScene):
    def construct(self):
        image = blur.kawase(photo()).image
        height, width = image.shape[:2]
        scale = min(FILL_WIDTH / width, FILL_HEIGHT / height)
        view = PixelView(image, box=(width * scale, height * scale))
        lines = always_redraw(lambda: grid_lines(view, MUTED, STROKE_THIN))
        self.add(view, lines)

        self.cue("Look closely at")
        self.play(zoom(view, TARGET, COLS, box=(COLS * CELL, ROWS * CELL), run_time=ZOOM, rate_func=EASE))

        cols, rows = view.visible_pixels()
        outlines = VGroup()
        readouts = VGroup()
        for r, c in PAIR:
            rgb = image[rows[r], cols[c], :3]
            centre = view.to_point(cols[c] + 0.5, rows[r] + 0.5)
            outlines.add(Square(view.unit, color=HIGHLIGHT, stroke_width=STROKE).move_to(centre))
            values = VGroup(*(Mono(f"{v:.2f}", font_size=TEXT_XS, color=text_on(colour(rgb))) for v in rgb))
            for i, value in enumerate(values):
                value.move_to(centre + DOWN * (i - 1) * LEAD)
            readouts.add(values)
        self.play(FadeIn(outlines), FadeIn(readouts), run_time=MOVE, rate_func=EASE)

        self.cue("A blur is a low-pass")
        label = Text("low-pass filter", font_size=TEXT_BASE, color=TEXT)
        label.next_to(DOWN * ROWS * CELL / 2, DOWN, buff=SPACE_1)
        self.play(FadeIn(label, shift=UP * SPACE_2), run_time=MOVE, rate_func=EASE)

        # The picture has made its point: what follows from it is said, so it's listed
        items = VGroup(
            bullet("Lossy"),
            bullet("Destroys high spatial frequency content"),
            bullet("Does not require full resolution"),
        ).arrange(DOWN, aligned_edge=LEFT, buff=SPACE_3)
        heading = Text("low-pass filter", font_size=TEXT_LG, color=TEXT)
        VGroup(heading, items).arrange(DOWN, aligned_edge=LEFT, buff=SPACE_4).move_to(ORIGIN)

        self.cue("It's lossy")
        self.play(
            FadeOut(view), FadeOut(lines), FadeOut(outlines), FadeOut(readouts),
            ReplacementTransform(label, heading),
            FadeIn(items[0], shift=UP * SPACE_2),
            run_time=BEAT,
            rate_func=EASE,
        )
        self.cue("it destroys high")
        self.play(FadeIn(items[1], shift=UP * SPACE_2), run_time=BEAT, rate_func=EASE)
        self.cue("with less detail")
        self.play(FadeIn(items[2], shift=UP * SPACE_2), run_time=BEAT, rate_func=EASE)
        self.cue("So let's shrink the image")
