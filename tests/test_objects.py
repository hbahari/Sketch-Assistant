"""Object mode on real still lifes.

What these pin down is narrower than it looks, and deliberately so.

Object mode segments with GrabCut seeded from a rectangle inset into the middle of the
frame. That works when the photograph contains one object, roughly centred. On a still
life of several objects -- which is the classic drawing subject, and so an entirely
natural thing for someone to photograph -- GrabCut still converges, but on some union of
objects and background, because nothing in the method knows which object the user meant.
Measured over twenty-five still lifes, the silhouette was unusable on roughly half.

So these tests assert that nothing crashes, that the sequence is complete, and that the
silhouette is not degenerate. They do *not* assert that it traces the right object,
because it frequently does not, and a test claiming otherwise would be a lie that blocked
the real fix: letting the user indicate the object, the way Portrait mode lets them tap a
face. `test_known_limitation_multi_object_scenes` records the gap in the meantime.
"""
import sys
from pathlib import Path

import cv2
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from sketch_assistant.core.faces import load_image  # noqa: E402
from sketch_assistant.core.guides import draw_guides  # noqa: E402
from sketch_assistant.core.modes import MODES, build_stages  # noqa: E402
from sketch_assistant.core.steps import contact_sheet  # noqa: E402
from sketch_assistant.core.styles import _prep, _silhouette, render  # noqa: E402

OBJECTS = Path(__file__).resolve().parent / "fixtures" / "objects"
ALL = sorted(p.name for p in OBJECTS.glob("*.jpg"))
pytestmark = pytest.mark.skipif(not ALL, reason="no object fixtures present")
if not ALL:
    ALL = ["<none>"]
MULTI = ["many_objects_cluttered.jpg", "multi_object_warm.jpg", "two_objects_touching.jpg"]


@pytest.mark.parametrize("name", ALL)
def test_every_style_renders(name):
    img = load_image(str(OBJECTS / name))
    for key in MODES["object"].styles:
        out = render(key, img, 0.5)
        assert out.ndim == 3 and out.dtype == np.uint8, f"{name}/{key}"
        assert out.shape[0] > 0 and out.shape[1] > 0


@pytest.mark.parametrize("name", ALL)
def test_the_silhouette_is_not_degenerate(name):
    """Whatever it traces, it must be a usable shape.

    A silhouette covering almost nothing, or almost the whole frame, breaks everything
    downstream: the block-in has nothing to draw, the proportion label divides by it, and
    the masked stages come back blank or unmasked.
    """
    img = _prep(load_image(str(OBJECTS / name)))
    h, w = img.shape[:2]
    sil = _silhouette(img)
    assert sil is not None and len(sil) >= 3, f"{name}: no silhouette at all"
    frac = cv2.contourArea(sil) / float(h * w)
    assert 0.02 < frac < 0.92, f"{name}: silhouette covers {frac:.0%} of the frame"
    x, y, bw, bh = cv2.boundingRect(sil)
    assert bw > 8 and bh > 8, f"{name}: silhouette bounding box is {bw}x{bh}"


@pytest.mark.parametrize("name", ALL)
def test_the_step_sequence_is_complete(name):
    img = load_image(str(OBJECTS / name))
    stages = build_stages("object", img, "obj_realistic", 0.5)
    keys = [s.key for s in stages]
    assert keys[0] == "proportion" and keys[-1] == "finish"
    assert len(keys) >= 4, f"{name}: only {keys}"
    assert len(set(keys)) == len(keys), f"{name}: duplicate stage in {keys}"
    for s in stages:
        assert s.image.ndim == 3 and s.image.dtype == np.uint8
    assert contact_sheet(stages, cell=80, cols=3).ndim == 3


@pytest.mark.parametrize("name", ALL)
def test_guides_render_over_every_style(name):
    img = load_image(str(OBJECTS / name))
    for key in MODES["object"].styles:
        sk = render(key, img, 0.5)
        out = draw_guides(sk, "object", key, (), img.shape[:2], None, img)
        assert out.shape == sk.shape


def test_a_drawn_box_isolates_the_object():
    """Cropping to a drawn selection must make the object dominate its own frame.

    This is the measurement behind the box picker. On the whole frame of a still life the
    silhouette spans several objects; cropped to one of them it covers a much larger share
    of a much smaller picture, which is what the block-in and the masked stages need.
    """
    from sketch_assistant.core.faces import crop_to_box
    boxes = {                      # fractions of (w, h), one object in each scene
        "many_objects_cluttered.jpg": (0.55, 0.33, 0.33, 0.60),
        "multi_object_warm.jpg": (0.30, 0.22, 0.42, 0.56),
        "two_objects_touching.jpg": (0.28, 0.16, 0.40, 0.56),
    }
    for name, (fx, fy, fw, fh) in boxes.items():
        img = _prep(load_image(str(OBJECTS / name)))
        H, W = img.shape[:2]
        crop = crop_to_box(img, (fx * W, fy * H, fw * W, fh * H))
        assert crop.shape[0] < H or crop.shape[1] < W, f"{name}: crop did not shrink"
        sil = _silhouette(crop)
        frac = cv2.contourArea(sil) / float(crop.shape[0] * crop.shape[1])
        assert frac > 0.12, f"{name}: object fills only {frac:.0%} of its own crop"


def test_whole_frame_still_renders():
    """The default selection is most of the photo, so the old behaviour is still a path
    through the code and still has to work."""
    spans = {}
    for name in MULTI:
        img = _prep(load_image(str(OBJECTS / name)))
        h, w = img.shape[:2]
        sil = _silhouette(img)
        spans[name] = cv2.contourArea(sil) / float(h * w)
    # every one of these still produces *a* shape; whether it is the right one is the
    # open question, and the only thing that can be checked without ground truth is that
    # the method has not simply given up
    for name, frac in spans.items():
        assert 0.02 < frac < 0.92, f"{name}: {frac:.0%}"
    print("\nsilhouette coverage on multi-object scenes (correctness unverified):")
    for name, frac in sorted(spans.items()):
        print(f"  {name:32} {frac:.0%} of frame")
