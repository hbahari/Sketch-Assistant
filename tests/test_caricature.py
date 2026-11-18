"""Caricature mode on real photographs.

The claims worth testing are the ones a tester could check by eye and the code could get
quietly wrong: that the exaggeration comes from this face rather than a fixed cartoon
recipe, that the slider really runs from none to strong, that only the head is drawn,
that it stays far lighter than the shaded portrait styles, and that it degrades without
a face or without the segmentation model rather than failing.
"""
import sys
from pathlib import Path

import cv2
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from sketch_assistant.core import caricature as C  # noqa: E402
from sketch_assistant.core.faces import crop_info, detect_faces, load_image  # noqa: E402
from sketch_assistant.core.modes import MODES, build_stages  # noqa: E402
from sketch_assistant.core.styles import render  # noqa: E402

FX = Path(__file__).resolve().parent / "fixtures"
# near face-on faces, where a 2D ratio means the same thing on the photo and the average
FACES = ["portraits_close/close_13.jpg", "portraits_close/close_09.jpg", "portraits_close/close_04.jpg",
         "portraits/front_adult.jpg", "portraits/beard_dark_skin.jpg", "portraits/glasses_older.jpg",
         "portraits_close/close_12.jpg", "portraits_close/close_02.jpg"]


def _models():
    from sketch_assistant.core import landmarks
    if not landmarks.mesh_available() or C._seg_net() is None:
        pytest.skip("face mesh or segmentation model not downloaded")


def _crop(name):
    img = load_image(str(FX / name))
    faces = detect_faces(img)
    assert faces, name
    return crop_info(img, max(faces, key=lambda f: f.w * f.h))[0]


def _ink(img):
    return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) < 200


# what is measured: four proportions a caricaturist pushes, each a ratio of two lengths
RATIOS = {
    "face width / height": ((234, 454), (10, 152)),
    "nose width / eye span": ((64, 294), (33, 263)),
    "mouth width / eye span": ((61, 291), (33, 263)),
    "eye-to-mouth / face height": ((168, 13), (10, 152)),
}


def _ratio(xy, pair):
    (a, b), (c, d) = pair
    return np.linalg.norm(xy[a] - xy[b]) / max(np.linalg.norm(xy[c] - xy[d]), 1e-6)


def test_the_exaggeration_pushes_this_face_s_own_differences():
    """For each face and each proportion that differs from MediaPipe's average face by
    more than 3%, the caricature at full strength moves it further the same way: a wide
    nose wider, a short chin shorter. 4 proportions on 8 faces.

    Measured: 26 of 29. Control, run here: a fixed cartoon recipe (the same push for
    every face -- here, every proportion 10% larger) agrees with the face's own direction
    21 of 29 times and fails the same threshold. Reintroducing the bug of pushing the
    other way fails it too."""
    _models()
    agree = total = cartoon = 0
    for name in FACES:
        m = C.measure(_crop(name))
        assert m.found, name
        photo, avg = m.P[:, :2], m.M[:, :2]
        full = C.Warp(m, C.strength(1.0)).dst
        for pair in RATIOS.values():
            p, a, c = _ratio(photo, pair), _ratio(avg, pair), _ratio(full, pair)
            if abs(p - a) < 0.03 * a:
                continue
            total += 1
            agree += (c - p) * (p - a) > 0
            cartoon += (1.10 * p - p) * (p - a) > 0
    assert total >= 12, f"only {total} proportions differ from the average enough to test"
    assert agree >= 0.85 * total, f"{agree} of {total} pushed the face's own way"
    assert cartoon < 0.85 * total, f"the control agreed {cartoon} of {total} times -- the test proves nothing"


def test_the_slider_runs_from_the_photo_to_strong():
    """At the bottom of the slider the drawing has the photo's own proportions, exactly;
    the push grows steadily with the slider."""
    _models()
    m = C.measure(_crop(FACES[0]))
    assert np.allclose(C.Warp(m, C.strength(0.0)).dst, m.P[:, :2])
    moves = [float(np.abs(C.Warp(m, C.strength(d)).dst - m.P[:, :2]).mean()) for d in (0.25, 0.5, 1.0)]
    assert 0 < moves[0] < moves[1] < moves[2], moves


@pytest.mark.parametrize("name", FACES[:4])
def test_only_the_head_is_drawn(name):
    """Head only, no surroundings: nothing drawn more than a sixth of a face below the
    chin, and nothing far outside the head. Control: with the cut under the chin and the
    limit beside the shoulders switched off, the collar and shoulders come back and two
    of these four photos fail."""
    _models()
    crop = _crop(name)
    D = C.drawing(crop, 0.5)
    out = C.paint(D, hatch=True)
    ink = _ink(out)
    chin = D.construct["chin"]
    (cx, cy), (a, b), ang = D.construct["head"]
    below = ink[int(chin[1] + b / 6):, :]
    assert below.sum() < 0.002 * ink.size, f"{name}: {below.sum()} inked pixels below the chin"
    near = np.zeros(ink.shape, np.uint8)
    pts = [p for part in D.lines.values() for p in part if not isinstance(p, tuple)]
    hull = cv2.convexHull(np.vstack(pts).astype(np.float32)).astype(np.int32)
    cv2.fillPoly(near, [hull], 255)
    near = cv2.dilate(near, np.ones((15, 15), np.uint8)) > 0
    assert (ink & ~near).sum() < 0.001 * ink.size, f"{name}: ink far from the head"


def test_it_is_far_lighter_than_the_shaded_portrait_styles():
    """"Simpler than photorealism, not too many shadings, not crowded": on every face the
    Light Hatching caricature puts down under a third of the ink of Portrait mode's
    Cross-Hatch on the same crop, and Clean Lines less again."""
    _models()
    for name in FACES[:4]:
        crop = _crop(name)
        hatched, lines = _ink(render("car_hatch", crop, 0.5)).mean(), _ink(render("car_lines", crop, 0.5)).mean()
        cross = _ink(render("crosshatch", crop, 0.5)).mean()
        assert hatched < cross / 3, f"{name}: caricature ink {hatched:.3f} vs cross-hatch {cross:.3f}"
        assert lines < hatched, name


def test_a_bald_head_gets_no_hairline():
    """A bald head is drawn with its outline but no hairline across the forehead; pink
    hair, which a colour test alone took for skin, keeps its hairline. Control: with the
    texture test off (every skin-coloured top counted bald) the pink-haired photo loses
    its hairline and the second assertion fails."""
    _models()

    def hairline_points(name):
        m = C.measure(_crop(name))
        top = m.P[C.FOREHEAD, :2]
        pts = np.vstack(m.hair) if m.hair else np.zeros((0, 2))
        return int((np.hypot(*(pts - top).T) < 0.08 * m.face_h).sum())
    C._cache.clear()
    assert hairline_points("portraits/beard_dark_skin.jpg") == 0
    assert hairline_points("portraits/glasses_older.jpg") > 0


def test_the_ladder_builds_up_from_shapes():
    """Shapes, then lines one feature at a time: each stage after the shapes has at least
    as much ink as the one before, and the hatching is its own stage."""
    _models()
    crop = _crop(FACES[0])
    st = build_stages("caricature", crop, "car_hatch", 0.5)
    keys = [s.key for s in st]
    assert keys == ["car_head", "car_features", "car_outline", "car_eyes", "car_nose_mouth",
                    "car_strands", "car_hatch", "finish"], keys
    dark = [int((cv2.cvtColor(s.image, cv2.COLOR_BGR2GRAY) < 128).sum()) for s in st[2:7]]
    assert dark == sorted(dark), dark
    assert [s.key for s in build_stages("caricature", crop, "car_lines", 0.5)][-2] == "car_strands"
    assert [s.key for s in build_stages("caricature", crop, "car_shapes", 0.5)] == ["car_head", "car_features", "finish"]


def test_no_face_means_a_message_not_a_crash():
    rng = np.random.default_rng(1)
    noise = rng.integers(0, 255, (400, 300, 3), dtype=np.uint8)
    C._cache.clear()
    for key in MODES["caricature"].styles:
        out = render(key, noise, 0.5)
        assert out.shape == noise.shape and out.dtype == np.uint8
    st = build_stages("caricature", noise, "car_hatch", 0.5)
    assert [s.key for s in st] == ["finish"]


def test_without_the_segmentation_model_it_still_draws_the_face(monkeypatch):
    """The segmentation model is a download like the others. Without it there is no hair,
    but the face is drawn."""
    from sketch_assistant.core import landmarks
    if not landmarks.mesh_available():
        pytest.skip("face mesh not downloaded")
    monkeypatch.setattr(C, "_seg_net", lambda: None)
    C._cache.clear()
    D = C.drawing(_crop(FACES[0]), 0.5)
    assert D.found and not D.lines["hair"] and D.lines["eyes_upper"]
    C._cache.clear()


def test_the_slider_says_exaggeration_in_caricature_mode():
    assert MODES["caricature"].slider_labels == ("Less exaggerated", "More exaggerated")
    assert all(m.slider_labels == ("Less detail", "More detail") for k, m in MODES.items() if k != "caricature")


def test_a_missing_model_is_named_not_reported_as_no_face(monkeypatch):
    """A tester saw "No face found" on a photo whose face Caricature mode had just boxed.
    The face had been found; it was the face mesh that couldn't be used. Without it the
    picture and the status line now say which model is missing and how to get it.
    Control: before, both said there was no face."""
    from sketch_assistant.core import landmarks
    monkeypatch.setattr(landmarks, "MESH_PATH", landmarks.MESH_PATH.with_name("not_there.tflite"))
    C._cache.clear()
    crop = _crop(FACES[0]) if detect_faces(load_image(str(FX / FACES[0]))) else None
    if crop is None:
        pytest.skip("no face detector")
    assert "not_there.tflite" in C.why_not(crop) and "No face" not in C.why_not(crop)
    assert "not_there.tflite" in MODES["caricature"].requires()
    out = render("car_hatch", crop, 0.5)
    assert out.shape == crop.shape
    C._cache.clear()


def test_the_eyes_brows_and_nose_carry_detail(monkeypatch):
    """A tester found the first version's eyes "creepy" and the nose too simple, and
    asked for lashes, brow lines and nose lines like the app icon. Measured as ink round
    each eye and the nose: with the details (lashes, crease, iris fibres and catchlight,
    hair-stroke brows, the wing curls and the side line) at least half as much again as
    the plain lids and dots that were there before. Control: with the details switched
    off the ratio is 1 and this fails."""
    _models()
    crop = _crop(FACES[0])
    D = C.drawing(crop, 0.35)
    full = _ink(C.paint(D, parts={"eyes", "brows", "nose"}, hatch=False))
    monkeypatch.setattr(C, "_eye_details", lambda out, u, lo, th: C._poly(out, u, C.INK, th + 1))
    monkeypatch.setattr(C, "_iris", lambda out, x, y, r, th: cv2.circle(out, (int(x), int(y)), int(r), C.INK, th))
    plain_lines = dict(D.lines, nose_side=[], nose=[])
    plain = _ink(C.paint(C.Drawing(D.shape, True, plain_lines, D.irises, th=D.th), parts={"eyes", "nose"}, hatch=False))
    assert full.sum() > 1.5 * plain.sum(), (full.sum(), plain.sum())
