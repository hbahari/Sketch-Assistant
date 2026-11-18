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
from .styles import ALL, _hatch_rhythm, _silhouette, render, value_levels

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


# --------------------------------------------------------------------------- value key
# What each grey of a Value Study is drawn with, lightest first, by how many greys there
# are. The lightest is always paper: graphite cannot be made lighter than the page, so
# the lightest shapes are saved, not drawn.
VALUE_PENCILS = {3: ("Paper", "HB", "4B"),
                 4: ("Paper", "HB", "2B", "4B-6B"),
                 5: ("Paper", "2H", "HB", "2B", "4B-6B"),
                 6: ("Paper", "2H", "HB", "2B", "4B", "6B"),
                 7: ("Paper", "2H", "H", "HB", "2B", "4B", "6B")}


def _value_key(img, d):
    """The picture with a key underneath: each flat grey it uses, and the pencil for it.

    A Value Study on its own looks like a posterised photo, and a tester asked what it
    was for. The key is the answer in the picture itself: these are the only greys on
    the page, here is what to draw each one with, match them shape by shape.
    """
    H, W = img.shape[:2]
    levels = value_levels(d)[::-1]                        # lightest first, as the key reads
    pencils = VALUE_PENCILS[len(levels)]
    sh = max(70, int(W * 0.17))
    strip = np.full((sh, W, 3), 255, np.uint8)
    fs, th = max(0.42, W / 1300), max(1, W // 500)
    cv2.putText(strip, "Value key: the only greys in the picture",
                (8, int(sh * 0.26)), cv2.FONT_HERSHEY_SIMPLEX, fs, (90, 90, 90), th, cv2.LINE_AA)
    pad, gap = 8, 6
    sw = (W - 2 * pad - gap * (len(levels) - 1)) / len(levels)
    y0, y1 = int(sh * 0.36), sh - 8
    for i, (v, pen) in enumerate(zip(levels, pencils)):
        x0 = int(pad + i * (sw + gap))
        x1 = int(x0 + sw)
        cv2.rectangle(strip, (x0, y0), (x1, y1), (int(v),) * 3, -1)
        cv2.rectangle(strip, (x0, y0), (x1, y1), (150, 150, 150), 1)
        ink = (30, 30, 30) if v > 140 else (245, 245, 245)
        (tw, tht), _ = cv2.getTextSize(pen, cv2.FONT_HERSHEY_SIMPLEX, fs * 1.15, th)
        cv2.putText(strip, pen, (int((x0 + x1 - tw) / 2), int((y0 + y1 + tht) / 2)),
                    cv2.FONT_HERSHEY_SIMPLEX, fs * 1.15, ink, th, cv2.LINE_AA)
    return np.vstack([img, strip])


# --------------------------------------------------------------------------- hatch to realistic
# The shaded styles are not equally hard. Hatching builds tone from separate strokes a
# beginner can see and copy; a realistic finish is continuous tone with highlights, deep
# accents and soft and hard edges, and shown straight after the value blocks it arrives
# as a leap. These stages are the bridge, and the method is a real one: hatch the tones
# in, blend the hatching smooth with a stump, then lift the lights with an eraser and
# deepen the darks. Every stage comes from renderers the app already has, so the
# sequence converges on the finished drawing instead of inventing pictures of its own.
LIGHT_PCT, DARK_PCT = 98.5, 2.5       # percentiles of the finished drawing marked as accents
BLEND_SIGMA = 0.8                     # blur of the blending stump, in stroke spacings
LINE_KEEP = 0.7                       # how strongly the outline shows through the blend
MARK_LIFT, MARK_DARK = (225, 140, 40), (40, 50, 200)   # BGR: blue = eraser, red = press harder


def _blend_hatching(hatch, d, real, art=None):
    """The hatching after a blending stump: strokes merged into tone, outline kept.

    Blurred by most of a stroke spacing, so the strokes and the moire between crossing
    layers both go -- at under half a spacing a faint criss-cross still showed. On its
    own that much blur turns the drawing into an out-of-focus photograph, the complaint
    that ended the Soft Tone style, so the outline is laid back over the smooth tone:
    blending moves graphite about, it does not rub out the drawing.

    Then one smooth tone curve brings its average to the finished drawing's, so the next
    two stages change only what they are about. Measured on one photo per mode, that is
    a correction of 1 to 8 grey levels either way; it keeps the blend within one level.
    A single gamma rather than quantile-by-quantile matching, which was tried first and
    stretched the hatching's few separate layers into hard bands, like a stencil.
    """
    g = cv2.cvtColor(hatch, cv2.COLOR_BGR2GRAY).astype(np.float32)
    sp, _ = _hatch_rhythm(g.shape[1], d)
    tone = cv2.GaussianBlur(g, (0, 0), sp * BLEND_SIGMA) / 255.0
    # where the finish leaves bare paper round the subject (Hands, Posture), so does the
    # blend -- otherwise the blur bleeds grey past the outline and tints the whole page
    paper = _feather(_paper(real).astype(np.uint8) * 255, max(1.5, min(g.shape) * 0.004)).astype(np.float32) / 255
    lines = np.full(g.shape, 255.0, np.float32)
    if art is not None:
        if art.shape[:2] != g.shape:
            art = cv2.resize(art, (g.shape[1], g.shape[0]), interpolation=cv2.INTER_AREA)
        lines = cv2.cvtColor(_fade(art, LINE_KEEP), cv2.COLOR_BGR2GRAY).astype(np.float32)

    def compose(gamma):
        t = 255.0 * tone ** gamma
        return np.minimum(t * (1 - paper) + 255.0 * paper, lines)

    # matched on the finished composite, outline and paper included: matched before the
    # outline went on, the blend came out about fifteen levels darker than the finish
    # ...and with the warm tint of graphite on paper counted in, on the drawing but not on
    # the bare paper round it: matched before the tint, the blend came out 4% too dark
    tint = np.array([0.94, 0.96, 0.97], np.float32)
    shade = float(tint @ [0.114, 0.587, 0.299]) * (1 - paper) + paper
    target = float(cv2.cvtColor(real, cv2.COLOR_BGR2GRAY).mean())
    lo, hi = 0.3, 6.0
    for _ in range(25):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if float((compose(mid) * shade).mean()) > target else (lo, mid)
    out = compose((lo + hi) / 2)
    grain = cv2.GaussianBlur(np.random.default_rng(1).normal(0, 6, g.shape).astype(np.float32), (0, 0), 0.8)
    out = np.clip(out + grain * (1 - out / 255.0) * (1 - paper), 0, 255)
    colour = tint * (1 - paper)[..., None] + paper[..., None]
    return np.clip(out[..., None] * colour, 0, 255).astype(np.uint8)


def _paper(real):
    """Where the finished drawing is bare paper round the subject: white areas joined to
    the edge of the picture. White inside the subject -- a highlight -- does not count."""
    R = cv2.cvtColor(real, cv2.COLOR_BGR2GRAY)
    white = (R >= 253).astype(np.uint8)
    n, lab = cv2.connectedComponents(white, connectivity=8)
    edge = np.unique(np.r_[lab[0], lab[-1], lab[:, 0], lab[:, -1]])
    return np.isin(lab, edge[edge > 0])


def _accent_shapes(m, max_frac, min_frac=0.0002, keep=8):
    """The small, separate shapes in a boolean mask: (filled uint8 mask, their contours).

    Capped in size because a big dark area is a value shape, already blocked in two steps
    earlier; an accent is the small darkest-dark or whitest-white inside it.
    """
    m = cv2.morphologyEx(m.astype(np.uint8) * 255, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(m, connectivity=8)
    ok = [k for k in range(1, n) if min_frac * m.size <= st[k, cv2.CC_STAT_AREA] <= max_frac * m.size]
    ok = sorted(ok, key=lambda k: -st[k, cv2.CC_STAT_AREA])[:keep]
    out = np.isin(lab, ok).astype(np.uint8) * 255
    out = cv2.dilate(out, np.ones((5, 5), np.uint8))   # a little room round each, to draw into
    cnts, _ = cv2.findContours(out, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    return out, cnts


def _lights_and_darks(blended, real):
    """Mark the finished drawing's whitest small shapes (keep them clean or lift them
    with an eraser) and its darkest small shapes (press to full dark), and bring both in.

    Taken from the finish alone, not from how it differs from the blend. Differences
    were tried first and marked half the picture, because any tonal drift between two
    renderings shows up as a "difference". The brightest and darkest accents are what
    this step of a drawing is actually about. Returns (marked image, unmarked image).
    """
    R = cv2.cvtColor(real, cv2.COLOR_BGR2GRAY)
    subject = ~_paper(real)                            # not the bare paper round a masked subject
    vals = R[subject] if subject.any() else R.ravel()
    light = (R >= np.percentile(vals, LIGHT_PCT)) & subject
    dark = R <= np.percentile(vals, DARK_PCT)
    lights, lc = _accent_shapes(light, max_frac=0.015)
    darks, dc = _accent_shapes(dark, max_frac=0.03)
    m = _feather(cv2.max(lights, darks), max(1.5, min(R.shape) * 0.006))
    clean = _blend(blended, real, m)
    marked = clean.copy()
    th = max(1, R.shape[1] // 420)
    cv2.drawContours(marked, lc, -1, MARK_LIFT, th, cv2.LINE_AA)
    cv2.drawContours(marked, dc, -1, MARK_DARK, th, cv2.LINE_AA)
    return marked, clean


def _hatch_to_real(img, hatch_key, real, detail, hatch=None, art=None):
    """The bridge stages, ending one step short of the finish.

    `hatch` is passed in where the ladder already has a hatching stage of its own (Posture
    builds one for every shaded finish); otherwise it is rendered and shown here.
    Returns (stages, the clean picture the last of them shows) so a ladder with more to
    add -- Eyes does -- can carry on from it.
    """
    stages = []
    d = detail
    if hatch is None:
        hatch = render(hatch_key, img, detail)
        stages.append(Stage("hatch_tone", "Build the tone in hatching", hatch))
    else:
        d = 0.45                                       # the detail that stage was drawn at
    if hatch.shape[:2] != real.shape[:2]:
        hatch = cv2.resize(hatch, (real.shape[1], real.shape[0]))
    blended = _blend_hatching(hatch, d, real, art)
    stages.append(Stage("hatch_blend", "Blend the hatching smooth", blended))
    marked, clean = _lights_and_darks(blended, real)
    stages.append(Stage("lights_darks", "Lift the lights, deepen the shadows", marked))
    return stages, clean


def _blend(base, top, mask):
    """`top` where the mask is set, `base` elsewhere, mixing across the feathered edge."""
    m = (mask.astype(np.float32) / 255)[..., None]
    return (base.astype(np.float32) * (1 - m) + top.astype(np.float32) * m).astype(np.uint8)


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
                            _value_key(_under(_fade(art, .45), render("value_study", crop, 0.1)), 0.1)))
        step()
    if ALL[style_key].family == "real":
        stages += _hatch_to_real(crop, "crosshatch", final, detail, art=art)[0]
        step()
    stages.append(Stage("finish", f"Finish in {ALL[style_key].label}", _finish(final, style_key, detail)))
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
    final = render(style_key, img, detail)
    if _shades(style_key):
        stages.append(Stage("values", "Light and shadow",
                            _value_key(_under(_fade(_apply(art, soft), .45),
                                              _apply(render("obj_value", img, 0.1), soft)), 0.1)))
        step()
    if ALL[style_key].family == "real":
        stages += _hatch_to_real(img, "obj_hatch", final, detail, art=_apply(art, soft))[0]
        step()
    stages.append(Stage("finish", f"Finish in {ALL[style_key].label}", _finish(final, style_key, detail)))
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
    final = render(style_key, img, detail)
    if _shades(style_key):
        stages.append(Stage("values", "Light and shadow",
                            _value_key(_under(_fade(art, .45), render("hand_value", img, 0.1)), 0.1)))
        step()
    if ALL[style_key].family == "real":
        stages += _hatch_to_real(img, "hand_hatch", final, detail, art=art)[0]
        step()
    stages.append(Stage("finish", f"Finish in {ALL[style_key].label}", _finish(final, style_key, detail)))
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
    final = render(style_key, img, detail)
    if _shades(style_key):
        stages.append(Stage("values", "Light and shadow",
                            _value_key(_under(_fade(art, .45), render("body_value", img, 0.1)), 0.1)))
        step()
        # Flat tone to finished rendering is too big a jump to show as one step: the
        # learner can see the result but not how the pencil got there. The hatching stage
        # is the missing middle -- the same tones, built from strokes they can copy.
        hatch = render("body_formhatch", img, 0.45)
        stages.append(Stage("body_hatch", "Build the tone in strokes", hatch))
        step()
        if ALL[style_key].family == "real":
            stages += _hatch_to_real(img, "body_formhatch", final, detail, hatch=hatch, art=art)[0]
            step()
    stages.append(Stage("finish", f"Finish in {ALL[style_key].label}", _finish(final, style_key, detail)))
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


def eye_stages(job):
    """Construction in four passes, the outline in two, then the tone.

    For Photorealism the tone comes in the most steps of any ladder: flat values, the same
    tones hatched, the hatching blended, lights lifted and darks deepened, then the iris,
    the lids and corners, and the lashes. Value Study and Cross-Hatch stop at their own
    kind of tone, since walking them through blending first would teach a method their
    finish then contradicts.

    Every tonal stage from the blend on is the finished rendering with something still
    missing, so the sequence converges on the finish instead of passing through pictures
    the finish never contained.
    """
    from .eyes import analyze
    from .styles import _prep
    img, style_key, detail = job.source_img, job.style_key, job.detail
    realistic = ALL[style_key].family == "real"
    step = _progress(job.progress, len(EYE_LEVELS) + (9 if realistic else 5))
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
    final = render(style_key, img, detail)
    if _shades(style_key):
        values = _under(_fade(art, .40), render("eye_value", img, 0.15))
        stages.append(Stage("values", "Block in the values", _value_key(values, 0.15)))
        step()
    if realistic:
        bridge, base = _hatch_to_real(img, "eye_hatch", final, detail, art=art)
        stages += bridge
        step()
        with_iris = _blend(base, final, masks["iris"])
        stages.append(Stage("eye_iris_tone", "Draw the iris", with_iris))
        step()
        with_lids = _blend(with_iris, final, masks["near"])
        stages.append(Stage("eye_form", "Model the lids and the corners", with_lids))
        step()
        # the hairs come from the finished rendering itself, let through only along the
        # lid margins and the brow, so this stage cannot show a lash the finish lacks
        stages.append(Stage("eye_lashes", "Lashes and brow hairs", _blend(with_lids, final, masks["fringe"])))
        step()
    stages.append(Stage("finish", f"Finish in {ALL[style_key].label}", _finish(final, style_key, detail)))
    step()
    return stages


# --------------------------------------------------------------------------- noses
# As long as the eye ladder, for the same reason, and with the same shape: structure in
# four passes, the outline in two, then the tone. A nose is drawn far more with tone than
# with line, so for Photorealism the tonal half carries most of the lesson.
NOSE_LEVELS = ((0.20, "nose_envelope", "Length, width and tilt"),
               (0.45, "nose_wedge", "The wedge: front, sides and base"),
               (0.70, "nose_balls", "Tip, wings and nostrils"),
               (1.00, "nose_plan", "Plan the light"))


def _nose_masks(n, shape):
    """Soft masks for the parts of a nose that are drawn at different times: the base
    (nostrils, wings and the shadow under the nose) and the planes (bridge and sides)."""
    H, W = shape[:2]
    P = lambda q: (int(round(q[0])), int(round(q[1])))
    w, s = n.width, n.spacing
    base = np.zeros((H, W), np.uint8)
    cv2.ellipse(base, P(n.along((n.half_right - n.half_left) / 2, 0.2 * s)),
                (int(0.62 * w), int(0.55 * s)), n.tilt, 0, 360, 255, -1)
    cv2.ellipse(base, P(n.along(0, -0.35 * s)), (int(0.55 * w), int(0.32 * s)), n.tilt, 0, 360, 255, -1)
    planes = np.zeros((H, W), np.uint8)
    up = lambda q, dy: (q[0] + dy * (n.along(0, 1)[0] - n.cx), q[1] + dy * (n.along(0, 1)[1] - n.base_y))
    poly = [up(n.radix, 0), n.along(-n.half_left * 1.1, 0.3 * s), n.along(n.half_right * 1.1, 0.3 * s)]
    poly = [(n.radix[0] - 0.25 * w, n.radix[1]), (n.radix[0] + 0.25 * w, n.radix[1])] + poly[2:] + poly[1:2]
    cv2.fillPoly(planes, [np.round(poly).astype(np.int32)], 255)
    planes = cv2.subtract(planes, base)
    f = max(2.0, 0.12 * s)
    return {"base": _feather(base, f), "planes": _feather(planes, f)}


def nose_stages(job):
    """Construction in four passes, the outline in two, then the tone.

    For Photorealism: flat values, the shared bridge from hatching (hatch, blend, lights
    and darks), then the bridge and side planes, then the nostrils and the shadow under
    the nose, then the finish -- thirteen stages. Value Study and Cross-Hatch stop at their
    own kind of tone, as in the other modes.
    """
    from .noses import analyze
    from .styles import _prep
    img, style_key, detail = job.source_img, job.style_key, job.detail
    realistic = ALL[style_key].family == "real"
    step = _progress(job.progress, len(NOSE_LEVELS) + (8 if realistic else 5))
    stages = []
    for d, key, title in NOSE_LEVELS:
        stages.append(Stage(key, title, render("nose_construct", img, d)))
        step()
    scaffold = stages[-2].image                       # the structure, without the light plan
    art = render("nose_contour", img, _outline_detail(style_key, detail, 0.4))
    step()
    if scaffold.shape[:2] != art.shape[:2]:
        scaffold = cv2.resize(scaffold, (art.shape[1], art.shape[0]))
    masks = _nose_masks(analyze(_prep(img)), art.shape)
    # the lines a nose really has are round the nostrils and the wings; the sides of the
    # bridge have none, which is the first thing this stage teaches
    stages.append(Stage("nose_outline", "Nostrils and wings", _under(_fade(scaffold, .25), _apply(art, masks["base"]))))
    stages.append(Stage("nose_surround", "Bridge, brows and cheeks", _under(_fade(scaffold, .12), art)))
    step()
    final = render(style_key, img, detail)
    if _shades(style_key):
        values = _under(_fade(art, .40), render("nose_value", img, 0.15))
        stages.append(Stage("values", "Block in the values", _value_key(values, 0.15)))
        step()
    if realistic:
        bridge, base = _hatch_to_real(img, "nose_hatch", final, detail, art=art)
        stages += bridge
        step()
        with_planes = _blend(base, final, masks["planes"])
        stages.append(Stage("nose_planes", "Model the bridge and sides", with_planes))
        step()
        stages.append(Stage("nose_base", "Nostrils and the shadow below", _blend(with_planes, final, masks["base"])))
        step()
    stages.append(Stage("finish", f"Finish in {ALL[style_key].label}", _finish(final, style_key, detail)))
    step()
    return stages


def _finish(final, style_key, detail):
    """The finished drawing; a Value Study keeps its key, since that is where it is used."""
    return _value_key(final, detail) if ALL[style_key].family == "value" else final


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


# --------------------------------------------------------------------------- caricature
def caricature_stages(job):
    """Shapes first, then the lines one feature at a time over the fading construction.

    Light Hatching: head, features, outline, eyes, nose and mouth, hair, hatching, finish
    -- eight stages. Clean Lines skips the hatching. Shapes stops at its own drawing. The
    exaggeration (the slider) is the same in every stage, so the proportions the first
    stage sets up are the ones the last one keeps.
    """
    from . import caricature as C
    img, style_key, detail = job.source_img, job.style_key, job.detail
    D = C.drawing(img, detail)
    final = render(style_key, img, detail)
    if not D.found:
        return [Stage("finish", "No caricature", final)]
    shapes_only = style_key == "car_shapes"
    hatched = style_key == "car_hatch"
    step = _progress(job.progress, 3 if shapes_only else (8 if hatched else 7))
    head = C.paint_construction(D, level=1)
    step()
    feats = C.paint_construction(D, level=2)
    step()
    stages = [Stage("car_head", "Head shape and the guide lines", head),
              Stage("car_features", "Place the features as shapes", feats)]
    if shapes_only:
        stages.append(Stage("finish", f"Finish in {ALL[style_key].label}", final))
        step()
        return stages
    under = _fade(feats, .45)
    order = [("car_outline", "Face, chin and hair outline", {"face", "chin", "hair"}),
             ("car_eyes", "Eyes and brows", {"face", "chin", "hair", "eyes", "brows"}),
             ("car_nose_mouth", "Nose and mouth", {"face", "chin", "hair", "eyes", "brows", "nose", "lips"}),
             ("car_strands", "A few strands of hair", {"face", "chin", "hair", "eyes", "brows", "nose", "lips", "strands"})]
    for key, title, parts in order:
        stages.append(Stage(key, title, C.paint(D, parts=parts, hatch=False, base=under)))
        step()
    if hatched:
        stages.append(Stage("car_hatch", "Light hatching in the shadows",
                            C.paint(D, hatch=True, base=_fade(feats, .2))))
        step()
    stages.append(Stage("finish", f"Finish in {ALL[style_key].label}", final))
    step()
    return stages
