"""Box blur 7: the lamp in the box blur is a hard square; a lens makes it a soft disc.

    uv run render box_artifact

The disc blur is computed here in numpy, as linear-light averaging like blur.box,
and stands in for a real lens. Both crops share a brightness lift (LIFT_BLACK,
LIFT_GAIN): the square is only about twice the brightness of the sand around it,
too faint to read as a shape at normal levels.
"""

from style import *

import blur
from components import FIGURES, LAMP, fit, photo_still
from pixels import PixelView, zoom
from sample import photo

ACROSS = 120  # Source pixels shown in each crop, close enough that the square fills half
CROP_SIDE = 4.4  # Manim units
ZOOM = 3.2  # Seconds to zoom from the whole photo to the lamp

# Same area as the 41x41 box, so both spread the lamp's light equally thin
DISC_RADIUS = round(((2 * FIGURES.radius_box + 1) ** 2 / PI) ** 0.5)

LIFT_BLACK = 0.06  # sRGB value that maps to black
LIFT_GAIN = 2.6


def disc_blur(image: np.ndarray, centre: tuple[int, int], reach: int, radius: int) -> np.ndarray:
    """A hard-edged disc of radius over the square of half-width reach around centre, as RGB.

    Convolved by FFT over a window wider by radius, so wrap-around stays outside
    the result, and clamped to the image, whose bottom edge is close to the lamp.
    """
    x, y = centre
    pad = reach + radius
    top, bottom = max(y - pad, 0), min(y + pad + 1, image.shape[0])
    left, right = max(x - pad, 0), min(x + pad + 1, image.shape[1])
    linear = blur.srgb_to_linear(image[top:bottom, left:right, :3]).astype(np.float64)

    ys, xs = np.mgrid[-radius : radius + 1, -radius : radius + 1]
    disc = (xs**2 + ys**2 <= radius**2).astype(np.float64)
    disc /= disc.sum()

    shape = linear.shape[:2]
    spectrum = np.fft.rfft2(disc, shape)
    out = np.stack([np.fft.irfft2(np.fft.rfft2(linear[..., c]) * spectrum, shape) for c in range(3)], axis=2)
    # rfft2 convolves from the kernel's corner, so result (i, j) is centred on (i - radius, j - radius)
    i, j = y - top + radius, x - left + radius
    return blur.linear_to_srgb(out[i - reach : i + reach, j - reach : j + reach].astype(np.float32))


def lifted(rgb: np.ndarray) -> np.ndarray:
    """Stretch brightness only, so the sand stays dark and doesn't turn orange."""
    brightness = rgb.mean(axis=2, keepdims=True)
    return np.clip(rgb * np.clip((brightness - LIFT_BLACK) * LIFT_GAIN, 0, None) / brightness, 0, 1)


IMAGE = photo()
BOXED = blur.box(IMAGE, FIGURES.radius_box).image
_x, _y, _reach = LAMP[0], LAMP[1], ACROSS // 2
BOX_CROP = lifted(BOXED[_y - _reach : _y + _reach, _x - _reach : _x + _reach, :3])
DISC_CROP = lifted(disc_blur(IMAGE, LAMP, _reach, DISC_RADIUS))


class Artifact(ClipScene):
    def construct(self):
        view = PixelView(BOXED, box=fit(BOXED.shape[1], BOXED.shape[0]))
        self.add(view)
        self.cue("You'll also notice")
        self.play(zoom(view, LAMP, ACROSS, box=(CROP_SIDE, CROP_SIDE), run_time=ZOOM, rate_func=EASE))

        # Swap the raw zoom for the smoothed, lifted crop as one change
        square = photo_still(BOX_CROP, width=CROP_SIDE)
        self.play(FadeIn(square), run_time=MOVE, rate_func=EASE)
        self.remove(view)

        offset = RIGHT * (CROP_SIDE + SPACE_3) / 2
        round_one = photo_still(DISC_CROP, width=CROP_SIDE).move_to(offset)
        box_label = Text("box blur", font_size=TEXT_BASE, color=BOX)
        lens_label = Text("lens blur", font_size=TEXT_BASE, color=TEXT)
        lens_label.next_to(round_one, DOWN, buff=SPACE_2)
        box_label.next_to(square, DOWN, buff=SPACE_2).shift(-offset)
        box_label.match_y(lens_label)

        self.play(
            square.animate.shift(-offset),
            FadeIn(box_label, shift=-offset),
            FadeIn(round_one),
            FadeIn(lens_label),
            run_time=MOVE,
            rate_func=EASE,
        )
        self.cue("Consider our box blur kernel")
