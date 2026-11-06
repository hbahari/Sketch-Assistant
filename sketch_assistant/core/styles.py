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


# One rhythm for every hatch in the app. Only the direction of the strokes changes per mode:
# a flat grid where there is no structure to follow, curves round the form where there is.
# Spacing, stroke weight, how many layers and the tone each layer starts at are shared, so
# the shading reads as the same pencil held the same way whichever subject you are drawing.
HATCH_CUTS = (40, 60, 78, 90)  # percentile of darkness at which each successive layer starts


def _hatch_rhythm(w, d):
    """Stroke spacing and weight at this detail. Weight tracks spacing so ink stays constant."""
    sp = max(5.0, w / lerp(65, 125, d))
    return sp, max(1.6, sp * 0.2)


def _hatch_ink(dark, fields, d, inside=None):
    """Lay the layers down: a stroke wherever a field crosses a period and the tone is dark enough.

    `fields` are scalar fields with unit gradient, one per layer, lightest first. Iso-lines of
    a field are the strokes, so a plane gives straight hatching and a distance-from-axis field
    gives strokes that wrap. Darkness comes from layers crossing, never from pressing harder —
    which is the thing a beginner has to be shown rather than told.
    """
    h, w = dark.shape[:2]
    sp, width = _hatch_rhythm(w, d)
    where = dark if inside is None else dark[inside]
    cuts = np.percentile(where, np.clip(np.array(HATCH_CUTS) + (0.5 - d) * 20, 20, 98))
    ink = np.zeros((h, w), bool)
    for i, (field, cut) in enumerate(zip(fields, cuts)):
        # stagger each layer so strokes interleave instead of landing on top of each other
        band = np.abs(((field + i * sp / len(fields)) % sp) - sp / 2) < width / 2
        ink |= band & (dark >= cut)
    return ink if inside is None else (ink & inside)


# Cross-hatching: darker = more hatch layers. Detail = line density, ink coverage, contour lines.
def crosshatch(img, d=0.5):
    img = _prep(img)
    h, w = img.shape[:2]
    g = _gray(img)
    dark = 255 - cv2.GaussianBlur(g, (0, 0), 2.5)
    ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
    planes = [xs * np.cos(np.deg2rad(a)) + ys * np.sin(np.deg2rad(a)) for a in (45, 135, 0, 90)]
    ink = _hatch_ink(dark, planes, d)
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


# --------------------------------------------------------------------------- figures
# Classical proportion, in head heights from the crown. Used for the measuring ruler.
HEAD_MARKS = ((1.0, "chin"), (1.4, "shoulders"), (3.0, "navel"), (3.6, "hips"),
              (5.5, "knees"), (7.5, "feet"))


def _smooth(points, n=24):
    """A flowing curve through a few points, for the line of action.

    Drawn as a quadratic through the midpoints rather than straight segments: a gesture
    line that visibly bends at each joint is not a gesture line.
    """
    p = np.asarray(points, np.float32)
    if len(p) < 3:
        return p
    out = []
    for i in range(len(p) - 1):
        a = p[i - 1] if i else p[0]
        b, c = p[i], p[i + 1]
        m0, m1 = (a + b) / 2, (b + c) / 2
        for t in np.linspace(0, 1, n, endpoint=False):
            out.append((1 - t) ** 2 * m0 + 2 * (1 - t) * t * b + t ** 2 * m1)
    out.append(p[-1])
    return np.asarray(out, np.float32)


def gesture(img, d=0.5):
    """The thirty-second drawing: line of action, and the limbs as single strokes.

    Deliberately almost empty. Gesture is about the whole pose's rhythm and weight, and
    detail is what stops a beginner seeing it, so even at full detail this adds only the
    shoulder and hip bars.
    """
    from .bodies import detect
    img = _prep(img)
    h, w = img.shape[:2]
    bodies = detect(img)
    out = np.full((h, w, 3), 255, np.uint8)
    if not bodies:
        return line_art(img, d)
    ink, accent = (60, 60, 60), (200, 120, 40)
    unit = max(2, int(min(h, w) * 0.006))
    for b in bodies:
        curve = _smooth(b.line_of_action)
        if len(curve) > 1:
            cv2.polylines(out, [curve.astype(np.int32)], False, ink, unit * 3, cv2.LINE_AA)
        for pts in b.limb_chains().values():
            cv2.polylines(out, [_smooth(pts).astype(np.int32)], False, ink,
                          max(1, int(unit * 1.6)), cv2.LINE_AA)
        hh = b.head_height
        cx, cy = b.p(0)
        cv2.circle(out, (int(cx), int(cy)), int(hh * 0.42), ink, unit, cv2.LINE_AA)
        if d > 0.35:                                     # the two bars, and nothing more
            for a, c in (b.shoulders, b.hips):
                cv2.line(out, (int(a[0]), int(a[1])), (int(c[0]), int(c[1])),
                         accent, unit * 2, cv2.LINE_AA)
    return out


def _tapered(out, pts, w0, w1, colour, th):
    """A limb segment drawn as a tapering box, wide at the joint and narrow at the end."""
    a, b = np.asarray(pts[0], float), np.asarray(pts[1], float)
    v = b - a
    n = np.array([-v[1], v[0]])
    ln = np.linalg.norm(n)
    if ln < 1e-6:
        return
    n /= ln
    quad = np.array([a - n * w0, b - n * w1, b + n * w1, a + n * w0], np.int32)
    cv2.polylines(out, [quad], True, colour, th, cv2.LINE_AA)


def mannequin(img, d=0.5):
    """The block-in: head oval, ribcage and pelvis masses, limbs as tapering volumes.

    This is the structural drawing a figure course spends weeks on. Falls back to the
    plain line art when no figure can be read, so the style always produces something.
    """
    from .bodies import detect, L_HIP, L_SHOULDER, R_HIP, R_SHOULDER
    img = _prep(img)
    h, w = img.shape[:2]
    bodies = detect(img)
    if not bodies:
        return line_art(img, d)
    out = np.full((h, w, 3), 255, np.uint8)
    ink, accent, soft = (60, 60, 60), (200, 120, 40), (170, 170, 170)

    for b in bodies:
        hh = b.head_height
        unit = max(2, int(hh * 0.07))
        lm = b.landmarks
        ls, rs = lm[L_SHOULDER], lm[R_SHOULDER]
        lh, rh = lm[L_HIP], lm[R_HIP]
        # ribcage and pelvis as the two masses everything else hangs between
        for quad in ((ls, rs, rs + (rh - rs) * 0.62, ls + (lh - ls) * 0.62),
                     (lh + (ls - lh) * 0.25, rh + (rs - rh) * 0.25, rh, lh)):
            cv2.polylines(out, [np.asarray(quad, np.int32)], True, ink, unit, cv2.LINE_AA)
        cv2.line(out, tuple(((ls + rs) / 2).astype(int)), tuple(((lh + rh) / 2).astype(int)),
                 soft, max(1, unit // 2), cv2.LINE_AA)

        cx, cy = b.p(0)
        cv2.ellipse(out, (int(cx), int(cy)), (int(hh * 0.37), int(hh * 0.5)),
                    0, 0, 360, ink, unit, cv2.LINE_AA)

        for pts in b.limb_chains().values():
            widths = (hh * 0.21, hh * 0.15, hh * 0.11)
            for i, (p0, p1) in enumerate(zip(pts, pts[1:])):
                cv2.line(out, (int(p0[0]), int(p0[1])), (int(p1[0]), int(p1[1])),
                         ink, max(1, unit), cv2.LINE_AA)
                if d > 0.55:
                    _tapered(out, (p0, p1), widths[min(i, 2)], widths[min(i + 1, 2)],
                             soft, max(1, unit // 2))
            if d > 0.25:
                for q in pts:
                    cv2.circle(out, (int(q[0]), int(q[1])), max(2, int(hh * 0.075)),
                               accent, -1, cv2.LINE_AA)

        for a, c in (b.shoulders, b.hips):               # the two bars: contrapposto
            cv2.line(out, (int(a[0]), int(a[1])), (int(c[0]), int(c[1])),
                     accent, max(2, unit), cv2.LINE_AA)

    if d > 0.4:                                          # the heads-tall ruler
        b = bodies[0]
        hh, bx, by, bh = b.head_height, b.box[0], b.box[1], b.box[3]
        x = int(max(8, bx - hh * 0.55))
        for k in range(int(bh / hh) + 1):
            y = int(by + k * hh)
            if y > h - 4:
                break
            dashed(out, (x - hh * 0.22, y), (x + hh * 0.22, y), accent, 1)
            cv2.putText(out, str(k), (int(x + hh * 0.28), y + int(hh * 0.12)),
                        cv2.FONT_HERSHEY_SIMPLEX, max(0.35, hh / 160), accent, 1, cv2.LINE_AA)
        cv2.putText(out, f"{b.heads_tall:.1f} heads", (int(max(6, bx)), max(16, int(by - hh * 0.18))),
                    cv2.FONT_HERSHEY_SIMPLEX, max(0.45, hh / 130), accent, 1, cv2.LINE_AA)
    return out


def _body_axes(bodies):
    """The figure as a set of axis segments: torso, limbs, head.

    Hatching that follows these wraps around the form instead of lying flat across it,
    which is the whole point of cross-contour shading.
    """
    from .bodies import L_HIP, L_SHOULDER, NOSE, R_HIP, R_SHOULDER
    segs = []
    for b in bodies:
        lm, vis = b.landmarks, b.visible
        if vis[L_SHOULDER] and vis[R_SHOULDER] and vis[L_HIP] and vis[R_HIP]:
            chest = (lm[L_SHOULDER] + lm[R_SHOULDER]) / 2
            pelvis = (lm[L_HIP] + lm[R_HIP]) / 2
            segs.append((chest, pelvis))
            if vis[NOSE]:
                segs.append((lm[NOSE], chest))
        for pts in b.limb_chains().values():
            for a, c in zip(pts, pts[1:]):
                segs.append((np.asarray(a, np.float32), np.asarray(c, np.float32)))
    return [(np.asarray(a, np.float32), np.asarray(c, np.float32))
            for a, c in segs if np.hypot(*(np.asarray(c) - np.asarray(a))) > 4]


def _axis_field(shape, segs):
    """For every pixel: distance along the nearest axis, and signed distance out from it.

    Iso-lines of the first wrap round the limb; iso-lines of the second run along it. One
    gives cross-contour strokes, the other the second hatching layer.

    Which segment owns a pixel is decided by distance to the segment, but both fields are
    measured against that segment's infinite line. Measuring them to the clamped endpoint
    instead makes them radial past the end of a limb, which draws bullseye rings at the hips
    and crown and flat blobs where `along` goes constant. Running them on past the joint
    keeps the strokes straight, which is also what a person drawing the figure would do.
    """
    h, w = shape[:2]
    ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
    best_d = np.full((h, w), 1e9, np.float32)
    along = np.zeros((h, w), np.float32)
    across = np.zeros((h, w), np.float32)
    offset = 0.0
    for p0, p1 in segs:
        v = p1 - p0
        L2 = float(v[0] ** 2 + v[1] ** 2) or 1.0
        L = float(np.sqrt(L2))
        t = ((xs - p0[0]) * v[0] + (ys - p0[1]) * v[1]) / L2
        tc = np.clip(t, 0.0, 1.0)
        cx, cy = p0[0] + tc * v[0], p0[1] + tc * v[1]
        d = np.hypot(xs - cx, ys - cy)
        take = d < best_d
        if take.any():
            best_d = np.where(take, d, best_d)
            along = np.where(take, offset + t * L, along)
            # signed perpendicular distance to the limb's line, so the two sides of a limb
            # hatch in opposite directions and the field keeps a unit gradient everywhere
            perp = ((xs - p0[0]) * v[1] - (ys - p0[1]) * v[0]) / L
            across = np.where(take, perp, across)
        offset += L
    return along, across, best_d


def form_hatch(img, d=0.5):
    """Cross-contour shading: strokes that wrap the form, layered up where it is dark.

    The step between a flat value study and a finished drawing is not more tone, it is
    knowing which way to pull the pencil. Hatching that runs straight across a limb
    flattens it; hatching that curves around it describes a cylinder. These strokes follow
    the axes between the pose landmarks, so they wrap arms, legs and torso the way a life
    drawing does, and build darkness by crossing rather than by pressing harder.

    Falls back to the ordinary cross-hatch when there is no figure to follow.
    """
    from .bodies import combined_mask, detect
    img = _prep(img)
    h, w = img.shape[:2]
    bodies = detect(img)
    segs = _body_axes(bodies) if bodies else []
    if not segs:
        return crosshatch(img, d)
    mask = combined_mask(bodies, img.shape)
    inside = (mask > 100) if mask is not None else np.ones((h, w), bool)

    along, across, _dist = _axis_field((h, w), segs)
    g = cv2.GaussianBlur(_gray(img), (0, 0), 2.0)
    dark = 255 - g
    # The same four layers, the same spacing and the same tone cuts as every other Cross-Hatch
    # in the app; only the direction differs. The wrapping layer goes down first because it is
    # the one that describes the form. Diagonals are divided by root two: `across` and `along`
    # are locally perpendicular unit-gradient fields, so their sum climbs root-two times as
    # fast and would otherwise hatch tighter than the layers it crosses.
    r2 = float(np.sqrt(2.0))
    fields = [across, along, (across + along) / r2, (across - along) / r2]
    ink = _hatch_ink(dark, fields, d, inside)
    ink |= _line_mask(g, int(lerp(250, 60, d)), 1.6, 3.6, 3.0).astype(bool) & inside
    out = np.where(ink, 50, 255).astype(np.uint8)
    out = cv2.GaussianBlur(out, (0, 0), 0.6)
    # the silhouette, so the figure reads even where it is light
    edge = (mask > 100).astype(np.uint8) * 255 if mask is not None else None
    bgr = _to_bgr(out)
    if edge is not None:
        cnts, _ = cv2.findContours(edge, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(bgr, cnts, -1, (60, 60, 60), max(2, int(min(h, w) * 0.004)), cv2.LINE_AA)
    return bgr


def on_body(render_fn):
    """Run a renderer, then keep only the figures.

    The pose model returns a body segmentation mask of its own, which is both free and far
    better than the GrabCut silhouette the other modes fall back on -- it knows what a
    person is, so a patterned floor or a second figure in the background does not confuse
    it.
    """
    def wrapped(img, d=0.5):
        from .bodies import combined_mask, detect
        img = _prep(img)
        art = render_fn(img, d)
        bodies = detect(img)
        if not bodies:
            return art
        m = combined_mask(bodies, img.shape)
        if m is None:
            return art
        grow = max(3, int(min(img.shape[:2]) * 0.012)) | 1
        m = cv2.dilate(m, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (grow, grow)))
        m = cv2.GaussianBlur(m, (0, 0), max(1.5, min(img.shape[:2]) * 0.006))
        if m.shape[:2] != art.shape[:2]:
            m = cv2.resize(m, (art.shape[1], art.shape[0]))
        a = (m.astype(np.float32) / 255)[..., None]
        return (255 - (255 - art.astype(np.float32)) * a).astype(np.uint8)
    wrapped.__name__ = f"on_body_{getattr(render_fn, '__name__', 'style')}"
    return wrapped


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
BODY_STYLES = {s.key: s for s in (      # posture mode: abstract first, rendered after
    Style("body_gesture", "Gesture", gesture, "Gesture", 0.5, "gesture"),
    Style("body_mannequin", "Mannequin", mannequin, "Mannequin", 0.5, "construct"),
    Style("body_contour", "Contour", on_body(line_art), "Contour", 0.3, "line"),
    Style("body_value", "Value Study", on_body(value_study), "Value", 0.3, "value"),
    Style("body_formhatch", "Cross-Contour", form_hatch, "Hatch", 0.5, "hatch"),
    Style("body_realistic", "Photorealism", on_body(photorealistic), "Realistic", 0.5, "real"),
)}
ALL = {**STYLES, **OBJECT_STYLES, **HAND_STYLES, **BODY_STYLES}


def family_of(style_key):
    return ALL[style_key].family


def render(style_key, img, detail=None):
    st = ALL[style_key]
    return st.render(img, st.default if detail is None else float(detail))
