"""Proportion / guide lines drawn over a sketch for the drawing-guide page."""
import cv2
import numpy as np
from .faces import MARGIN

LINE = (230, 120, 40)   # BGR blue
SOFT = (235, 170, 110)


def dashed(img, p1, p2, color, th, dash=14):
    p1, p2 = np.array(p1, float), np.array(p2, float)
    n = max(1, int(np.linalg.norm(p2 - p1) // dash))
    for i in range(0, n, 2):
        a, b = p1 + (p2 - p1) * i / n, p1 + (p2 - p1) * min(i + 1, n) / n
        cv2.line(img, tuple(a.astype(int)), tuple(b.astype(int)), color, th, cv2.LINE_AA)


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


def _proportional_guides(ov, w, h, th, box):
    """Fallback when the detector gives no landmarks: average proportions inside the box."""
    bx, by, bw, bh = box
    cx, cy, _, ax2 = _oval(ov, box, 0.0, th, grow=1.12)
    top, chin = cy - ax2, cy + ax2
    dashed(ov, (cx, top - ax2 * 0.12), (cx, chin + ax2 * 0.12), LINE, th)
    labels, half = [], bw * 0.62
    for name, f in (("top of head", 0.0), ("eyes", 0.47), ("nose", 0.72), ("mouth", 0.84), ("chin", 1.0)):
        y = top + (chin - top) * f
        dashed(ov, (cx - half, y), (cx + half, y), LINE, th)
        labels.append((name, cx - half, y))
    return labels


def draw_guides(sketch, style_key, landmarks=(), crop_shape=None, box=None):
    """Thirds grid for every style. Portraits add face guides (Technical has its own); objects add centre cross + diagonals."""
    out = sketch.copy()
    h, w = out.shape[:2]
    th, fs = max(1, w // 450), max(0.45, w / 1100)
    ov, labels = out.copy(), []
    for i in (1, 2):
        dashed(ov, (w * i / 3, 0), (w * i / 3, h), SOFT, th)
        dashed(ov, (0, h * i / 3), (w, h * i / 3), SOFT, th)
    if style_key.startswith("obj_"):
        dashed(ov, (w / 2, 0), (w / 2, h), LINE, th); dashed(ov, (0, h / 2), (w, h / 2), LINE, th)
        dashed(ov, (0, 0), (w, h), SOFT, th); dashed(ov, (w, 0), (0, h), SOFT, th)
    elif style_key != "technical":
        sc = (w / crop_shape[1], h / crop_shape[0]) if crop_shape else (1.0, 1.0)
        if box is None:     # no detector box: assume the crop is the box plus MARGIN all round
            f = MARGIN / (1 + 2 * MARGIN)
            box = (w * f, h * f, w * (1 - 2 * f), h * (1 - 2 * f))
        else:
            bx, by, bw_, bh_ = box
            box = (bx * sc[0], by * sc[1], bw_ * sc[0], bh_ * sc[1])
        if len(landmarks) == 5 and crop_shape:
            labels = _landmark_guides(ov, landmarks, sc, th, box)
        else:
            labels = _proportional_guides(ov, w, h, th, box)
    out = cv2.addWeighted(ov, 0.8, out, 0.2, 0)
    for name, x, y in labels:
        cv2.putText(out, name, (int(np.clip(x, 6, w - 90)), int(np.clip(y, 14, h - 4)) - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, fs, LINE, th, cv2.LINE_AA)
    return out
