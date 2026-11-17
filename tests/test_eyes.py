"""Eyes mode on real photographs.

The fixtures are nine of the nineteen eye photographs the mode was developed against,
chosen to keep one of each thing that went wrong on the way:

* pale eyes, where the strongest dark circle is the pupil and the iris has to be found
  round it (`blue_macro`, `green_fills_frame`, `small_in_face`);
* a pupil with a window reflected in it (`amber_reflection`);
* dark eyes, where the iris is already the strongest circle and looking further out
  lands on the curve of the lids (`brown_macro`, `brown_with_brow`, `brown_side_light`);
* and two the analysis still gets wrong, kept so that it stays wrong *safely*
  (`highlight_in_pupil`, `mono_shadowed_sclera`).

What the "expected" numbers are, honestly: there is no independent ground truth here.
They are this code's own output on each photograph, kept only where an overlay of the
result on the photo was checked by eye and judged right. So these tests pin behaviour
that was verified once; they do not prove the measurement is accurate to the tolerance
they allow.
"""
import sys
from pathlib import Path

import cv2
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from sketch_assistant.core import eyes  # noqa: E402
from sketch_assistant.core.faces import load_image  # noqa: E402
from sketch_assistant.core.guides import Ctx, eye_guides  # noqa: E402
from sketch_assistant.core.modes import MODES, build_stages  # noqa: E402
from sketch_assistant.core.styles import render  # noqa: E402
from sketch_assistant.data.steps_text import step_markup  # noqa: E402

EYES = Path(__file__).resolve().parent / "fixtures" / "eyes"
pytestmark = pytest.mark.skipif(not EYES.exists(), reason="no eye fixtures present")

# iris centre (fraction of width, of height) and radius (fraction of width), read off an
# overlay that was checked against the photograph
READ = {
    "blue_macro": (0.44, 0.54, 0.187),
    "brown_macro": (0.50, 0.42, 0.215),
    "amber_reflection": (0.46, 0.44, 0.301),
    "brown_with_brow": (0.50, 0.54, 0.134),
    "green_fills_frame": (0.54, 0.50, 0.346),
    "small_in_face": (0.46, 0.49, 0.107),
    "brown_side_light": (0.63, 0.38, 0.149),
}
PALE = ["blue_macro", "green_fills_frame", "small_in_face", "amber_reflection"]
DARK = ["brown_macro", "brown_with_brow", "brown_side_light"]
MISSED = ["highlight_in_pupil", "mono_shadowed_sclera"]


def _img(name):
    return load_image(str(EYES / f"{name}.jpg"))


def _fresh(name):
    """Analyse without the cache, for tests that change a constant and look again."""
    eyes._cache.clear()
    img = _img(name)
    return img, eyes.analyze(img)


@pytest.mark.parametrize("name", sorted(READ))
def test_the_iris_is_found_where_it_is(name):
    img = _img(name)
    eye = eyes.analyze(img)
    H, W = img.shape[:2]
    fx, fy, fr = READ[name]
    assert eye.found, f"{name}: no iris found (score {eye.score:.2f})"
    assert eye.r / W == pytest.approx(fr, rel=0.15), f"{name}: iris radius {eye.r / W:.3f} of the width"
    off = np.hypot(eye.iris[0] - fx * W, eye.iris[1] - fy * H)
    assert off <= 0.4 * fr * W, f"{name}: iris centre is {off:.0f}px from where it was read"


@pytest.mark.parametrize("name", PALE)
def test_a_pale_eye_gets_its_iris_not_its_pupil(name):
    """In a pale eye the strongest dark circle is the pupil. Left at that, everything
    built on the iris -- the lids, the eyeball, the whole construction -- comes out a
    third of its real size. Control: with promotion switched off, all four of these
    report a radius under 0.14 of the width and this test fails."""
    img = _img(name)
    eye = eyes.analyze(img)
    assert eye.r / img.shape[1] >= READ[name][2] * 0.85
    assert 0.15 <= eye.pupil_r / eye.r <= 0.6, f"{name}: pupil is {eye.pupil_r / eye.r:.2f} of the iris"


@pytest.mark.parametrize("name", DARK)
def test_a_dark_iris_is_not_promoted_to_the_lids(name):
    """The opposite mistake. A brown iris is already the strongest circle, and looking
    for a bigger one round it finds the curve of the lids. Control: with the pupil-is-
    black check disabled, `brown_side_light` jumps from 0.149 to 0.241 and this fails."""
    img = _img(name)
    eye = eyes.analyze(img)
    assert eye.r / img.shape[1] <= READ[name][2] * 1.15, \
        f"{name}: iris radius {eye.r / img.shape[1]:.3f}, read as {READ[name][2]:.3f}"


@pytest.mark.parametrize("name", MISSED)
def test_the_known_misses_fail_small_not_wild(name):
    """Two photographs the analysis gets wrong, and the way it is allowed to be wrong.

    `highlight_in_pupil`: a catchlight covers half the pupil, so the pupil is not black
    enough to be recognised as one and is taken for the iris. `mono_shadowed_sclera`: a
    black-and-white photograph in which the white of the eye is in shadow and darker than
    the iris, which inverts the one edge the search looks for.

    In both the answer is a too-small eye in the right place, which gives a too-small but
    correctly placed construction. That is the acceptable failure. The unacceptable one --
    an "iris" over the brow or half off the frame -- is what this guards against. If
    either photograph ever starts being read correctly, move it to READ.
    """
    img = _img(name)
    eye = eyes.analyze(img)
    H, W = img.shape[:2]
    assert 0.3 * W <= eye.iris[0] <= 0.7 * W and 0.3 * H <= eye.iris[1] <= 0.7 * H
    assert eye.iris[0] - eye.r >= 0 and eye.iris[0] + eye.r <= W
    assert 1.5 <= eye.irises_wide <= 3.5


@pytest.mark.parametrize("name", sorted(READ) + MISSED)
def test_the_lids_are_always_a_plausible_eye(name):
    """The lids come from a template confined to the range real eyes occupy, so whatever
    the photograph does, the answer is eye-shaped: between one and a half and three and a
    half irises wide, upper lid above lower, pupil between the corners."""
    eye = eyes.analyze(_img(name))
    assert 1.5 <= eye.irises_wide <= 3.5, f"{name}: {eye.irises_wide:.2f} irises wide"
    mid = len(eye.upper) // 2
    assert eye.upper[mid][1] < eye.lower[mid][1], f"{name}: lids are inside out"
    assert eye.left[0] < eye.iris[0] < eye.right[0], f"{name}: pupil is outside the corners"
    assert abs(eye.tilt) <= 12.0


def test_no_eye_is_reported_as_no_eye():
    """A blank frame still returns a template -- the styles need something to draw --
    but says plainly that the iris was assumed rather than measured."""
    eye = eyes.analyze(np.full((240, 360, 3), 128, np.uint8))
    assert not eye.found
    assert eye.highlight is None and eye.crease is None
    assert 1.5 <= eye.irises_wide <= 3.5


# --------------------------------------------------------------------------- the mode
def test_eyes_use_the_box_picker_not_the_face_detector():
    """Seventeen of the nineteen test photographs are close-ups with no face in them,
    and the face detector reported one inside ten of those. So there is no detection
    step: the user frames the eye."""
    m = MODES["eyes"]
    assert m.pick_box and m.detect is None


@pytest.mark.parametrize("style,expect", [("eye_contour", 7), ("eye_construct", 7),
                                          ("eye_value", 8), ("eye_hatch", 8),
                                          ("eye_realistic", 12)])
def test_the_ladder_is_long_where_the_drawing_is_hard(style, expect):
    """Outline styles stop after the construction and the two outline passes.
    Photorealism gets four more stages between flat values and the finish, because that
    gap is the one this mode exists to close."""
    stages = build_stages("eyes", _img("blue_macro"), style, 0.6)
    assert len(stages) == expect, [s.key for s in stages]
    for a, b in zip(stages, stages[1:]):
        assert a.image.shape != b.image.shape or (a.image != b.image).mean() > 0.002, \
            f"'{a.key}' and '{b.key}' show the same picture"
    for s in stages:
        assert step_markup(s.key, style), f"stage '{s.key}' has no instructions"


def _ink(img):
    return int((cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) < 235).sum())


def test_each_construction_level_adds_to_the_last():
    img = _img("blue_macro")
    ink = [_ink(render("eye_construct", img, d)) for d in (0.2, 0.45, 0.7, 1.0)]
    assert ink == sorted(ink) and len(set(ink)) == 4, f"ink per level: {ink}"


def test_the_blended_stage_is_the_finished_drawing_without_its_detail():
    """The blended stages lead to Photorealism, so they have to be the same drawing: the
    same overall tone, with the fine detail missing. The first version used its own tone
    curve and came out nearly sixty grey levels darker than the finish it leads to, so
    the last step of the ladder appeared to bleach the drawing."""
    from sketch_assistant.core.styles import soft_tone
    img = _img("blue_macro")
    soft = cv2.cvtColor(soft_tone(img, 0.3), cv2.COLOR_BGR2GRAY)
    real = cv2.cvtColor(render("eye_realistic", img, 0.6), cv2.COLOR_BGR2GRAY)
    assert abs(float(soft.mean()) - float(real.mean())) < 15, \
        f"blended {soft.mean():.0f} vs finished {real.mean():.0f}"
    blur = lambda g: cv2.GaussianBlur(g, (0, 0), 1.5)          # ignore the paper grain
    assert cv2.Laplacian(blur(soft), cv2.CV_64F).var() < 0.25 * cv2.Laplacian(blur(real), cv2.CV_64F).var()


@pytest.mark.parametrize("detail", [0.1, 0.5, 0.9])
def test_the_tonal_stages_only_ever_approach_the_finish(detail):
    """From 'Draw the iris' on, each stage is the finished rendering with something still
    missing, so each one is closer to the finish than the one before. They used to be
    built at fixed settings whatever the slider said, and the lash stage laid black line
    art over the tone that the finish did not contain."""
    stages = build_stages("eyes", _img("blue_macro"), "eye_realistic", detail)
    by = {s.key: s.image.astype(np.float32) for s in stages}
    gap = [float(np.abs(by[k] - by["finish"]).mean()) for k in ("eye_blend", "eye_iris_tone", "eye_form", "eye_lashes")]
    assert gap == sorted(gap, reverse=True), f"distance from the finish, stage by stage: {gap}"


def test_soft_tone_is_a_step_not_a_style():
    """It was offered as a style for one build. On its own it reads as the photograph
    out of focus; it only means something on the way to Photorealism."""
    assert "eye_soft" not in MODES["eyes"].styles and len(MODES["eyes"].styles) == 5


def test_eye_guides_say_where_the_pupil_and_the_lids_sit():
    img = _img("brown_macro")
    h, w = img.shape[:2]
    eye = eyes.analyze(img)
    labels = eye_guides(np.full_like(img, 255), w, h, 1, Ctx(source_img=img))
    got = {}
    for lab in labels:
        name, _, tail = lab[0].rpartition(" ")
        try:
            got.setdefault(name, []).append(float(tail))
        except ValueError:
            pass
    assert got["pupil"][0] == pytest.approx(eye.iris[0] / w, abs=0.006)     # across
    assert got["pupil"][1] == pytest.approx(eye.iris[1] / h, abs=0.006)     # down
    assert got["upper lid"][0] < got["pupil"][1] < got["lower lid"][0]
    assert len(got["corner"]) == 2 and got["corner"][0] < got["pupil"][0] < got["corner"][1]
