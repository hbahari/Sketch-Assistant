"""Sketch styles. Every renderer: (BGR image, detail 0..1) -> BGR sketch on white paper.
`detail` tunes how much is drawn WITHIN the style (it never turns one style into another)."""
from dataclasses import dataclass
from typing import Callable
import cv2
import numpy as np
from .guides import dashed

WORK_SIZE = 800  # long side used while processing


def lerp(a, b, t):
    return a + (b - a) * t


def _prep(img):
    s = WORK_SIZE / max(img.shape[:2])
    return cv2.resize(img, None, fx=s, fy=s, interpolation=cv2.INTER_AREA if s < 1 else cv2.INTER_CUBIC)


def _gray(img):
    return cv2.createCLAHE(2.0, (8, 8)).apply(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY))


def _dodge(gray, sigma):
    """Classic pencil effect: colour-dodge the image with its blurred negative."""
    return cv2.divide(gray, 255 - cv2.GaussianBlur(255 - gray, (0, 0), sigma), scale=256)


def _to_bgr(gray):
    return cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)


def _line_mask(gray, min_area=40, s1=1.0, s2=2.4, thr=1.5):
    """Clean binary outlines via Difference of Gaussians; specks removed."""
    g = cv2.bilateralFilter(gray, 9, 50, 50)
    dog = cv2.GaussianBlur(g, (0, 0), s1).astype(np.float32) - cv2.GaussianBlur(g, (0, 0), s2)
    n, lab, stats, _ = cv2.connectedComponentsWithStats((dog < -thr).astype(np.uint8), connectivity=8)
    return ((stats[:, cv2.CC_STAT_AREA][lab] >= min_area) & (lab > 0)).astype(np.uint8)


# Line art: outlines only. Detail = how many/fine the lines are. Every knob moves the same way
# (low detail = blurrier source, higher threshold, bigger minimum stroke), so more detail ALWAYS means more lines.
def line_art(img, d=0.5):
    img = _prep(img)
    g = cv2.GaussianBlur(_gray(img), (0, 0), lerp(1.9, 0.6, d))
    m = _line_mask(g, int(lerp(240, 40, d)), 1.0, 2.4, lerp(2.6, 1.0, d))
    return _to_bgr(np.where(cv2.dilate(m, np.ones((2, 2), np.uint8)) > 0, 0, 255).astype(np.uint8))


# Technical: light tone + hatching + construction grid. Detail = shadow coverage, hatch density, line count.
def technical(img, d=0.5):
    img = _prep(img)
    h, w = img.shape[:2]
    g = _gray(img)
    out = 255 - ((255 - _dodge(g, 14)).astype(np.float32) * 0.45)
    ys, xs = np.mgrid[0:h, 0:w]
    hatch = ((xs + ys) % int(lerp(12, 6, d)) == 0) & (cv2.GaussianBlur(g, (0, 0), 3) < lerp(55, 115, d))
    out[hatch] = np.minimum(out[hatch], 120)
    lines = _line_mask(g, int(lerp(100, 20, d)), 1.0, 2.4, lerp(2.5, 0.5, d))
    bgr = _to_bgr(np.minimum(out, np.where(lines > 0, 40, 255)).astype(np.uint8))
    guide, m = (190, 140, 90), int(0.08 * w)
    cv2.rectangle(bgr, (m, int(0.05 * h)), (w - m, int(0.95 * h)), guide, 1, cv2.LINE_AA)
    cv2.line(bgr, (w // 2, 0), (w // 2, h), guide, 1, cv2.LINE_AA)
    for f in (0.40, 0.58, 0.74):
        cv2.line(bgr, (m, int(f * h)), (w - m, int(f * h)), guide, 1, cv2.LINE_AA)
    for f in (0.3, 0.7):
        cv2.line(bgr, (int(f * w), int(0.05 * h)), (int(f * w), int(0.95 * h)), guide, 1, cv2.LINE_AA)
    return bgr


# Value study: flat tonal blocks. Detail = number of tones (3-7) and how fine the shapes are.
def value_study(img, d=0.3):
    img = _prep(img)
    n = 3 + int(d * 4)
    g = cv2.GaussianBlur(_gray(img), (0, 0), lerp(4.5, 2.0, d))
    levels = np.linspace(38, 238, n).astype(np.uint8)
    q = np.take(levels, np.digitize(g, np.percentile(g, np.linspace(0, 100, n + 1)[1:-1])))
    return _to_bgr(cv2.medianBlur(q, int(lerp(15, 7, d)) | 1))


# Cross-hatching: darker = more hatch layers. Detail = line density, ink coverage, contour lines.
def crosshatch(img, d=0.5):
    img = _prep(img)
    h, w = img.shape[:2]
    g = _gray(img)
    dark = 255 - cv2.GaussianBlur(g, (0, 0), 2.5)
    cuts = np.percentile(dark, np.clip(np.array([40, 60, 78, 90]) + (0.5 - d) * 20, 20, 98))
    sp = max(5, int(w / lerp(65, 125, d)))
    ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
    ink = np.zeros((h, w), bool)
    for cut, ang in zip(cuts, (45, 135, 0, 90)):
        a = np.deg2rad(ang)
        ink |= ((xs * np.cos(a) + ys * np.sin(a)) % sp < 1.6) & (dark >= cut)
    ink |= _line_mask(g, int(lerp(250, 60, d)), 1.6, 3.6, 3.0).astype(bool)
    return _to_bgr(cv2.GaussianBlur(np.where(ink, 50, 255).astype(np.uint8), (0, 0), 0.6))


# Photorealism: smooth graphite. Detail = softness, pencil-stroke crispness, grain.
def photorealistic(img, d=0.5):
    img = _prep(img)
    g = _gray(img)
    sigma = float(np.clip(max(g.shape) / 55 * lerp(1.5, 0.5, d), 4, 30))
    soft = cv2.GaussianBlur(g, (0, 0), lerp(1.8, 0.6, d))
    tone = cv2.addWeighted(_dodge(soft, sigma), 0.65, soft, 0.35, 0)
    tone = (255 * (tone / 255.0) ** 1.25).astype(np.float32)
    grain = cv2.GaussianBlur(np.random.default_rng(0).normal(0, lerp(3, 11, d), g.shape).astype(np.float32), (0, 0), 0.8)
    tone = np.clip(tone + grain * (1 - tone / 255.0), 0, 255)
    return np.clip(tone[..., None] * np.array([0.94, 0.96, 0.97], np.float32), 0, 255).astype(np.uint8)


# Basic shapes (objects): a "block-in" of the main object.
_sil_cache = {}


def _silhouette(img):
    """Outline of the main object: GrabCut seeded with a centred rectangle (offline, cached per image)."""
    key = (img.shape, hash(img.tobytes()[::97]))
    if key in _sil_cache:
        return _sil_cache[key]
    h, w = img.shape[:2]
    s = 320 / max(h, w)
    small = cv2.resize(img, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
    sh, sw = small.shape[:2]
    m, mask = int(0.04 * min(sh, sw)), np.zeros((sh, sw), np.uint8)
    sil = None
    try:
        cv2.grabCut(small, mask, (m, m, sw - 2 * m, sh - 2 * m), np.zeros((1, 65)), np.zeros((1, 65)), 4, cv2.GC_INIT_WITH_RECT)
        fg = ((mask == 1) | (mask == 3)).astype(np.uint8) * 255
        fg = cv2.morphologyEx(cv2.morphologyEx(fg, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8)), cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
        cs, _ = cv2.findContours(fg, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if cs:
            c = max(cs, key=cv2.contourArea)
            if 0.04 < cv2.contourArea(c) / (sh * sw) < 0.9:
                sil = (c.astype(np.float32) / s).astype(np.int32)
    except cv2.error:
        pass
    if sil is None:  # fallback: biggest blob of a heavily blurred two-tone split
        g = cv2.GaussianBlur(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), (0, 0), 10)
        _, t = cv2.threshold(g, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        best = []
        for mk in (t, 255 - t):
            cs, _ = cv2.findContours(mk, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            best += [c for c in cs if cv2.contourArea(c) < 0.85 * h * w]
        sil = max(best, key=cv2.contourArea) if best else np.array([[[0, 0]], [[w - 1, 0]], [[w - 1, h - 1]], [[0, h - 1]]], np.int32)
    _sil_cache[key] = sil
    return sil


def shapes(img, d=0.5):
    """Object mass + angular silhouette with corner dots + the big shadow shapes + bounding box, centre lines and proportion."""
    img = _prep(img)
    h, w = img.shape[:2]
    sil = _silhouette(img)
    out, blue = np.full((h, w, 3), 255, np.uint8), (200, 120, 40)
    cv2.drawContours(out, [sil], -1, (236, 236, 236), -1)  # the object's mass
    inside = np.zeros((h, w), np.uint8)
    cv2.drawContours(inside, [sil], -1, 255, -1)
    n = int(lerp(0, 6, d))  # how many shadow shapes to block in
    if n:
        g = cv2.GaussianBlur(_gray(img), (0, 0), lerp(12, 5, d))
        dk = ((g < np.percentile(g[inside > 0], 32)) & (inside > 0)).astype(np.uint8) * 255
        dk = cv2.morphologyEx(dk, cv2.MORPH_OPEN, np.ones((7, 7), np.uint8))
        cs, _ = cv2.findContours(dk, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for c in sorted(cs, key=cv2.contourArea, reverse=True)[:n]:
            if cv2.contourArea(c) > w * h * 0.004:
                poly = cv2.approxPolyDP(c, 0.025 * cv2.arcLength(c, True), True)
                cv2.fillPoly(out, [poly], (190, 190, 190)); cv2.polylines(out, [poly], True, (110, 110, 110), 1, cv2.LINE_AA)
    poly = cv2.approxPolyDP(sil, lerp(0.035, 0.008, d) * cv2.arcLength(sil, True), True)  # fewer corners at low detail
    cv2.polylines(out, [poly], True, (60, 60, 60), 3, cv2.LINE_AA)
    for p in poly[:, 0]:
        cv2.circle(out, (int(p[0]), int(p[1])), 4, blue, -1, cv2.LINE_AA)
    x, y, bw, bh = cv2.boundingRect(sil)
    for p, q in (((x, y), (x + bw, y)), ((x + bw, y), (x + bw, y + bh)), ((x + bw, y + bh), (x, y + bh)), ((x, y + bh), (x, y)),
                 ((x + bw / 2, y), (x + bw / 2, y + bh)), ((x, y + bh / 2), (x + bw, y + bh / 2))):
        dashed(out, p, q, blue, 1)
    if len(sil) >= 5:
        box = cv2.fitEllipse(sil)
        if cv2.contourArea(sil) / (np.pi * box[1][0] * box[1][1] / 4 + 1e-6) > 0.85:
            cv2.ellipse(out, box, blue, 1, cv2.LINE_AA)  # roundish object: show its ellipse
    cv2.putText(out, f"W : H = 1 : {bh / max(bw, 1):.2f}", (max(x, 6), max(20, y - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, blue, 1, cv2.LINE_AA)
    return out


# Construction (hands): the block-in a figure-drawing book would start with.
# Fallback joint positions along a finger, used only when the landmark models are missing.
# The proximal phalanx is the longest, then the middle, then the distal -- roughly
# 2 : 1.2 : 1, which puts the joints at these fractions of the finger's length.
JOINTS = (0.465, 0.744)
SEG_WIDTH = (0.30, 0.25, 0.20)      # how wide each segment is drawn, in palm radii


def _chain(hand, base, tip):
    """A finger as the points along it, knuckle to tip.

    With the landmark models this is the real chain of joints. Without them the joints
    are placed at average proportions along the straight axis, which is the best a
    silhouette supports.
    """
    b, t = np.array(base, float), np.array(tip, float)
    return [b] + [b + (t - b) * f for f in JOINTS] + [t]


def construction(img, d=0.5):
    """Palm block, knuckle arc, finger axes and joints -- the structure under a hand.

    Falls back to the generic object block-in when no hand can be read, so the style
    always renders something useful.
    """
    from .hands import analyze                 # imported here: hands.py needs _silhouette
    img = _prep(img)
    h, w = img.shape[:2]
    hand = analyze(img)
    if hand is None:
        return shapes(img, d)

    out, blue, ink = np.full((h, w, 3), 255, np.uint8), (200, 120, 40), (60, 60, 60)
    if hand.contour is not None:
        cv2.drawContours(out, [hand.contour], -1, (238, 238, 238), -1)   # the hand's mass
    pr = hand.palm_r
    thick = max(2, int(pr * 0.05))

    # the palm block, and the knuckle arc across the top of it
    quad = hand.palm_quad
    if len(quad) >= 3:
        cv2.polylines(out, [np.array(quad, np.int32)], True, ink, thick, cv2.LINE_AA)
    kn = hand.knuckles
    if len(kn) >= 2:
        cv2.polylines(out, [np.array(kn, np.int32)], False, blue, thick, cv2.LINE_AA)

    cv2.circle(out, (int(hand.palm[0]), int(hand.palm[1])), int(pr), blue, 1, cv2.LINE_AA)
    dashed(out, hand.wrist, hand.palm, blue, 1)

    chains = hand.joints or [_chain(hand, b, t) for b, t in hand.fingers]
    for chain in chains:
        pts = [np.array(p, float) for p in chain]
        cv2.polylines(out, [np.array(pts, np.int32)], False, ink, max(2, int(pr * 0.045)), cv2.LINE_AA)
        cv2.circle(out, tuple(pts[0].astype(int)), max(3, int(pr * 0.09)), blue, -1, cv2.LINE_AA)
        if d > 0.25:                                     # joints appear with detail
            for p in pts[1:]:
                cv2.circle(out, tuple(p.astype(int)), max(2, int(pr * 0.07)), blue, -1, cv2.LINE_AA)
        if d > 0.6:                                      # ...then the volume on each segment
            for (p0, p1), wf in zip(zip(pts, pts[1:]), SEG_WIDTH):
                v = p1 - p0
                n = np.array([-v[1], v[0]])
                n = n / (np.linalg.norm(n) + 1e-6) * pr * wf * 0.6
                cv2.polylines(out, [np.array([p0 - n, p1 - n, p1 + n, p0 + n], np.int32)],
                              True, (150, 150, 150), 1, cv2.LINE_AA)

    ref = hand.contour if hand.contour is not None else np.array(
        [[[int(p[0]), int(p[1])]] for p in np.vstack([hand.landmarks])], np.int32)
    x, y, bw, bh = cv2.boundingRect(ref)
    for p, q in (((x, y), (x + bw, y)), ((x + bw, y), (x + bw, y + bh)),
                 ((x + bw, y + bh), (x, y + bh)), ((x, y + bh), (x, y)),
                 ((x + bw / 2, y), (x + bw / 2, y + bh)), ((x, y + bh / 2), (x + bw, y + bh / 2))):
        dashed(out, p, q, blue, 1)
    cv2.putText(out, f"palm : hand = 1 : {bh / max(2 * pr, 1):.2f}", (max(x, 6), max(20, y - 8)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, blue, 1, cv2.LINE_AA)
    return out


def on_hand(render_fn, outline=False):
    """Run a renderer, then drop everything outside the hand.

    Without this a hand photographed on a wooden table comes back with the table hatched
    and toned exactly as heavily as the hand: the two stop reading as separate things, and
    there is nothing in the picture to tell a learner where the hand ends. Shading the
    subject and leaving the ground as paper is also what the drawing advice tells them to
    do, so the reference should match.

    The hand is left untouched when it cannot be found, which is better than masking with
    a wrong shape.
    """
    def wrapped(img, d=0.5):
        from .hands import analyze, hand_mask
        img = _prep(img)
        art = render_fn(img, d)
        hand = analyze(img)
        if hand is None:
            return art
        m = hand_mask(img, hand)
        if m is None:
            return art
        if m.shape[:2] != art.shape[:2]:
            m = cv2.resize(m, (art.shape[1], art.shape[0]))
        a = (m.astype(np.float32) / 255)[..., None]
        out = (255 - (255 - art.astype(np.float32)) * a).astype(np.uint8)
        if outline:
            # Draw the silhouette explicitly. Difference-of-Gaussians finds edges by
            # contrast, and the edge of a hand against a pale table or a grey wall often
            # has very little, so the one line that matters most to someone drawing came
            # back broken or missing while every knuckle crease came through strongly.
            h2, w2 = out.shape[:2]
            hard = (m > 128).astype(np.uint8) * 255
            cnts, _ = cv2.findContours(hard, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            cv2.drawContours(out, cnts, -1, (0, 0, 0),
                             max(2, int(min(h2, w2) * 0.005)), cv2.LINE_AA)
        return out
    wrapped.__name__ = f"on_hand_{getattr(render_fn, '__name__', 'style')}"
    return wrapped


@dataclass(frozen=True)
class Style:
    """One renderer, as offered in one mode.

    `family` groups the same transform across modes: Line Art in Portrait, Contour in
    Object and Contour in Hands are all the `line` family. The pencil-tip and step tables
    are keyed by family with per-style overrides, so adding a mode needs new text only
    where the advice genuinely differs -- not five fresh entries every time.
    """
    key: str
    label: str
    render: Callable
    short: str = ""        # compact label for tabs/tiles
    default: float = 0.5   # default detail
    family: str = ""       # line | construct | value | hatch | real


STYLES = {s.key: s for s in (           # portrait mode
    Style("line_art", "Line Art", line_art, "Line Art", family="line"),
    Style("technical", "Technical", technical, "Technical", family="construct"),
    Style("value_study", "Value Study", value_study, "Value", 0.3, family="value"),
    Style("crosshatch", "Cross-Hatch", crosshatch, "Hatch", family="hatch"),
    Style("photoreal", "Photorealism", photorealistic, "Realistic", family="real"),
)}
OBJECT_STYLES = {s.key: s for s in (    # object mode: whole image, no detection
    Style("obj_contour", "Contour", line_art, "Contour", family="line"),
    Style("obj_shapes", "Basic Shapes", shapes, "Shapes", family="construct"),
    Style("obj_value", "Value Study", value_study, "Value", 0.3, family="value"),
    Style("obj_hatch", "Cross-Hatch", crosshatch, "Hatch", family="hatch"),
    Style("obj_realistic", "Photorealism", photorealistic, "Realistic", family="real"),
)}
HAND_STYLES = {s.key: s for s in (      # hands mode: every style is masked to the hand
    # a lower default than the other modes: skin creases, knuckle folds and hair all read
    # as edges, so a hand at the usual 0.5 comes back as a thicket of interior lines
    Style("hand_contour", "Contour", on_hand(line_art, outline=True), "Contour", 0.3, "line"),
    Style("hand_construct", "Construction", construction, "Construct", family="construct"),
    Style("hand_value", "Value Study", on_hand(value_study), "Value", 0.3, family="value"),
    Style("hand_hatch", "Cross-Hatch", on_hand(crosshatch), "Hatch", family="hatch"),
    Style("hand_realistic", "Photorealism", on_hand(photorealistic), "Realistic", family="real"),
)}
ALL = {**STYLES, **OBJECT_STYLES, **HAND_STYLES}


def family_of(style_key):
    return ALL[style_key].family


def render(style_key, img, detail=None):
    st = ALL[style_key]
    return st.render(img, st.default if detail is None else float(detail))
