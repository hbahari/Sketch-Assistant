import numpy as np
import pytest
from sketch_assistant.core.faces import Face, crop_face, crop_info, detect_faces
from sketch_assistant.core.guides import draw_guides
from sketch_assistant.core.modes import MODES
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
    crop, lm, box = crop_info(photo, f)
    assert crop.size > 0 and len(lm) == 5 and crop_face(photo, f).shape == crop.shape
    bx, by, bw, bh = box
    assert (bw, bh) == (f.w, f.h) and bx >= 0 and by >= 0


def test_guides_with_and_without_landmarks(photo):
    sk = render("line_art", photo)
    lm = ((100, 120), (180, 110), (140, 160), (110, 200), (170, 195))
    assert draw_guides(sk, "portrait", "line_art", lm, photo.shape[:2]).shape == sk.shape
    assert draw_guides(sk, "portrait", "line_art", lm, photo.shape[:2], (100, 100, 80, 80)).shape == sk.shape
    assert draw_guides(sk, "portrait", "line_art").shape == sk.shape
    assert draw_guides(sk, "object", "obj_shapes").shape == sk.shape
    assert draw_guides(sk, "hands", "hand_contour", source_img=photo).shape == sk.shape


@pytest.mark.parametrize("mode", list(MODES))
def test_every_mode_renders_guides_for_every_style(mode, photo):
    """Every mode x every style must draw guides without raising, since the guide page
    lets you switch styles freely once a photo is loaded."""
    for key in MODES[mode].styles:
        sk = render(key, photo, 0.5)
        out = draw_guides(sk, mode, key, (), photo.shape[:2], None, photo)
        assert out.shape == sk.shape and out.dtype == np.uint8


# ---- drawing steps -----------------------------------------------------------------
def test_steps_portrait_with_landmarks(photo):
    from sketch_assistant.core.modes import build_stages
    from sketch_assistant.core.steps import contact_sheet
    from sketch_assistant.data.steps_text import step_markup
    h, w = photo.shape[:2]
    P = lambda fx, fy: (fx * w, fy * h)
    lm = (P(.37, .42), P(.66, .42), P(.50, .57), P(.41, .71), P(.60, .71))
    box = (w * .2, h * .2, w * .6, h * .6)
    st = build_stages("portrait", photo, "photoreal", 0.5, lm, photo.shape[:2], box)
    keys = [s.key for s in st]
    assert keys[0] == "construction" and keys[-1] == "finish"
    assert all(s.image.ndim == 3 and s.image.dtype == np.uint8 for s in st)
    assert all(step_markup(s.key, "photoreal") for s in st)      # every stage has text
    assert contact_sheet(st, cell=80, cols=3).ndim == 3


def test_steps_skip_shading_for_line_styles(photo):
    from sketch_assistant.core.modes import build_stages
    box = (20, 20, 100, 100)
    st = build_stages("portrait", photo, "line_art", 0.5, (), photo.shape[:2], box)
    assert "values" not in [s.key for s in st]                   # line art has no shading pass


def test_steps_object(photo):
    from sketch_assistant.core.modes import build_stages
    from sketch_assistant.data.steps_text import step_markup
    st = build_stages("object", photo, "obj_realistic", 0.5)
    assert [s.key for s in st][0] == "proportion"
    assert all(step_markup(s.key, "obj_realistic") for s in st)


@pytest.fixture
def face_photo():
    """A crude synthetic face: the step generator needs actual features to reveal."""
    import cv2
    img = np.full((400, 320, 3), 235, np.uint8)
    cv2.ellipse(img, (160, 200), (105, 140), 0, 0, 360, (205, 200, 195), -1)   # head
    for ex in (118, 202):                                                      # eyes
        cv2.ellipse(img, (ex, 170), (24, 12), 0, 0, 360, (40, 40, 40), 2)
        cv2.circle(img, (ex, 170), 6, (20, 20, 20), -1)
        cv2.ellipse(img, (ex, 148), (26, 9), 0, 200, 340, (50, 50, 50), 3)     # brows
    cv2.line(img, (160, 185), (152, 232), (70, 70, 70), 2)                     # nose
    cv2.ellipse(img, (160, 238), (12, 7), 0, 0, 180, (60, 60, 60), 2)
    cv2.line(img, (128, 272), (192, 272), (35, 35, 35), 3)                     # mouth
    cv2.ellipse(img, (160, 272), (32, 16), 0, 0, 360, (70, 70, 70), 2)
    for ex in (55, 265):                                                       # ears
        cv2.ellipse(img, (ex, 200), (14, 30), 0, 0, 360, (60, 60, 60), 2)
    cv2.ellipse(img, (160, 110), (100, 60), 0, 180, 360, (45, 45, 45), 3)      # hairline
    return img


def test_steps_work_without_landmarks(face_photo):
    """The detector often returns no landmarks (Haar fallback, or YuNet below threshold).
    The feature stages must still appear - estimated from the box - or the sequence
    collapses to construction-then-everything, which is no use to a learner."""
    from sketch_assistant.core.modes import build_stages
    h, w = face_photo.shape[:2]
    box = (w * .17, h * .17, w * .66, h * .66)
    keys = [s.key for s in build_stages("portrait", face_photo, "photoreal", 0.5, (), face_photo.shape[:2], box)]
    for feature in ("eyes", "nose", "mouth"):
        assert feature in keys, f"{feature} stage missing without landmarks"
    assert len(keys) >= 7


# ---- the mode registry -------------------------------------------------------------
def test_registry_is_self_consistent():
    """Guards the contract every mode must satisfy, so a new subject added to MODES
    cannot half-work: a missing style family or absent step text fails here rather than
    on someone's phone."""
    from sketch_assistant.core.modes import MODES, mode_of_style
    from sketch_assistant.data.tips import tips_markup
    seen = set()
    for key, m in MODES.items():
        assert m.key == key and m.label and m.styles, key
        assert m.default_style in m.styles, key
        if m.detect is not None:                 # a detecting mode needs both status lines
            assert m.found_fmt and m.none_fmt, key
            assert "{n}" in m.found_fmt, key
        for sk, st in m.styles.items():
            assert sk not in seen, f"style {sk} offered by two modes"
            seen.add(sk)
            assert st.family, f"{sk} has no family"
            assert mode_of_style(sk) is m, sk
            assert tips_markup(sk), f"{sk} resolves to no pencil tips"


@pytest.mark.parametrize("mode", list(MODES))
def test_every_mode_builds_a_usable_sequence(mode, hand_photo):
    """Each mode must produce a sequence that starts somewhere, ends at 'finish', and has
    step text for every stage - including stages that fall back to a family entry."""
    from sketch_assistant.core.modes import build_stages
    from sketch_assistant.data.steps_text import step_markup
    h, w = hand_photo.shape[:2]
    box = (w * .2, h * .2, w * .6, h * .6)
    for style in MODES[mode].styles:
        st = build_stages(mode, hand_photo, style, 0.5, (), hand_photo.shape[:2], box)
        keys = [s.key for s in st]
        assert len(st) >= 3, f"{mode}/{style}: only {keys}"
        assert keys[-1] == "finish", f"{mode}/{style}: ends on {keys[-1]}"
        assert len(set(keys)) == len(keys), f"{mode}/{style}: duplicate stage {keys}"
        for s in st:
            assert step_markup(s.key, style), f"{mode}/{style}: no text for stage '{s.key}'"
            assert s.image.ndim == 3 and s.image.dtype == np.uint8


def test_shading_stage_follows_the_family_not_the_mode():
    """'Block in the values' must appear for tonal styles and not for line ones, in every
    mode. Before the family field this was a hand-maintained list of style keys that a new
    mode would silently fall out of."""
    from sketch_assistant.core.modes import MODES, build_stages
    rng = np.random.default_rng(3)
    photo = rng.integers(60, 200, (300, 240, 3), dtype=np.uint8)
    for mode, m in MODES.items():
        for sk, st in m.styles.items():
            keys = [s.key for s in build_stages(mode, photo, sk, 0.5, (), photo.shape[:2],
                                                (40, 40, 160, 200))]
            tonal = st.family not in ("line", "construct")
            assert ("values" in keys) == tonal, f"{mode}/{sk}: values={'values' in keys}"


# ---- hands -------------------------------------------------------------------------
@pytest.fixture
def hand_photo():
    """A synthetic open hand, the same shape tests/test_hands.py checks the geometry on."""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from test_hands import draw_hand
    return draw_hand()


def test_hand_sequence_is_structure_first(hand_photo):
    from sketch_assistant.core.modes import build_stages
    keys = [s.key for s in build_stages("hands", hand_photo, "hand_realistic", 0.5)]
    assert keys[:3] == ["hand_block", "hand_joints", "hand_volumes"]
    assert "hand_outline" in keys and keys[-1] == "finish"


def test_hand_construction_levels_add_ink(hand_photo):
    """The three construction stages must look different, or the learner is shown the
    same picture three times. Measured as ink coverage, which must rise each step."""
    import cv2
    from sketch_assistant.core.styles import render
    from sketch_assistant.core.steps import HAND_LEVELS
    ink = []
    for d, _, _ in HAND_LEVELS:
        g = cv2.cvtColor(render("hand_construct", hand_photo, d), cv2.COLOR_BGR2GRAY)
        ink.append(float((g < 170).mean()))
    assert ink[0] < ink[1] < ink[2], f"construction levels do not build up: {ink}"


def test_hand_styles_survive_a_photo_with_no_hand_in_it(photo):
    """A noise image has no hand. Every hand style must still render rather than raise,
    because nothing stops someone choosing Hands and loading a landscape."""
    from sketch_assistant.core.modes import MODES, build_stages
    for key in MODES["hands"].styles:
        out = render(key, photo, 0.5)
        assert out.ndim == 3 and out.dtype == np.uint8, key
    st = build_stages("hands", photo, "hand_contour", 0.5)
    assert st and st[-1].key == "finish"
