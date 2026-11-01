"""Render the presentation's clips: manim scenes in, Resolve-ready video out.

    uv run render                                        # every scene in src/examples
    uv run render demo_dual_kawase                       # every scene in one file
    uv run render demo_dual_kawase:DualKawasePyramid     # one scene
    uv run render -q l                                   # 480p15 preview quality
    uv run render --list                                 # what can be rendered
    uv run render 20261101_165600.mp4                    # a recording from assets/recordings

Every clip is ProRes 4444 with an alpha channel, written to media/resolve/. Free
DaVinci Resolve on Linux can decode it (it can't read H.264), and the alpha means
any clip can sit over or under the greenscreen footage. Scenes always render on a
transparent background; one that needs a backdrop draws it.

Manim's cache can't see changes inside blur.py, so it is always disabled. All
video IO goes through PyAV, which manim already depends on, so no system ffmpeg
is needed.
"""

import argparse
import ast
import importlib.util
import sys
import traceback
from fractions import Fraction
from pathlib import Path

import av
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
EXAMPLES = ROOT / "src" / "examples"
MEDIA = ROOT / "media" / "manim"  # Manim's own output, including its LaTeX cache
CLIPS = ROOT / "media" / "resolve"
RECORDINGS = ROOT / "assets" / "recordings"

# Phones record variable frame rate, which drifts out of sync in Resolve, so
# footage is resampled onto this constant rate. It divides the 60 fps of the
# manim clips, so a 60 fps timeline shows every recorded frame exactly twice.
FOOTAGE_FPS = 30
# Recordings are shot in 4K and shrunk to this long edge, so a portrait clip
# fills the height of the 1080p timeline with room left to punch in. Shrinking
# also averages away sensor noise and 4:2:0 colour blocks, for cleaner key edges.
FOOTAGE_LONG_EDGE = 1920

QUALITIES = {
    "l": "low_quality",
    "m": "medium_quality",
    "h": "high_quality",
    "p": "production_quality",
    "k": "fourk_quality",
}

PIX_FMT = "yuva444p10le"


# MARK: Video IO


class ClipWriter:
    """Writes ProRes 4444 with alpha, plus optional PCM audio, to a .mov file.

    write() takes decoded av.VideoFrames or RGBA numpy arrays (uint8, or float
    in [0, 1]), so it serves both transcoding and frames generated in Python.
    """

    def __init__(self, path: Path, fps, size: tuple[int, int], audio_rate: int | None = None, audio_layout: str = "stereo"):
        self.container = av.open(str(path), "w")
        self.time_base = 1 / Fraction(fps)
        self.frames = 0

        self.video = self.container.add_stream("prores_ks", rate=Fraction(fps))
        self.video.width, self.video.height = size
        self.video.pix_fmt = PIX_FMT
        self.video.options = {"profile": "4444", "alpha_bits": "16", "vendor": "apl0"}
        # Tag the stream as HD video so Resolve reads the colours back unchanged
        context = self.video.codec_context
        context.colorspace = context.color_primaries = context.color_trc = 1  # BT.709

        self.audio = None
        if audio_rate:
            self.audio = self.container.add_stream("pcm_s16le", rate=audio_rate, layout=audio_layout)
            self.resampler = av.AudioResampler(format="s16", layout=audio_layout, rate=audio_rate)

    def write(self, frame: av.VideoFrame | np.ndarray):
        if isinstance(frame, np.ndarray):
            if frame.dtype == np.uint8:
                frame = av.VideoFrame.from_ndarray(np.ascontiguousarray(frame), format="rgba")
            else:
                # 16-bit keeps float input from being crushed to 8 bits before the 10-bit encode
                pixels = (np.clip(frame, 0.0, 1.0) * 65535 + 0.5).astype(np.uint16)
                frame = av.VideoFrame.from_ndarray(np.ascontiguousarray(pixels), format="rgba64le")
        # Single-threaded: PyAV's threaded swscale corrupts alpha along its slice seams
        frame = frame.reformat(format=PIX_FMT, dst_colorspace="ITU709", threads=1)
        frame.pts = self.frames
        frame.time_base = self.time_base
        self.frames += 1
        self.container.mux(self.video.encode(frame))

    def write_audio(self, frame: av.AudioFrame):
        for resampled in self.resampler.resample(frame):
            self.container.mux(self.audio.encode(resampled))

    def close(self):
        self.container.mux(self.video.encode(None))
        if self.audio is not None:
            for resampled in self.resampler.resample(None):
                self.container.mux(self.audio.encode(resampled))
            self.container.mux(self.audio.encode(None))
        self.container.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


def _upright(frame: av.VideoFrame, size: tuple[int, int]) -> av.VideoFrame | np.ndarray:
    """Scale to size, as stored, then apply a phone's rotation flag, which ProRes can't carry."""
    if (frame.width, frame.height) != size:
        frame = frame.reformat(width=size[0], height=size[1], interpolation="AREA")
    if not frame.rotation:
        return frame
    return np.rot90(frame.to_ndarray(format="rgba"), k=frame.rotation // 90)


def transcode(src: Path, dst: Path, fps=None, long_edge=None):
    """Re-encode any video PyAV can read as a ProRes 4444 clip, keeping its audio.

    With fps, frames are placed by their timestamps on that constant rate,
    repeated or dropped as needed, so variable frame rate footage stays in sync
    with its audio. Without it, every frame is kept as is. With long_edge,
    larger video is shrunk to fit it; smaller video is never enlarged.
    """
    with av.open(str(src)) as source:
        video = source.streams.video[0]
        audio = source.streams.audio[0] if source.streams.audio else None
        width, height = video.width, video.height
        if long_edge and max(width, height) > long_edge:
            scale = long_edge / max(width, height)
            width, height = (round(width * scale / 2) * 2, round(height * scale / 2) * 2)
        size = (width, height)
        rotation = next(source.decode(video=0)).rotation
        source.seek(0)
        if rotation % 180:
            width, height = height, width
        writer = ClipWriter(
            dst,
            fps or video.average_rate,
            (width, height),
            audio_rate=audio.rate if audio else None,
            audio_layout=audio.layout.name if audio else "stereo",
        )
        held = None  # The latest frame, shown until the next one's timestamp
        with writer:
            for packet in source.demux([s for s in (video, audio) if s is not None]):
                for frame in packet.decode():
                    if packet.stream is not video:
                        writer.write_audio(frame)
                    elif not fps:
                        writer.write(_upright(frame, size))
                    else:
                        if held is not None:
                            while writer.frames < frame.time * fps:
                                writer.write(held)
                        held = _upright(frame, size)
            if fps and held is not None:
                while writer.frames < float(source.duration / av.time_base) * fps:
                    writer.write(held)


# MARK: Manim


def find_scenes(path: Path) -> list[str]:
    """Scene classes defined in a file, found without importing it."""
    tree = ast.parse(path.read_text(), filename=str(path))

    def base_name(base):
        return base.id if isinstance(base, ast.Name) else getattr(base, "attr", "")

    return [
        node.name
        for node in tree.body
        if isinstance(node, ast.ClassDef) and any(base_name(b).endswith("Scene") for b in node.bases)
    ]


_modules = {}


def _load(path: Path):
    if path not in _modules:
        # Like manim's CLI, let scenes import helpers that sit beside them
        sys.path.insert(0, str(path.parent))
        spec = importlib.util.spec_from_file_location(f"_scene_{path.stem}", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _modules[path] = module
    return _modules[path]


def render_scene(path: Path, scene: str, quality: str) -> Path:
    """Render one scene with manim, in process, and transcode it into CLIPS."""
    from manim import tempconfig

    options = {
        "input_file": path,
        "media_dir": MEDIA,
        "quality": QUALITIES[quality],
        "transparent": True,
        "disable_caching": True,
        "progress_bar": "none",
        "verbosity": "WARNING",
    }
    with tempconfig(options):
        instance = getattr(_load(path), scene)()
        raw = Path(instance.renderer.file_writer.movie_file_path)
        raw.unlink(missing_ok=True)  # A failed render must not leave an old file to pick up
        instance.render()

    CLIPS.mkdir(parents=True, exist_ok=True)
    clip = CLIPS / f"{path.stem}_{scene}.mov"
    transcode(raw, clip)
    return clip


# MARK: Footage


def render_footage(path: Path, scene: str, quality: str) -> Path:
    """Transcode a recording into CLIPS, upright, at FOOTAGE_FPS and FOOTAGE_LONG_EDGE."""
    CLIPS.mkdir(parents=True, exist_ok=True)
    clip = CLIPS / f"{path.stem}.mov"
    transcode(path, clip, fps=FOOTAGE_FPS, long_edge=FOOTAGE_LONG_EDGE)
    return clip


# Target kinds by file suffix. Future pipelines, such as blurring recorded
# footage, register their file types here.
HANDLERS = {".py": render_scene, ".mp4": render_footage, ".mov": render_footage}


# MARK: Targets


# Shared modules whose base classes would otherwise look like scenes
HELPERS = {"style"}


def _scene_files() -> list[Path]:
    return [p for p in sorted(EXAMPLES.glob("*.py")) if p.stem not in HELPERS and find_scenes(p)]


def resolve_targets(targets: list[str]) -> list[tuple[Path, str]]:
    """Expand CLI targets into (file, scene) pairs.

    A target is a file path or an example's name, optionally followed by
    :Scene. No targets means every scene in every example.
    """
    if not targets:
        return [(path, scene) for path in _scene_files() for scene in find_scenes(path)]

    resolved = []
    for target in targets:
        name, _, scene = target.partition(":")
        path = Path(name)
        if not path.exists() and (RECORDINGS / name).exists():
            path = RECORDINGS / name
        if path.suffix in HANDLERS and path.suffix != ".py":
            if not path.exists():
                raise SystemExit(f"No such recording: {name}")
            resolved.append((path.resolve(), ""))
            continue
        if not path.exists():
            path = EXAMPLES / (name if name.endswith(".py") else f"{name}.py")
        if not path.exists():
            names = ", ".join(p.stem for p in _scene_files())
            raise SystemExit(f"No such example: {name}. Examples: {names}")

        scenes = find_scenes(path)
        if scene and scene not in scenes:
            raise SystemExit(f"No scene {scene} in {path.name}. Scenes: {', '.join(scenes) or 'none'}")
        resolved += [(path.resolve(), s) for s in ([scene] if scene else scenes)]
    return resolved


# MARK: CLI


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("targets", nargs="*", help="example name or path, optionally with :Scene")
    parser.add_argument("-q", "--quality", choices=QUALITIES, default="h", help="l=480p15, m=720p30, h=1080p60 (default), p=1440p60, k=2160p60")
    parser.add_argument("--list", action="store_true", help="list renderable scenes and exit")
    args = parser.parse_args()

    if args.list:
        for path in _scene_files():
            for scene in find_scenes(path):
                print(f"{path.stem}:{scene}")
        for path in sorted(RECORDINGS.glob("*")):
            if path.suffix in HANDLERS:
                print(path.name)
        return

    failures = []
    for path, scene in resolve_targets(args.targets):
        label = f"{path.stem}:{scene}" if scene else path.name
        print(f"==> {label}", flush=True)
        try:
            clip = HANDLERS[path.suffix](path, scene, args.quality)
            print(f"    {clip.relative_to(ROOT)}", flush=True)
        except Exception:
            traceback.print_exc()
            failures.append(label)

    if failures:
        raise SystemExit(f"Failed: {', '.join(failures)}")
    print(f"Clips ready in \x1b]8;;file://{CLIPS}\x1b\\{CLIPS.relative_to(ROOT)}/\x1b]8;;\x1b\\")


if __name__ == "__main__":
    main()
