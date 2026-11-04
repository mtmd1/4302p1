"""Bjorge 3: one tap per 2x2 tile, tiles that never overlap and all regroup when the image moves.

    uv run render bjorge_tiles
"""

from style import *

import blur
from components import grey
from sample import photo

# Real photo pixels, the bright shopfronts and their dark frames, found by searching
# the town for where every tile's average changes most when the photo moves one
# pixel. One spare column slides in on the shift.
PATCH_X, PATCH_Y = 488, 815
SIZE = 8
CELL = 0.55
GAP = 1.6  # Between the source grid and the output grid
FLOW = 2.0  # Seconds for the remaining tiles to flow, after the first
FLOW_LAG = 0.08  # Lag ratio of those tiles
FLASH_OPACITY = 0.6


def patch() -> np.ndarray:
    return photo()[PATCH_Y : PATCH_Y + SIZE, PATCH_X : PATCH_X + SIZE + 1, :3].mean(axis=2)


def halved(pixels: np.ndarray) -> np.ndarray:
    return blur.downscale(pixels).image


class BjorgeTiles(ClipScene):
    def construct(self):
        values = patch()
        before, after = halved(values[:, :SIZE]), halved(values[:, 1:])

        cells = VGroup(*(
            Square(CELL, fill_color=grey(values[r, c]), fill_opacity=1, stroke_color=MUTED, stroke_width=STROKE_THIN)
            .move_to(np.array([(c - (SIZE - 1) / 2) * CELL, ((SIZE - 1) / 2 - r) * CELL, 0]))
            for r in range(SIZE)
            for c in range(SIZE + 1)
        ))
        spare = VGroup(*(cells[r * (SIZE + 1) + SIZE] for r in range(SIZE)))
        spare.set_opacity(0)

        half = SIZE // 2
        outputs = VGroup(*(
            Square(CELL, stroke_color=MUTED, stroke_width=STROKE_THIN).move_to(
                np.array([(c - (half - 1) / 2) * CELL, ((half - 1) / 2 - r) * CELL, 0])
            )
            for r in range(half)
            for c in range(half)
        ))
        total = SIZE * CELL + GAP + half * CELL
        source_shift = LEFT * (total - SIZE * CELL) / 2
        output_shift = RIGHT * (total - half * CELL) / 2
        cells.shift(source_shift)
        outputs.shift(output_shift)

        source_label = Text("source", font_size=TEXT_SM, color=MUTED)
        source_label.next_to(source_shift + DOWN * SIZE * CELL / 2, DOWN, buff=SPACE_1)
        output_label = Text("half size", font_size=TEXT_SM, color=MUTED)
        output_label.next_to(outputs, DOWN, buff=SPACE_1)

        self.add(cells, outputs, source_label, output_label)
        self.cue("Why? When we halve")

        def tile_point(r, c):
            return source_shift + np.array([(c - (half - 1) / 2) * 2 * CELL, ((half - 1) / 2 - r) * 2 * CELL, 0])

        tiles = VGroup(*(
            Square(2 * CELL, color=HIGHLIGHT, stroke_width=STROKE).move_to(tile_point(r, c))
            for r in range(half)
            for c in range(half)
        ))
        tiles.set_z_index(1)  # Stay over the pixels, which slide beneath them
        self.play(FadeIn(tiles), run_time=MOVE, rate_func=EASE)

        def flow(index: int) -> Animation:
            r, c = divmod(index, half)
            members = [cells[(2 * r + i) * (SIZE + 1) + 2 * c + j] for i in (0, 1) for j in (0, 1)]
            target = outputs[index].copy().set_fill(grey(before[r, c]), opacity=1)
            return AnimationGroup(*(
                Transform(member.copy(), target.copy(), remover=True) for member in members
            ), rate_func=EASE)

        def land(index: int):
            r, c = divmod(index, half)
            outputs[index].set_fill(grey(before[r, c]), opacity=1)

        self.play(flow(0), run_time=MOVE)
        land(0)
        self.play(LaggedStart(*(flow(i) for i in range(1, half * half)), lag_ratio=FLOW_LAG, run_time=FLOW))
        for i in range(1, half * half):
            land(i)

        self.cue("The blocks never overlap")
        shift_label = Mono("shift 1 pixel", font_size=TEXT_SM, color=HIGHLIGHT)
        shift_label.next_to(source_shift + UP * SIZE * CELL / 2, UP, buff=SPACE_1)
        leaving = VGroup(*(cells[r * (SIZE + 1)] for r in range(SIZE)))
        kept = VGroup(*(cell for cell in cells if cell not in leaving and cell not in spare))
        self.play(
            FadeIn(shift_label),
            kept.animate.shift(LEFT * CELL),
            spare.animate.shift(LEFT * CELL).set_opacity(1),
            leaving.animate.shift(LEFT * CELL).set_opacity(0),
            run_time=MOVE,
            rate_func=EASE,
        )

        flash = VGroup(*(
            tile.copy().set_stroke(width=0).set_fill(HIGHLIGHT, opacity=FLASH_OPACITY) for tile in tiles
        ))
        self.play(
            Succession(FadeIn(flash, run_time=QUICK), FadeOut(flash, run_time=MOVE)),
            *(
                square.animate.set_fill(grey(after[divmod(i, half)]), opacity=1)
                for i, square in enumerate(outputs)
            ),
            run_time=QUICK + MOVE,
        )
        self.cue("So as we shrink")
