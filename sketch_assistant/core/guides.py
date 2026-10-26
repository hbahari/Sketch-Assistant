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


def _landmark_guides(ov, lm, sc, th):
    """Tilt-aware face guides from YuNet's eyes / nose / mouth points."""
    re, le, nose, mr, ml = [np.array(p, float) * sc for p in lm]
    eye, mouth = (re + le) / 2, (mr + ml) / 2
    ax = mouth - eye                                   # eyes -> mouth (face's "down" axis)
    e = (le - re) / np.linalg.norm(le - re)            # direction of the eye line
    top, chin = eye - 1.5 * ax, eye + 1.5 * ax         # eyes sit halfway down the head
    H = np.linalg.norm(chin - top)
    cv2.ellipse(ov, tuple(int(v) for v in (top + chin) / 2), (int(H * 0.34), int(H * 0.5)),
                float(np.degrees(np.arctan2(e[1], e[0]))), 0, 360, LINE, th, cv2.LINE_AA)
    dashed(ov, top - 0.15 * ax, chin + 0.15 * ax, LINE, th)
    labels, half = [], np.linalg.norm(ax) * 2.6
    for name, pt in (("top of head", top), ("eyes", eye), ("nose", nose), ("mouth", mouth), ("chin", chin)):
        a = pt - e * half
        dashed(ov, a, pt + e * half, LINE, th)
        labels.append((name, a[0], a[1]))
    return labels


def _proportional_guides(ov, w, h, th):
    """Fallback when there are no landmarks: assume a front-facing face centred in the crop."""
    fx0, fy0 = w * MARGIN / (1 + 2 * MARGIN), h * MARGIN / (1 + 2 * MARGIN)
    fh, labels = h - 2 * fy0, []
    cv2.ellipse(ov, (w // 2, int(fy0 + fh * 0.45)), (int((w - 2 * fx0) * 0.55), int(fh * 0.68)), 0, 0, 360, LINE, th, cv2.LINE_AA)
    dashed(ov, (w / 2, fy0 - fh * 0.3), (w / 2, h - fy0 * 0.4), LINE, th)
    for name, f in (("top of head", -0.22), ("eyes", 0.38), ("nose", 0.72), ("mouth", 0.84), ("chin", 1.0)):
        y = fy0 + fh * f
        dashed(ov, (fx0 * 0.5, y), (w - fx0 * 0.5, y), LINE, th)
        labels.append((name, fx0 * 0.5, y))
    return labels


def draw_guides(sketch, style_key, landmarks=(), crop_shape=None):
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
        if len(landmarks) == 5 and crop_shape:
            labels = _landmark_guides(ov, landmarks, (w / crop_shape[1], h / crop_shape[0]), th)
        else:
            labels = _proportional_guides(ov, w, h, th)
    out = cv2.addWeighted(ov, 0.8, out, 0.2, 0)
    for name, x, y in labels:
        cv2.putText(out, name, (int(np.clip(x, 6, w - 90)), int(np.clip(y, 14, h - 4)) - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, fs, LINE, th, cv2.LINE_AA)
    return out
