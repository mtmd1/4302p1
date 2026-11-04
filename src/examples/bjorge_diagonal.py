"""Bjorge 4: the down kernel. Four diagonal taps straddle the tiles, so the borders go.

    uv run render bjorge_diagonal

Geometry from blur.py's dual_kawase_down. Its offsets are half a destination
texel, which is one source pixel: the centre tap and the four diagonals all sit
on source pixel corners, so each averages exactly one 2x2 block.
"""

from style import *

from components import TapPoint

SIZE = 10
CELL = 0.44  # Leaves the heading room inside the FILL area
CENTRE_OPACITY = 0.7
DIAGONAL_OPACITY = 0.45
LEGEND_GAP = 0.8
NEIGHBOUR_OPACITY = 0.7

DIAGONALS = ((-1, 1), (1, 1), (-1, -1), (1, -1))  # In source pixels from the centre


class BjorgeDiagonal(ClipScene):
    def construct(self):
        cells = VGroup(*(
            Square(CELL, stroke_color=MUTED, stroke_width=STROKE_THIN).move_to(
                np.array([(c - (SIZE - 1) / 2) * CELL, ((SIZE - 1) / 2 - r) * CELL, 0])
            )
            for r in range(SIZE)
            for c in range(SIZE)
        ))
        # An odd number of tiles, so one sits centred on the grid: the output pixel being written
        count = SIZE // 2
        tiles = VGroup(*(
            Square(2 * CELL, color=HIGHLIGHT, stroke_width=STROKE).move_to(
                np.array([(c - (count - 1) / 2) * 2 * CELL, ((count - 1) / 2 - r) * 2 * CELL, 0])
            )
            for r in range(count)
            for c in range(count)
        ))

        grid = VGroup(cells, tiles)
        centre_tile = Square(2 * CELL, stroke_width=0, fill_color=DUAL_KAWASE, fill_opacity=CENTRE_OPACITY)
        centre_cross = TapPoint().set_z_index(1)  # Over the diagonal blocks to come

        legend_centre = VGroup(
            Text("centre", font_size=TEXT_BASE, color=TEXT), Mono("×4", font_size=TEXT_BASE, color=DUAL_KAWASE)
        ).arrange(RIGHT, buff=SPACE_1)
        legend_diagonal = VGroup(
            Text("diagonals", font_size=TEXT_BASE, color=TEXT), Mono("×1", font_size=TEXT_BASE, color=DUAL_KAWASE)
        ).arrange(RIGHT, buff=SPACE_1)
        legend_total = VGroup(Mono("5", font_size=TEXT_BASE, color=TEXT), Text("taps", font_size=TEXT_BASE, color=TEXT)).arrange(RIGHT, buff=SPACE_1)
        legend = VGroup(legend_centre, legend_diagonal, legend_total).arrange(DOWN, aligned_edge=LEFT, buff=SPACE_2)
        legend.next_to(grid, RIGHT, buff=LEGEND_GAP)

        # Stands in for the line the recording lacks, so it's up from the very first frame
        heading = Text("What a modern algorithm does", font_size=TEXT_LG, color=TEXT)
        heading.move_to(UP * FILL_HEIGHT / 2, aligned_edge=UP)

        everything = VGroup(grid, centre_tile, centre_cross, legend)
        offset = np.array([-VGroup(grid, legend).get_center()[0], heading.get_bottom()[1] - SPACE_2 - grid.get_top()[1], 0])
        everything.shift(offset)

        self.add(grid, heading)
        self.cue("So as we shrink")
        self.cue("Keep the centre tap")
        self.play(FadeIn(centre_tile), FadeIn(centre_cross), FadeIn(legend_centre), run_time=MOVE, rate_func=EASE)

        self.cue("add four of Kawase's")
        taps = VGroup()
        for dx, dy in DIAGONALS:
            point = offset + np.array([dx * CELL, dy * CELL, 0])
            block = Square(2 * CELL, stroke_width=0, fill_color=DUAL_KAWASE, fill_opacity=DIAGONAL_OPACITY).move_to(point)
            taps.add(block, TapPoint().set_z_index(1).move_to(point))
        self.play(FadeIn(taps), FadeIn(legend_diagonal), FadeIn(legend_total), run_time=MOVE, rate_func=EASE)

        self.cue("No hard borders")
        footprint = Square(4 * CELL, color=DUAL_KAWASE, stroke_width=STROKE_BOLD).move_to(offset)
        neighbours = VGroup(*(
            Square(4 * CELL, color=DUAL_KAWASE, stroke_width=STROKE, stroke_opacity=NEIGHBOUR_OPACITY).move_to(offset + 2 * CELL * direction)
            for direction in (LEFT, RIGHT, UP, DOWN)
        ))
        self.play(FadeOut(tiles), FadeIn(footprint), FadeIn(neighbours), run_time=MOVE, rate_func=EASE)
        self.cue("And on the way up")
