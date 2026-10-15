import numpy as np
import pytest
from sketch_assistant.core.faces import detect_faces, crop_face, Face
from sketch_assistant.core.styles import STYLES, render


@pytest.fixture
def photo():
    rng = np.random.default_rng(1)
    base = np.tile(np.linspace(40, 220, 300, dtype=np.uint8), (400, 1))
    return np.dstack([base] * 3) + rng.integers(0, 15, (400, 300, 3), dtype=np.uint8)


@pytest.mark.parametrize("key", list(STYLES))
def test_style_outputs_bgr_uint8(key, photo):
    out = render(key, photo)
    assert out.dtype == np.uint8 and out.ndim == 3 and out.shape[2] == 3


def test_detect_and_crop(photo):
    assert isinstance(detect_faces(photo), list)
    assert crop_face(photo, Face(100, 100, 80, 80)).size > 0
