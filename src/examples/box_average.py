"""Box blur 2: a 3x3 kernel averages a small grid into a second buffer.

    uv run render box_average

The kernel visits every cell in reading order. It starts on the corner, which is
also the edge case the narration names, so "sum / 4" arrives with "ignoring
positions". After that it only speeds up, never skipping a cell.
"""

from style import *

from components import NumberGrid, grey, kernel_box
from sample import photo

# A real 6x6 of the photo's red channel across a hard edge, so the blur visibly
# softens it. One decimal: two wouldn't fit a cell of a grid this size at TEXT_XS.
PATCH = (651, 816)  # Left and top, in source pixels
SIZE = 6
CHANNEL = 0
DECIMALS = 1

CELL = 0.6
KERNEL = 3
LIT = 0.25  # Opacity of the wash over the cells under the kernel
HATCH_LINES = 4  # Diagonals across each out-of-bounds cell

# Seconds on each cell of the sweep: the first, a shrink per cell, and the fastest,
# which is three frames at 60 fps so every cell is still seen
SLOWEST_STEP = BEAT
SPEED_UP = 0.75
FASTEST_STEP = 0.05
GLIDE = 0.3  # Fraction of a step spent moving to the cell; the values then fly to its centre


def in_bounds(r: int, c: int) -> bool:
    return 0 <= r < SIZE and 0 <= c < SIZE


def averages(values: np.ndarray) -> np.ndarray:
    """Mean of each pixel's 3x3 neighbourhood, ignoring positions off the edge."""
    out = np.empty_like(values)
    for r in range(SIZE):
        for c in range(SIZE):
            out[r, c] = values[max(r - 1, 0) : r + 2, max(c - 1, 0) : c + 2].mean()
    return out


def neighbours(r: int, c: int) -> list[tuple[int, int]]:
    return [(r + dr, c + dc) for dr in (-1, 0, 1) for dc in (-1, 0, 1) if in_bounds(r + dr, c + dc)]


def hatched(centre: np.ndarray) -> VGroup:
    """An out-of-bounds cell: outline plus diagonals clipped to the square."""
    half = CELL / 2
    lines = VGroup()
    for i in range(1, HATCH_LINES + 1):
        # The line y = x + rise, between where it enters and leaves the square
        rise = 2 * CELL * i / (HATCH_LINES + 1) - CELL
        first, last = max(-half, -half - rise), min(half, half - rise)
        lines.add(Line([first, first + rise, 0], [last, last + rise, 0]))
    return VGroup(Square(CELL), lines).set_stroke(MUTED, STROKE_THIN).move_to(centre)


def lit_cells(grid: NumberGrid, kernel: Square) -> Rectangle:
    """A wash over the part of the kernel that lies on the grid, so off-edge cells stay dark."""
    left = max(kernel.get_left()[0], grid.squares.get_left()[0])
    right = min(kernel.get_right()[0], grid.squares.get_right()[0])
    top = min(kernel.get_top()[1], grid.squares.get_top()[1])
    bottom = max(kernel.get_bottom()[1], grid.squares.get_bottom()[1])
    wash = Rectangle(width=right - left, height=top - bottom, stroke_width=0, fill_color=HIGHLIGHT, fill_opacity=LIT)
    return wash.move_to([(left + right) / 2, (top + bottom) / 2, 0])


class Average(ClipScene):
    def construct(self):
        x, y = PATCH
        values = np.round(photo()[y : y + SIZE, x : x + SIZE, CHANNEL].astype(np.float64), DECIMALS)
        results = averages(values)

        read = NumberGrid(values.tolist(), cell=CELL, font_size=TEXT_XS, decimals=DECIMALS)
        write = NumberGrid(results.tolist(), cell=CELL, font_size=TEXT_XS, decimals=DECIMALS)
        write.squares.set_fill(opacity=0)
        write.labels.set_opacity(0)

        # Centred with room left of the read grid for the corner's hatching
        side = SIZE * CELL
        read.move_to(LEFT * (FILL_WIDTH / 2 - CELL - side / 2) + DOWN * CELL / 2)
        write.move_to(RIGHT * (FILL_WIDTH / 2 - side / 2) + DOWN * CELL / 2)
        # The readouts sit right of the gap's centre, clear of the kernel overhanging the read grid
        readout = (read.get_right() + write.get_left() + RIGHT * CELL) / 2 + UP * SPACE_2

        order = [(r, c) for r in range(SIZE) for c in range(SIZE)]
        sums = {
            count: Mono(f"sum / {count}", font_size=TEXT_XS, color=TEXT).move_to(readout)
            for count in {len(neighbours(*cell)) for cell in order}
        }
        answers = {
            cell: Mono(f"= {results[cell]:.{DECIMALS}f}", font_size=TEXT_XS, color=HIGHLIGHT)
            .next_to(sums[KERNEL**2], DOWN, buff=SPACE_2)
            for cell in order
        }

        def flying_values(cell: tuple[int, int]) -> VGroup:
            return VGroup(*(read.label(*source).copy().set_color(POINT) for source in neighbours(*cell)))

        self.add(read, write)
        self.cue("To blur it")

        # The first pixel in reading order, which is also the corner
        first = order[0]
        kernel = kernel_box(read, *first, size=1)
        wash = always_redraw(lambda: lit_cells(read, kernel))
        self.play(FadeIn(kernel), FadeIn(wash), run_time=BEAT, rate_func=EASE)

        self.cue("the average of the pixels")
        self.play(kernel.animate.scale(KERNEL), FadeIn(sums[KERNEL**2]), run_time=MOVE, rate_func=EASE)

        # The kernel hangs off the corner: the missing cells are hatched, the count becomes 4
        self.cue("ignoring any positions")
        offgrid = [(first[0] + dr, first[1] + dc) for dr in (-1, 0, 1) for dc in (-1, 0, 1)]
        hatches = VGroup(*(hatched(read.point(*cell)) for cell in offgrid if not in_bounds(*cell)))
        corner_sum = sums[len(neighbours(*first))]
        self.play(FadeIn(hatches), FadeOut(sums[KERNEL**2]), FadeIn(corner_sum), run_time=BEAT, rate_func=EASE)

        # The values under the kernel fly to its centre pixel; their average appears
        flying = flying_values(first)
        self.play(
            LaggedStart(*(f.animate.move_to(read.point(*first)).scale(0.6).set_opacity(0) for f in flying), lag_ratio=0.03),
            run_time=MOVE,
            rate_func=EASE,
        )
        self.remove(flying)
        answer = answers[first]
        self.play(FadeIn(answer), run_time=QUICK, rate_func=EASE)
        self.cue("Each result goes")

        # The average lands in the second buffer, which gets its name
        name = Text("write buffer", font_size=TEXT_BASE, color=TEXT).next_to(write.squares, DOWN, buff=SPACE_1)
        value = answer[1:].copy()
        self.add(value)
        landed = write.label(*first).copy().set_opacity(1)
        self.play(
            ReplacementTransform(value, landed),
            write.square(*first).animate.set_fill(opacity=1),
            FadeOut(hatches),
            FadeIn(name),
            run_time=MOVE,
            rate_func=EASE,
        )
        self.remove(landed)
        write.label(*first).set_opacity(1)

        # The sweep through every other cell. One animation, for exact timing at any speed
        steps = order[1:]
        durations = np.maximum(FASTEST_STEP, SLOWEST_STEP * SPEED_UP ** np.arange(len(steps)))
        ends = np.cumsum(durations)
        total = durations.sum()
        # Fixed mobjects restyled per step: the scene only redraws those it held when the play began
        shown_sum, shown_answer = corner_sum.copy(), answer.copy()
        self.remove(corner_sum, answer)
        in_flight = VGroup(*(read.label(*first).copy().set_opacity(0) for _ in range(KERNEL**2)))
        progress = {"step": -1, "sources": []}

        def sweep(_, alpha):
            now = alpha * total
            i = min(int(np.searchsorted(ends, now, side="right")), len(steps) - 1)
            within = (now - ends[i] + durations[i]) / durations[i]
            r, c = steps[i]
            previous = order[i]

            if i != progress["step"]:
                # Everything before this cell is now written, with its answer showing
                for cell in order[: i + 1]:
                    write.square(*cell).set_fill(opacity=1)
                    write.label(*cell).set_opacity(1)
                shown_sum.become(sums[len(neighbours(r, c))])
                shown_answer.become(answers[previous])
                sources = neighbours(r, c)
                for mob, source in zip(in_flight, sources):
                    mob.become(read.label(*source).copy().set_color(POINT))
                progress.update(step=i, sources=[read.point(*cell) for cell in sources])

            # A new row starts with a clean cut back to the left, never a diagonal glide
            arrived = min(within / GLIDE, 1.0)
            start = read.point(*previous) if previous[0] == r else read.point(r, c)
            kernel.move_to(interpolate(start, read.point(r, c), EASE(arrived)))

            flown = max((within - GLIDE) / (1 - GLIDE), 0.0)
            in_flight.set_opacity(0)
            if arrived >= 1:
                for mob, source in zip(in_flight, progress["sources"]):
                    mob.move_to(interpolate(source, read.point(r, c), flown)).set_opacity(1)

            if alpha >= 1:
                write.square(r, c).set_fill(opacity=1)
                write.label(r, c).set_opacity(1)
                shown_answer.become(answers[r, c])
                in_flight.set_opacity(0)

        self.play(
            UpdateFromAlphaFunc(VGroup(kernel, write, shown_sum, shown_answer, in_flight), sweep),
            run_time=total,
            rate_func=linear,
        )

        wash.clear_updaters()
        self.play(FadeOut(kernel), FadeOut(wash), FadeOut(shown_sum), FadeOut(shown_answer), run_time=QUICK, rate_func=EASE)
        self.cue("Let's try a 41 by 41")
