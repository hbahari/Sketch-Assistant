"""Build a drawing sequence: the sketch as it should look after each stage.

Nothing here does new image processing. Every stage is composed from the existing
renderers in `styles.py` plus the construction lines from `guides.py`:

* complexity comes from the detail slider (a low-detail Line Art is the "big shapes" pass);
* portrait stages reveal one feature at a time through soft masks placed on YuNet's
  landmarks, so the drawing appears the way a person would actually build it;
* object stages are masked to the GrabCut silhouette so the background stays out of
  the early passes.

A stage that would add almost no new ink (ears hidden by hair, say) is dropped, so the
sequence never shows the learner an apparently unchanged picture.
"""
from dataclasses import dataclass

import cv2
import numpy as np

from .guides import OVAL_H, OVAL_RISE, OVAL_W, draw_guides
from .styles import ALL, _silhouette, render

# Families whose finished drawing carries no tone, so a "block in the values" stage
# would show nothing. Keyed by family rather than by style so a new mode inherits it.
NO_SHADING_FAMILIES = {"line", "construct"}
MIN_INK_DENSITY = 0.010      # a stage is dropped only if its region is near-empty


def _shades(style_key):
    return ALL[style_key].family not in NO_SHADING_FAMILIES


def _outline_detail(style_key, detail, floor):
    """How much detail the outline stages carry.

    When the finish is itself an outline, exactly what the slider says -- the outline
    stages are then the finished drawing arriving in pieces, and they must never hold
    more than it will. They used to be held to a floor regardless, so at low detail the
    last outline step showed two or three times the ink of the "finished" drawing after
    it and the sequence appeared to go backwards.

    Under a shaded finish the floor stays: there the outline is scaffolding for tone,
    and a sparse one leaves the feature-by-feature stages with nothing in them.
    """
    return detail if ALL[style_key].family == "line" else max(detail, floor)


@dataclass
class Stage:
    key: str                 # stable id; the step text is keyed off this
    title: str
    image: np.ndarray


@dataclass
class Job:
    """One request for a drawing sequence. Every stage builder takes exactly this, so
    `core/modes.py` can hold a reference to the right builder and call it blind."""
    source_img: np.ndarray
    style_key: str
    detail: float
    landmarks: tuple = ()
    crop_shape: tuple = None
    box: tuple = None
    progress: object = None
    mode: str = ""


def _ink(img):
    return (cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) < 170)


def _fade(img, k):
    """Push an image toward white so earlier work reads as 'already on the paper'."""
    return (255 - (255 - img.astype(np.float32)) * k).astype(np.uint8)


def _under(base, top):
    return np.minimum(base, top)


def _feather(mask, sigma):
    return cv2.GaussianBlur(mask, (0, 0), max(1.0, sigma))


def _apply(art, mask):
    """Show `art` only where mask is set, fading out across the feathered edge."""
    m = (mask.astype(np.float32) / 255)[..., None]
    return (255 - (255 - art.astype(np.float32)) * m).astype(np.uint8)


# --------------------------------------------------------------------------- portraits
def _regions(shape, lm, box):
    """Soft masks for each facial feature, placed on the landmarks."""
    H, W = shape[:2]
    re, le, nose, mr, ml = [np.asarray(p, float) for p in lm]
    eye_mid, mouth_mid = (re + le) / 2, (mr + ml) / 2
    iod = max(np.linalg.norm(le - re), 1.0)          # inter-ocular distance: the unit of a face
    bx, by, bw, bh = box
    ocx, ocy = bx + bw / 2, by + bh / 2 - bh * OVAL_RISE
    oax, oay = bw * OVAL_W / 2, bh * OVAL_H / 2
    blur = iod * 0.10

    def blob(*els):
        m = np.zeros((H, W), np.uint8)
        for c, ax in els:
            cv2.ellipse(m, (int(c[0]), int(c[1])), (int(ax[0]), int(ax[1])), 0, 0, 360, 255, -1)
        return _feather(m, blur)

    # the nose sits between the eye line and the tip; keep it clear of the mouth
    nose_c = eye_mid * 0.30 + nose * 0.70
    ear_y = (eye_mid[1] + nose[1]) / 2
    ring = np.zeros((H, W), np.uint8)
    cv2.ellipse(ring, (int(ocx), int(ocy)), (int(oax), int(oay)), 0, 0, 360, 255, int(max(3, iod * 0.42)))
    return {
        "eyes": blob((re, (iod * .46, iod * .34)), (le, (iod * .46, iod * .34))),
        "nose": blob((nose_c, (iod * .34, iod * .44))),
        "mouth": blob((mouth_mid, (iod * .64, iod * .34))),
        "ears": blob(((ocx - oax * .94, ear_y), (iod * .28, iod * .46)),
                     ((ocx + oax * .94, ear_y), (iod * .28, iod * .46))),
        "contour": _feather(ring, blur),
    }


def _estimate_landmarks(box):
    """Place eyes, nose and mouth from the face box using average proportions.

    Used whenever the detector returns no landmarks -- YuNet below its confidence
    threshold, or the Haar fallback. The feature masks are soft and generous, so an
    approximate position still stages the drawing usefully; without this the sequence
    collapses to construction-then-everything, which is no help to a beginner.
    """
    bx, by, bw, bh = box
    cx = bx + bw / 2
    ocy = by + bh / 2 - bh * OVAL_RISE
    oax, oay = bw * OVAL_W / 2, bh * OVAL_H / 2
    top, hh = ocy - oay, 2 * oay
    ex, mx = oax * 0.47, oax * 0.33
    # same measured proportions as guides._proportional_guides; see the note there
    eye_y, nose_y, mouth_y = top + hh * 0.43, top + hh * 0.64, top + hh * 0.78
    return [(cx - ex, eye_y), (cx + ex, eye_y), (cx, nose_y), (cx - mx, mouth_y), (cx + mx, mouth_y)]


def portrait_stages(job):
    """Reveal one feature at a time. Real landmarks are used when the detector supplies
    them; otherwise they are estimated from the face box so the sequence still works."""
    crop, style_key, detail = job.source_img, job.style_key, job.detail
    lm, crop_shape, box = job.landmarks, job.crop_shape, job.box
    if crop_shape is None or box is None:                    # shouldn't happen; be safe
        h, w = crop.shape[:2]
        crop_shape, box = (h, w), (w * 0.2, h * 0.2, w * 0.6, h * 0.6)
    step = _progress(job.progress, 8)
    has_lm = len(lm) == 5
    art = render("line_art", crop, _outline_detail(style_key, detail, 0.45))        # the outline used for the reveals
    step()
    H, W = art.shape[:2]
    sx, sy = W / crop_shape[1], H / crop_shape[0]
    lm_s = [(p[0] * sx, p[1] * sy) for p in lm] if has_lm else None
    box_s = (box[0] * sx, box[1] * sy, box[2] * sx, box[3] * sy)

    guides = draw_guides(np.full_like(art, 255), "portrait", "line_art", lm, crop_shape, box, crop)
    stages = [Stage("construction", "Construction", guides)]
    step()

    reg = _regions(art.shape, lm_s or _estimate_landmarks(box_s), box_s)
    seen = np.zeros((H, W), np.uint8)
    prev_ink = 0
    for key, title, g_fade in (("eyes", "Eyes and brows", .55), ("nose", "Nose", .50),
                               ("mouth", "Mouth", .45), ("ears", "Ears", .40),
                               ("contour", "Jaw and hairline", .30)):
        cand = np.maximum(seen, reg[key])
        shown = _apply(art, cand)
        ink = _ink(shown).sum()
        step()
        # judge the new region on its own density, not against the whole drawing:
        # on a detailed photo the eyes are a tiny share of total ink but far from empty
        area = max(int((cv2.subtract(cand, seen) > 128).sum()), 1)
        if (ink - prev_ink) / area < MIN_INK_DENSITY:
            continue                                          # nothing visible there on this face
        seen, prev_ink = cand, ink
        stages.append(Stage(key, title, _under(_fade(guides, g_fade), shown)))

    stages.append(Stage("outline", "Complete the outline", _under(_fade(guides, .20), art)))
    step()
    final = render(style_key, crop, detail)
    if _shades(style_key):
        stages.append(Stage("values", "Block in the values",
                            _under(_fade(art, .45), render("value_study", crop, 0.1))))
        step()
    stages.append(Stage("finish", f"Finish in {ALL[style_key].label}", final))
    step()
    return stages


# --------------------------------------------------------------------------- objects
def object_stages(job):
    img, style_key, detail = job.source_img, job.style_key, job.detail
    step = _progress(job.progress, 6)
    art = render("obj_contour", img, _outline_detail(style_key, detail, 0.45))
    step()
    H, W = art.shape[:2]
    sil = _silhouette(cv2.resize(img, (W, H), interpolation=cv2.INTER_AREA))
    inside = np.zeros((H, W), np.uint8)
    cv2.drawContours(inside, [sil], -1, 255, -1)
    soft = _feather(inside, max(2.0, min(H, W) * 0.012))      # keep the background out
    step()

    stages = [Stage("proportion", "Proportion and placement", render("obj_shapes", img, 0.15))]
    edge = np.zeros((H, W), np.uint8)
    cv2.drawContours(edge, [sil], -1, 255, int(max(3, min(H, W) * 0.02)))
    stages.append(Stage("silhouette", "Silhouette", _apply(art, _feather(edge, 4))))
    step()
    stages.append(Stage("contours", "Inner contours", _apply(art, soft)))
    step()
    if _shades(style_key):
        stages.append(Stage("values", "Light and shadow",
                            _under(_fade(_apply(art, soft), .45),
                                   _apply(render("obj_value", img, 0.1), soft))))
        step()
    stages.append(Stage("finish", f"Finish in {ALL[style_key].label}", render(style_key, img, detail)))
    step()
    return stages


# --------------------------------------------------------------------------- hands
# A hand is taught structure-first: the palm block and the axes, then the volume on those
# axes, and only then the real outline. Each level is one more pass of the Construction
# renderer, which already knows how to draw them (see styles.construction).
HAND_LEVELS = ((0.10, "hand_block", "Palm block and axes"),
               (0.45, "hand_joints", "Knuckles and joints"),
               (0.85, "hand_volumes", "Finger volumes"))


def hand_stages(job):
    """Palm block, then joints, then volumes, then the outline over the construction."""
    img, style_key, detail = job.source_img, job.style_key, job.detail
    step = _progress(job.progress, len(HAND_LEVELS) + 4)
    stages = []
    for d, key, title in HAND_LEVELS:
        stages.append(Stage(key, title, render("hand_construct", img, d)))
        step()
    scaffold = stages[-1].image
    # the hand styles are masked to the hand, so the outline and the tones come back
    # without the table or the wall in them -- the same separation the step text asks for
    art = render("hand_contour", img, _outline_detail(style_key, detail, 0.45))
    step()
    if art.shape[:2] != scaffold.shape[:2]:                   # renderers agree, but don't assume
        scaffold = cv2.resize(scaffold, (art.shape[1], art.shape[0]))
    stages.append(Stage("hand_outline", "Draw the real outline", _under(_fade(scaffold, .25), art)))
    step()
    if _shades(style_key):
        stages.append(Stage("values", "Light and shadow",
                            _under(_fade(art, .45), render("hand_value", img, 0.1))))
        step()
    stages.append(Stage("finish", f"Finish in {ALL[style_key].label}", render(style_key, img, detail)))
    step()
    return stages


# --------------------------------------------------------------------------- figures
# Each level is one more pass of a renderer that already knows how to draw it, the same
# way the hand ladder works.
BODY_LEVELS = (("body_gesture", 0.10, "body_action", "Line of action"),
               ("body_gesture", 0.60, "body_tilts", "Shoulders and hips"),
               ("body_mannequin", 0.35, "body_masses", "Ribcage and pelvis"),
               ("body_mannequin", 0.80, "body_limbs", "Limbs as volumes"))


def body_stages(job):
    """Gesture first, then structure, then the real outline -- the order a figure class
    teaches, and the reason Posture mode exists in an abstract form at all."""
    img, style_key, detail = job.source_img, job.style_key, job.detail
    step = _progress(job.progress, len(BODY_LEVELS) + 4)
    stages = []
    for style, d, key, title in BODY_LEVELS:
        stages.append(Stage(key, title, render(style, img, d)))
        step()
    art = render("body_contour", img, _outline_detail(style_key, detail, 0.35))
    step()
    scaffold = stages[-1].image
    if scaffold.shape[:2] != art.shape[:2]:
        scaffold = cv2.resize(scaffold, (art.shape[1], art.shape[0]))
    stages.append(Stage("body_outline", "Draw the real outline",
                        _under(_fade(scaffold, .22), art)))
    step()
    if _shades(style_key):
        stages.append(Stage("values", "Light and shadow",
                            _under(_fade(art, .45), render("body_value", img, 0.1))))
        step()
        # Flat tone to finished rendering is too big a jump to show as one step: the
        # learner can see the result but not how the pencil got there. The hatching stage
        # is the missing middle -- the same tones, built from strokes they can copy.
        stages.append(Stage("body_hatch", "Build the tone in strokes",
                            render("body_formhatch", img, 0.45)))
        step()
    stages.append(Stage("finish", f"Finish in {ALL[style_key].label}", render(style_key, img, detail)))
    step()
    return stages


# --------------------------------------------------------------------------- eyes
# The longest ladder in the app, deliberately. An eye is small, everyone looks straight at
# it, and the distance from an outline to a convincing rendering is where beginners give
# up -- so that distance is cut into steps small enough to copy one at a time.
EYE_LEVELS = ((0.20, "eye_envelope", "Width, height and tilt"),
              (0.45, "eye_ball", "The ball and the lids"),
              (0.70, "eye_lids", "Iris, pupil and lid thickness"),
              (1.00, "eye_plan", "Plan the light"))


def _eye_masks(eye, shape):
    """Soft masks for the parts of an eye that are drawn at different times."""
    H, W = shape[:2]
    r = float(eye.r)
    opening = np.zeros((H, W), np.uint8)
    cv2.fillPoly(opening, [eye.opening], 255)
    ys, xs = np.mgrid[0:H, 0:W]
    disc = (((xs - eye.iris[0]) ** 2 + (ys - eye.iris[1]) ** 2) <= r * r).astype(np.uint8) * 255
    k = lambda f: cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * int(max(1, r * f)) + 1,) * 2)
    near = cv2.dilate(opening, k(0.45))
    if eye.crease is not None:
        cv2.polylines(near, [np.round(eye.crease).astype(np.int32)], False, 255, int(max(3, r * 0.5)))
    # lashes grow out of the lid margins; the brow is whatever lies well above the lid
    fringe = cv2.subtract(cv2.dilate(opening, k(0.95)), cv2.erode(opening, k(0.12)))
    brow_y = int(max(0, eye.upper[:, 1].min() - r * 1.1))
    fringe[:brow_y] = 255
    f = max(2.0, r * 0.08)
    return {"near": _feather(near, f), "iris": _feather(cv2.bitwise_and(disc, opening), f * 0.6),
            "fringe": _feather(fringe, f)}


def _blend(base, top, mask):
    """`top` where the mask is set, `base` elsewhere, mixing across the feathered edge."""
    m = (mask.astype(np.float32) / 255)[..., None]
    return (base.astype(np.float32) * (1 - m) + top.astype(np.float32) * m).astype(np.uint8)


def eye_stages(job):
    """Construction in four passes, the outline in two, then tone in five.

    The tonal half is only shown for Photorealism. Value Study and Cross-Hatch finish in
    flat blocks and in strokes, and walking them through three stages of blending first
    would teach a method their own finish then contradicts.

    Every tonal stage is the finished rendering with something still missing, at the
    detail the slider is set to, so the sequence converges on the finish instead of
    passing through pictures the finish never contained.
    """
    from .eyes import analyze
    from .styles import _prep, soft_tone
    img, style_key, detail = job.source_img, job.style_key, job.detail
    blended = style_key == "eye_realistic"
    step = _progress(job.progress, len(EYE_LEVELS) + (9 if blended else 5))
    stages = []
    for d, key, title in EYE_LEVELS:
        stages.append(Stage(key, title, render("eye_construct", img, d)))
        step()
    scaffold = stages[-2].image                       # the structure, without the lash plan
    art = render("eye_contour", img, _outline_detail(style_key, detail, 0.4))
    step()
    masks = _eye_masks(analyze(_prep(img)), art.shape)
    stages.append(Stage("eye_outline", "Lids, iris and crease", _under(_fade(scaffold, .25), _apply(art, masks["near"]))))
    stages.append(Stage("eye_surround", "Brow and the skin around", _under(_fade(scaffold, .12), art)))
    step()
    if _shades(style_key):
        values = _under(_fade(art, .40), render("eye_value", img, 0.15))
        stages.append(Stage("values", "Block in the values", values))
        step()
    if blended:
        real = render(style_key, img, detail)
        loose, tight = soft_tone(img, 0.3), soft_tone(img, 0.85)
        step()
        stages.append(Stage("eye_blend", "Blend the tones together", loose))
        stages.append(Stage("eye_iris_tone", "Draw the iris", _blend(loose, real, masks["iris"])))
        step()
        stages.append(Stage("eye_form", "Model the lids and the corners", _blend(tight, real, masks["iris"])))
        step()
        # the hairs come from the finished rendering itself, let through only along the
        # lid margins and the brow, so this stage cannot show a lash the finish lacks
        stages.append(Stage("eye_lashes", "Lashes and brow hairs",
                            _blend(_blend(tight, real, masks["iris"]), real, masks["fringe"])))
        step()
    stages.append(Stage("finish", f"Finish in {ALL[style_key].label}", render(style_key, img, detail)))
    step()
    return stages


def _progress(cb, n):
    state = {"i": 0}

    def tick():
        state["i"] += 1
        if cb:
            cb(min(state["i"], n), n)
    return tick


def contact_sheet(stages, cell=420, cols=3):
    """All stages on one printable sheet."""
    rows = (len(stages) + cols - 1) // cols
    pad, head = 10, 34
    sheet = np.full((rows * (cell + head + pad) + pad, cols * (cell + pad) + pad, 3), 255, np.uint8)
    for i, st in enumerate(stages):
        r, c = divmod(i, cols)
        y = pad + r * (cell + head + pad)
        x = pad + c * (cell + pad)
        cv2.putText(sheet, f"{i + 1}.  {st.title}", (x + 2, y + 23),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (30, 30, 30), 1, cv2.LINE_AA)
        cv2.line(sheet, (x, y + head - 5), (x + cell, y + head - 5), (205, 205, 205), 1)
        sheet[y + head:y + head + cell, x:x + cell] = cv2.resize(st.image, (cell, cell))
    return sheet
