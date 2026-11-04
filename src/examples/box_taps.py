"""Box blur 5: one output pixel reads its whole 41x41 window, and those reads are taps.

    uv run render box_taps

Every read gets its line, in reading order, speeding up as it goes. The lines and
cells are one path each rather than 1681 mobjects, so the sweep renders quickly.
"""

from style import *

from components import FIGURES

KERNEL = 2 * FIGURES.radius_box + 1
WINDOW_SIDE = 4.6
FAN_GAP = 1.8  # Between the window and the output pixel
PIXEL_SIDE = 0.5

READ_SWEEP = 3.6  # Seconds to read the whole window, ending as "seventeen hundred values" does
ACCELERATION = 3  # Reads so far grow as time to this power: a slow first row, then faster

FAINT = 0.5  # Grid lines of the window
RESTING_LINE = 0.5  # Opacity of the lines, thin and translucent so the fan stays legible
RESTING_CELL = 0.2


def line_points(start: np.ndarray, ends: np.ndarray) -> np.ndarray:
    """One straight cubic per end, from start, as a VMobject's points."""
    weights = np.linspace(0, 1, 4)[None, :, None]
    return (start[None, None, :] * (1 - weights) + ends[:, None, :] * weights).reshape(-1, 3)


def square_points(centres: np.ndarray, side: float) -> np.ndarray:
    """One closed square per centre, as a VMobject's points."""
    half = side / 2
    corners = np.array([[-half, half, 0], [half, half, 0], [half, -half, 0], [-half, -half, 0], [-half, half, 0]])
    weights = np.linspace(0, 1, 4)[None, :, None]
    edges = (corners[:-1, None, :] * (1 - weights) + corners[1:, None, :] * weights).reshape(-1, 3)
    return (centres[:, None, :] + edges[None, :, :]).reshape(-1, 3)


class Taps(ClipScene):
    def construct(self):
        cell = WINDOW_SIDE / KERNEL
        window = Square(WINDOW_SIDE, color=MUTED, stroke_width=STROKE)
        ticks = [i * cell - WINDOW_SIDE / 2 for i in range(1, KERNEL)]
        half = WINDOW_SIDE / 2
        grid = VGroup(
            *(Line([x, -half, 0], [x, half, 0]) for x in ticks),
            *(Line([-half, y, 0], [half, y, 0]) for y in ticks),
        ).set_stroke(MUTED, STROKE_THIN, FAINT)
        size = Mono(f"{KERNEL} x {KERNEL}", font_size=TEXT_SM, color=MUTED).next_to(window, DOWN, buff=SPACE_1)
        left_part = VGroup(window, grid, size)

        pixel = Square(PIXEL_SIDE, stroke_width=0, fill_color=POINT, fill_opacity=1)
        # All the pixel's words sit to its right, clear of the lines fanning out on its left
        total = Mono(f"x {FIGURES.taps_box}", font_size=TEXT_LG, color=TEXT).next_to(pixel, RIGHT, buff=SPACE_2)
        word = Text("taps", font_size=TEXT_LG, color=POINT).next_to(total, DOWN, buff=SPACE_2).align_to(total, LEFT)

        pixel_part = VGroup(pixel, total, word)
        pixel_part.next_to(window, RIGHT, buff=FAN_GAP)
        pixel_part.shift(UP * (window.get_center()[1] - pixel.get_center()[1]))
        VGroup(left_part, pixel_part).move_to(ORIGIN)

        # Every pixel in the window, in reading order
        corner = window.get_corner(UL)
        centres = np.array(
            [corner + RIGHT * (c + 0.5) * cell + DOWN * (r + 0.5) * cell for r in range(KERNEL) for c in range(KERNEL)]
        )
        all_lines = line_points(pixel.get_center(), centres)
        all_cells = square_points(centres, cell)
        per_line = len(all_lines) // len(centres)
        per_cell = len(all_cells) // len(centres)

        cells = VMobject(stroke_width=0, fill_color=POINT, fill_opacity=RESTING_CELL)
        lines = VMobject(fill_opacity=0).set_stroke(POINT, STROKE_THIN, RESTING_LINE)
        active_cell = Square(cell, stroke_width=0, fill_color=POINT, fill_opacity=1)
        active_line = Line(pixel.get_center(), centres[0]).set_stroke(POINT, STROKE)
        reads = Mono("x 1", font_size=TEXT_LG, color=TEXT)
        reads_left = total.get_left()

        self.add(window, grid, size, pixel)
        self.cue("every pixel still reads")

        def read_up_to(_, alpha):
            count = max(1, int(np.ceil(len(centres) * alpha**ACCELERATION)))
            lines.set_points(all_lines[: count * per_line])
            cells.set_points(all_cells[: count * per_cell])
            active_cell.move_to(centres[count - 1])
            active_line.put_start_and_end_on(pixel.get_center(), centres[count - 1])
            reads.become(Mono(f"x {count}", font_size=TEXT_LG, color=TEXT).move_to(reads_left, aligned_edge=LEFT))

        self.play(
            UpdateFromAlphaFunc(VGroup(cells, lines, active_line, active_cell, reads), read_up_to),
            run_time=READ_SWEEP,
            rate_func=linear,
        )
        self.play(FadeOut(active_line), FadeOut(active_cell), run_time=QUICK, rate_func=EASE)
        self.cue("call these taps")

        self.play(FadeIn(word, shift=LEFT * SPACE_1), run_time=BEAT, rate_func=EASE)
        self.cue("That's almost three and a half")
