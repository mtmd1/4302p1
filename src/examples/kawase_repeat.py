"""Kawase 6: the same pass with no offset: the count climbs, the image all but stops changing.

    uv run render kawase_repeat

Every frame is the real result of that many passes of blur.kawase at offset 0, and
the plot is the real mean absolute difference each of those passes made, drawn as
each pass lands.
"""

from functools import lru_cache

from style import *

import blur
from components import FIGURES
from sample import photo

PHOTO_WIDTH = 6.2
SHRINK = 2  # The cached stills are this much smaller than the photo, to spare memory
SLOW_PASSES = 3  # Shown one at a time before the race starts
RACE = 2.1  # Seconds from there to the last pass
PANEL_WIDTH = 3.1
PLOT_HEIGHT = 1.9
PASSES_Y, PASSES_NAME_Y = 1.85, 0.95
PLOT_BOTTOM = -1.6
CAPTION_Y = PLOT_BOTTOM - SPACE_3
END_DOT = 0.07


@lru_cache
def stills() -> tuple[list[np.ndarray], np.ndarray]:
    """The photo after 0, 1, ... passes at offset 0, as small uint8 images, and each pass's change."""
    image = photo()
    out, change = [], []
    for n in range(FIGURES.passes_no_offset + 1):
        small = image[: image.shape[0] // SHRINK * SHRINK, : image.shape[1] // SHRINK * SHRINK]
        height, width = small.shape[0] // SHRINK, small.shape[1] // SHRINK
        small = small.reshape(height, SHRINK, width, SHRINK, -1).mean(axis=(1, 3))
        out.append(blur.to_uint8(small))
        if n < FIGURES.passes_no_offset:
            after = blur.kawase(image, (0,)).image
            change.append(float(np.abs(after - image).mean()))
            image = after
    return out, np.array(change)


class Repeat(ClipScene):
    def construct(self):
        frames, change = stills()
        last = FIGURES.passes_no_offset
        left_x = -FILL_WIDTH / 2
        still = ImageMobject(frames[0]).set_resampling_algorithm(RESAMPLING_ALGORITHMS["bilinear"])
        still.width = PHOTO_WIDTH
        still.move_to([left_x + PHOTO_WIDTH / 2, 0, 0])

        panel_left = FILL_WIDTH / 2 - PANEL_WIDTH
        panel_x = panel_left + PANEL_WIDTH / 2
        passes = Integer(0, font_size=TEXT_XL, color=TEXT, group_with_commas=False)
        passes.move_to([panel_x, PASSES_Y, 0])
        passes_name = Text("passes", font_size=TEXT_BASE, color=MUTED).move_to([panel_x, PASSES_NAME_Y, 0])

        def point(n: float, value: float) -> np.ndarray:
            return np.array([panel_left + (n - 1) / (last - 1) * PANEL_WIDTH, PLOT_BOTTOM + value / change[0] * PLOT_HEIGHT, 0.0])

        base = Line(point(1, 0), point(last, 0), color=MUTED, stroke_width=STROKE)
        spine = Line(point(1, 0), point(1, change[0]), color=MUTED, stroke_width=STROKE)
        zero = Mono("0", font_size=TEXT_XS, color=MUTED).next_to(point(1, 0), LEFT, buff=SPACE_1)
        caption = Text("change per pass", font_size=TEXT_SM, color=MUTED).move_to([panel_x, CAPTION_Y, 0])
        line = VMobject(color=KAWASE, stroke_width=STROKE)
        latest = Dot(radius=END_DOT, color=KAWASE, fill_opacity=0)

        def show(n: int):
            """One state: the photo, the count and the plot all after n passes."""
            still.pixel_array = frames[n]
            passes.set_value(n)
            passes.move_to([panel_x, passes.get_y(), 0])
            if n:
                latest.move_to(point(n, change[n - 1])).set_fill(opacity=1)
            if n > 1:
                line.set_points_as_corners([point(i + 1, value) for i, value in enumerate(change[:n])])

        self.cue("But repeat this as it is")
        self.play(
            FadeIn(still), FadeIn(passes), FadeIn(passes_name), FadeIn(VGroup(base, spine, zero, caption)),
            run_time=MOVE, rate_func=EASE,
        )
        self.add(line, latest)  # Empty until the first pass, and after the photo, which redraws them

        # The first passes one by one, so the method is clear, then the race
        for n in range(1, SLOW_PASSES + 1):
            self.play(
                UpdateFromAlphaFunc(still, lambda m, a, n=n: show(n) if a > 0 else None),
                run_time=BEAT,
                rate_func=EASE,
            )

        def race(mob, alpha):
            show(SLOW_PASSES + round(alpha * (last - SLOW_PASSES)))

        self.play(UpdateFromAlphaFunc(still, race), run_time=RACE, rate_func=linear)

        # The tail: flat, on zero
        self.cue("having an effect")
        self.play(passes.animate.set_color(HIGHLIGHT), latest.animate.set_color(HIGHLIGHT), run_time=QUICK, rate_func=EASE)
        self.cue("So Kawase reaches further")
