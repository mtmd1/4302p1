"""Test images shared by the example scenes: procedural ones and our photos."""

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ASSETS = Path(__file__).resolve().parents[2] / "assets"


def test_card(width: int = 480, height: int = 270, seed: int = 4302) -> np.ndarray:
    """Bright points and hard edges on a dark ground, as float32 RGBA.

    Points show a kernel's shape directly: a box blur turns each into a square
    and a Gaussian into a soft disc. The text and stripes show edge handling.
    """
    rng = np.random.default_rng(seed)
    image = Image.new("RGB", (width, height), (12, 14, 24))
    draw = ImageDraw.Draw(image)

    for x in range(0, width // 3, 8):
        draw.rectangle([x, 0, x + 3, height], fill=(60, 70, 110))

    palette = [(255, 220, 140), (140, 200, 255), (255, 120, 160), (255, 255, 255)]
    for _ in range(40):
        x, y = rng.integers(width // 3, width), rng.integers(0, height)
        r = int(rng.integers(1, 4))
        draw.ellipse([x - r, y - r, x + r, y + r], fill=palette[rng.integers(len(palette))])

    font = ImageFont.load_default(size=height // 4)
    draw.text((width * 0.42, height * 0.36), "BLUR", font=font, fill=(240, 240, 240))

    rgb = np.asarray(image, dtype=np.float32) / 255
    return np.concatenate([rgb, np.ones_like(rgb[..., :1])], axis=2)


def photo(name: str = "sands.jpg") -> np.ndarray:
    """A photo from assets/ as float32 RGBA, the format the blurs take.

    sands.jpg is the 1920x1080 skyline crop, so timings measured on it match
    the 1080p numbers in the script.
    """
    rgb = np.asarray(Image.open(ASSETS / name).convert("RGB"), dtype=np.float32) / 255
    return np.concatenate([rgb, np.ones_like(rgb[..., :1])], axis=2)
