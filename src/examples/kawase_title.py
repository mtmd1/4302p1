"""Kawase 1: an empty, credited frame for the GDC 2003 slides and the gameplay video.

    uv run render kawase_title

The footage itself is placed over this in Resolve.
"""

from style import *

from components import slot


class Title(ClipScene):
    def construct(self):
        frame = slot("GDC 2003 slides, then gameplay", "Kawase, GDC 2003. Gameplay: Game PLAY Archives, YouTube")
        self.cue("In his 2003 GDC talk")
        self.play(FadeIn(frame), run_time=MOVE, rate_func=EASE)
        self.cue("What do you think")
