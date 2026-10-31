"""GPU image blurs for the Dual Kawase presentation.

Every blur runs as OpenGL 4.3 compute shaders on a headless moderngl context.
The shaders are ported from Acerola's AcerolaFX_Blur (src/acerola); deviations
from that source are noted where they occur.

Images are numpy arrays of shape (H, W), (H, W, 3) or (H, W, 4), either uint8
or float in [0, 1]. Each blur returns a Result whose images keep the input's
channel count, as float32.

By default blurs operate in linear light: sRGB input is decoded before the blur
and re-encoded after, as a game engine's HDR buffer would be. Pass linear=False
to blur the encoded values directly.

Textures are 32-bit floats by default, so comparisons between methods are exact.
Pass half=True for 16-bit floats (rgba16f), the format games and Acerola use.
Every blur here is bound by memory reads, so half precision runs 1.5-3x faster.
"""

import math
from dataclasses import dataclass, field
from pathlib import Path
from statistics import median

import moderngl
import numpy as np
from PIL import Image

__all__ = [
    "Result",
    "box",
    "gaussian",
    "kawase",
    "downscale",
    "upscale",
    "downscale_upscale",
    "dual_kawase",
    "load",
    "save",
    "to_uint8",
    "srgb_to_linear",
    "linear_to_srgb",
    "KAWASE_OFFSETS",
]

# The pass offsets from Kawase's GDC 2003 talk, as used by Acerola
KAWASE_OFFSETS = (0, 1, 2, 2, 3)

GROUP_SIZE = 8


@dataclass
class Result:
    image: np.ndarray
    """The blurred image."""
    gpu_ms: float
    """Median GPU time across all passes, excluding upload and readback."""
    taps: int
    """Texture reads issued, ignoring edge handling (see the script's tap counts)."""
    passes: int
    """Compute dispatches."""
    pixels: int
    """Pixels in the input image."""
    steps: list[np.ndarray] = field(default_factory=list)
    """The output of every pass in order, if requested with steps=True."""

    @property
    def taps_per_pixel(self) -> float:
        return self.taps / self.pixels


# MARK: Shaders

_HEADER = f"""
#version 430
layout(local_size_x = {GROUP_SIZE}, local_size_y = {GROUP_SIZE}) in;

uniform ivec2 size;  // Destination size in pixels

bool out_of_bounds(ivec2 p, ivec2 bounds) {{
    return any(lessThan(p, ivec2(0))) || any(greaterThanEqual(p, bounds));
}}
"""

# Shared by box and Gaussian. Out-of-bounds taps are discarded rather than
# clamped, so they add neither colour nor weight. Discarding keeps the separated
# and unseparated results identical, since the in-bounds region is a rectangle
# and its total weight factorises just like the kernel does. When the source and
# destination alias (race=True), reads and writes happen in place.
_CONVOLVE = """
layout(rgba32f, binding = 0) uniform readonly image2D source;
layout(rgba32f, binding = 1) uniform writeonly image2D destination;

uniform int radius;
uniform float sigma;  // 0 means box: every tap weighs 1

// Acerola's unseparated shader computes 2 * sigma^2 as sigma * sigma, giving it
// a different sigma from his separated shader. The constant 1 / (2 pi sigma^2)
// is also dropped, since dividing by the total weight cancels it anyway.
float weight(int x, int y) {
    if (sigma <= 0.0) return 1.0;
    return exp(-float(x * x + y * y) / (2.0 * sigma * sigma));
}
"""

_SHADERS = {
    "convolve_2d": _CONVOLVE + """
void main() {
    ivec2 p = ivec2(gl_GlobalInvocationID.xy);
    if (out_of_bounds(p, size)) return;

    vec4 sum = vec4(0.0);
    float total = 0.0;
    for (int y = -radius; y <= radius; ++y) {
        for (int x = -radius; x <= radius; ++x) {
            ivec2 q = p + ivec2(x, y);
            if (out_of_bounds(q, size)) continue;
            float w = weight(x, y);
            sum += w * imageLoad(source, q);
            total += w;
        }
    }
    imageStore(destination, p, sum / total);
}
""",
    "convolve_1d": _CONVOLVE + """
uniform ivec2 direction;  // (1, 0) for horizontal, (0, 1) for vertical

void main() {
    ivec2 p = ivec2(gl_GlobalInvocationID.xy);
    if (out_of_bounds(p, size)) return;

    vec4 sum = vec4(0.0);
    float total = 0.0;
    for (int i = -radius; i <= radius; ++i) {
        ivec2 q = p + i * direction;
        if (out_of_bounds(q, size)) continue;
        float w = weight(i, 0);
        sum += w * imageLoad(source, q);
        total += w;
    }
    imageStore(destination, p, sum / total);
}
""",
    # The remaining shaders sample with hardware bilinear filtering and
    # clamp-to-edge addressing. A tap placed on the corner shared by four texels
    # returns their average for the cost of one read.
    "kawase": """
layout(binding = 0) uniform sampler2D source;
layout(rgba32f, binding = 1) uniform writeonly image2D destination;

uniform float offset;

void main() {
    ivec2 p = ivec2(gl_GlobalInvocationID.xy);
    if (out_of_bounds(p, size)) return;

    vec2 texel = 1.0 / vec2(size);
    vec2 uv = (vec2(p) + 0.5) * texel;
    vec2 d = (offset + 0.5) * texel;

    vec4 sum = texture(source, uv + vec2(-d.x, -d.y))
             + texture(source, uv + vec2( d.x, -d.y))
             + texture(source, uv + vec2(-d.x,  d.y))
             + texture(source, uv + vec2( d.x,  d.y));
    imageStore(destination, p, sum / 4.0);
}
""",
    # Used for both downscaling and upscaling, like Acerola's pair of shaders.
    # Halving puts every destination centre on a source texel corner, so the one
    # tap is an exact 2x2 box average.
    "resample": """
layout(binding = 0) uniform sampler2D source;
layout(rgba32f, binding = 1) uniform writeonly image2D destination;

void main() {
    ivec2 p = ivec2(gl_GlobalInvocationID.xy);
    if (out_of_bounds(p, size)) return;

    vec2 uv = (vec2(p) + 0.5) / vec2(size);
    imageStore(destination, p, texture(source, uv));
}
""",
    # Offsets are in destination texels, as in Acerola and Bjorge's notes
    "dual_kawase_down": """
layout(binding = 0) uniform sampler2D source;
layout(rgba32f, binding = 1) uniform writeonly image2D destination;

uniform float offset;

void main() {
    ivec2 p = ivec2(gl_GlobalInvocationID.xy);
    if (out_of_bounds(p, size)) return;

    vec2 uv = (vec2(p) + 0.5) / vec2(size);
    vec2 h = offset / vec2(size) / 2.0;

    vec4 sum = texture(source, uv) * 4.0
             + texture(source, uv - h)
             + texture(source, uv + h)
             + texture(source, uv + vec2(h.x, -h.y))
             + texture(source, uv - vec2(h.x, -h.y));
    imageStore(destination, p, sum / 8.0);
}
""",
    "dual_kawase_up": """
layout(binding = 0) uniform sampler2D source;
layout(rgba32f, binding = 1) uniform writeonly image2D destination;

uniform float offset;

void main() {
    ivec2 p = ivec2(gl_GlobalInvocationID.xy);
    if (out_of_bounds(p, size)) return;

    vec2 uv = (vec2(p) + 0.5) / vec2(size);
    vec2 t = offset / vec2(size);
    vec2 h = t / 2.0;

    vec4 sum = texture(source, uv + vec2(-t.x, 0.0))
             + texture(source, uv + vec2( t.x, 0.0))
             + texture(source, uv + vec2(0.0, -t.y))
             + texture(source, uv + vec2(0.0,  t.y))
             + texture(source, uv + vec2(-h.x,  h.y)) * 2.0
             + texture(source, uv + vec2( h.x,  h.y)) * 2.0
             + texture(source, uv + vec2( h.x, -h.y)) * 2.0
             + texture(source, uv + vec2(-h.x, -h.y)) * 2.0;
    imageStore(destination, p, sum / 12.0);
}
""",
}

_SAMPLED = {"kawase", "resample", "dual_kawase_down", "dual_kawase_up"}


# MARK: GPU plumbing

_ctx: moderngl.Context | None = None
_programs: dict[tuple[str, str], moderngl.ComputeShader] = {}


def context() -> moderngl.Context:
    """The shared headless OpenGL context, created on first use."""
    global _ctx
    if _ctx is None:
        try:
            _ctx = moderngl.create_context(standalone=True, backend="egl", require=430)
        except Exception:
            _ctx = moderngl.create_context(standalone=True, require=430)
    return _ctx


def _program(name: str, image_format: str) -> moderngl.ComputeShader:
    key = (name, image_format)
    if key not in _programs:
        source = (_HEADER + _SHADERS[name]).replace("rgba32f", image_format)
        _programs[key] = context().compute_shader(source)
    return _programs[key]


@dataclass
class _Pass:
    program: str
    source: moderngl.Texture
    destination: moderngl.Texture
    taps: int
    """Texture reads per destination pixel."""
    uniforms: dict = field(default_factory=dict)

    def dispatch(self):
        ctx = context()
        half = self.destination.dtype == "f2"
        program = _program(self.program, "rgba16f" if half else "rgba32f")
        width, height = self.destination.size
        program["size"] = (width, height)
        for name, value in self.uniforms.items():
            program[name] = value

        if self.program in _SAMPLED:
            self.source.use(0)
        else:
            self.source.bind_to_image(0, read=True, write=False)
        self.destination.bind_to_image(1, read=False, write=True)

        program.run(math.ceil(width / GROUP_SIZE), math.ceil(height / GROUP_SIZE))
        ctx.memory_barrier()


class _Textures:
    """Allocates pass destinations, ping-ponging between same-sized textures.

    When every step is kept, each pass gets a fresh texture instead. The input
    texture is never handed out, so repeated runs all start from the same data.
    """

    def __init__(self, keep: bool, half: bool):
        self.keep = keep
        self.dtype = "f2" if half else "f4"
        self.pools: dict[tuple[int, int], list[moderngl.Texture]] = {}
        self.all: list[moderngl.Texture] = []

    def new(self, size: tuple[int, int], data: bytes | None = None) -> moderngl.Texture:
        texture = context().texture(size, 4, data, dtype=self.dtype)
        texture.filter = (moderngl.LINEAR, moderngl.LINEAR)
        texture.repeat_x = texture.repeat_y = False  # Clamp to edge
        self.all.append(texture)
        return texture

    def target(self, size: tuple[int, int], source: moderngl.Texture) -> moderngl.Texture:
        if self.keep:
            return self.new(size)
        pool = self.pools.setdefault(size, [])
        for texture in pool:
            if texture is not source:
                return texture
        pool.append(texture := self.new(size))
        return texture

    def release(self):
        for texture in self.all:
            texture.release()


def _read(texture: moderngl.Texture) -> np.ndarray:
    width, height = texture.size
    dtype = np.float16 if texture.dtype == "f2" else np.float32
    return np.frombuffer(texture.read(), dtype=dtype).reshape(height, width, 4).astype(np.float32)


def _run(
    img, build, *, linear: bool, steps: bool, repeat: int, half: bool, in_place: bool = False
) -> Result:
    """Upload img, run the passes that build(source, textures) returns, and read back."""
    rgba, channels = _prepare(img, linear)
    data = rgba.astype(np.float16 if half else np.float32).tobytes()
    height, width = rgba.shape[:2]

    textures = _Textures(keep=steps, half=half)
    try:
        source = textures.new((width, height), data)
        passes: list[_Pass] = build(source, textures)

        def run_once() -> float:
            if in_place:
                source.write(data)  # In-place passes destroy their input
            query = context().query(time=True)
            with query:
                for p in passes:
                    p.dispatch()
            return query.elapsed / 1e6

        if repeat > 1:
            run_once()  # Warm-up
        gpu_ms = median(run_once() for _ in range(repeat))

        def finish(texture):
            return _finish(_read(texture), channels, linear)

        return Result(
            image=finish(passes[-1].destination),
            gpu_ms=gpu_ms,
            taps=sum(p.taps * p.destination.width * p.destination.height for p in passes),
            passes=len(passes),
            pixels=width * height,
            steps=[finish(p.destination) for p in passes] if steps else [],
        )
    finally:
        textures.release()


# MARK: Blurs


def _convolve(img, radius: int, sigma: float, *, separable, race=False, **options) -> Result:
    if radius < 0:
        raise ValueError(f"radius must be non-negative, got {radius}")

    def build(source, textures):
        size = source.size
        uniforms = {"radius": radius, "sigma": sigma}

        def target(src):
            return src if race else textures.target(size, src)

        if not separable:
            return [_Pass("convolve_2d", source, target(source), (2 * radius + 1) ** 2, uniforms)]

        horizontal = _Pass(
            "convolve_1d", source, target(source), 2 * radius + 1, uniforms | {"direction": (1, 0)}
        )
        vertical = _Pass(
            "convolve_1d",
            horizontal.destination,
            target(horizontal.destination),
            2 * radius + 1,
            uniforms | {"direction": (0, 1)},
        )
        return [horizontal, vertical]

    return _run(img, build, in_place=race, **options)


def box(
    img,
    radius: int,
    *,
    separable: bool = False,
    race: bool = False,
    linear: bool = True,
    steps: bool = False,
    repeat: int = 1,
    half: bool = False,
) -> Result:
    """Average every pixel within radius, giving a (2 * radius + 1) square kernel.

    separable runs a horizontal pass then a vertical pass, which gives the same
    result. race reads and writes a single buffer, as in Acerola's "bad blur":
    pixels read neighbours that may already have been blurred, so the output is
    wrong and changes from run to run.
    """
    return _convolve(
        img, radius, 0.0, separable=separable, race=race, linear=linear, steps=steps, repeat=repeat, half=half
    )


def gaussian(
    img,
    sigma: float,
    radius: int | None = None,
    *,
    separable: bool = False,
    linear: bool = True,
    steps: bool = False,
    repeat: int = 1,
    half: bool = False,
) -> Result:
    """Weight pixels by a Gaussian of standard deviation sigma.

    radius defaults to ceil(3 * sigma), so the kernel spans at least 6 sigma.
    Pass a smaller radius to bring back the box artifacts of a truncated kernel.
    """
    if sigma <= 0:
        raise ValueError(f"sigma must be positive, got {sigma}")
    if radius is None:
        radius = math.ceil(3 * sigma)
    return _convolve(
        img, radius, float(sigma), separable=separable, linear=linear, steps=steps, repeat=repeat, half=half
    )


def kawase(
    img,
    offsets=KAWASE_OFFSETS,
    *,
    linear: bool = True,
    steps: bool = False,
    repeat: int = 1,
    half: bool = False,
) -> Result:
    """Kawase blur: one full-resolution pass of 4 diagonal bilinear taps per offset."""

    def build(source, textures):
        passes = []
        for offset in offsets:
            passes.append(
                _Pass("kawase", source, textures.target(source.size, source), 4, {"offset": float(offset)})
            )
            source = passes[-1].destination
        return passes

    return _run(img, build, linear=linear, steps=steps, repeat=repeat, half=half)


def _halvings(ratio: int) -> int:
    if ratio < 2 or ratio & (ratio - 1):
        raise ValueError(f"ratio must be a power of two of at least 2, got {ratio}")
    return ratio.bit_length() - 1


def _half(size: tuple[int, int]) -> tuple[int, int]:
    return (math.ceil(size[0] / 2), math.ceil(size[1] / 2))


def _pyramid(down: str, up: str | None, levels: int, down_taps: int, up_taps: int, uniforms=None):
    """Build passes that halve the image levels times, then optionally double it back."""
    uniforms = uniforms or {}

    def build(source, textures):
        passes = []
        sizes = [source.size]
        for _ in range(levels):
            sizes.append(_half(sizes[-1]))
            passes.append(_Pass(down, source, textures.target(sizes[-1], source), down_taps, uniforms))
            source = passes[-1].destination
        if up is not None:
            # Retrace the recorded sizes so odd dimensions come back exactly
            for size in reversed(sizes[:-1]):
                passes.append(_Pass(up, source, textures.target(size, source), up_taps, uniforms))
                source = passes[-1].destination
        return passes

    return build


def downscale(
    img,
    ratio: int = 2,
    *,
    linear: bool = True,
    steps: bool = False,
    repeat: int = 1,
    half: bool = False,
) -> Result:
    """Shrink by ratio, a power of two, one halving at a time.

    Each halving is a single bilinear tap that averages a 2x2 block exactly. One
    tap at a larger ratio would skip texels and alias, so ratio 4 is two
    halvings; steps=True returns each one.
    """
    build = _pyramid("resample", None, _halvings(ratio), 1, 1)
    return _run(img, build, linear=linear, steps=steps, repeat=repeat, half=half)


def upscale(
    img,
    ratio: int = 2,
    *,
    linear: bool = True,
    steps: bool = False,
    repeat: int = 1,
    half: bool = False,
) -> Result:
    """Grow by ratio, a power of two, one bilinear doubling at a time.

    Chained doublings blur more than one bilinear stretch would. That extra
    blur is what downscale_upscale relies on.
    """

    def build(source, textures):
        passes = []
        for _ in range(_halvings(ratio)):
            size = (source.width * 2, source.height * 2)
            passes.append(_Pass("resample", source, textures.target(size, source), 1))
            source = passes[-1].destination
        return passes

    return _run(img, build, linear=linear, steps=steps, repeat=repeat, half=half)


def downscale_upscale(
    img,
    levels: int = 4,
    *,
    linear: bool = True,
    steps: bool = False,
    repeat: int = 1,
    half: bool = False,
) -> Result:
    """Halve levels times, then double back, using plain bilinear taps.

    levels=4 reaches 1/16 resolution, Acerola's deepest setting.
    """
    build = _pyramid("resample", "resample", levels, 1, 1)
    return _run(img, build, linear=linear, steps=steps, repeat=repeat, half=half)


def dual_kawase(
    img,
    levels: int = 4,
    offset: float = 1.0,
    *,
    linear: bool = True,
    steps: bool = False,
    repeat: int = 1,
    half: bool = False,
) -> Result:
    """Dual Kawase blur (Bjorge, SIGGRAPH 2015): downscale_upscale with smarter taps.

    Going down costs 5 taps per pixel and coming up costs 8, all at reduced
    resolution. offset spreads the taps further apart; Acerola reuses his
    standard deviation slider for it.
    """
    build = _pyramid("dual_kawase_down", "dual_kawase_up", levels, 5, 8, {"offset": float(offset)})
    return _run(img, build, linear=linear, steps=steps, repeat=repeat, half=half)


# MARK: Image IO


def srgb_to_linear(c: np.ndarray) -> np.ndarray:
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4).astype(np.float32)


def linear_to_srgb(c: np.ndarray) -> np.ndarray:
    c = np.clip(c, 0.0, 1.0)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * c ** (1 / 2.4) - 0.055).astype(np.float32)


def _prepare(img, linear: bool) -> tuple[np.ndarray, int]:
    """Convert any supported image to contiguous float32 RGBA, plus its channel count."""
    a = np.asarray(img)
    a = a.astype(np.float32) / 255 if a.dtype == np.uint8 else a.astype(np.float32)
    if a.ndim == 2:
        a = a[..., None]
    channels = a.shape[2]
    if channels not in (1, 3, 4):
        raise ValueError(f"expected 1, 3 or 4 channels, got {channels}")

    rgb = np.repeat(a, 3, axis=2) if channels == 1 else a[..., :3]
    if linear:
        rgb = srgb_to_linear(rgb)
    alpha = a[..., 3:] if channels == 4 else np.ones_like(a[..., :1])
    return np.ascontiguousarray(np.concatenate([rgb, alpha], axis=2)), channels


def _finish(rgba: np.ndarray, channels: int, linear: bool) -> np.ndarray:
    rgb = linear_to_srgb(rgba[..., :3]) if linear else rgba[..., :3]
    if channels == 1:
        return rgb[..., 0]
    if channels == 3:
        return rgb
    return np.concatenate([rgb, rgba[..., 3:]], axis=2)


def load(path: str | Path) -> np.ndarray:
    """Load an image as float32 in [0, 1], keeping its sRGB encoding."""
    image = Image.open(path)
    if image.mode not in ("L", "RGB", "RGBA"):
        image = image.convert("RGBA" if "A" in image.getbands() else "RGB")
    return np.asarray(image, dtype=np.float32) / 255


def to_uint8(img: np.ndarray) -> np.ndarray:
    """Convert a float image to uint8, as manim's ImageMobject expects."""
    return (np.clip(img, 0.0, 1.0) * 255 + 0.5).astype(np.uint8)


def save(path: str | Path, img: np.ndarray):
    Image.fromarray(to_uint8(img)).save(path)
