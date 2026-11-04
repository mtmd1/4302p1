"""Gaussian 4: wipe between box r = 20 and Gaussian sigma = 7, then zoom both to LAMP.

    uv run render gauss_compare

Both kernels really are 41 x 41, so their cost matches in the next clip.
"""

from functools import lru_cache

from PIL import Image

from style import *

import blur
from components import FIGURES, LAMP
from sample import photo

# The part of the photo shown, in source pixels: little sky, so the town fills it
# and there's room below for each method's name and its kernel
VIEW = (240, 380, 1440, 700)  # x, y, width, height
IMAGE_WIDTH = 5.7
IMAGE_HEIGHT = IMAGE_WIDTH * VIEW[3] / VIEW[2]
IMAGE_AT = UP * (FILL_HEIGHT - IMAGE_HEIGHT) / 2
ZOOM_ACROSS = 150  # Source pixels across each half once zoomed

HEATMAP_SIDE = 1.85  # Of each square kernel heatmap, big enough for 41 x 41 cells to stay apart
CELL_GAP = 0.3  # Share of a cell's side left empty around it
WIPE = 2.4  # Seconds for the slider to reach the middle
ZOOM = 3.0  # Seconds to zoom both halves to the lamp
KNOB = 0.11


@lru_cache
def blurred() -> tuple[np.ndarray, np.ndarray]:
    image = photo()
    radius = FIGURES.radius_box
    box = blur.box(image, radius).image
    gaussian = blur.gaussian(image, FIGURES.sigma_gaussian, radius=radius, separable=True).image
    return blur.to_uint8(box), blur.to_uint8(gaussian)


def pixel_size() -> tuple[int, int]:
    scale = config.pixel_width / config.frame_width
    return round(IMAGE_WIDTH * scale), round(IMAGE_HEIGHT * scale)


def view(source: np.ndarray, focus, across: float, size: tuple[int, int]) -> np.ndarray:
    """A window of source, focus-centred and across pixels wide, resampled to size."""
    half_w, half_h = across / 2, across * size[1] / size[0] / 2
    # Pixel rounding can tip a window that touches the photo's edge just past it
    x = min(max(focus[0], half_w), source.shape[1] - half_w)
    y = min(max(focus[1], half_h), source.shape[0] - half_h)
    box = (x - half_w, y - half_h, x + half_w, y + half_h)
    return np.asarray(Image.fromarray(source).resize(size, Image.BILINEAR, box=box))


def frame(slider: float, zoomed: float) -> np.ndarray:
    """The picture: at zoomed = 0 one view split at slider, at 1 each half centred on the lamp."""
    box, gaussian = blurred()
    width, height = pixel_size()
    x, y, view_w, view_h = VIEW
    middle = width // 2
    if zoomed == 0:
        left = view(box, (x + view_w / 2, y + view_h / 2), view_w, (width, height))
        right = view(gaussian, (x + view_w / 2, y + view_h / 2), view_w, (width, height))
        split = round(slider * width)
        return np.concatenate([left[:, :split], right[:, split:]], axis=1)

    # The zoom is even on a log scale, with the lamp sliding in to each half's middle
    start = view_w / 2
    across = np.exp((1 - zoomed) * np.log(start) + zoomed * np.log(ZOOM_ACROSS))
    target = np.array(LAMP, float)
    drift = (across / start) * (1 - zoomed)
    sides = []
    for source, centre, size in (
        (box, x + view_w / 4, (middle, height)),
        (gaussian, x + 3 * view_w / 4, (width - middle, height)),
    ):
        focus = target + (np.array([centre, y + view_h / 2]) - target) * drift
        sides.append(view(source, focus, across, size))
    return np.concatenate(sides, axis=1)


def picture(slider: float = 0.5, zoomed: float = 0.0) -> ImageMobject:
    mob = ImageMobject(frame(slider, zoomed)).set_resampling_algorithm(RESAMPLING_ALGORITHMS["nearest"])
    mob.width = IMAGE_WIDTH
    return mob.move_to(IMAGE_AT)


def divider() -> Line:
    return Line(IMAGE_AT + UP * IMAGE_HEIGHT / 2, IMAGE_AT + DOWN * IMAGE_HEIGHT / 2, color=TEXT, stroke_width=STROKE)


def half_centre(side: int) -> np.ndarray:
    """Where a caption under the left (-1) or right (1) half is centred, at height 0."""
    return np.array([side * IMAGE_WIDTH / 4, 0.0, 0.0])


def method_label(name: str, parameter: str, color) -> VGroup:
    word = Text(name, font_size=TEXT_SM, color=color)
    value = Mono(parameter, font_size=TEXT_SM, color=TEXT).next_to(word, RIGHT, buff=SPACE_1)
    # Measured from the last letter's baseline, so a "g" doesn't lift one name above the other
    value.shift(UP * (word[-1].get_bottom()[1] - value.get_bottom()[1]))
    return VGroup(word, value)


def caption_y() -> float:
    """Middle of the space under the image."""
    return (IMAGE_AT[1] - IMAGE_HEIGHT / 2 - FILL_HEIGHT / 2) / 2


def heatmap(weights: np.ndarray) -> Group:
    """A kernel as separate cells, on one colour scale so the two can be compared.

    Drawn on the output's pixel grid, as resampling would blur the gaps away.
    """
    scale = config.pixel_width / config.frame_width
    size = len(weights)
    pitch = int(HEATMAP_SIDE * scale / size)
    gap = max(1, round(pitch * CELL_GAP))
    pixels = np.zeros((size * pitch + gap, size * pitch + gap, 4), np.uint8)
    for r, c in np.ndindex(size, size):
        shade = (np.array(magma(float(weights[r, c])).to_rgb()) * 255).astype(np.uint8)
        pixels[r * pitch + gap : (r + 1) * pitch, c * pitch + gap : (c + 1) * pitch] = [*shade, 255]
    mob = ImageMobject(pixels).set_resampling_algorithm(RESAMPLING_ALGORITHMS["nearest"])
    mob.width = pixels.shape[1] / scale
    return Group(mob)


def kernels() -> tuple[np.ndarray, np.ndarray]:
    radius = FIGURES.radius_box
    offsets = np.arange(-radius, radius + 1)
    x, y = np.meshgrid(offsets, offsets)
    gaussian = np.exp(-(x**2 + y**2) / (2 * FIGURES.sigma_gaussian**2))
    gaussian /= gaussian.sum()
    box = np.full_like(gaussian, 1 / gaussian.size)
    return box / gaussian.max(), gaussian / gaussian.max()


def captions() -> tuple[Group, Group]:
    """Under each half: the method's name and value, then its kernel's weights."""
    box_map, gaussian_map = (heatmap(k) for k in kernels())
    names = (
        method_label("box", f"r = {FIGURES.radius_box}", BOX),
        method_label("gaussian", f"σ = {FIGURES.sigma_gaussian}", GAUSSIAN),
    )
    # On one baseline, whatever their descenders, with even gaps above and below the row
    above = max(name.get_top()[1] - name[0][-1].get_bottom()[1] for name in names)
    below = max(name[0][-1].get_bottom()[1] - name.get_bottom()[1] for name in names)
    baseline = IMAGE_AT[1] - IMAGE_HEIGHT / 2 - SPACE_2 - above
    groups = []
    for side, name, weights in zip((-1, 1), names, (box_map, gaussian_map)):
        weights.move_to(half_centre(side) + UP * (baseline - below - SPACE_2), aligned_edge=UP)
        name.set_x(weights.get_x()).shift(UP * (baseline - name[0][-1].get_bottom()[1]))
        groups.append(Group(name, weights))
    return tuple(groups)


class GaussCompare(ClipScene):
    def construct(self):
        slider = ValueTracker(1.0)
        zoomed = ValueTracker(0.0)
        still = picture(1.0)
        last = {}

        def refresh(mob):
            key = (slider.get_value(), zoomed.get_value())
            if last.get("key") != key:
                last.update(key=key)
                mob.pixel_array = frame(*key)

        still.add_updater(refresh)

        line = divider()
        knob = Circle(radius=KNOB, stroke_width=0, fill_color=TEXT, fill_opacity=1)
        handle = VGroup(line, knob)
        handle.add_updater(
            lambda g: g.set_x(IMAGE_AT[0] + (slider.get_value() - 0.5) * IMAGE_WIDTH)
        )
        handle.update()

        left, right = captions()

        self.cue("At roughly the same kernel size")
        self.play(FadeIn(still), FadeIn(left), FadeIn(handle), run_time=MOVE, rate_func=EASE)

        # The slider comes in from the right edge, uncovering the Gaussian
        self.play(
            slider.animate.set_value(0.5),
            FadeIn(right),
            run_time=WIPE,
            rate_func=EASE,
        )
        self.cue("looks nice and smooth")

        # Knob goes as the zoom starts, since the halves stop being one picture
        self.play(
            FadeOut(knob, run_time=QUICK, rate_func=EASE),
            zoomed.animate(run_time=ZOOM, rate_func=EASE).set_value(1.0),
        )
        self.cue("But it's just as slow")
