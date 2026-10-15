"""The four sketch styles. Every renderer: BGR face crop -> BGR sketch (white paper)."""
from dataclasses import dataclass
from typing import Callable
import cv2
import numpy as np

WORK_SIZE = 800  # long side used while processing


def _prep(img):
    s = WORK_SIZE / max(img.shape[:2])
    return cv2.resize(img, None, fx=s, fy=s, interpolation=cv2.INTER_AREA if s < 1 else cv2.INTER_CUBIC)


def _gray(img):
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return cv2.createCLAHE(2.0, (8, 8)).apply(g)


def _dodge(gray, sigma):
    """Classic pencil effect: colour-dodge the image with its blurred negative."""
    blur = cv2.GaussianBlur(255 - gray, (0, 0), sigma)
    return cv2.divide(gray, 255 - blur, scale=256)


def _to_bgr(gray):
    return cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)


def _line_mask(gray, min_area=40, s1=1.0, s2=2.4, thr=1.5):
    """Clean binary outlines via Difference of Gaussians; specks removed."""
    g = cv2.bilateralFilter(gray, 9, 50, 50)
    dog = cv2.GaussianBlur(g, (0, 0), s1).astype(np.float32) - cv2.GaussianBlur(g, (0, 0), s2)
    lines = (dog < -thr).astype(np.uint8)
    n, lab, stats, _ = cv2.connectedComponentsWithStats(lines, connectivity=8)
    keep = (stats[:, cv2.CC_STAT_AREA][lab] >= min_area) & (lab > 0)
    return keep.astype(np.uint8)


# 1 - Line art
def line_art(img):
    img = _prep(img)
    mask = cv2.dilate(_line_mask(_gray(img), 150, 1.8, 4.0, 3.0), np.ones((2, 2), np.uint8))
    return _to_bgr(np.where(mask > 0, 0, 255).astype(np.uint8))


# 2 - Architectural / technical
def technical(img):
    img = _prep(img)
    h, w = img.shape[:2]
    g = _gray(img)
    out = 255 - ((255 - _dodge(g, 14)).astype(np.float32) * 0.45)  # light tone
    ys, xs = np.mgrid[0:h, 0:w]
    hatch = ((xs + ys) % 9 == 0) & (cv2.GaussianBlur(g, (0, 0), 3) < 85)  # shadows only
    out[hatch] = np.minimum(out[hatch], 120)
    out = np.minimum(out, np.where(_line_mask(g, 60) > 0, 40, 255)).astype(np.uint8)
    bgr = _to_bgr(out)
    guide = (190, 140, 90)  # light blue construction lines (BGR)
    m = int(0.08 * w)
    cv2.rectangle(bgr, (m, int(0.05 * h)), (w - m, int(0.95 * h)), guide, 1, cv2.LINE_AA)
    cv2.line(bgr, (w // 2, 0), (w // 2, h), guide, 1, cv2.LINE_AA)  # centre axis
    for frac in (0.40, 0.58, 0.74):  # eye line, nose base, mouth line
        cv2.line(bgr, (m, int(frac * h)), (w - m, int(frac * h)), guide, 1, cv2.LINE_AA)
    for frac in (0.3, 0.7):  # vertical thirds
        cv2.line(bgr, (int(frac * w), int(0.05 * h)), (int(frac * w), int(0.95 * h)), guide, 1, cv2.LINE_AA)
    return bgr


# 3 - Value study: flat tonal blocks
def value_study(img, levels=(38, 108, 176, 238)):
    img = _prep(img)
    g = cv2.GaussianBlur(_gray(img), (0, 0), 3)
    cuts = np.percentile(g, [22, 48, 76])  # every tone is used, whatever the photo's exposure
    q = np.take(np.array(levels, np.uint8), np.digitize(g, cuts))
    return _to_bgr(cv2.medianBlur(q, 11))  # smooth the shape edges


# 4 - Cross-hatching: darker areas get more hatch layers at new angles
def crosshatch(img):
    img = _prep(img)
    h, w = img.shape[:2]
    g = _gray(img)
    dark = 255 - cv2.GaussianBlur(g, (0, 0), 2.5)
    cuts = np.percentile(dark, [40, 60, 78, 90])
    sp = max(6, w // 95)
    ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
    ink = np.zeros((h, w), bool)
    for cut, ang in zip(cuts, (45, 135, 0, 90)):
        a = np.deg2rad(ang)
        ink |= ((xs * np.cos(a) + ys * np.sin(a)) % sp < 1.6) & (dark >= cut)
    ink |= _line_mask(g, 120, 1.6, 3.6, 3.0).astype(bool)  # contour lines
    canvas = np.where(ink, 50, 255).astype(np.uint8)
    return _to_bgr(cv2.GaussianBlur(canvas, (0, 0), 0.6))


# 5 - Photorealism
def photorealistic(img):
    img = _prep(img)
    g = _gray(img)
    sigma = float(np.clip(max(g.shape) / 55, 6, 25))
    soft = cv2.GaussianBlur(g, (0, 0), 1.2)
    tone = cv2.addWeighted(_dodge(soft, sigma), 0.65, soft, 0.35, 0)  # keep mid-tones smooth
    tone = (255 * (tone / 255.0) ** 1.25).astype(np.float32)  # richer darks
    grain = cv2.GaussianBlur(np.random.default_rng(0).normal(0, 7, g.shape).astype(np.float32), (0, 0), 0.8)
    tone = np.clip(tone + grain * (1 - tone / 255.0), 0, 255)  # graphite grain in shadows
    paper = np.array([0.94, 0.96, 0.97], np.float32)  # subtle warm paper (BGR)
    return np.clip(tone[..., None] * paper, 0, 255).astype(np.uint8)


@dataclass(frozen=True)
class Style:
    key: str
    label: str
    render: Callable
    short: str = ""  # compact label for tabs/tiles


STYLES = {s.key: s for s in (
    Style("line_art", "Line Art", line_art, "Line Art"),
    Style("technical", "Technical", technical, "Technical"),
    Style("value_study", "Value Study", value_study, "Value"),
    Style("crosshatch", "Cross-Hatch", crosshatch, "Hatch"),
    Style("photoreal", "Photorealism", photorealistic, "Realistic"),
)}


def render(style_key, face_img):
    return STYLES[style_key].render(face_img)
