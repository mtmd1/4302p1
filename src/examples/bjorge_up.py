"""Bjorge 5: one bilinear tap makes a pyramid, eight taps in a ring make a dome, and
the same sweep with the ring comes out smooth where the pyramids left it blocky.

    uv run render bjorge_up

Both surfaces are the real kernels: an impulse run through blur.py's own shaders
at a much higher destination resolution, so the response can be drawn smoothly.
Its dual_kawase_up offset is one destination texel at a true 2x stretch, which is
half a low-res pixel, whatever size is actually rendered.
"""

from functools import lru_cache

from style import *

import blur
from components import TapPoint

STRETCH = 17  # Odd, so a destination pixel lands on each low-res centre and the peak is exact
SPAN = 7  # Low-res pixels across the floor
HEIGHT = 2.2  # Scene units for a kernel value of 1
RESOLUTION = 8  # Surface facets per low-res pixel, on the kinks of the bilinear kernel
LOCAL = 2  # Half-width of the single-kernel surface, in low-res pixels
FADE = 0.05  # Kernel value below which facets fade out, so the outline isn't a staircase
EDGE = 0.5  # Hairline between facets, so no seams show

FIELD_LOW, FIELD_HIGH = 0.2, 0.55  # The field's low-res pixel values, a checker. See kernels()
PHI, THETA = 58 * DEGREES, -68 * DEGREES  # Turned so the checker's peaks read as diamonds
ZOOM = 0.95
CLOSE_PHI, CLOSE_ZOOM = 38 * DEGREES, 1.2  # Higher and nearer, so all eight taps show
CLOSE_SPAN = 5  # The floor trims to this, to stay inside the frame up close
DOT_LIFT = 0.06  # Above the surface they read, so they aren't buried in it

SWEEP = 1.7  # Every low-res pixel's kernel arrives in this; at least one frame each at 30 fps
RING_UNIFORMS = {"offset": STRETCH / 2}  # One destination texel at the true 2x stretch
SINK_STEPS = SPAN  # The lone pyramid drains away over the first row of arrivals

# Offsets in low-res pixels, with weights. One destination texel is half a low-res pixel.
RING = [
    (0.5, 0.0, 1), (-0.5, 0.0, 1), (0.0, 0.5, 1), (0.0, -0.5, 1),
    (0.25, 0.25, 2), (-0.25, 0.25, 2), (0.25, -0.25, 2), (-0.25, -0.25, 2),
]


def stretched(source: np.ndarray, program: str, uniforms: dict) -> np.ndarray:
    """Run one of blur.py's shaders at STRETCH times the source's resolution."""
    h, w = source.shape

    def build(texture, textures):
        return [blur._Pass(program, texture, textures.target((w * STRETCH, h * STRETCH), texture), 1, uniforms)]

    return blur._run(source.astype(np.float32), build, linear=False, steps=False, repeat=1, half=False).image


@lru_cache(maxsize=None)
def kernels() -> dict[str, np.ndarray]:
    impulse = np.zeros((SPAN, SPAN), np.float32)
    impulse[SPAN // 2, SPAN // 2] = 1
    # A photo crop is too smooth for the kernel's shape to show, so the field is a checker
    checker = np.indices((SPAN, SPAN)).sum(axis=0) % 2
    field = FIELD_LOW + (FIELD_HIGH - FIELD_LOW) * checker
    return {
        "pyramid": stretched(impulse, "resample", {}),
        "dome": stretched(impulse, "dual_kawase_up", RING_UNIFORMS),
        "field": stretched(field, "resample", {}),
    }


def sample(values: np.ndarray, x: float, y: float) -> float:
    """Bilinear lookup at (x, y) in low-res pixels from the centre of the floor."""
    size = values.shape[0]
    u = np.clip((x + SPAN / 2) * STRETCH - 0.5, 0, size - 1.001)
    v = np.clip((SPAN / 2 - y) * STRETCH - 0.5, 0, size - 1.001)
    i, j = int(u), int(v)
    a, b = u - i, v - j
    return float(
        values[j, i] * (1 - a) * (1 - b) + values[j, i + 1] * a * (1 - b)
        + values[j + 1, i] * (1 - a) * b + values[j + 1, i + 1] * a * b
    )


def arrivals(lone: np.ndarray, count: int, program: str, uniforms: dict) -> np.ndarray:
    """The field once count kernels have landed, in order from the far left, as the
    shader would make it, with the lone kernel draining away. Row 0 of the floor is the far one."""
    landed = np.zeros(SPAN * SPAN, np.float32)
    landed[:count] = 1
    # The same checker kernels() blurred for its field, cut down to the pixels so far
    checker = np.indices((SPAN, SPAN)).sum(axis=0) % 2
    field = (FIELD_LOW + (FIELD_HIGH - FIELD_LOW) * checker) * landed.reshape(SPAN, SPAN)
    return stretched(field, program, uniforms) + max(1 - count / SINK_STEPS, 0) * lone


def surface(values: np.ndarray, half: float) -> Surface:
    """values as a height field over [-half, half]^2, faceted on the low-res grid."""
    res = int(2 * half * RESOLUTION)
    shape = Surface(
        lambda u, v: np.array([u, v, HEIGHT * sample(values, u, v)]),
        u_range=[-half, half],
        v_range=[-half, half],
        resolution=(res, res),
        checkerboard_colors=False,
    )
    for face in shape:
        value = face.get_center()[2] / HEIGHT
        tint = magma(value)
        opacity = min(value / FADE, 1.0)
        face.set_fill(tint, opacity=opacity).set_stroke(tint, width=EDGE, opacity=opacity)
    return shape


def floor_grid(cells: int) -> VGroup:
    """Low-res pixel boundaries on the floor, cells wide, centred."""
    half = cells / 2
    return VGroup(*(
        Line([i - half, -half, 0], [i - half, half, 0], color=MUTED, stroke_width=STROKE_THIN)
        for i in range(cells + 1)
    ), *(
        Line([-half, i - half, 0], [half, i - half, 0], color=MUTED, stroke_width=STROKE_THIN)
        for i in range(cells + 1)
    ))


class BjorgeUp(Clip, ThreeDScene):
    def sweep(self, mob: Surface, lone: np.ndarray, program: str, uniforms: dict):
        """Pixel by pixel, left to right and far to near, reshaping mob as each kernel lands.
        Built as needed: all fifty surfaces at once take gigabytes."""
        half = SPAN / 2
        steps = SPAN * SPAN
        shown = [None]

        def arrive(target, alpha):
            count = min(int(alpha * (steps + 1)), steps)
            if count != shown[0]:
                shown[0] = count
                target.become(surface(arrivals(lone, count, program, uniforms), half))  # In place: a new set of faces wouldn't redraw

        self.play(UpdateFromAlphaFunc(mob, arrive), run_time=SWEEP, rate_func=linear)

    def construct(self):
        tables = kernels()
        self.set_camera_orientation(phi=PHI, theta=THETA, zoom=ZOOM)

        half = SPAN / 2
        floor = floor_grid(SPAN)
        self.add(floor)

        self.cue("And on the way up")
        flat = surface(tables["pyramid"] * 0, half)
        wide_pyramid = surface(tables["pyramid"], half)
        self.add(flat)
        self.cue("one bilinear tap")
        self.play(Transform(flat, wide_pyramid), run_time=SLOW, rate_func=EASE)

        # Adjacent peaks meet at their bases and sum there, leaving a hole wherever a low
        # pixel sits among high ones.
        self.cue("which is where the")
        self.sweep(flat, tables["pyramid"], "resample", {})

        self.cue("Instead, take eight taps")
        self.play(Transform(flat, surface(tables["pyramid"], half)), run_time=MOVE, rate_func=EASE)
        self.remove(flat)
        local = surface(tables["pyramid"], LOCAL)
        self.add(local)

        # A thin light ring, since the red alone would be lost on the magma under it
        dots = VGroup(*(
            TapPoint().set_stroke(TEXT, width=STROKE_THIN).move_to([x, y, HEIGHT * sample(tables["pyramid"], x, y) + DOT_LIFT])
            for x, y, _ in RING
        ))
        self.add_fixed_orientation_mobjects(*dots)
        self.remove(*dots)
        # Top left, the one corner the floor never reaches
        tap_eight = Mono("8 taps", font_size=TEXT_BASE, color=TEXT)
        tap_eight.move_to([-FILL_WIDTH / 2, FILL_HEIGHT / 2, 0], aligned_edge=UL)
        self.add_fixed_in_frame_mobjects(tap_eight)
        self.remove(tap_eight)
        close_floor = floor_grid(CLOSE_SPAN)
        self.move_camera(
            phi=CLOSE_PHI,
            zoom=CLOSE_ZOOM,
            added_anims=[FadeOut(floor), FadeIn(close_floor), FadeIn(dots), FadeIn(tap_eight)],
            run_time=SLOW,
            rate_func=EASE,
        )
        # MOVE, not SLOW: the pull-back and the whole sweep still have to fit this sentence
        self.cue("so no direction")
        self.play(
            Transform(local, surface(tables["dome"], LOCAL)),
            # The dots ride the surface up as they fade, their job done
            *(
                FadeOut(dot, shift=OUT * (HEIGHT * sample(tables["dome"], x, y) + DOT_LIFT - dot.get_z()))
                for dot, (x, y, _) in zip(dots, RING)
            ),
            run_time=MOVE,
            rate_func=EASE,
        )

        # Back out to the whole floor, then the same sweep as the pyramids', with the ring
        self.cue("is favoured")
        self.remove(local)
        ring = surface(tables["dome"], half)
        self.add(ring)
        self.move_camera(
            phi=PHI,
            zoom=ZOOM,
            added_anims=[FadeOut(close_floor), FadeIn(floor)],
            run_time=MOVE,
            rate_func=EASE,
        )
        self.cue("and the way up")
        self.sweep(ring, tables["dome"], "dual_kawase_up", RING_UNIFORMS)
        self.cue("That's exactly what Marius")
