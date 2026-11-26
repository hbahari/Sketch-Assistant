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
import json
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
    "brown_with_brow": (0.50, 0.50, 0.138),   # re-read after the pupil re-centring; was 0.54, a little low
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


def _shadowed_iris(pupil=9):
    """An iris of radius 30 at (180, 100) with its left side in shadow, so its left
    limbus is weak: the condition behind the lopsided circle on a real photograph, with
    every position known exactly."""
    g = np.full((200, 320), 215, np.uint8)
    g[:, :150] = 150
    cv2.circle(g, (180, 100), 30, 120, -1)
    cv2.circle(g, (180, 100), pupil, 4, -1)
    g = cv2.GaussianBlur(g, (0, 0), 1.5)
    a = np.deg2rad(np.r_[np.arange(-eyes.ARC, eyes.ARC + 1, 8), np.arange(180 - eyes.ARC, 180 + eyes.ARC + 1, 8)])
    return g, float(g.std()) + 1e-6, float(g.mean()), a, np.deg2rad(np.arange(0, 360, 20))


def test_a_lopsided_circle_is_recentred_on_its_pupil():
    """A circle whose bright side is on the limbus and whose shadowed side is on the
    pupil's edge -- what the search found on a side-lit photograph a tester sent, drawn
    two-thirds the size of the iris and pushed toward the light. Re-centred on the pupil,
    it should come back as the iris.

    Tested on exact geometry because a synthetic photograph built to show the fault did
    not show it: the full pipeline found that iris correctly with or without the fix.
    The evidence that it matters on real eyes is the comparison over 38 photographs
    recorded in core/eyes.py. Control: with RECENTRE set out of reach this returns None.
    """
    g, sd, mean, a, full = _shadowed_iris()
    got = eyes._recentre_on_pupil(g, 190.5, 100.0, 19.5, sd, mean, a, full)
    assert got is not None, "lopsided circle not corrected"
    x, y, r = got
    assert np.hypot(x - 180, y - 100) <= 4.0, f"re-centred to ({x:.1f}, {y:.1f})"
    assert r == pytest.approx(30, rel=0.1)


def test_a_circle_already_on_its_pupil_is_left_alone():
    g, sd, mean, a, full = _shadowed_iris()
    assert eyes._recentre_on_pupil(g, 180.0, 100.0, 30.0, sd, mean, a, full) is None


# --------------------------------------------------------------------------- the mode
def test_eyes_use_the_box_picker_started_from_the_face():
    """Seventeen of the nineteen test photographs are close-ups with no face in them, so
    the user still frames the eye and nothing is tapped; where there is a face, the box
    starts on an eye and the crop is read with the face's reading."""
    m = MODES["eyes"]
    assert m.pick_box and m.detect is None
    assert m.locate is eyes.propose_box and m.on_crop is eyes.note_crop


@pytest.mark.parametrize("style,expect", [("eye_contour", 7), ("eye_construct", 7),
                                          ("eye_value", 8), ("eye_hatch", 8),
                                          ("eye_realistic", 14)])
def test_the_ladder_is_long_where_the_drawing_is_hard(style, expect):
    """Outline styles stop after the construction and the two outline passes.
    Photorealism gets six more between flat values and the finish -- hatching, blending,
    lights and darks, then the iris, the lids and the lashes -- because that gap is the
    one this mode exists to close."""
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


@pytest.mark.parametrize("detail", [0.1, 0.5, 0.9])
def test_the_tonal_stages_only_ever_approach_the_finish(detail):
    """From the blend on, each stage is the finished rendering with something still
    missing, so each one is closer to the finish than the one before. They used to be
    built at fixed settings whatever the slider said, and the lash stage laid black line
    art over the tone that the finish did not contain. 'Lift the lights' is left out of
    the comparison because it carries coloured marks that the finish does not."""
    stages = build_stages("eyes", _img("blue_macro"), "eye_realistic", detail)
    by = {s.key: s.image.astype(np.float32) for s in stages}
    gap = [float(np.abs(by[k] - by["finish"]).mean()) for k in ("hatch_blend", "eye_iris_tone", "eye_form", "eye_lashes")]
    assert gap == sorted(gap, reverse=True), f"distance from the finish, stage by stage: {gap}"


def test_soft_tone_is_gone():
    """It was offered as a style for one build and then as a ladder stage; on its own it
    read as the photograph out of focus. Blended hatching replaced it."""
    import sketch_assistant.core.styles as st
    assert "eye_soft" not in MODES["eyes"].styles and len(MODES["eyes"].styles) == 5
    assert not hasattr(st, "soft_tone")


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


@pytest.mark.parametrize("name", ["brown_macro", "small_in_face", "blue_macro"])
def test_eye_guide_numbers_stay_in_the_margins(name):
    """A tester called the first eye guides crowded: the numbers sat on the eye itself,
    beside the features they measured. They now sit along the top edge (measured across)
    and the left edge (measured down), so the eye carries only markers. The thirds grid
    is off in this mode for the same reason."""
    from sketch_assistant.core.guides import NO_GRID, label_rows
    img = _img(name)
    h, w = img.shape[:2]
    labels = eye_guides(np.full_like(img, 255), w, h, 1, Ctx(source_img=img))
    first, second = label_rows(w)
    top_band = first + 3 * (second - first) + 12
    for text, x, y, *_ in labels:
        if text.endswith("irises wide"):
            assert y > h * 0.9, "the eye-width caption should sit at the bottom edge"
            continue
        assert y <= top_band or x <= 30, f"'{text}' is drawn at ({x:.0f}, {y:.0f}), on the picture"
    assert "eyes" in NO_GRID


# --------------------------------------------------------------------------- eyes in a face
# A tester: "the guiding lines for the eyes are way bigger than the eye itself". On a photo
# with a face in it the eye is now found from the face (face mesh, then the iris model at
# the face's scale); the rules reading a box on its own set the scale from the box, and
# read six of these ten 2.7 to 4 times too big given a loose box. Unlike READ above, these marks are
# independent of the code: each iris was marked by hand on a crop with nothing drawn on it.
FACES = Path(__file__).resolve().parent / "fixtures"
FACE_MARKS = {k: v for k, v in json.loads((FACES / "eyes_in_faces" / "marks.json").read_text()).items()
              if not k.startswith("_")}
FACE_EYES = [(photo, i) for photo, eyes_ in sorted(FACE_MARKS.items()) for i in range(len(eyes_))]


def _models():
    from sketch_assistant.core import landmarks, noses
    if not (landmarks.iris_available() and landmarks.mesh_available() and noses._detector() is not None):
        pytest.skip("landmark models not downloaded")


def _boxed_reading(photo, i, k, note=True):
    """What the app does: a box round the eye about `k` eye-widths wide (as a user might
    draw it), cut out, noted, resized by the renderer, read. Returns (error in radii of the
    centre, signed error of the radius as a fraction)."""
    img = load_image(str(FACES / photo))
    H, W = img.shape[:2]
    mx, my, mr = FACE_MARKS[photo][i]
    tx, ty, tr = mx * W, my * H, mr * W
    w = 5.0 * tr                                       # an eye is about five iris radii wide
    x0, x1 = int(max(0, tx - k * w / 2)), int(min(W, tx + k * w / 2))
    y0, y1 = int(max(0, ty - k * w / 3)), int(min(H, ty + k * w / 3))
    crop = img[y0:y1, x0:x1].copy()
    eyes.forget_crop()
    if note:
        eyes.note_crop(img, crop, (x0, y0))
    eyes._cache.clear()
    e = eyes.analyze(cv2.resize(crop, None, fx=2.0, fy=2.0))
    eyes.forget_crop()
    cx, cy, r = e.iris[0] / 2 + x0, e.iris[1] / 2 + y0, e.r / 2
    return float(np.hypot(cx - tx, cy - ty) / tr), float(r / tr - 1), e


def test_an_eye_in_a_face_is_drawn_at_its_true_size():
    """Ten eyes, boxes of two and three eye-widths: the iris within a quarter of its marked
    size every time and typically within a tenth, whatever box was drawn.

    Control, run here because the claim is comparative: the rules reading the same boxes
    on their own, which is what the app did before. Their median size error is several
    times the face path's. Reintroducing the bug (not noting the crop, so the box is read
    on its own) fails the first assertion."""
    _models()
    face, rules = [], []
    for photo, i in FACE_EYES:
        for k in (2.0, 3.0):
            face.append(_boxed_reading(photo, i, k)[1])
            rules.append(_boxed_reading(photo, i, k, note=False)[1])
    face, rules = np.abs(face), np.abs(rules)
    assert face.max() <= 0.25, f"an iris {face.max():.0%} off its marked size"
    assert np.median(face) <= 0.10, f"median size error {np.median(face):.0%}"
    assert np.median(rules) >= 3 * np.median(face), (np.median(rules), np.median(face))


def test_an_eye_in_a_face_is_centred_within_half_an_iris():
    """The centre is the weaker half of the reading: within about half an iris radius
    of the mark on every eye, a third or better on half of them. (Marking a dark iris by
    hand is itself uncertain by perhaps 0.15 radii.)"""
    _models()
    errs = np.array([_boxed_reading(photo, i, 2.0)[0] for photo, i in FACE_EYES])
    assert errs.max() <= 0.6, errs.round(2)
    assert np.median(errs) <= 0.35, errs.round(2)


def test_the_face_tells_which_corner_is_the_tear_duct():
    _models()
    img = load_image(str(FACES / "noses" / "photos" / "front_freckles_ring.jpg"))
    found = eyes.photo_eyes(img)
    assert [e.inner for e in found] == ["right", "left"]          # both point at the nose
    assert found[0].iris[0] < found[1].iris[0]


def test_close_ups_of_one_eye_never_take_the_face_path():
    """The face detector reports a "face" in five of these nine close-ups. None may be
    read as a face. Control: with the detector's agreement check off (support 0), the
    almadastudio close-up (`small_in_face`), whose invented face the face mesh also
    believes, is read as one. (The mesh's verdict is a second line of defence that none of
    these fixtures needs: the agreement check alone keeps all of them out.)"""
    _models()
    for f in sorted(EYES.glob("*.jpg")):
        img = load_image(str(f))
        assert eyes.photo_eyes(img) == [], f.name
        assert eyes.propose_box(img) is None, f.name
    keep = eyes.EYE_FACE_SUPPORT
    try:
        eyes.EYE_FACE_SUPPORT = 0.0
        eyes._photos.clear()
        assert eyes.photo_eyes(_img("small_in_face")) != []
    finally:
        eyes.EYE_FACE_SUPPORT = keep
        eyes._photos.clear()


def test_the_box_starts_on_the_nearer_eye():
    _models()
    for photo, marks in FACE_MARKS.items():
        img = load_image(str(FACES / photo))
        H, W = img.shape[:2]
        box = eyes.propose_box(img)
        assert box is not None, photo
        x, y, w, h = box
        assert w * h < 0.3 * W * H, photo
        inside = [m for m in marks if x <= m[0] * W <= x + w and y <= m[1] * H <= y + h]
        assert inside or len(marks) == 1, photo       # one marked eye: the box may take the other


def test_a_box_drawn_away_from_the_eyes_is_read_on_its_own():
    _models()
    img = load_image(str(FACES / "noses" / "photos" / "front_freckles_ring.jpg"))
    H, W = img.shape[:2]
    crop = img[int(0.6 * H):H, 0:W // 2].copy()          # the cheek and the mouth
    eyes.note_crop(img, crop, (0, int(0.6 * H)))
    eyes._cache.clear()
    try:
        assert eyes.analyze(crop).notes.get("source") != "face"
    finally:
        eyes.forget_crop()


def test_where_the_face_gives_no_eye_it_still_sets_the_size(monkeypatch):
    """A tester: where the eye isn't found, "the guiding lines end up bigger than the
    eye". With the face path switched off (as on a side profile, where the face mesh
    declines), the face's eye-to-mouth length still caps the iris size and the detector's
    eye point anchors where to look. Ten eyes, boxes of two and three eye-widths: size
    within 55% every time and within 20% typically, centre within an iris radius.

    Control, run here: the rules alone on the same boxes are typically 28-168% out and
    up to four times the size. Reintroducing the bug (no scale noted with the crop) fails
    the first assertion."""
    _models()
    monkeypatch.setattr(eyes, "photo_eyes", lambda photo: [])
    sizes, centres, rules = [], [], []
    for photo, i in FACE_EYES:
        for k in (2.0, 3.0):
            c, r, e = _boxed_reading(photo, i, k)
            assert e.notes.get("source") == "face scale"
            sizes.append(abs(r)); centres.append(c)
            rules.append(abs(_boxed_reading(photo, i, k, note=False)[1]))
    assert max(sizes) <= 0.55, np.round(sizes, 2)
    assert np.median(sizes) <= 0.20 and max(centres) <= 1.0, (np.median(sizes), max(centres))
    assert max(rules) >= 2.0 and np.median(rules) >= 2 * np.median(sizes)
