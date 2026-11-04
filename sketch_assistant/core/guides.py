"""Construction lines drawn over a sketch on the drawing-guide page.

One function per subject, all with the same signature so `core/modes.py` can simply hold
a reference to the right one:

    guide(overlay, w, h, th, ctx) -> [(label, x, y), ...]

`ctx` carries whatever the subject needs -- the detector's box and landmarks for a face,
the source photo for a hand -- so adding a subject never changes this module's callers.
"""
from dataclasses import dataclass, field

import cv2
import numpy as np

from .faces import MARGIN

LINE = (230, 120, 40)   # BGR amber
SOFT = (235, 170, 110)


def dashed(img, p1, p2, color, th, dash=14):
    p1, p2 = np.array(p1, float), np.array(p2, float)
    n = max(1, int(np.linalg.norm(p2 - p1) // dash))
    for i in range(0, n, 2):
        a, b = p1 + (p2 - p1) * i / n, p1 + (p2 - p1) * min(i + 1, n) / n
        cv2.line(img, tuple(a.astype(int)), tuple(b.astype(int)), color, th, cv2.LINE_AA)


@dataclass
class Ctx:
    """Everything a guide function might need about the subject in this sketch."""
    source_img: np.ndarray = None     # the photo the sketch was made from
    landmarks: tuple = ()             # 5 face landmarks, in source-image pixels
    crop_shape: tuple = None          # (h, w) of the source, for scaling to the sketch
    box: tuple = None                 # detector box, in source-image pixels
    scale: tuple = field(default=(1.0, 1.0))   # filled in by draw_guides


# The oval is the skull. It is sized from the detector's face box rather than from a
# multiple of the eye-to-mouth distance: that multiple assumes average proportions and
# is visibly wrong on faces with a beard, a long jaw or an unusual eye-to-mouth gap.
# These factors map a YuNet/Haar box onto the skull outline.
OVAL_H, OVAL_W, OVAL_RISE = 1.04, 0.90, 0.05


def _oval(ov, box, angle, th, grow=1.0):
    """Draw the skull oval over the detected face box. `grow` widens it for the Haar
    fallback, whose boxes sit tighter on the face than YuNet's."""
    bx, by, bw, bh = box
    cx, cy = bx + bw / 2, by + bh / 2 - bh * OVAL_RISE
    ax1, ax2 = bw * OVAL_W * grow / 2, bh * OVAL_H * grow / 2
    cv2.ellipse(ov, (int(cx), int(cy)), (int(ax1), int(ax2)), angle, 0, 360, LINE, th, cv2.LINE_AA)
    return cx, cy, ax1, ax2


def _landmark_guides(ov, lm, sc, th, box):
    """Tilt-aware face guides: features from YuNet's landmarks, skull oval from the box."""
    re, le, nose, mr, ml = [np.array(p, float) * sc for p in lm]
    eye, mouth = (re + le) / 2, (mr + ml) / 2
    e = (le - re) / np.linalg.norm(le - re)            # direction of the eye line
    angle = float(np.degrees(np.arctan2(e[1], e[0])))
    cx, cy, _, ax2 = _oval(ov, box, angle, th)
    down = np.array([-e[1], e[0]])                     # "down the face", square to the eye line
    centre = np.array([cx, cy])
    top, chin = centre - down * ax2, centre + down * ax2
    dashed(ov, top - down * ax2 * 0.12, chin + down * ax2 * 0.12, LINE, th)   # centre axis
    labels, half = [], np.linalg.norm(mouth - eye) * 2.6
    for name, pt in (("top of head", top), ("eyes", eye), ("nose", nose), ("mouth", mouth), ("chin", chin)):
        a = pt - e * half
        dashed(ov, a, pt + e * half, LINE, th)
        labels.append((name, a[0], a[1]))
    return labels


def _proportional_guides(ov, th, box):
    """Fallback when the detector gives no landmarks: average proportions inside the box."""
    bx, by, bw, bh = box
    cx, cy, _, ax2 = _oval(ov, box, 0.0, th, grow=1.12)
    top, chin = cy - ax2, cy + ax2
    dashed(ov, (cx, top - ax2 * 0.12), (cx, chin + ax2 * 0.12), LINE, th)
    labels, half = [], bw * 0.62
    # Measured, not assumed. Across the 26 portraits in tests/fixtures/portraits that
    # YuNet gives landmarks for, the eyes sit 0.43 of the way down this oval, the nose
    # 0.64 and the mouth 0.78, with a standard deviation of 0.04 or less. The textbook
    # figures that used to be here (0.47 / 0.72 / 0.84) are for the whole skull including
    # the hair, which is not what the detector box spans, and they put the nose and mouth
    # lines down on the neck whenever this fallback ran.
    for name, f in (("top of head", 0.0), ("eyes", 0.43), ("nose", 0.64), ("mouth", 0.78), ("chin", 1.0)):
        y = top + (chin - top) * f
        dashed(ov, (cx - half, y), (cx + half, y), LINE, th)
        labels.append((name, cx - half, y))
    return labels


# --------------------------------------------------------------------------- per subject
def face_guides(ov, w, h, th, ctx):
    """Skull oval, centre axis and the eye / nose / mouth / chin lines."""
    sc = ctx.scale
    if ctx.box is None:     # no detector box: assume the crop is the box plus MARGIN all round
        f = MARGIN / (1 + 2 * MARGIN)
        box = (w * f, h * f, w * (1 - 2 * f), h * (1 - 2 * f))
    else:
        bx, by, bw, bh = ctx.box
        box = (bx * sc[0], by * sc[1], bw * sc[0], bh * sc[1])
    if len(ctx.landmarks) == 5 and ctx.crop_shape:
        return _landmark_guides(ov, ctx.landmarks, sc, th, box)
    return _proportional_guides(ov, th, box)


def frame_guides(ov, w, h, th, ctx):
    """Objects: centre cross and the two diagonals, for checking placement and angles."""
    dashed(ov, (w / 2, 0), (w / 2, h), LINE, th)
    dashed(ov, (0, h / 2), (w, h / 2), LINE, th)
    dashed(ov, (0, 0), (w, h), SOFT, th)
    dashed(ov, (w, 0), (0, h), SOFT, th)
    return []


def hand_guides(ov, w, h, th, ctx):
    """Hands: palm block and circle, wrist axis, knuckle arc, and every finger joint.

    A box around a hand says nothing a beginner can use, so the real structure is used:
    the 21 landmarks from the models when they are installed, otherwise whatever the
    silhouette gives up (see core/hands.py). When neither works -- a cluttered background,
    two hands overlapping -- this falls back to the object guides, which at least help
    with placement.
    """
    from .hands import analyze                 # local: hands.py pulls in styles.py
    src = ctx.source_img
    if src is None:
        return frame_guides(ov, w, h, th, ctx)
    hand = analyze(src)
    if hand is None:
        return frame_guides(ov, w, h, th, ctx)

    sx, sy = w / src.shape[1], h / src.shape[0]
    P = lambda p: (p[0] * sx, p[1] * sy)
    palm, pr = P(hand.palm), hand.palm_r * (sx + sy) / 2
    cv2.circle(ov, (int(palm[0]), int(palm[1])), int(pr), SOFT, th, cv2.LINE_AA)
    quad = [P(p) for p in hand.palm_quad]
    if len(quad) >= 3:
        cv2.polylines(ov, [np.array(quad, np.int32)], True, LINE, th, cv2.LINE_AA)
    dashed(ov, P(hand.wrist), palm, SOFT, th)
    kn = [P(p) for p in hand.knuckles]
    if len(kn) >= 2:
        cv2.polylines(ov, [np.array(kn, np.int32)], False, LINE, max(1, th + 1), cv2.LINE_AA)

    # Full strength, not SOFT: the finger axes are the single most useful line on a hand
    # guide and at SOFT they vanish into a dark or busy sketch. With the landmark models
    # these are the real joint chains, so they bend with the finger instead of being a
    # straight line from knuckle to tip.
    for chain in (hand.joints or [[b, t] for b, t in hand.fingers]):
        pts = [P(p) for p in chain]
        for a, b in zip(pts, pts[1:]):
            dashed(ov, a, b, LINE, th)
        for p in pts[1:-1]:
            cv2.circle(ov, (int(p[0]), int(p[1])), max(2, th + 1), LINE, -1, cv2.LINE_AA)

    labels = [("palm", palm[0] - pr * 0.5, palm[1])]
    if kn:
        labels.append(("knuckles", kn[len(kn) // 2][0], kn[len(kn) // 2][1] - pr * 0.25))
    labels.append(("wrist", *P(hand.wrist)))
    return labels


GUIDES = {"portrait": face_guides, "object": frame_guides, "hands": hand_guides}


def draw_guides(sketch, mode, style_key=None, landmarks=(), crop_shape=None, box=None, source_img=None):
    """Thirds grid for every style, plus the construction lines for `mode`.

    A style of the `construct` family (Technical, Basic Shapes, Construction) already
    draws its own scaffolding, so the mode guides are left off to avoid two sets of
    lines over each other.
    """
    out = sketch.copy()
    h, w = out.shape[:2]
    th, fs = max(1, w // 450), max(0.45, w / 1100)
    ov, labels = out.copy(), []
    for i in (1, 2):
        dashed(ov, (w * i / 3, 0), (w * i / 3, h), SOFT, th)
        dashed(ov, (0, h * i / 3), (w, h * i / 3), SOFT, th)

    own_construction = False
    if style_key is not None:
        from .styles import ALL
        own_construction = ALL[style_key].family == "construct"
    if not own_construction:
        sc = (w / crop_shape[1], h / crop_shape[0]) if crop_shape else (1.0, 1.0)
        ctx = Ctx(source_img, tuple(landmarks), crop_shape, box, sc)
        labels = GUIDES.get(mode, frame_guides)(ov, w, h, th, ctx)

    out = cv2.addWeighted(ov, 0.8, out, 0.2, 0)
    for name, x, y in labels:
        cv2.putText(out, name, (int(np.clip(x, 6, w - 90)), int(np.clip(y, 14, h - 4)) - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, fs, LINE, th, cv2.LINE_AA)
    return out
