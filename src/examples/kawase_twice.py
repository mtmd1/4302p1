"""Kawase 2: blurring twice. A gaussian only gets blurrier; a box loses its square.

    uv run render kawase_twice

Each second pass is the real blur run again on the first pass's output.
"""

from functools import lru_cache

from style import *

import blur
from components import FIGURES, LAMP, photo_still
from sample import photo

LABEL_ROOM = 0.6  # Height kept under the photo for its label
PHOTO_WIDTH = (FILL_HEIGHT - LABEL_ROOM) * 16 / 9
PHOTO_POS = UP * LABEL_ROOM / 2

CIRCLE_RADIUS = 0.34  # Around the lamp on the photo
INSET_SIZE = 2.5  # Side of the close-up of the lamp
INSET_HALF = 62  # Source pixels from the lamp to the close-up's edge
LINE_FADE = 0.1  # Fraction of a sweep over which its line fades, at each end


@lru_cache
def images() -> dict[str, np.ndarray]:
    """Uint8 stills of each result, and of the lamp in the box blurs."""
    image = photo()
    gauss = blur.gaussian(image, FIGURES.sigma_gaussian, separable=True).image
    box = blur.box(image, FIGURES.radius_box, separable=True).image
    return {
        "gauss 1": gauss,
        "gauss 2": blur.gaussian(gauss, FIGURES.sigma_gaussian, separable=True).image,
        "box 1": box,
        "box 2": blur.box(box, FIGURES.radius_box, separable=True).image,
    }


def close_up(image: np.ndarray) -> ImageMobject:
    x, y = LAMP
    crop = image[y - INSET_HALF : y + INSET_HALF, x - INSET_HALF : x + INSET_HALF]
    return photo_still(crop, width=INSET_SIZE)


def sweep(still: ImageMobject, after: np.ndarray, line: Line, **kwargs) -> Animation:
    """Replace still's pixels with after's from left to right, behind a moving line."""
    before = still.pixel_array.copy()
    target = blur.to_uint8(after)
    columns = before.shape[1]
    left, right = still.get_left()[0], still.get_right()[0]

    def update(mob, alpha):
        split = int(alpha * columns)
        mob.pixel_array = np.concatenate((target[:, :split], before[:, split:]), axis=1)
        line.set_x(interpolate(left, right, alpha))
        line.set_stroke(opacity=min(alpha / LINE_FADE, (1 - alpha) / LINE_FADE, 1))

    return UpdateFromAlphaFunc(still, update, **kwargs)


def two_passes(count: Mono) -> Mono:
    """Fades in over count: on the mono grid, the "pass" they share stays put and only the rest changes."""
    return Mono("2 passes", font_size=TEXT_BASE, color=TEXT).move_to(count, LEFT)


class Twice(ClipScene):
    def construct(self):
        shots = images()
        still = photo_still(shots["gauss 1"], width=PHOTO_WIDTH).move_to(PHOTO_POS)
        method = Text("gaussian", font_size=TEXT_BASE, color=GAUSSIAN)
        count = Mono("1 pass", font_size=TEXT_BASE, color=TEXT)
        label = VGroup(method, count).arrange(RIGHT, buff=SPACE_2).next_to(still, DOWN, buff=SPACE_2)
        line = Line(still.get_top(), still.get_bottom(), color=HIGHLIGHT, stroke_width=STROKE)

        self.cue("What do you think")
        self.play(FadeIn(still), FadeIn(label), run_time=MOVE, rate_func=EASE)

        # The second pass, left to right, counted as it goes
        self.cue("As you'd expect")
        line.set_stroke(opacity=0)
        self.add(line)
        twice = two_passes(count)
        self.play(sweep(still, shots["gauss 2"], line), FadeOut(count), FadeIn(twice), run_time=SLOW, rate_func=EASE)
        self.remove(line)
        label.remove(count).add(twice)

        # The box blur, in the same place, with the lamp ringed and enlarged
        self.cue("What about a box blur")
        box_still = photo_still(shots["box 1"], width=PHOTO_WIDTH).move_to(still)
        box_label = VGroup(
            Text("box", font_size=TEXT_BASE, color=BOX),
            Mono("1 pass", font_size=TEXT_BASE, color=TEXT),
        ).arrange(RIGHT, buff=SPACE_2).next_to(still, DOWN, buff=SPACE_2)
        lamp_at = still.get_corner(UL) + np.array([LAMP[0], -LAMP[1], 0.0]) * still.width / shots["box 1"].shape[1]
        # What's going wrong, in HIGHLIGHT: the box's square. The sweep line stays HIGHLIGHT, the active step
        ring = Circle(CIRCLE_RADIUS, color=HIGHLIGHT, stroke_width=STROKE).move_to(lamp_at)
        inset = close_up(shots["box 1"]).move_to(still.get_corner(DR) + (UL) * (INSET_SIZE / 2 + SPACE_2))
        inset_frame = SurroundingRectangle(inset, color=HIGHLIGHT, buff=0, stroke_width=STROKE)
        link = Line(ring.get_right(), inset_frame.get_left(), color=HIGHLIGHT, stroke_width=STROKE)
        self.play(
            FadeIn(box_still),
            FadeTransform(label, box_label),
            FadeIn(VGroup(ring, link, inset_frame)),
            FadeIn(inset),
            run_time=MOVE,
            rate_func=EASE,
        )
        self.remove(still)

        # Its second pass, counted as it goes, softens the close-up's square into a round blob
        self.cue("Also blurrier")
        softened = close_up(shots["box 2"]).move_to(inset)
        self.add(line)
        self.add(ring, link, inset, softened, inset_frame)  # Stacked now: a play won't reorder them
        self.play(
            sweep(box_still, shots["box 2"], line),
            FadeIn(softened),
            FadeOut(box_label[1]),
            FadeIn(two_passes(box_label[1])),
            run_time=SLOW,
            rate_func=EASE,
        )
        self.remove(line)

        self.cue("Convolution is associative")
