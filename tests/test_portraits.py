"""Portrait mode on real photographs.

The interesting test here is `test_fallback_proportions_match_real_faces`. The guide lines
drawn when the detector gives no landmarks used to sit at the textbook proportions for a
skull -- eyes halfway down, nose at 0.72, mouth at 0.84. Those are measured on the whole
head including the hair, which is not what a detector box spans, so the nose and mouth
lines came out on the neck. Nobody noticed because nothing compared them to a real face.

That test now measures where the features actually are, using YuNet's landmarks as ground
truth, and fails if the constants drift away from the measurement. It is the shape of test
that would have caught the original error.
"""
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from sketch_assistant.core.faces import (crop_info, detect_faces,  # noqa: E402
                                         load_image, yunet_available)
from sketch_assistant.core.guides import OVAL_H, OVAL_RISE, OVAL_W, draw_guides  # noqa: E402
from sketch_assistant.core.modes import build_stages  # noqa: E402

PORTRAITS = Path(__file__).resolve().parent / "fixtures" / "portraits"
ALL = sorted(p.name for p in PORTRAITS.glob("*.jpg"))
# The fixtures are photographs, so a checkout without them is a legitimate state. Skip
# cleanly rather than erroring: a red suite that only means "no sample images here" trains
# people to ignore red suites.
pytestmark = pytest.mark.skipif(not ALL, reason="no portrait fixtures present")
if not ALL:
    ALL = ["<none>"]
# YuNet declines this one and the Haar cascade picks it up instead, with no landmarks --
# which is exactly why it is in the set: it is the only fixture exercising the fallback
# guides, and that is where the proportions were wrong.
NO_LANDMARKS = {"no_landmarks_haar.jpg"}

# What `guides._proportional_guides` assumes, as a fraction of the way down the oval.
ASSUMED = {"eyes": 0.43, "nose": 0.64, "mouth": 0.78}
TOLERANCE = 0.06            # a little over one standard deviation of the measurements


def _first_face(name):
    img = load_image(str(PORTRAITS / name))
    faces = detect_faces(img)
    assert faces, f"{name}: no face detected"
    return img, faces


@pytest.mark.parametrize("name", ALL)
def test_a_face_is_found_in_every_portrait(name):
    img, faces = _first_face(name)
    f = faces[0]
    assert f.w > 0 and f.h > 0
    short = min(img.shape[:2])
    assert f.w > short * 0.05, f"{name}: face box is implausibly small"
    if name not in NO_LANDMARKS:
        assert len(faces[0].landmarks) == 5, f"{name}: expected YuNet landmarks"


@pytest.mark.parametrize("name", ALL)
def test_the_step_sequence_is_complete(name):
    """Every portrait must break into the full ladder.

    The feature stages are dropped when they would add no visible ink, which is right for
    an ear hidden by hair but was once firing for whole faces -- the sequence collapsed to
    construction, outline, shading and was no use to a learner.
    """
    img, faces = _first_face(name)
    crop, lm, box = crop_info(img, faces[0])
    keys = [s.key for s in build_stages("portrait", crop, "photoreal", 0.5, lm,
                                        crop.shape[:2], box)]
    assert keys[0] == "construction" and keys[-1] == "finish"
    for feature in ("eyes", "nose", "mouth"):
        assert feature in keys, f"{name}: no '{feature}' stage"
    assert len(keys) >= 8, f"{name}: only {len(keys)} stages: {keys}"


@pytest.mark.skipif(not yunet_available(), reason="needs YuNet for ground-truth landmarks")
def test_fallback_proportions_match_real_faces():
    """Where the guide lines are drawn must match where features actually are.

    Measured over every portrait fixture YuNet can landmark. If this fails, either the
    constants in `guides._proportional_guides` have drifted or the oval geometry has
    changed under them -- in both cases the no-landmark guides are lying to the user.
    """
    got = {"eyes": [], "nose": [], "mouth": []}
    for name in ALL:
        img = load_image(str(PORTRAITS / name))
        faces = detect_faces(img)
        crop, lm, box = crop_info(img, faces[0])
        if len(lm) != 5:
            continue
        bx, by, bw, bh = box
        cy = by + bh / 2 - bh * OVAL_RISE
        ay = bh * OVAL_H / 2
        top, height = cy - ay, 2 * ay
        re, le, nose, mr, ml = [np.array(p, float) for p in lm]
        got["eyes"].append(((re[1] + le[1]) / 2 - top) / height)
        got["nose"].append((nose[1] - top) / height)
        got["mouth"].append(((mr[1] + ml[1]) / 2 - top) / height)

    assert len(got["eyes"]) >= 4, "too few landmarked portraits to measure against"
    for feature, assumed in ASSUMED.items():
        measured = float(np.mean(got[feature]))
        assert abs(measured - assumed) < TOLERANCE, (
            f"the guides put the {feature} line at {assumed:.2f} down the oval but on real "
            f"faces it sits at {measured:.2f} -- update the constant in "
            f"guides._proportional_guides and steps._estimate_landmarks together")


@pytest.mark.parametrize("name", ALL)
def test_the_oval_contains_the_face(name):
    """The skull oval has to enclose the features it is meant to guide.

    Checked loosely -- a landmark may sit a little proud of the oval on a turned head --
    but a face mostly outside its own guide oval means the box-to-skull mapping is wrong.
    """
    img, faces = _first_face(name)
    crop, lm, box = crop_info(img, faces[0])
    if len(lm) != 5:
        pytest.skip("no landmarks to check against")
    bx, by, bw, bh = box
    cx, cy = bx + bw / 2, by + bh / 2 - bh * OVAL_RISE
    ax, ay = bw * OVAL_W / 2, bh * OVAL_H / 2
    out = [p for p in lm if ((p[0] - cx) / ax) ** 2 + ((p[1] - cy) / ay) ** 2 > 1.25]
    assert not out, f"{name}: {len(out)} of 5 landmarks well outside the guide oval"


@pytest.mark.parametrize("name", ALL)
def test_guides_render_for_every_style(name):
    img, faces = _first_face(name)
    crop, lm, box = crop_info(img, faces[0])
    from sketch_assistant.core.modes import MODES
    for key in MODES["portrait"].styles:
        from sketch_assistant.core.styles import render
        sk = render(key, crop, 0.5)
        out = draw_guides(sk, "portrait", key, lm, crop.shape[:2], box, crop)
        assert out.shape == sk.shape and out.dtype == np.uint8
