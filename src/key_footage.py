# /// script
# requires-python = ">=3.12"
# dependencies = ["numpy", "scipy"]
# ///
"""Green-screen a whole recording in code, so no clip needs keying in Resolve.

    uv run src/key_footage.py media/resolve/video.mov
    uv run src/key_footage.py media/resolve/video.mov --start 800 --duration 20

Writes <name>_keyed.mov beside the input: ProRes 4444 with real alpha, the same
frames at the same times and the same audio. Replace the clip in Resolve's media
pool with it and every cut made from the original comes out keyed.

The key looks at colour, not brightness, because the light on the sheet changes
over the take. The camera never moves, so a fixed mask drops the ceiling and the
carpet, and keeping only the largest shape drops anything left on the screen.
"""

import argparse
import json
import multiprocessing
import subprocess
import tempfile
from pathlib import Path

import numpy as np
from scipy import ndimage

# How green a pixel is, as a fraction of its green channel: 0 = none, 0.5 = the sheet
OPAQUE_BELOW = 0.10
CLEAR_ABOVE = 0.26
# Near-black pixels have too little light to tell their colour. Dividing by at least
# this much treats them as the subject, which stops dark fabric speckling.
DARK_GREEN = 0.16

# Rows outside the sheet, at 1080x1920
TOP = 150
BOTTOM = 1850

SOLID = 0.6  # Alpha that counts as part of the subject when finding its shape
REACH = 10  # Pixels of soft edge kept around that shape
FEATHER = 0.8  # Sigma, in pixels, of the softening on the edge
TIGHTEN = 0.21  # Alpha below this clears and above 1 - this fills, so the edge stays crisp


def key_frame(rgb: np.ndarray) -> np.ndarray:
    """RGBA, uint8, from an RGB uint8 frame."""
    pixels = rgb.astype(np.float32) / 255
    green = pixels[..., 1]
    other = np.maximum(pixels[..., 0], pixels[..., 2])
    greenness = (green - other) / np.maximum(green, DARK_GREEN)
    alpha = 1 - np.clip((greenness - OPAQUE_BELOW) / (CLEAR_ABOVE - OPAQUE_BELOW), 0, 1)
    alpha[:TOP] = 0
    alpha[BOTTOM:] = 0

    # The subject is the largest shape, so anything apart from it is cut away
    solid = alpha > SOLID
    labels, count = ndimage.label(solid)
    if count:
        sizes = np.bincount(labels.ravel())
        sizes[0] = 0
        alpha = alpha * ndimage.binary_dilation(labels == sizes.argmax(), iterations=REACH)
    else:
        alpha[:] = 0

    alpha = ndimage.gaussian_filter(alpha, FEATHER)
    alpha = np.clip((alpha - TIGHTEN) / (1 - 2 * TIGHTEN), 0, 1)

    # Whatever green is left on the subject is the screen's light, not the subject's
    out = np.empty((*alpha.shape, 4), np.uint8)
    out[..., 0] = rgb[..., 0]
    out[..., 1] = np.minimum(rgb[..., 1], np.maximum(rgb[..., 0], rgb[..., 2]))
    out[..., 2] = rgb[..., 2]
    out[..., 3] = (alpha * 255 + 0.5).astype(np.uint8)
    return out


def probe(path: Path) -> tuple[int, int, float, int]:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_packets",
         "-show_entries", "stream=width,height,r_frame_rate,nb_read_packets", "-of", "json", str(path)],
        capture_output=True, check=True,
    )
    stream = json.loads(result.stdout)["streams"][0]
    top, bottom = stream["r_frame_rate"].split("/")
    return stream["width"], stream["height"], int(top) / int(bottom), int(stream["nb_read_packets"])


def key_segment(job: tuple) -> Path:
    """Key frames [first, first + count) of src into dst, a video-only clip."""
    src, dst, width, height, fps, first, count = job
    reader = subprocess.Popen(
        ["ffmpeg", "-nostdin", "-v", "error", "-ss", f"{first / fps:.6f}", "-i", str(src),
         "-map", "0:v:0", "-frames:v", str(count), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
        stdout=subprocess.PIPE,
    )
    # Single-threaded scaling: threaded swscale can corrupt alpha along its slice seams
    writer = subprocess.Popen(
        ["ffmpeg", "-nostdin", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{width}x{height}",
         "-r", str(fps), "-i", "-", "-filter_threads", "1", "-sws_flags", "accurate_rnd+full_chroma_int",
         "-vf", "scale=out_color_matrix=bt709:out_range=tv:threads=1,format=yuva444p10le",
         "-c:v", "prores_ks", "-profile:v", "4444", "-alpha_bits", "16", "-vendor", "apl0", "-threads", "4",
         "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", str(dst)],
        stdin=subprocess.PIPE,
    )
    size = width * height * 3
    written = 0
    while written < count:
        raw = reader.stdout.read(size)
        if len(raw) < size:
            break
        writer.stdin.write(key_frame(np.frombuffer(raw, np.uint8).reshape(height, width, 3)).tobytes())
        written += 1
    writer.stdin.close()
    if reader.wait() or writer.wait() or written != count:
        raise RuntimeError(f"Segment at frame {first}: wrote {written} of {count} frames")
    return dst


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("source", type=Path)
    parser.add_argument("--start", type=float, default=0, help="seconds, for a test")
    parser.add_argument("--duration", type=float, help="seconds, for a test")
    parser.add_argument("--workers", type=int, default=12)
    args = parser.parse_args()

    width, height, fps, total = probe(args.source)
    first = round(args.start * fps)
    count = min(round(args.duration * fps), total - first) if args.duration else total - first
    suffix = f"_test_{args.start:g}" if args.duration else ""
    dst = args.source.with_name(f"{args.source.stem}_keyed{suffix}.mov")

    # ProRes frames are independent, so the pieces join without re-encoding
    size = max(1, count // (args.workers * 4) + 1)
    with tempfile.TemporaryDirectory(dir=dst.parent) as folder:
        folder = Path(folder)
        jobs = [
            (args.source, folder / f"{i:05d}.mov", width, height, fps, first + start, min(size, count - start))
            for i, start in enumerate(range(0, count, size))
        ]
        with multiprocessing.Pool(args.workers) as pool:
            for done, _ in enumerate(pool.imap(key_segment, jobs), 1):
                print(f"  {done}/{len(jobs)} segments", flush=True)
        playlist = folder / "list.txt"
        playlist.write_text("".join(f"file '{job[1]}'\n" for job in jobs))
        subprocess.run(
            ["ffmpeg", "-nostdin", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(playlist),
             "-ss", f"{first / fps:.6f}", "-t", f"{count / fps:.6f}", "-i", str(args.source),
             "-map", "0:v:0", "-map", "1:a:0?", "-c:v", "copy", "-c:a", "copy", str(dst)],
            check=True,
        )
    print(f"{dst}: {count} frames")


if __name__ == "__main__":
    main()
