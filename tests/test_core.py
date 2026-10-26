import numpy as np
import pytest
from sketch_assistant.core.faces import Face, crop_face, crop_info, detect_faces
from sketch_assistant.core.guides import draw_guides
from sketch_assistant.core.styles import ALL, render


@pytest.fixture
def photo():
    rng = np.random.default_rng(1)
    base = np.tile(np.linspace(40, 220, 300, dtype=np.uint8), (400, 1))
    return np.dstack([base] * 3) + rng.integers(0, 15, (400, 300, 3), dtype=np.uint8)


@pytest.mark.parametrize("detail", [0.0, 0.5, 1.0])
@pytest.mark.parametrize("key", list(ALL))
def test_every_style_every_detail(key, detail, photo):
    out = render(key, photo, detail)
    assert out.dtype == np.uint8 and out.ndim == 3 and out.shape[2] == 3


def test_detail_changes_output():
    import cv2
    img = np.full((400, 300, 3), 200, np.uint8)
    cv2.circle(img, (150, 200), 90, (60, 60, 60), -1); cv2.rectangle(img, (40, 40), (120, 120), (90, 90, 90), 3)
    cv2.putText(img, "abc", (60, 350), cv2.FONT_HERSHEY_SIMPLEX, 2, (30, 30, 30), 3)
    for key in ("line_art", "value_study", "crosshatch", "photoreal"):
        assert not np.array_equal(render(key, img, 0.0), render(key, img, 1.0)), key


def test_detect_and_crop(photo):
    assert isinstance(detect_faces(photo), list)
    f = Face(100, 100, 80, 80, ((120, 130), (160, 130), (140, 150), (125, 170), (155, 170)))
    crop, lm = crop_info(photo, f)
    assert crop.size > 0 and len(lm) == 5 and crop_face(photo, f).shape == crop.shape


def test_guides_with_and_without_landmarks(photo):
    sk = render("line_art", photo)
    lm = ((100, 120), (180, 110), (140, 160), (110, 200), (170, 195))
    assert draw_guides(sk, "line_art", lm, photo.shape[:2]).shape == sk.shape
    assert draw_guides(sk, "line_art").shape == sk.shape
    assert draw_guides(sk, "obj_shapes").shape == sk.shape
