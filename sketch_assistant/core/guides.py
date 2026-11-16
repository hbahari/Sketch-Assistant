"""Construction lines drawn over a sketch on the drawing-guide page.

One function per subject, all with the same signature so `core/modes.py` can simply hold
a reference to the right one:

    guide(overlay, w, h, th, ctx) -> [(label, x, y), ...]  or [(label, x, y, colour), ...]

`ctx` carries whatever the subject needs -- the detector's box and landmarks for a face,
the source photo for a hand -- so adding a subject never changes this module's callers.

Every guide that runs straight across or straight down the sketch is labelled with where
it sits as a fraction of the whole: 0 is the top or left edge, 1 the bottom or right.
`at()` builds those labels. A line that is tilted, such as the eye line on a turned head
or the shoulder bar of a twisted figure, is measured at its midpoint -- it is still the
eye line, and a reader marking it out on paper wants to know how far down the page it
goes. Guides that are not lines at all (the palm circle, the finger joints) carry no
fraction; the thirds grid is numbered in every mode, so no mode is left without any.
"""
from dataclasses import dataclass, field

import cv2
import numpy as np

from .faces import MARGIN

LINE = (230, 120, 40)   # BGR amber
SOFT = (235, 170, 110)


def text_metrics(w):
    """Line thickness and font scale for a sketch this wide. One definition, so the label
    rows below and the text that lands in them cannot drift apart."""
    return max(1, w // 450), max(0.45, w / 1100)


def label_rows(w):
    """Where along the top edge the two rows of vertical-line labels sit.

    Vertical lines have to be labelled along the top, so they share one strip. The thirds
    grid takes the first row and a mode's own vertical guides the second: a third and a
    half of the width are only about 60px apart, and "centre 0.50" is wider than that, so
    on a single row they collide. Measured from the font rather than fixed, because the
    font scales with the sketch and a fixed row clips the digits on a large one.
    """
    th, fs = text_metrics(w)
    (_, hh), _ = cv2.getTextSize("0.00", cv2.FONT_HERSHEY_SIMPLEX, fs, th)
    return hh + 10.0, hh * 2 + 20.0


def at(name, value, total):
    """Label a guide with where it sits, 0 to 1 across the sketch: `at("eyes", y, h)`.

    Two decimals. Three is false precision on a line a person is about to draw freehand,
    and one cannot tell 0.43 from 0.47 -- which is the difference between the eye line
    being right and being visibly wrong.
    """
    return f"{name} {np.clip(value / max(total, 1e-6), 0.0, 1.0):.2f}"


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


def _landmark_guides(ov, lm, sc, th, box, w, h):
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
    labels.append((at("centre", cx, w), cx, top[1] - ax2 * 0.16))
    for name, pt in (("top of head", top), ("eyes", eye), ("nose", nose), ("mouth", mouth), ("chin", chin)):
        a = pt - e * half
        dashed(ov, a, pt + e * half, LINE, th)
        # the line is tilted on a turned head, so it is measured where the feature is
        labels.append((at(name, pt[1], h), a[0], a[1]))
    return labels


def _proportional_guides(ov, th, box, w, h):
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
    labels.append((at("centre", cx, w), cx, top - ax2 * 0.16))
    for name, f in (("top of head", 0.0), ("eyes", 0.43), ("nose", 0.64), ("mouth", 0.78), ("chin", 1.0)):
        y = top + (chin - top) * f
        dashed(ov, (cx - half, y), (cx + half, y), LINE, th)
        labels.append((at(name, y, h), cx - half, y))
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
        return _landmark_guides(ov, ctx.landmarks, sc, th, box, w, h)
    return _proportional_guides(ov, th, box, w, h)


def frame_guides(ov, w, h, th, ctx):
    """Objects: centre cross and the two diagonals, for checking placement and angles."""
    dashed(ov, (w / 2, 0), (w / 2, h), LINE, th)
    dashed(ov, (0, h / 2), (w, h / 2), LINE, th)
    dashed(ov, (0, 0), (w, h), SOFT, th)
    dashed(ov, (w, 0), (0, h), SOFT, th)
    # the diagonals are not measured: they cross every fraction on the way down
    return [(at("centre", w / 2, w), w / 2, label_rows(w)[1]),
            (at("centre", h / 2, h), 6.0, h / 2)]


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


def body_guides(ov, w, h, th, ctx):
    """Figures: line of action, the shoulder and hip bars, and the heads-tall ruler.

    These are the three things a figure-drawing class checks first, and they are all a
    beginner needs over the top of a reference. Deliberately no skeleton -- tracing joints
    is what the Mannequin style is for; the guides are for seeing the pose.
    """
    from .bodies import detect                 # local: bodies.py pulls in styles.py
    src = ctx.source_img
    if src is None:
        return frame_guides(ov, w, h, th, ctx)
    bodies = detect(src)
    if not bodies:
        return frame_guides(ov, w, h, th, ctx)

    sx, sy = w / src.shape[1], h / src.shape[0]
    P = lambda p: (p[0] * sx, p[1] * sy)
    labels = []
    for b in bodies:
        pts = [P(p) for p in b.line_of_action]
        for a, c in zip(pts, pts[1:]):
            dashed(ov, a, c, LINE, max(1, th + 1))
        for (p1, p2), name in (((b.shoulders), "shoulders"), ((b.hips), "hips")):
            a, c = P(p1), P(p2)
            cv2.line(ov, (int(a[0]), int(a[1])), (int(c[0]), int(c[1])), LINE,
                     max(1, th + 1), cv2.LINE_AA)
            mid = (a[1] + c[1]) / 2       # the bar tilts, so it is measured at its middle
            labels.append((at(name, mid, h), min(a[0], c[0]), mid))
        # a plumb line from the chest: where the weight falls, and whether it is over a foot
        chest = np.mean([np.array(b.shoulders[0]), np.array(b.shoulders[1])], axis=0)
        cx = P(tuple(chest))[0]
        dashed(ov, (cx, P(b.box[:2])[1]), (cx, h), SOFT, th)
        labels.append((at("plumb", cx, w), cx, h - 12.0))

    b = bodies[0]
    hh = b.head_height * (sx + sy) / 2
    bx, by, _bw, bh = b.box
    x = max(6.0, P((bx, by))[0] - hh * 0.5)
    for k in range(int((bh * sy) / max(hh, 1)) + 1):
        y = P((bx, by))[1] + k * hh
        if y > h - 3:
            break
        dashed(ov, (x - hh * 0.2, y), (x + hh * 0.2, y), SOFT, th)
    labels.append((f"{b.heads_tall:.1f} heads", x, max(14.0, P((bx, by))[1] - hh * 0.2)))
    return labels


GUIDES = {"portrait": face_guides, "object": frame_guides, "hands": hand_guides,
          "body": body_guides}


def draw_guides(sketch, mode, style_key=None, landmarks=(), crop_shape=None, box=None, source_img=None):
    """Thirds grid for every style, plus the construction lines for `mode`.

    A style of the `construct` family (Technical, Basic Shapes, Construction) already
    draws its own scaffolding, so the mode guides are left off to avoid two sets of
    lines over each other.
    """
    out = sketch.copy()
    h, w = out.shape[:2]
    th, fs = text_metrics(w)
    grid_row = label_rows(w)[0]
    ov, labels = out.copy(), []
    for i in (1, 2):
        dashed(ov, (w * i / 3, 0), (w * i / 3, h), SOFT, th)
        dashed(ov, (0, h * i / 3), (w, h * i / 3), SOFT, th)
        # numbered in every mode, including the ones whose own guides are not straight
        # lines, so no mode is left with nothing to measure against
        labels.append((f"{i / 3:.2f}", w * i / 3 + 4, grid_row, SOFT))
        labels.append((f"{i / 3:.2f}", 6.0, h * i / 3, SOFT))

    own_construction = False
    if style_key is not None:
        from .styles import ALL
        own_construction = ALL[style_key].family == "construct"
    if not own_construction:
        sc = (w / crop_shape[1], h / crop_shape[0]) if crop_shape else (1.0, 1.0)
        ctx = Ctx(source_img, tuple(landmarks), crop_shape, box, sc)
        labels += GUIDES.get(mode, frame_guides)(ov, w, h, th, ctx)

    out = cv2.addWeighted(ov, 0.8, out, 0.2, 0)
    for label in labels:
        name, x, y = label[:3]
        colour = label[3] if len(label) > 3 else LINE
        # measured rather than a fixed 90px allowance: the labels carry a fraction now, so
        # a fixed allowance either lets "top of head 0.00" run off the edge or wastes room
        (tw, _), _ = cv2.getTextSize(name, cv2.FONT_HERSHEY_SIMPLEX, fs, th)
        cv2.putText(out, name, (int(np.clip(x, 6, max(6, w - tw - 4))),
                                int(np.clip(y, 14, h - 4)) - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, fs, colour, th, cv2.LINE_AA)
    return out
