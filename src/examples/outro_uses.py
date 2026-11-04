"""Conclusion 2: three credited frames for the footage of the blur in use, placed in Resolve.

    uv run render outro_uses
"""

from style import *

from components import slot

# Two rows of frames and credits fill the FILL height, leaving this much for each credit
CREDIT_HEIGHT = SPACE_1 + SPACE_2
SLOT_HEIGHT = (FILL_HEIGHT - 2 * CREDIT_HEIGHT - SPACE_2) / 2
SLOT_WIDTH = SLOT_HEIGHT * 16 / 9


class OutroUses(ClipScene):
    def construct(self):
        kde = slot("KDE panel", "KWin, Nemeth 2018", width=SLOT_WIDTH)
        android = slot("Android dialog", "Android, AOSP", width=SLOT_WIDTH)
        game = slot("game bloom", "DOUBLE-S.T.E.A.L, Game PLAY Archives", width=SLOT_WIDTH)

        VGroup(
            VGroup(kde, android).arrange(RIGHT, buff=SPACE_2, aligned_edge=UP),
            game,
        ).arrange(DOWN, buff=SPACE_2).move_to(ORIGIN)

        self.cue("That is why this technique")
        self.play(FadeIn(kde), run_time=MOVE, rate_func=EASE)
        self.cue("Android's window blurs")
        self.play(FadeIn(android), run_time=MOVE, rate_func=EASE)
        self.cue("and many video games")
        self.play(FadeIn(game), run_time=MOVE, rate_func=EASE)
        self.cue("By understanding the hardware")
