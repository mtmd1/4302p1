"""Box blur 6: the running tap counter starts, and taps per frame roll up to billions.

    uv run render box_counter
"""

from style import *

from components import FIGURES, TapCounter

COUNTER_TOP = FILL_HEIGHT / 2 - SPACE_2
PRODUCT_Y = 1.65
ODOMETER_Y = 0.8
FRAME_4K_HEIGHT = 2.9
FRAME_CENTRE = DOWN * (FILL_HEIGHT / 2 - FRAME_4K_HEIGHT / 2)
# Faster than style's count pace: the total must have settled before "three and a half"
FIRST_ROLL = 1.2


def roll(tracker: ValueTracker, start: float, end: float, run_time: float) -> Animation:
    """An odometer to end over run_time, even on a log scale, so each decade takes the same time."""

    def update(mob, alpha):
        mob.set_value(end if alpha >= 1 else start * (end / start) ** alpha)

    return UpdateFromAlphaFunc(tracker, update, run_time=run_time, rate_func=linear)


def odometer_text(value: float) -> Mono:
    return Mono(f"{round(value):,}", font_size=TEXT_XL, color=TEXT)


class Counter(ClipScene):
    def construct(self):
        taps = FIGURES.taps_box
        per_frame, per_frame_4k = FIGURES.taps_per_frame_1080p, FIGURES.taps_per_frame_4k

        counter = TapCounter(taps, top=COUNTER_TOP)
        product = Mono(f"{taps} x 1920 x 1080", font_size=TEXT_SM, color=MUTED).move_to(UP * PRODUCT_Y)
        # Redrawn whole, not as manim's Integer: that spaces digits by their ink, so it
        # isn't really monospaced and would jitter as the digits roll
        total = ValueTracker(taps)
        shown = ValueTracker(0)  # A FadeIn would freeze the redraw, and the roll runs through the fade
        odometer = always_redraw(
            lambda: odometer_text(total.get_value())
            .move_to(UP * ODOMETER_Y)
            .set_opacity(shown.get_value())
        )

        width_4k = FRAME_4K_HEIGHT * 16 / 9
        frame = Rectangle(width=width_4k / 2, height=FRAME_4K_HEIGHT / 2, color=TEXT, stroke_width=STROKE).move_to(FRAME_CENTRE)
        size = Mono("1920 x 1080", font_size=TEXT_XS, color=TEXT).move_to(frame)

        self.cue("That's almost three and a half")
        self.add(odometer)
        self.play(
            counter.add_row("taps per pixel", taps, BOX),
            *(FadeIn(mob, run_time=MOVE, rate_func=EASE) for mob in (product, frame, size)),
            shown.animate(run_time=MOVE, rate_func=EASE).set_value(1),
            roll(total, taps, per_frame, run_time=FIRST_ROLL),
        )
        self.cue("or 14 billion")

        # The 1080p frame stays behind as a ghost, so 4K reads as four of it
        ghost = frame.copy().set_stroke(MUTED, STROKE_THIN)
        self.add(ghost)
        target = frame.copy().stretch_to_fit_width(width_4k).stretch_to_fit_height(FRAME_4K_HEIGHT).move_to(FRAME_CENTRE)
        size_4k = Mono("3840 x 2160", font_size=TEXT_XS, color=TEXT)
        size_4k.next_to(ghost, UP, buff=SPACE_1)
        product_4k = Mono(f"{taps} x 3840 x 2160", font_size=TEXT_SM, color=MUTED).move_to(product)
        self.play(
            Transform(frame, target),
            size.animate.set_color(MUTED),
            FadeIn(size_4k),
            FadeTransform(product, product_4k),
            roll(total, per_frame, per_frame_4k, run_time=MOVE),
            run_time=MOVE,
            rate_func=EASE,
        )
        self.cue("You'll also notice")
