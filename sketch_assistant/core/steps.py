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

NO_SHADING = {"line_art", "technical", "obj_contour", "obj_shapes"}
MIN_INK_DENSITY = 0.010      # a stage is dropped only if its region is near-empty


@dataclass
class Stage:
    key: str                 # stable id; the step text is keyed off this
    title: str
    image: np.ndarray


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
    eye_y, nose_y, mouth_y = top + hh * 0.45, top + hh * 0.68, top + hh * 0.80
    return [(cx - ex, eye_y), (cx + ex, eye_y), (cx, nose_y), (cx - mx, mouth_y), (cx + mx, mouth_y)]


def portrait_stages(crop, style_key, detail, lm, crop_shape, box, progress=None):
    """Reveal one feature at a time. Real landmarks are used when the detector supplies
    them; otherwise they are estimated from the face box so the sequence still works."""
    step = _progress(progress, 8)
    has_lm = len(lm) == 5
    art = render("line_art", crop, max(detail, 0.45))        # the outline used for the reveals
    step()
    H, W = art.shape[:2]
    sx, sy = W / crop_shape[1], H / crop_shape[0]
    lm_s = [(p[0] * sx, p[1] * sy) for p in lm] if has_lm else None
    box_s = (box[0] * sx, box[1] * sy, box[2] * sx, box[3] * sy)

    guides = draw_guides(np.full_like(art, 255), "line_art", lm, crop_shape, box)
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
    if style_key not in NO_SHADING:
        stages.append(Stage("values", "Block in the values",
                            _under(_fade(art, .45), render("value_study", crop, 0.1))))
        step()
    stages.append(Stage("finish", f"Finish in {ALL[style_key].label}", final))
    step()
    return stages


# --------------------------------------------------------------------------- objects
def object_stages(img, style_key, detail, progress=None):
    step = _progress(progress, 6)
    art = render("obj_contour", img, max(detail, 0.45))
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
    if style_key not in NO_SHADING:
        stages.append(Stage("values", "Light and shadow",
                            _under(_fade(_apply(art, soft), .45),
                                   _apply(render("obj_value", img, 0.1), soft))))
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


def build_stages(mode, source_img, style_key, detail, lm=(), crop_shape=None, box=None, progress=None):
    """Entry point used by the UI. Returns a list of Stage, longest side ~800px."""
    if mode == "object":
        return object_stages(source_img, style_key, detail, progress)
    if crop_shape is None or box is None:                     # shouldn't happen; be safe
        h, w = source_img.shape[:2]
        crop_shape, box = (h, w), (w * 0.2, h * 0.2, w * 0.6, h * 0.6)
    return portrait_stages(source_img, style_key, detail, lm, crop_shape, box, progress)


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
