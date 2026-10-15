"""Proportion / guide lines drawn over a sketch for the drawing-guide page."""
import cv2
import numpy as np
from .faces import MARGIN

LINE = (230, 120, 40)   # BGR blue
SOFT = (235, 170, 110)


def _dashed(img, p1, p2, color, th, dash=14):
    p1, p2 = np.array(p1, float), np.array(p2, float)
    n = max(1, int(np.linalg.norm(p2 - p1) // dash))
    for i in range(0, n, 2):
        a, b = p1 + (p2 - p1) * i / n, p1 + (p2 - p1) * min(i + 1, n) / n
        cv2.line(img, tuple(a.astype(int)), tuple(b.astype(int)), color, th, cv2.LINE_AA)


def draw_guides(sketch, style_key):
    """Rule-of-thirds grid for every style; face proportion lines too (except Technical, which has its own)."""
    out = sketch.copy()
    h, w = out.shape[:2]
    th, fs = max(1, w // 450), max(0.45, w / 1100)
    ov = out.copy()
    for i in (1, 2):
        _dashed(ov, (w * i / 3, 0), (w * i / 3, h), SOFT, th)
        _dashed(ov, (0, h * i / 3), (w, h * i / 3), SOFT, th)
    labels = []
    if style_key != "technical":
        fx0, fy0 = w * MARGIN / (1 + 2 * MARGIN), h * MARGIN / (1 + 2 * MARGIN)
        fh = h - 2 * fy0
        cv2.ellipse(ov, (w // 2, int(fy0 + fh * 0.45)), (int((w - 2 * fx0) * 0.55), int(fh * 0.68)), 0, 0, 360, LINE, th, cv2.LINE_AA)
        _dashed(ov, (w / 2, fy0 - fh * 0.3), (w / 2, h - fy0 * 0.4), LINE, th)  # centre axis
        for name, f in (("top of head", -0.22), ("eyes", 0.38), ("nose", 0.72), ("mouth", 0.84), ("chin", 1.0)):
            y = fy0 + fh * f
            _dashed(ov, (fx0 * 0.5, y), (w - fx0 * 0.5, y), LINE, th)
            labels.append((name, y))
    out = cv2.addWeighted(ov, 0.8, out, 0.2, 0)
    for name, y in labels:
        cv2.putText(out, name, (6, int(y) - 5), cv2.FONT_HERSHEY_SIMPLEX, fs, LINE, th, cv2.LINE_AA)
    return out
