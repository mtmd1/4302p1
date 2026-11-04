"""Kawase 7: five passes, with the taps stepping out along the diagonals.

    uv run render kawase_offsets

The photo shows blur.kawase's real output after each pass. The diagram's heatmap is
the real kernel of the passes so far, computed in numpy, cropped to the diagram.
The two buffers replay those passes for real, on a close crop of the photo, where a
frame this small can still show each pass getting blurrier.
"""

from functools import lru_cache

from style import *

import blur
from components import FIGURES, TapPoint, credit, photo_still
from sample import photo

PHOTO_WIDTH = 6.0
DIAGRAM_RADIUS = 4  # Cells either side of the centre; offset 3's taps reach this far
CELL = 0.34
BLOCK_OPACITY = 0.45
GAP_OPACITY = 0.45
DIAGRAM_X, DIAGRAM_Y = 3.3, 0.2
BUFFER_WIDTH = 3.0  # Each buffer, in the photo's shape
BUFFER_CROP = (800, 520, 640, 360)  # x, y, width, height in source pixels: the buildings
SWAP_HOLD = 0.18  # On each pass's result, before the next
SWAP_ARC = PI / 8  # Just enough for the tags to pass each other, clear of the images
SMEARED_AT = 3  # Passes done when the gaps are marked: offsets 0, 1, 2


@lru_cache
def results() -> tuple[np.ndarray, list[np.ndarray]]:
    """The sharp photo and each pass of the five."""
    image = photo()
    return image, blur.kawase(image, FIGURES.kawase_offsets, steps=True).steps


def buffer_still(image: np.ndarray) -> ImageMobject:
    x, y, width, height = BUFFER_CROP
    return photo_still(image[y : y + height, x : x + width], width=BUFFER_WIDTH)


def convolve(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    out = np.zeros((a.shape[0] + b.shape[0] - 1, a.shape[1] + b.shape[1] - 1))
    for (r, c), weight in np.ndenumerate(b):
        out[r : r + a.shape[0], c : c + a.shape[1]] += weight * a
    return out


def pass_kernel(offset: int) -> np.ndarray:
    """One pass as a pixel kernel: 2 x 2 blocks of 1/16 at the four diagonal taps."""
    size = 2 * offset + 3
    kernel = np.zeros((size, size))
    for r in (0, size - 2):
        for c in (0, size - 2):
            kernel[r : r + 2, c : c + 2] += 1 / 16
    return kernel


def kernel_after(passes: int) -> np.ndarray:
    kernel = np.ones((1, 1))
    for offset in FIGURES.kawase_offsets[:passes]:
        kernel = convolve(kernel, pass_kernel(offset))
    return kernel


class Diagram:
    """Pixels around one centre pixel, in manim coordinates."""

    def __init__(self):
        self.centre = np.array([DIAGRAM_X, DIAGRAM_Y, 0.0])

    def cell(self, dx: float, dy: float) -> np.ndarray:
        return self.centre + np.array([dx, -dy, 0.0]) * CELL

    def grid(self) -> VGroup:
        span = range(-DIAGRAM_RADIUS, DIAGRAM_RADIUS + 1)
        return VGroup(*(
            Square(CELL, stroke_color=MUTED, stroke_width=STROKE_THIN).move_to(self.cell(x, y)) for y in span for x in span
        ))

    def tap_points(self, offset: float) -> list[np.ndarray]:
        reach = offset + 0.5
        return [self.cell(sx * reach, sy * reach) for sx, sy in ((-1, -1), (1, -1), (-1, 1), (1, 1))]

    def blocks(self, offset: float) -> VGroup:
        return VGroup(*(
            Square(2 * CELL, stroke_width=0, fill_color=KAWASE, fill_opacity=BLOCK_OPACITY).move_to(at)
            for at in self.tap_points(offset)
        ))

    def gaps(self, offset: int) -> VGroup:
        """Cells inside the taps' reach that no block covers."""
        reach = offset + 1
        marks = VGroup()
        for y in range(-reach, reach + 1):
            for x in range(-reach, reach + 1):
                covered = abs(x) in (offset, offset + 1) and abs(y) in (offset, offset + 1)
                if not covered:
                    marks.add(
                        Square(CELL, stroke_width=0, fill_color=HIGHLIGHT, fill_opacity=GAP_OPACITY).move_to(self.cell(x, y))
                    )
        return marks

    def heat(self, passes: int) -> VGroup:
        kernel = kernel_after(passes)
        middle = kernel.shape[0] // 2
        cells = VGroup()
        for y in range(-DIAGRAM_RADIUS, DIAGRAM_RADIUS + 1):
            for x in range(-DIAGRAM_RADIUS, DIAGRAM_RADIUS + 1):
                inside = abs(x) <= middle and abs(y) <= middle
                value = kernel[middle + y, middle + x] / kernel.max() if inside else 0.0
                cells.add(
                    Square(CELL, stroke_color=MUTED, stroke_width=STROKE_THIN, fill_color=magma(value), fill_opacity=1)
                    .move_to(self.cell(x, y))
                )
        return cells


class Offsets(ClipScene):
    def construct(self):
        image, steps = results()
        offsets = FIGURES.kawase_offsets

        left_x = -FILL_WIDTH / 2 + PHOTO_WIDTH / 2
        still = photo_still(image, width=PHOTO_WIDTH)
        still.move_to([left_x, DIAGRAM_Y, 0.0])

        diagram = Diagram()
        grid = diagram.grid()
        centre = Square(CELL, color=TEXT, stroke_width=STROKE).move_to(diagram.cell(0, 0)).set_z_index(4)
        blocks = diagram.blocks(offsets[0]).set_z_index(1)
        taps = VGroup(*(TapPoint().move_to(at) for at in diagram.tap_points(offsets[0]))).set_z_index(3)

        chips = VGroup(*(Mono(f"{o}", font_size=TEXT_BASE, color=MUTED) for o in offsets)).arrange(RIGHT, buff=SPACE_2)
        chip_name = Text("offset", font_size=TEXT_BASE, color=MUTED)
        chip_row = VGroup(chip_name, chips).arrange(RIGHT, buff=SPACE_2)
        chip_row.next_to(grid, UP, buff=SPACE_3)

        caption = Text("gaps", font_size=TEXT_BASE, color=HIGHLIGHT).next_to(grid, DOWN, buff=SPACE_2)
        smeared = Text("already blurred", font_size=TEXT_BASE, color=TEXT).move_to(caption)

        source = credit("Kawase, GDC 2003. Offsets: Intel, 2014")

        self.cue("So Kawase reaches further")
        self.play(
            FadeIn(still), FadeIn(grid), FadeIn(centre), FadeIn(blocks), FadeIn(taps), FadeIn(chip_row), FadeIn(source),
            run_time=MOVE, rate_func=EASE,
        )

        shown = [still]

        def pass_changes(index: int) -> list[Animation]:
            """Current chip lights, taps step out."""
            changes = [
                chips[index].animate.set_color(HIGHLIGHT),
                Transform(blocks, diagram.blocks(offsets[index]).set_z_index(1)),
            ]
            if index:
                changes.append(chips[index - 1].animate.set_color(TEXT))
            for tap, at in zip(taps, diagram.tap_points(offsets[index])):
                changes.append(tap.animate.move_to(at))
            return changes

        def one_pass(index: int):
            """That pass's diagram, as the photo takes its output."""
            next_still = photo_still(steps[index], width=PHOTO_WIDTH).move_to(still)
            self.play(*pass_changes(index), FadeIn(next_still), run_time=MOVE, rate_func=EASE)
            self.remove(shown.pop())
            shown.append(next_still)

        for index in range(SMEARED_AT):
            one_pass(index)

        # The holes between the taps, then why they don't print
        self.cue("The gaps between them")
        gaps = diagram.gaps(offsets[SMEARED_AT - 1]).set_z_index(2)
        self.play(FadeIn(gaps), FadeIn(caption), run_time=MOVE, rate_func=EASE)
        self.cue("land on pixels")
        heat = diagram.heat(SMEARED_AT)
        # The captions share a spot, so they pass rather than ghost over each other
        self.play(
            FadeOut(gaps, rate_func=EASE),
            FadeOut(blocks, rate_func=EASE),
            FadeOut(taps, rate_func=EASE),  # Red wouldn't read on magma
            FadeIn(heat, rate_func=EASE),
            FadeOut(caption, shift=UP * SPACE_2, rate_func=EASE),
            FadeIn(smeared, shift=UP * SPACE_2, rate_func=EASE),
            run_time=SLOW,
        )

        # Back to the tap pattern for the last two passes
        self.cue("A common choice")
        blocks.set_opacity(BLOCK_OPACITY)
        self.play(
            FadeOut(heat), FadeOut(smeared), FadeIn(blocks), FadeIn(taps),
            run_time=MOVE, rate_func=EASE,
        )
        for index in range(SMEARED_AT, len(offsets)):
            one_pass(index)

        # Two buffers are enough: each pass reads one and writes the other. The five passes
        # again from the sharp photo, each one's real output landing in the buffer it wrote
        self.cue("Swapping between two buffers")
        a = Rectangle(width=BUFFER_WIDTH, height=BUFFER_WIDTH * still.height / still.width, color=MUTED, stroke_width=STROKE)
        b = a.copy()
        VGroup(a, b).arrange(RIGHT, buff=SPACE_2).move_to([-FILL_WIDTH / 2 + BUFFER_WIDTH + SPACE_2 / 2, DIAGRAM_Y, 0.0])
        VGroup(a, b).set_z_index(1)
        letters = VGroup(
            Mono("A", font_size=TEXT_BASE, color=TEXT).next_to(a, DOWN, buff=SPACE_1),
            Mono("B", font_size=TEXT_BASE, color=TEXT).next_to(b, DOWN, buff=SPACE_1),
        )
        read = Text("read", font_size=TEXT_SM, color=TEXT).next_to(a, UP, buff=SPACE_1)
        write = Text("write", font_size=TEXT_SM, color=HIGHLIGHT).next_to(b, UP, buff=SPACE_1)
        held = {0: buffer_still(image).move_to(a)}
        self.play(
            FadeOut(shown[0]),
            FadeIn(held[0]),
            FadeIn(VGroup(a, b, letters, read, write)),
            chips.animate.set_color(MUTED),
            run_time=MOVE,
            rate_func=EASE,
        )
        for index, step in enumerate(steps):
            target = 1 - index % 2  # B, then A, then B...
            landed = buffer_still(step).move_to((a, b)[target])
            swap = [Swap(read, write, path_arc=SWAP_ARC)] if index else []  # The first pass already reads A and writes B
            self.play(*pass_changes(index), *swap, FadeIn(landed), run_time=BEAT, rate_func=EASE)
            if target in held:
                self.remove(held[target])
            held[target] = landed
            self.wait(SWAP_HOLD)
        self.cue("Five passes of four taps")
