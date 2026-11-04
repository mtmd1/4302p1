"""Gaussian 2: w(x, y) becomes the formula below, and a bell replaces the kernel.

    uv run render gauss_bell
"""

from style import *

from gauss_weights import KERNEL, build, denominator, offset_label, weight_label

SIGMA = 0.75  # Of the drawn bell, in cells: narrow enough to look like a bell inside 3 x 3
BELL_HEIGHT = 2.1
RESOLUTION = 41  # Surface faces per side
FORMULA_Y = -2.2
KERNEL_AT = UP * 0.55  # Above the formula while looking straight down
PHI = 56 * DEGREES
THETA = -68 * DEGREES
DRIFT = 0.025  # Radians per second of slow turn while holding
LOOK_AT = KERNEL_AT + IN * 0.55  # Where the camera looks once tilted, which lifts the bell clear of the formula
FAR_BELOW = IN * 40  # Depth-sorting point that keeps the fading cells behind the surface


def height(u: float, v: float) -> float:
    return float(np.exp(-(u**2 + v**2) / (2 * SIGMA**2)))


def bell(half: float, scale: float, opacity: float) -> Surface:
    surface = Surface(
        lambda u, v: KERNEL_AT + np.array([u, v, scale * BELL_HEIGHT * height(u / half * 1.5, v / half * 1.5)]),
        u_range=[-half, half],
        v_range=[-half, half],
        resolution=(RESOLUTION, RESOLUTION),
        checkerboard_colors=False,
        fill_opacity=opacity,
        stroke_width=0,
    )
    for face in surface:
        centre = (face.get_center() - KERNEL_AT) / half * 1.5
        shade = magma(height(centre[0], centre[1]))
        # A stroke of its own colour, so the faces' antialiased seams don't let the background through
        face.set_fill(shade, opacity=opacity).set_stroke(shade, width=STROKE_THIN, opacity=opacity)
    return surface


class GaussBell(Clip, ThreeDScene):
    def construct(self):
        self.renderer.camera.should_apply_shading = False  # Colours stay true to the heatmap

        # Exactly where the last clip left off
        state = build()
        grid = state.grid
        cells = [grid.square(r, c) for r, c in state.cells]
        for cell in cells:
            cell.set_fill(BACKGROUND)
        for r, c in state.cells:
            grid.labels.remove(grid.label(r, c))
        weights = {(r, c): weight_label(grid, r, c) for r, c in state.cells}
        offsets = VGroup(*(offset_label(grid, r, c) for r, c in state.cells))
        readout = VGroup(state.sum, denominator(state, "sum of weights"))
        outer = VGroup(*(s for s in grid.squares if s not in cells), grid.labels)
        kernel = VGroup(*cells, state.outline)
        centre = weights[KERNEL[1], KERNEL[1]]
        # Stacked now, as a play leaves mobjects already in the scene where they are
        self.add(outer, kernel, *weights.values(), offsets, readout)
        self.cue("For a gaussian blur")

        # Everything but the kernel leaves, and it comes to the middle
        moved_by = KERNEL_AT - kernel.get_center()
        self.play(
            FadeOut(outer),
            FadeOut(readout),
            FadeOut(offsets, shift=moved_by),
            *(FadeOut(w, shift=moved_by) for w in weights.values() if w is not centre),
            kernel.animate.shift(moved_by),
            centre.animate.shift(moved_by),
            run_time=MOVE,
            rate_func=EASE,
        )

        # w(x, y) lifts out of the centre cell and becomes the formula
        formula = MathTex(
            "w(x, y)",
            r"= \frac{1}{2 \pi \sigma^2} e^{\frac{- x^2 - y^2}{2 \sigma^2}}",
            font_size=TEXT_LG,
            color=TEXT,
        ).move_to(UP * FORMULA_Y)
        self.play(ReplacementTransform(centre, formula[0]), FadeIn(formula[1]), run_time=MOVE, rate_func=EASE)
        self.add_fixed_in_frame_mobjects(formula)

        half = kernel.width / 2
        anchor = VectorizedPoint(FAR_BELOW)
        for mob in kernel:
            mob.set_shade_in_3d(True)
            mob.z_index_group = anchor

        # The kernel has served its purpose: only the bell stays, solid
        surface = bell(half, 0.0, 0.0)
        self.add(surface)
        self.move_camera(
            phi=PHI,
            theta=THETA,
            frame_center=LOOK_AT,
            added_anims=[Transform(surface, bell(half, 1.0, 1.0)), FadeOut(kernel)],
            run_time=SLOW,
            rate_func=EASE,
        )
        self.begin_ambient_camera_rotation(rate=DRIFT)
        self.cue("This gives us a second parameter")
