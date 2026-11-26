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
import json
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
        # the fallback scales its oval from the detector's box (it only runs without
        # landmarks, so without the face mesh's outline too): measure on that oval
        faces[0].oval_box = None
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


# --------------------------------------------------------------------------- close-ups
# A tester, with nineteen close-up portraits: "the guiding circle for some of these faces
# is smaller than the face itself". The oval is now fitted to the face mesh's outline of
# the face. The marks are the chin and the widest points of the face, by hand, on copies
# with nothing drawn on them.
CLOSE = Path(__file__).resolve().parent / "fixtures" / "portraits_close"
CLOSE_MARKS = {k: v for k, v in json.loads((CLOSE / "marks.json").read_text()).items()
               if not k.startswith("_")} if CLOSE.exists() else {}


def _mesh_models():
    from sketch_assistant.core import landmarks
    if not (landmarks.mesh_available() and yunet_available()):
        pytest.skip("face models not downloaded")


def _oval_fit(name, use_outline=True):
    """True if the drawn oval runs through the chin (within 12%) with the sides of the
    face inside it (within 10%), for the face nearest the marked chin."""
    img = load_image(str(CLOSE / name))
    H, W = img.shape[:2]
    faces = detect_faces(img)
    if not faces:
        return False
    marks = {k: (x * W, y * H) for k, (x, y) in CLOSE_MARKS[name].items()}
    chin = np.array(marks["chin"])
    f = min(faces, key=lambda f: np.hypot(f.x + f.w / 2 - chin[0], f.y + f.h / 2 - chin[1]))
    if not use_outline:
        f.oval_box = None
    bx, by, bw, bh = f.oval_box or (f.x, f.y, f.w, f.h)
    cx, cy = bx + bw / 2, by + bh / 2 - bh * OVAL_RISE
    ax, ay = bw * OVAL_W / 2, bh * OVAL_H / 2
    lm = f.landmarks
    t = np.arctan2(lm[1][1] - lm[0][1], lm[1][0] - lm[0][0]) if len(lm) == 5 else 0.0

    def rho(p):
        dx, dy = p[0] - cx, p[1] - cy
        u, v = dx * np.cos(t) + dy * np.sin(t), -dx * np.sin(t) + dy * np.cos(t)
        return float(np.hypot(u / ax, v / ay))
    r = {k: rho(p) for k, p in marks.items()}
    return 0.88 <= r["chin"] <= 1.12 and all(v <= 1.10 for k, v in r.items() if k != "chin")


@pytest.mark.skipif(not CLOSE_MARKS, reason="no close-up fixtures present")
def test_the_oval_fits_the_face_on_close_ups():
    """On the fifteen markable faces, at least nine ovals run through the chin with the
    face inside (ten measured). Control, run here because the claim is comparative: the
    oval scaled from the detector's box, as before, fits two -- and it fails the first
    assertion. Honest note: the start point and number of mesh passes were chosen on
    these same photos."""
    _mesh_models()
    now = sum(_oval_fit(n) for n in CLOSE_MARKS)
    before = sum(_oval_fit(n, use_outline=False) for n in CLOSE_MARKS)
    assert now >= 9, f"only {now} of {len(CLOSE_MARKS)} ovals fit the face"
    assert before <= now - 5, (before, now)


@pytest.mark.skipif(not CLOSE_MARKS, reason="no close-up fixtures present")
def test_a_close_up_face_the_detector_misses_is_found():
    """YuNet alone finds no face on close_08, an extreme close-up; the padded face finder
    recovers it, with an oval. (close_03, a strict profile, used to stay unfound here, as
    the face mesh can't read it; since the tester asked for profiles it is found as a
    profile instead -- see the side-profile tests below.)

    At the photos' original size YuNet also missed close_14 (heavy sunglasses) and read
    only the mouth and chin on close_17, and both were recovered the same way; at the
    900 px the fixtures are stored at, YuNet gets those two right on its own, so they
    can't be tested here. Control: YuNet alone on close_08 finds nothing."""
    _mesh_models()
    from sketch_assistant.core import faces as F
    img = load_image(str(CLOSE / "close_08.jpg"))
    assert F._yunet_faces(img) == []
    got = detect_faces(img)
    assert len(got) == 1 and got[0].oval_box is not None
    x, y, w, h = got[0].oval_box
    assert w * h > 0.3 * img.shape[0] * img.shape[1], "the face found is too small for this close-up"
    profile = detect_faces(load_image(str(CLOSE / "close_03.jpg")))
    assert len(profile) == 1 and profile[0].view == "profile"


# --------------------------------------------------------------------------- side profiles
FIXTURES = Path(__file__).resolve().parent / "fixtures"
def _guide_labels(img, face):
    """The labels the portrait guides put on this face (names only)."""
    from sketch_assistant.core import faces as F
    from sketch_assistant.core.guides import Ctx, face_guides
    crop, lm, box = F.crop_info(img, face)
    h, w = crop.shape[:2]
    ov = np.full((h, w, 3), 255, np.uint8)
    labels = face_guides(ov, w, h, 2, Ctx(crop, tuple(lm), crop.shape[:2], box, (1.0, 1.0)))
    return [lab[0].rsplit(" ", 1)[0] for lab in labels]


def test_a_side_profile_is_found_in_portrait_mode():
    """The tester's profile photo (close_03): YuNet and both Haar cascades find nothing, and
    the face mesh can't confirm a profile, so Portrait mode used to say no face. Now the
    padded finder's face is accepted as a profile, facing right, its box on the face."""
    from sketch_assistant.core import faces as F
    img = F.load_image(FIXTURES / "portraits_close" / "close_03.jpg")
    found = F.detect_faces(img)
    assert len(found) == 1, f"{len(found)} faces"
    f = found[0]
    assert f.view == "profile" and F.profile_facing(f.landmarks) == +1
    eye = np.mean(f.landmarks[:2], axis=0)
    assert f.contains(*eye), "the box misses the eye"
    crop, _, _ = F.crop_info(img, f)
    assert crop.shape[0] > 0.25 * img.shape[0], "crop too small to draw from"


def test_profiles_get_profile_guides_and_faces_keep_theirs():
    """A profile's guides have no centre line (it means nothing side on); a face-on portrait
    keeps its centre line. Control: the face-on fixtures."""
    from sketch_assistant.core import faces as F
    img = F.load_image(FIXTURES / "portraits_close" / "close_03.jpg")
    names = _guide_labels(img, F.detect_faces(img)[0])
    assert "centre" not in names
    assert {"eyes", "nose", "mouth", "chin"} <= set(names)
    for name in ("close_12.jpg", "close_02.jpg"):
        img = F.load_image(FIXTURES / "portraits_close" / name)
        f = max(F.detect_faces(img), key=lambda f: f.w * f.h)
        assert F.profile_facing(f.landmarks) == 0, f"{name} taken for a profile"
        names = _guide_labels(img, f)
        assert "centre" in names, name


def test_a_profile_found_twice_is_one_face():
    """bodies/seated_twist: YuNet finds the woman on the right, and the padded finder finds
    her again as a profile. Her nose tip stands out past YuNet's box, so a nose-only "same
    face?" check let the copy through. Seen to fail that way (3 faces, not 2)."""
    from sketch_assistant.core import faces as F
    img = F.load_image(FIXTURES / "bodies" / "seated_twist.jpg")
    assert len(F.detect_faces(img)) == 2


def test_cartoon_says_profiles_arent_supported():
    from sketch_assistant.core import caricature as C, faces as F
    img = F.load_image(FIXTURES / "portraits_close" / "close_03.jpg")
    crop, _, _ = F.crop_info(img, F.detect_faces(img)[0])
    assert "side profiles" in C.why_not(crop)
    assert "No face found" in C.why_not(F.load_image(FIXTURES / "objects" / "pale_on_pale.jpg"))


def _profile_oval(img, face):
    """(centre, half-width, half-height, angle in degrees) of the guide oval drawn on a
    profile, in image pixels -- the same numbers guides._oval and _profile_guides use."""
    from sketch_assistant.core.guides import OVAL_H, OVAL_RISE, OVAL_W
    bx, by, bw, bh = face.oval_box
    pts = np.asarray(face.landmarks, float)
    eye, mouth = pts[:2].mean(0), pts[3:].mean(0)
    up = (eye - mouth) / np.linalg.norm(eye - mouth)
    across = np.array([-up[1], up[0]])
    if across[0] < 0:
        across = -across
    centre = np.array([bx + bw / 2, by + bh / 2 - bh * OVAL_RISE])
    return centre, bw * OVAL_W / 2, bh * OVAL_H / 2, across


@pytest.mark.parametrize("name", ["close_03.jpg", "close_06.jpg", "close_01.jpg"])
def test_the_profile_oval_encloses_the_whole_face(name):
    """Every hand-marked point of the face -- hairline, brow, nose tip, lips, chin, under
    the chin, and the ear where it shows -- lies inside the profile's guide oval, and the
    oval isn't absurdly large. The tester's complaint about the face-on oval ("smaller than
    the face itself") applied here too at first: the skull-sized oval left the nose, lips
    and chin outside on all three, and YuNet's narrow box did on close_06 and close_01."""
    import json
    from sketch_assistant.core import faces as F
    marks = json.loads((CLOSE / "profile_marks.json").read_text())[name]
    img = F.load_image(CLOSE / name)
    f = max(F.detect_faces(img), key=lambda f: f.w * f.h)
    assert f.view == "profile" and f.oval_box is not None, f.view
    c, a1, a2, across = _profile_oval(img, f)
    down = np.array([-across[1], across[0]]) if across[0] >= 0 else np.array([across[1], -across[0]])
    if down[1] < 0:
        down = -down
    for part, p in marks.items():
        v = np.array(p, float) - c
        r = (v @ across / a1) ** 2 + (v @ down / a2) ** 2
        assert r <= 1.0, f"{name}: {part} outside the oval (r={r ** 0.5:.2f})"
    pts = np.array(list(marks.values()), float)
    span = pts.max(0) - pts.min(0)
    assert 2 * a2 < 1.9 * max(span), f"{name}: oval far bigger than the face"
