import numpy as np
import pytest

import blur


@pytest.fixture(scope="module")
def image():
    rng = np.random.default_rng(4302)
    return rng.random((67, 93, 3), dtype=np.float32)  # Odd sizes catch edge bugs


@pytest.mark.parametrize("make", [lambda i, s: blur.box(i, 6, separable=s), lambda i, s: blur.gaussian(i, 2.5, separable=s)])
def test_separation_is_exact(image, make):
    np.testing.assert_allclose(make(image, True).image, make(image, False).image, atol=1e-5)


def test_box_matches_numpy(image):
    r = 3
    expected = np.empty_like(image)
    h, w = image.shape[:2]
    for y in range(h):
        for x in range(w):
            window = image[max(0, y - r) : y + r + 1, max(0, x - r) : x + r + 1]
            expected[y, x] = window.mean(axis=(0, 1))
    np.testing.assert_allclose(blur.box(image, r, linear=False).image, expected, atol=1e-5)


@pytest.mark.parametrize(
    "run",
    [
        lambda i: blur.box(i, 4),
        lambda i: blur.box(i, 4, race=True),
        lambda i: blur.gaussian(i, 3),
        lambda i: blur.kawase(i),
        lambda i: blur.downscale_upscale(i, 3),
        lambda i: blur.dual_kawase(i, 3),
    ],
)
def test_constant_image_is_unchanged(run):
    flat = np.full((40, 56, 4), 0.25, dtype=np.float32)
    np.testing.assert_allclose(run(flat).image, flat, atol=1e-5)


def test_shapes_and_steps(image):
    result = blur.dual_kawase(image, levels=3, steps=True)
    assert [s.shape[:2] for s in result.steps] == [(34, 47), (17, 24), (9, 12), (17, 24), (34, 47), (67, 93)]
    assert result.image.shape == image.shape
    assert blur.downscale(image, 4).image.shape == (17, 24, 3)
    assert blur.upscale(image[..., 0], 2).image.shape == (134, 186)


def test_tap_counts():
    flat = np.zeros((1080, 1920), dtype=np.float32)
    assert blur.box(flat, 20).taps == 41 * 41 * 1920 * 1080
    assert blur.box(flat, 20, separable=True).taps == 2 * 41 * 1920 * 1080
    assert blur.kawase(flat).taps_per_pixel == 4 * 5


def test_race_differs_from_buffered(image):
    raced = blur.box(image, 8, race=True).image
    assert not np.allclose(raced, blur.box(image, 8).image, atol=1e-3)


def test_half_precision_matches(image):
    full, half = blur.dual_kawase(image, 3), blur.dual_kawase(image, 3, half=True)
    np.testing.assert_allclose(half.image, full.image, atol=2e-3)
    assert half.image.dtype == np.float32
