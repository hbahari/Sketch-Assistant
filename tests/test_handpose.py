"""The landmark path, checked on a real photograph.

This is the test that the synthetic hand tests could not be: it runs the actual ONNX
models over an actual photo of a hand on a cluttered background, and asserts the anatomy
that a drawing guide depends on -- five fingers, joints in order along each one, the wrist
below the knuckles.

It skips when the models are absent, since they are downloaded rather than committed.
"""
import sys
from pathlib import Path

import cv2
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from sketch_assistant.core import hands  # noqa: E402
from sketch_assistant.core.hands import FINGERS, analyze, models_available  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures"
FIXTURE = FIXTURES / "hand.jpg"
# every photo here must be read correctly, not just the easy one
ALL_HANDS = sorted(p.name for p in FIXTURES.glob("*.jpg"))
# The landmark models read every fixture but one. On phone_grip the palm detector offers
# boxes and the landmark model rejects all of them -- it does not see a hand in a hand
# that is mostly off the frame and wrapped round a phone. No padding or resolution
# recovers it. It is listed here rather than quietly dropped: the app falls back to the
# silhouette and still draws usable guides, and `test_the_hard_case_degrades` pins that.
HARD = {"phone_grip.jpg"}
MODEL_HANDS = [n for n in ALL_HANDS if n not in HARD]
# hands touching another object: the cases where a segmentation that knows nothing about
# hands grabs the paper, the mug or the phone instead
WITH_OBJECTS = ["pen_signing.jpg", "mug_grip.jpg", "mug_handle.jpg"]
needs_models = pytest.mark.skipif(not models_available(),
                                  reason="ONNX models not downloaded (scripts/download_models.py)")
# likewise for the photographs themselves
pytestmark = pytest.mark.skipif(not FIXTURE.exists(), reason="no hand fixtures present")


@pytest.fixture(scope="module")
def photo():
    img = cv2.imread(str(FIXTURE))
    assert img is not None, f"missing fixture {FIXTURE}"
    return img


def test_generated_anchors_match_the_published_grid():
    """The vendored palm detector generates its anchor grid instead of listing 2016 pairs.

    If the generated grid were wrong, detection would not fail loudly -- it would decode
    boxes to the wrong places and quietly return nonsense -- so it is worth pinning. The
    published grid is two feature maps: 24x24 at stride 8 with two anchors per cell, then
    12x12 at stride 16 with six.
    """
    from sketch_assistant.core.vendor.mp_palmdet import MPPalmDet
    if not hands.PALM_MODEL.exists():
        pytest.skip("palm model not downloaded")
    anchors = MPPalmDet(modelPath=str(hands.PALM_MODEL)).anchors
    assert anchors.shape == (2016, 2)
    expected = []
    for stride, per_cell in ((8, 2), (16, 6)):
        g = 192 // stride
        cy, cx = np.mgrid[0:g, 0:g]
        c = np.stack([(cx + 0.5) * stride / 192, (cy + 0.5) * stride / 192], -1).reshape(-1, 2)
        expected.append(np.repeat(c, per_cell, axis=0))
    assert np.allclose(anchors, np.concatenate(expected), atol=1e-6)


@needs_models
def test_landmarks_on_a_real_photo(photo):
    h = analyze(photo)
    assert h is not None, "no hand found in the fixture photo"
    assert h.from_model, "fell back to the silhouette on a clean photo of a hand"
    lm = h.landmarks
    assert lm.shape == (21, 2)

    H, W = photo.shape[:2]
    inside = ((lm[:, 0] >= -W * 0.05) & (lm[:, 0] <= W * 1.05) &
              (lm[:, 1] >= -H * 0.05) & (lm[:, 1] <= H * 1.05))
    assert inside.all(), f"{(~inside).sum()} landmarks fell outside the picture"

    # all five fingers, every one with its four points
    assert len(h.joints) == 5
    assert all(len(f) == 4 for f in h.joints)
    assert len(h.tips) == 5

    span = float(np.hypot(*(lm.max(0) - lm.min(0))))
    for name, idx in FINGERS.items():
        pts = [lm[i] for i in idx]
        # joints run outward along the finger, never doubling back onto the wrist
        d = [float(np.hypot(*(p - lm[0]))) for p in pts]
        assert d == sorted(d), f"{name}: joints are not in order from the wrist ({d})"
        # and the finger has real length rather than collapsing to a point
        length = sum(float(np.hypot(*(b - a))) for a, b in zip(pts, pts[1:]))
        assert length > span * 0.08, f"{name}: finger is {length:.0f}px across a {span:.0f}px hand"


@needs_models
def test_palm_and_knuckles_are_anatomically_placed(photo):
    """The palm circle must sit on the palm and the knuckle arc across the knuckles.

    These are what every style draws over the sketch, so when they drift the guides look
    wrong even though the landmarks are right.
    """
    h = analyze(photo)
    lm = h.landmarks
    knuckles = np.array([lm[i] for i in (5, 9, 13, 17)])
    tips = np.array([lm[i] for i in (8, 12, 16, 20)])
    wrist = lm[0]

    # the palm lies between the wrist and the knuckles, not out among the fingers
    to_knuckles = float(np.hypot(*(knuckles.mean(0) - wrist)))
    to_palm = float(np.hypot(*(np.array(h.palm) - wrist)))
    assert 0.25 * to_knuckles < to_palm < 1.10 * to_knuckles, "palm centre is not on the palm"

    # and the circle reaches the knuckles without swallowing the fingers
    tip_d = float(np.hypot(*(tips.mean(0) - np.array(h.palm))))
    assert h.palm_r < tip_d, "palm circle extends past the fingertips"
    assert h.palm_r > 0.3 * to_knuckles, "palm circle is too small to be a block-in"

    assert len(h.knuckles) == 5
    assert len(h.palm_quad) >= 4


@needs_models
def test_hand_styles_keep_the_background_out(photo):
    """Hands are drawn on tables and against walls. Every hand style must shade the hand
    and leave the ground as paper, or the two stop reading as separate things."""
    from sketch_assistant.core.hands import hand_mask
    from sketch_assistant.core.styles import _prep, render

    small = _prep(photo)
    h = analyze(small)
    mask = hand_mask(small, h)
    assert mask is not None
    outside = mask < 40
    assert outside.sum() > outside.size * 0.1, "fixture should have real background in it"

    for key in ("hand_contour", "hand_value", "hand_hatch", "hand_realistic"):
        art = render(key, photo, 0.5)
        if art.shape[:2] != outside.shape:
            m = cv2.resize(mask, (art.shape[1], art.shape[0]))
            out = m < 40
        else:
            out = outside
        grey = cv2.cvtColor(art, cv2.COLOR_BGR2GRAY)
        ink_outside = float((grey[out] < 200).mean())
        assert ink_outside < 0.02, f"{key}: {ink_outside:.1%} of the background was drawn on"


@needs_models
def test_falls_back_rather_than_inventing_a_hand():
    """A picture with no hand in it must come back as None, not as a confident guess."""
    rng = np.random.default_rng(5)
    noise = rng.integers(60, 200, (420, 320, 3), dtype=np.uint8)
    assert analyze(noise) is None or not analyze(noise).from_model


@needs_models
@pytest.mark.parametrize("name", MODEL_HANDS)
def test_every_fixture_is_read_by_the_models(name):
    """All five fingers on every test photograph, not just the splayed one.

    These cover a fist head-on, fingers wrapped round a mug, a pinch, darker skin and a
    hand running off the edge of the frame. The fallback is not good enough for any of
    them, so landing on it here is a failure rather than a graceful degradation.
    """
    img = cv2.imread(str(FIXTURES / name))
    h = analyze(img)
    assert h is not None, f"{name}: no hand found"
    assert h.from_model, f"{name}: fell back to the silhouette"
    assert len(h.joints) == 5 and len(h.tips) == 5

    lm = h.landmarks
    span = float(np.hypot(*(lm.max(0) - lm.min(0))))
    for finger, idx in FINGERS.items():
        pts = [lm[i] for i in idx]
        # no two joints on top of each other, and the finger has real length
        for a, b in zip(pts, pts[1:]):
            assert float(np.hypot(*(b - a))) > span * 0.01, f"{name}/{finger}: joints coincide"
        length = sum(float(np.hypot(*(b - a))) for a, b in zip(pts, pts[1:]))
        assert span * 0.15 < length < span * 1.2, \
            f"{name}/{finger}: {length:.0f}px along a {span:.0f}px hand"

    # The knuckles sit on the palm, which is rigid, so they stay roughly equidistant from
    # the wrist whatever the fingers are doing. This is the structural check that holds
    # for a fist as well as a flat hand -- unlike "joints get further from the wrist as
    # you go out along a finger", which is only true when the finger is extended, and
    # which an earlier version of this test wrongly required.
    mcp_d = [float(np.hypot(*(lm[i] - lm[0]))) for i in (5, 9, 13, 17)]
    assert max(mcp_d) < min(mcp_d) * 1.8, f"{name}: knuckles are not on one palm {mcp_d}"


@needs_models
@pytest.mark.parametrize("name", WITH_OBJECTS)
def test_the_mask_excludes_what_the_hand_is_holding(name):
    """The mask must be the hand, not the hand plus the thing it is touching.

    GrabCut cheerfully returns hand-and-paper or hand-and-mug as one blob, and every
    landmark sits inside that blob, so checking the landmarks are contained does not
    catch it. The mask is the hull of the landmarks intersected with GrabCut, and this
    pins the result: it may not be much larger than the hand itself.
    """
    from sketch_assistant.core.hands import _hull_mask, hand_mask
    from sketch_assistant.core.styles import _prep

    img = _prep(cv2.imread(str(FIXTURES / name)))
    h = analyze(img)
    assert h is not None and h.from_model, f"{name}: no landmarks"
    mask = hand_mask(img, h)
    assert mask is not None

    covered = float((mask > 128).sum())
    hull = float((_hull_mask(img.shape, h, 0.85) > 128).sum())
    assert covered <= hull * 1.05, (
        f"{name}: mask covers {covered / hull:.1f}x the hand's own region -- it has "
        "taken in the object as well")
    # and it still covers the hand: every landmark inside, with room to spare
    H2, W2 = mask.shape
    inside = sum(1 for p in h.landmarks
                 if 0 <= int(p[1]) < H2 and 0 <= int(p[0]) < W2 and mask[int(p[1]), int(p[0])] > 128)
    assert inside >= len(h.landmarks) - 1, f"{name}: mask misses {len(h.landmarks) - inside} landmarks"


@needs_models
@pytest.mark.parametrize("name", ALL_HANDS)
def test_the_contour_style_closes_the_silhouette(name):
    """Contour must come back with an unbroken outline of the hand.

    Difference-of-Gaussians finds edges by contrast, and a hand against a pale table or a
    grey wall has very little of it, so the one line that matters most to someone drawing
    came back dashed or missing while every knuckle crease came through. The silhouette
    is now drawn explicitly; this checks it survived.
    """
    from sketch_assistant.core.hands import hand_mask
    from sketch_assistant.core.styles import _prep, render

    img = _prep(cv2.imread(str(FIXTURES / name)))
    h = analyze(img)
    mask = hand_mask(img, h)
    art = render("hand_contour", img)
    grey = cv2.cvtColor(art, cv2.COLOR_BGR2GRAY)

    # Walk the mask's boundary and ask whether there is ink near each point. Measuring
    # what fraction of a thick band is inked instead would mostly measure the band's
    # thickness against the line's, which says nothing about whether the outline is
    # continuous -- the thing actually being checked.
    boundary = cv2.Canny((mask > 128).astype(np.uint8) * 255, 50, 150) > 0
    ink = cv2.dilate((grey < 170).astype(np.uint8),
                     cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))) > 0
    covered = float(ink[boundary].mean())
    assert covered > 0.9, f"{name}: the silhouette is broken -- {covered:.0%} of it has ink"


@needs_models
@pytest.mark.parametrize("name", sorted(HARD))
def test_the_hard_case_degrades_instead_of_failing(name):
    """Where the landmark models cannot read the hand, the app must still draw something.

    Falling back to the silhouette gives cruder guides, but the alternative -- forcing a
    result by lowering the landmark model's confidence threshold -- puts confidently wrong
    joints on the page, which is worse than approximate ones.
    """
    from sketch_assistant.core.styles import render

    img = cv2.imread(str(FIXTURES / name))
    h = analyze(img)
    assert h is not None, f"{name}: produced nothing at all"
    assert not h.from_model, f"{name}: now reads from the model -- move it out of HARD"
    assert h.palm_r > 0 and len(h.tips) >= 2
    for key in ("hand_contour", "hand_construct", "hand_value"):
        art = render(key, img, 0.5)
        assert art.ndim == 3 and art.dtype == np.uint8, f"{name}/{key} did not render"
