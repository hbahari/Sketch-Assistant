"""Posture mode on real photographs.

Two of these pin down measurements that were wrong on the first attempt and would be easy
to get wrong again:

* `test_proportion_is_plausible` -- head height is inferred, since the landmark set has no
  crown or chin. Measuring it across the body (ear to ear, or shoulder to shoulder) looks
  natural and fails badly: those spans collapse the moment the figure turns, and the first
  version claimed one figure was 68 heads tall. Measuring along the body instead survives
  rotation.
* `test_tilts_read_as_lines_not_directions` -- a line has no direction, so a shoulder bar
  at -178 degrees and one at +2 are the same tilt. Reporting the raw angle made nearly
  parallel bars look wildly opposed.
"""
import sys
from pathlib import Path

import cv2
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from sketch_assistant.core import bodies  # noqa: E402
from sketch_assistant.core.bodies import (combined_mask, detect,  # noqa: E402
                                          models_available, union_box)
from sketch_assistant.core.faces import crop_to_box, load_image  # noqa: E402
from sketch_assistant.core.modes import MODES, build_stages  # noqa: E402
from sketch_assistant.core.styles import _prep, render  # noqa: E402

BODIES = Path(__file__).resolve().parent / "fixtures" / "bodies"
ALL = sorted(p.name for p in BODIES.glob("*.jpg"))
MULTI = ["two_people.jpg", "seated_twist.jpg"]      # more than one figure in shot

pytestmark = pytest.mark.skipif(not ALL, reason="no body fixtures present")
needs_models = pytest.mark.skipif(not models_available(),
                                  reason="pose models not downloaded (scripts/download_models.py)")
if not ALL:
    ALL = ["<none>"]


def _img(name):
    return load_image(str(BODIES / name))


def test_generated_anchors_match_the_published_grid():
    """The vendored person detector generates its anchors rather than listing 2254 pairs.

    A wrong grid would not fail loudly -- it would decode boxes to the wrong places and
    return plausible nonsense -- so it is worth pinning. Three feature maps over a 224px
    input: 28x28 at stride 8 with two anchors per cell, 14x14 at stride 16 with two, and
    7x7 at stride 32 with six.
    """
    if not bodies.PERSON_MODEL.exists():
        pytest.skip("person model not downloaded")
    from sketch_assistant.core.vendor.mp_persondet import MPPersonDet
    anchors = MPPersonDet(modelPath=str(bodies.PERSON_MODEL)).anchors
    assert anchors.shape == (2254, 2)
    expected = []
    for stride, per_cell in ((8, 2), (16, 2), (32, 6)):
        g = 224 // stride
        cy, cx = np.mgrid[0:g, 0:g]
        c = np.stack([(cx + 0.5) * stride / 224, (cy + 0.5) * stride / 224], -1).reshape(-1, 2)
        expected.append(np.repeat(c, per_cell, axis=0))
    assert np.allclose(anchors, np.concatenate(expected), atol=1e-6)


@needs_models
@pytest.mark.parametrize("name", ALL)
def test_a_figure_is_found(name):
    found = detect(_img(name))
    assert found, f"{name}: no figure found"
    for b in found:
        assert b.landmarks.shape == (33, 2)
        assert b.visible.sum() >= 6, f"{name}: almost nothing visible"
        assert b.w > 8 and b.h > 8
        assert b.mask is not None, f"{name}: no body mask"


@needs_models
@pytest.mark.parametrize("name", MULTI)
def test_several_figures_are_found_where_there_are_several(name):
    assert len(detect(_img(name))) >= 2, f"{name}: expected more than one figure"


@needs_models
@pytest.mark.parametrize("name", ALL)
def test_proportion_is_plausible(name):
    """A figure is a few heads tall, never dozens.

    The bounding box shrinks on a crouched or seated pose so the number varies, but any
    estimate outside roughly 2.5 to 9.5 means the head itself was measured wrongly rather
    than the pose being unusual.
    """
    for b in detect(_img(name)):
        assert 2.5 <= b.heads_tall <= 9.5, \
            f"{name}: {b.heads_tall:.1f} heads tall -- the head estimate has collapsed"
        assert b.head_height > 1.0


@needs_models
@pytest.mark.parametrize("name", ALL)
def test_tilts_read_as_lines_not_directions(name):
    for b in detect(_img(name)):
        sh, hp = b.tilts
        assert -90 < sh <= 90 and -90 < hp <= 90, f"{name}: tilt not normalised ({sh}, {hp})"
        assert abs(b.contrapposto) <= 180


@needs_models
@pytest.mark.parametrize("name", MULTI)
def test_choosing_two_figures_spans_both_and_the_gap(name):
    """Two people interacting are one composition, so selecting both gives one region
    covering them and the space between -- not two separate drawings."""
    img = _img(name)
    found = detect(img)
    one = union_box(found[:1], img.shape)
    both = union_box(found[:2], img.shape)

    # containment is the real contract: every chosen figure, whole, inside one region
    for b in found[:2]:
        assert both[0] - 1 <= b.x and b.x + b.w <= both[0] + both[2] + 1
        assert both[1] - 1 <= b.y and b.y + b.h <= both[1] + both[3] + 1
    assert both[2] >= one[2] - 1 and both[3] >= one[3] - 1, "the region shrank"

    # It only has to *grow* when the second figure actually sticks out of the first. Two
    # people sitting back to back overlap almost completely -- one box contains the other
    # -- and an unchanged region is then the right answer, not a failure.
    a, b2 = found[0], found[1]
    nested = (b2.x >= a.x and b2.y >= a.y
              and b2.x + b2.w <= a.x + a.w and b2.y + b2.h <= a.y + a.h)
    if not nested:
        assert both[2] * both[3] > one[2] * one[3] * 1.05, \
            "a second figure outside the first did not widen the region"


@needs_models
@pytest.mark.parametrize("name", ALL)
def test_every_style_renders(name):
    img = _img(name)
    for key in MODES["body"].styles:
        out = render(key, img, 0.5)
        assert out.ndim == 3 and out.dtype == np.uint8, f"{name}/{key}"


@needs_models
@pytest.mark.parametrize("name", ALL)
def test_the_step_sequence_is_gesture_first(name):
    """Structure before detail, which is the whole reason this mode is abstract."""
    img = _img(name)
    found = detect(img)
    crop = crop_to_box(img, union_box(found, img.shape), margin=0.0)
    stages = build_stages("body", crop, "body_realistic", 0.5)
    keys = [s.key for s in stages]
    assert keys[0] == "body_action", f"{name}: starts with {keys[0]}, not the line of action"
    assert keys[:4] == ["body_action", "body_tilts", "body_masses", "body_limbs"]
    assert keys[-1] == "finish"
    from sketch_assistant.data.steps_text import step_markup
    for s in stages:
        assert step_markup(s.key, "body_realistic"), f"{name}: no text for '{s.key}'"


@needs_models
@pytest.mark.parametrize("name", ALL)
def test_the_body_mask_keeps_the_background_out(name):
    """The pose model returns its own segmentation, which knows what a person is -- so a
    patterned floor or a figure in the background does not end up shaded as part of the
    drawing."""
    img = _prep(_img(name))
    found = detect(img)
    mask = combined_mask(found, img.shape)
    assert mask is not None
    outside = mask < 40
    assert outside.sum() > outside.size * 0.1, "fixture should have real background in it"
    for key in ("body_contour", "body_value", "body_realistic"):
        art = render(key, img, 0.5)
        out = outside
        if art.shape[:2] != outside.shape:
            out = cv2.resize(mask, (art.shape[1], art.shape[0])) < 40
        grey = cv2.cvtColor(art, cv2.COLOR_BGR2GRAY)
        ink = float((grey[out] < 200).mean())
        assert ink < 0.05, f"{name}/{key}: {ink:.1%} of the background was drawn on"


@needs_models
def test_gesture_stays_sparse():
    """Gesture is a thirty-second drawing. If it accumulates detail it stops doing its job,
    so it must stay far lighter than the rendered styles at the same detail."""
    img = _img(ALL[0])
    ink = {}
    for key in ("body_gesture", "body_contour", "body_realistic"):
        grey = cv2.cvtColor(render(key, img, 0.8), cv2.COLOR_BGR2GRAY)
        ink[key] = float((grey < 170).mean())
    assert ink["body_gesture"] < ink["body_contour"], "gesture is busier than the contour"
    assert ink["body_gesture"] < 0.08, f"gesture covers {ink['body_gesture']:.1%} of the page"


# ---- cross-contour hatching ---------------------------------------------------------
def test_the_axis_field_runs_along_and_across_a_limb():
    """The mechanism behind cross-contour hatching, tested directly.

    The strokes are iso-lines of two scalar fields: one measuring distance *along* the
    nearest limb axis, one measuring distance *across* it. If those are right the strokes
    wrap the form by construction, so this checks them on a segment whose geometry is
    known rather than trying to infer stroke direction from a finished render.

    Two output-level metrics were tried first -- the spread of gradient orientations, and
    the angle between strokes and the limb axis -- and neither separated this style from
    the ordinary cross-hatch. On a figure in dark clothing all three hatching layers fire
    at once and the silhouette dominates the gradients, so the measurement was mostly
    noise. Testing the field is both exact and honest about what is being claimed.
    """
    from sketch_assistant.core.styles import _axis_field

    # a horizontal segment across the middle of a 120x200 field
    p0, p1 = np.array([40.0, 60.0], np.float32), np.array([160.0, 60.0], np.float32)
    along, across, dist = _axis_field((120, 200), [(p0, p1)])

    # along the segment: the value tracks x and barely changes with y
    row = along[60, 50:150]
    assert np.all(np.diff(row) > 0.5), "'along' does not increase down the limb"
    col = along[40:80, 100]
    spread = float(col.max() - col.min())
    assert spread < 1.0, f"'along' changes across the limb by {spread:.2f}"

    # across it: zero on the axis, growing either side, and opposite in sign
    assert abs(across[60, 100]) < 1.5, "'across' is not zero on the axis"
    assert across[40, 100] * across[80, 100] < 0, "'across' has the same sign on both sides"
    assert abs(across[40, 100]) > 15 and abs(across[80, 100]) > 15

    # distance is a true distance from the segment
    assert abs(dist[60, 100]) < 1.5
    assert abs(dist[80, 100] - 20) < 2.0


def _median_stroke_width(bgr):
    """Median length of a horizontal run of ink: how thick the strokes actually are.

    Measured from the render rather than from the constants, so it catches a style that
    drifts apart from the others however it does it. Runs longer than 60px are solid
    shapes (hair, a dark garment), not strokes, so they are left out.
    """
    g = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    runs = []
    for row in (g < 150)[::3]:
        d = np.diff(np.concatenate(([0], row.view(np.int8), [0])))
        runs.extend((np.where(d == -1)[0] - np.where(d == 1)[0]).tolist())
    runs = [r for r in runs if r < 60]
    assert len(runs) > 200, "not enough strokes to measure"
    return float(np.median(runs))


@needs_models
def test_every_hatch_uses_the_same_stroke_rhythm():
    """Posture's hatching must look like the same pencil as every other mode's.

    It did not: Posture drew 7px strokes 25px apart where the rest of the app drew 1.6px
    strokes 8px apart, which reads as a different style rather than the same technique
    applied to a figure. They now share one spacing and weight and differ only in the
    direction the strokes run.

    The control for this test was the old rhythm, which gives a median stroke width of
    7-8px against 2-4px for the shared one, so the measurement does separate them.
    """
    from sketch_assistant.core.styles import crosshatch, render

    portrait = BODIES.parent / "portraits" / "front_adult.jpg"
    if not portrait.exists():
        pytest.skip("no portrait fixture to compare against")
    flat = _median_stroke_width(crosshatch(load_image(str(portrait)), 0.5))
    wrap = _median_stroke_width(render("body_formhatch", _img("standing.jpg"), 0.5))
    assert wrap <= 5.0, f"posture strokes are {wrap:.1f}px thick -- heavier than the other modes"
    assert abs(wrap - flat) <= 2.0, f"posture {wrap:.1f}px vs the usual cross-hatch {flat:.1f}px"


def test_the_axis_fields_keep_running_past_the_end_of_a_limb():
    """No bullseyes at the hips and crown.

    Measuring the fields to the nearest point *on the segment* makes them radial beyond its
    ends: `across` turns into distance-from-a-point, so its iso-lines are circles, and
    `along` goes constant, so a whole cap region either inks solid or not at all. Both were
    visible once the strokes were tightened to match the other modes. Measuring against the
    segment's infinite line instead keeps the strokes straight past the joint, which is
    what someone drawing the figure would do anyway.
    """
    from sketch_assistant.core.styles import _axis_field

    p0, p1 = np.array([40.0, 60.0], np.float32), np.array([160.0, 60.0], np.float32)
    along, across, _ = _axis_field((120, 200), [(p0, p1)])

    # well past the right-hand end of the segment
    assert along[60, 190] > along[60, 170] > along[60, 155], "'along' stops increasing past the end"
    # out there, 'across' must still be perpendicular distance, not radial distance
    assert abs(across[60, 190]) < 1.5, f"'across' is {across[60, 190]:.1f} on the axis past the end"
    assert abs(abs(across[30, 190]) - 30) < 2.0, "'across' is not perpendicular distance past the end"
    assert across[30, 190] * across[90, 190] < 0, "'across' lost its sign past the end"


@needs_models
def test_cross_contour_is_not_the_ordinary_hatch():
    """It must actually differ from the generic grid it falls back to."""
    from sketch_assistant.core.styles import _prep, crosshatch, render
    img = _prep(_img("crouched.jpg"))
    a = cv2.cvtColor(render("body_formhatch", img, 0.5), cv2.COLOR_BGR2GRAY)
    b = cv2.cvtColor(crosshatch(img, 0.5), cv2.COLOR_BGR2GRAY)
    assert a.shape == b.shape
    differ = float((np.abs(a.astype(int) - b.astype(int)) > 40).mean())
    assert differ > 0.05, f"only {differ:.1%} of pixels differ from the plain cross-hatch"


@needs_models
@pytest.mark.parametrize("name", ALL)
def test_hatching_stays_strokes_and_does_not_fill_in(name):
    """Darkness has to come from crossing layers, not from flooding the area.

    If the layers merge into solid black the style stops teaching anything: the learner
    cannot count the layers or see which way to pull the pencil.
    """
    from sketch_assistant.core.bodies import combined_mask
    from sketch_assistant.core.styles import _prep, render

    img = _prep(_img(name))
    found = detect(img)
    mask = combined_mask(found, img.shape) > 100
    art = render("body_formhatch", img, 0.8)          # densest setting
    grey = cv2.cvtColor(art, cv2.COLOR_BGR2GRAY)
    covered = float((grey[mask] < 150).mean())
    assert covered < 0.70, f"{name}: hatching covers {covered:.0%} of the figure -- it has filled in"
    assert covered > 0.02, f"{name}: almost no hatching at all ({covered:.1%})"


@needs_models
def test_the_ladder_bridges_flat_tone_and_finish():
    """The gap this stage exists to close: value blocks, then strokes, then the finish."""
    img = _img("kneeling.jpg")
    found = detect(img)
    crop = crop_to_box(img, union_box(found, img.shape), margin=0.0)
    keys = [s.key for s in build_stages("body", crop, "body_realistic", 0.5)]
    assert "values" in keys and "body_hatch" in keys
    assert keys.index("values") < keys.index("body_hatch") < keys.index("finish"), keys
