# eaubbies/eaubbies/src/tests/test_tesseract_client.py
"""Tests for :mod:`utils.tesseract_client`.

The critical regression covered here is that the preprocessing pipeline must
accept a frame that is *already* greyscale (the default image pipeline enables
``convert_to_grey``). Previously ``process_image`` called
``cv2.cvtColor(frame, COLOR_BGR2GRAY)`` unconditionally and crashed on a
single-channel input.
"""

import numpy as np
import pytest

from utils.tesseract_client import TesseractClient


def test_to_grayscale_accepts_bgr_frame():
    """A 3-channel BGR frame is reduced to a single-channel uint8 image."""
    bgr = np.zeros((10, 12, 3), dtype=np.uint8)
    gray = TesseractClient._to_grayscale(bgr)
    assert gray.ndim == 2
    assert gray.shape == (10, 12)
    assert gray.dtype == np.uint8


def test_to_grayscale_accepts_already_grey_frame():
    """A 2-D greyscale frame must pass through without raising (the bug fix)."""
    grey = np.full((8, 8), 128, dtype=np.uint8)
    out = TesseractClient._to_grayscale(grey)
    assert out.ndim == 2
    assert out.shape == (8, 8)
    assert int(out[0][0]) == 128


def test_to_grayscale_accepts_single_channel_3d_frame():
    """A (H, W, 1) frame is squeezed to (H, W)."""
    grey = np.zeros((5, 5, 1), dtype=np.uint8)
    out = TesseractClient._to_grayscale(grey)
    assert out.ndim == 2
    assert out.shape == (5, 5)


def test_to_grayscale_casts_float_to_uint8():
    """Float frames (e.g. after exposure rescale) are clipped to uint8."""
    frame = np.array([[300.0, -5.0], [10.5, 40.0]], dtype=np.float64)
    out = TesseractClient._to_grayscale(frame)
    assert out.dtype == np.uint8
    assert out.max() <= 255
    assert out.min() >= 0


def test_to_grayscale_rejects_none():
    """Passing None must raise a clear ValueError."""
    with pytest.raises(ValueError):
        TesseractClient._to_grayscale(None)


def test_process_image_requires_a_source():
    """Calling process_image with neither frame nor path raises ValueError."""
    client = TesseractClient(save_frame=False)
    with pytest.raises(ValueError):
        client.process_image(frame=None, image_path=None)
