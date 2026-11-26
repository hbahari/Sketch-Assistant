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


def dashed_path(img, pts, color, th, dash=14):
    """A dashed line through a series of points: the ridge of a nose, which bends."""
    for a, b in zip(pts[:-1], pts[1:]):
        dashed(img, a, b, color, th, dash)


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


def _profile_guides(ov, lm, sc, th, box, w, h, facing):
    """Side profile: the oval round the whole face, and the eye / nose / mouth / chin lines
    square to the face's own up-and-down -- no centre line, which means nothing side on.

    The eye points of a profile nearly coincide, so the face's direction comes from
    eyes-to-mouth, not the eye line the face-on guides use. There's no ear marker: the
    textbook rule (between the eye and nose lines, just behind the middle of the head) put
    it well above the ear on the one profile where the ear shows, a head tipped back.
    """
    re, le, nose, mr, ml = [np.array(p, float) * sc for p in lm]
    eye, mouth = (re + le) / 2, (mr + ml) / 2
    d = max(1e-6, float(np.linalg.norm(eye - mouth)))
    up = (eye - mouth) / d
    across = np.array([-up[1], up[0]])                 # towards the picture's right when upright
    if across[0] < 0:
        across = -across
    down = -up
    angle = float(np.degrees(np.arctan2(across[1], across[0])))
    cx, cy, ax1, ax2 = _oval(ov, box, angle, th)
    centre = np.array([cx, cy])
    top, chin = centre - down * ax2, centre + down * ax2
    back, front = -facing * ax1 * 1.02, facing * ax1 * 1.02   # across the oval
    labels = []

    def level(pt):
        """The point on the oval's vertical axis level with pt, measured square to the face."""
        return centre + down * float(np.dot(pt - centre, down))
    for name, pt in (("top of head", top), ("eyes", eye), ("nose", nose), ("mouth", mouth), ("chin", chin)):
        c = level(pt)
        a, b = c + across * back, c + across * front
        dashed(ov, a, b, LINE, th)
        left = a if a[0] < b[0] else b
        labels.append((at(name, pt[1], h), left[0], left[1]))
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
        from .faces import profile_facing
        facing = profile_facing(ctx.landmarks)
        if facing:
            return _profile_guides(ov, ctx.landmarks, sc, th, box, w, h, facing)
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


def _margin_rows(items, w, row_step, first_row):
    """Top-margin rows for labels centred on given x positions, so none overlap.

    Greedy: each label takes the first row where it clears the label before it.
    Returns [(text, x, y), ...] with x the left edge of the text.
    """
    th, fs = text_metrics(w)
    ends, out = [], []
    for text, x in sorted(items, key=lambda t: t[1]):
        (tw, _), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, fs, th)
        left = float(np.clip(x - tw / 2, 6, max(6, w - tw - 4)))
        row = next((i for i, e in enumerate(ends) if left > e + 8), len(ends))
        if row == len(ends):
            ends.append(0.0)
        ends[row] = left + tw
        out.append((text, left, first_row + row * row_step))
    return out


def eye_guides(ov, w, h, th, ctx):
    """Eyes: the corner-to-corner line, the iris, and where each sits on the page.

    The measurements a drawing book gives for an eye are all relations between these: how
    many irises wide the eye is, how far across it the pupil sits, how much of the iris
    the upper lid covers. The lids themselves are left to the Construction style.

    Laid out as a dimensioned drawing, because the first version was not and a tester
    called it crowded: nine labels sat on the eye itself, two full-length lines crossed
    at the pupil, and the thirds grid ran through all of it. Now the eye carries only
    markers -- the iris circle, a cross at the pupil, dots at the corners, short ticks
    at the top and bottom of the lids -- and every number sits in the margin, the ones
    measured across along the top edge and the ones measured down along the left, each
    with a tick at the edge in line with what it measures.
    """
    from .eyes import analyze                  # local: keeps the import graph one-way
    src = ctx.source_img
    if src is None:
        return frame_guides(ov, w, h, th, ctx)
    eye = analyze(src)
    sx, sy = w / src.shape[1], h / src.shape[0]
    P = lambda p: np.array([p[0] * sx, p[1] * sy])
    I = lambda q: (int(round(q[0])), int(round(q[1])))
    c, r = P(eye.iris), eye.r * (sx + sy) / 2
    A, B = P(eye.left), P(eye.right)
    axis = (B - A) / (np.linalg.norm(B - A) + 1e-6)
    top, bot = P(eye.upper[len(eye.upper) // 2]), P(eye.lower[len(eye.lower) // 2])

    # markers on the eye
    dashed(ov, A - axis * r * 0.5, B + axis * r * 0.5, LINE, th)
    cv2.circle(ov, I(c), int(r), LINE, th, cv2.LINE_AA)
    arm = max(5.0, r * 0.18)
    cv2.line(ov, I(c - (arm, 0)), I(c + (arm, 0)), LINE, th, cv2.LINE_AA)
    cv2.line(ov, I(c - (0, arm)), I(c + (0, arm)), LINE, th, cv2.LINE_AA)
    for q in (A, B):
        cv2.circle(ov, I(q), max(3, th * 2), LINE, -1, cv2.LINE_AA)
    for q in (top, bot):
        cv2.line(ov, I(q - (r * 0.35, 0)), I(q + (r * 0.35, 0)), LINE, th, cv2.LINE_AA)

    # the numbers, in the margins
    tick = max(6, th * 4)
    for x in (A[0], c[0], B[0]):
        cv2.line(ov, (int(x), 0), (int(x), tick), LINE, th, cv2.LINE_AA)
    for y in (top[1], c[1], bot[1]):
        cv2.line(ov, (0, int(y)), (tick, int(y)), LINE, th, cv2.LINE_AA)
    first, second = label_rows(w)
    across = _margin_rows([(at("corner", A[0], w), A[0]), (at("pupil", c[0], w), c[0]),
                           (at("corner", B[0], w), B[0])], w, second - first, first + tick)
    # the pupil's across label goes first, so labels read across before down
    labels = sorted(across, key=lambda t: not t[0].startswith("pupil"))
    # down the left edge, spread apart where a narrow eye would stack them on each other;
    # the ticks stay where the features are and only the text moves
    th_, fs_ = text_metrics(w)
    (_, hh), _ = cv2.getTextSize("0", cv2.FONT_HERSHEY_SIMPLEX, fs_, th_)
    # ...and below the rows of numbers along the top edge, which they would otherwise
    # run into when a feature sits near the top of the picture
    down, last = [], max(t[2] for t in across) + 4
    for name, y in (("upper lid", top[1]), ("pupil", c[1]), ("lower lid", bot[1])):
        placed = max(y + 6, last + hh + 8)
        down.append((at(name, y, h), tick + 4.0, placed))
        last = placed
    labels += down
    labels.append((f"{eye.irises_wide:.1f} irises wide", 6.0, h - 8.0))
    return labels


def nose_guides(ov, w, h, th, ctx):
    """Noses: the axis, the base line, the tip and the wings, and where each sits.

    Laid out like the eye guides -- markers on the nose, numbers in the margins -- for
    the same reason: on a close-up the numbers would otherwise sit on the drawing.
    """
    from .noses import analyze                 # local: keeps the import graph one-way
    src = ctx.source_img
    if src is None:
        return frame_guides(ov, w, h, th, ctx)
    n = analyze(src)
    sx, sy = w / src.shape[1], h / src.shape[0]
    P = lambda p: np.array([p[0] * sx, p[1] * sy])
    I = lambda q: (int(round(q[0])), int(round(q[1])))
    tip, radix = P(n.tip[:2]), P(n.radix)
    base_c, wl, wr = P(n.along(0, 0)), P(n.along(-n.half_left, 0)), P(n.along(n.half_right, 0))
    s = n.spacing * (sx + sy) / 2

    # the nose's own line: down the ridge of the bridge to the tip, then to the base
    ridge = [P(q) for q in n.bridge]
    dashed_path(ov, ridge + ([base_c + (base_c - ridge[-1]) * 0.12] if not n.side else []), LINE, th)
    dashed(ov, wl + (wl - wr) * 0.15, wr + (wr - wl) * 0.15, LINE, th)       # the base line
    arm = max(5.0, 0.18 * s)
    cv2.line(ov, I(tip - (arm, 0)), I(tip + (arm, 0)), LINE, th, cv2.LINE_AA)
    cv2.line(ov, I(tip - (0, arm)), I(tip + (0, arm)), LINE, th, cv2.LINE_AA)
    # side-on the front of the base line is the tip itself, so only the back wing is marked
    wings = [wl, wr] if not n.side else ([wr] if n.side < 0 else [wl])
    for q in wings:
        cv2.line(ov, I(q - (0, 0.4 * s)), I(q + (0, 0.25 * s)), LINE, th, cv2.LINE_AA)
    for x, y, _a, _b in n.nostrils:
        cv2.circle(ov, I(P((x, y))), max(3, th * 2), LINE, -1, cv2.LINE_AA)
    cv2.circle(ov, I(radix), max(3, th * 2), LINE, -1, cv2.LINE_AA)

    tick = max(6, th * 4)
    for x in [q[0] for q in wings] + [tip[0]]:
        cv2.line(ov, (int(x), 0), (int(x), tick), LINE, th, cv2.LINE_AA)
    for y in (radix[1], tip[1], base_c[1]):
        cv2.line(ov, (0, int(y)), (tick, int(y)), LINE, th, cv2.LINE_AA)
    first, second = label_rows(w)
    across = _margin_rows([(at("wing", q[0], w), q[0]) for q in wings] + [(at("tip", tip[0], w), tip[0])],
                          w, second - first, first + tick)
    labels = sorted(across, key=lambda t: not t[0].startswith("tip"))
    th_, fs_ = text_metrics(w)
    (_, hh), _ = cv2.getTextSize("0", cv2.FONT_HERSHEY_SIMPLEX, fs_, th_)
    last = max(t[2] for t in across) + 4            # below the numbers along the top edge
    for name, y in (("radix", radix[1]), ("tip", tip[1]), ("base", base_c[1])):
        placed = max(y + 6, last + hh + 8)
        labels.append((at(name, y, h), tick + 4.0, placed))
        last = placed
    labels.append((f"{n.length / max(n.width, 1e-6):.1f} widths long", 6.0, h - 8.0))
    return labels


# Modes that draw no thirds grid. The grid is a composition aid; on a close-up of a
# single eye it says nothing useful and ran straight through the eye's own measurements.
def caricature_guides(ov, w, h, th, ctx):
    """Caricature: the centre line and the eye, nose and mouth lines of the *exaggerated*
    face, with where each sits -- the proportions to copy are the caricature's, not the
    photo's."""
    from . import caricature                   # local: keeps the import graph one-way
    src = ctx.source_img
    if src is None:
        return []
    D = caricature._last.get(caricature._key(src)) or caricature.drawing(src, 0.5)
    if not D.found:
        return []
    sx, sy = w / D.shape[1], h / D.shape[0]
    P = lambda p: np.array([p[0] * sx, p[1] * sy])
    c = D.construct
    root, chin = P(c["centre"][0]), P(c["centre"][1])
    down = (chin - root) / (np.linalg.norm(chin - root) + 1e-6)
    (hx, hy), (ha, hb), _ = c["head"]
    top = P((hx, hy)) - down * hb * sy / 2
    dashed(ov, top - down * 0.04 * h, chin + down * 0.04 * h, LINE, th)
    labels = [(at("centre", root[0], w), root[0] + 6, top[1] - 0.02 * h)]
    across = np.array([down[1], -down[0]])
    half = 0.5 * ha * sx
    rows = []
    if len(c["eye_line"]) == 2:
        e0, e1 = P(c["eye_line"][0]), P(c["eye_line"][1])
        rows.append(("eyes", (e0 + e1) / 2))
    rows += [("nose", P(c["nose"])), ("mouth", P(c["mouth"])), ("chin", chin)]
    for name, q in rows:
        a = q - across * half * (1.15 if name == "eyes" else 0.8)
        b = q + across * half * (1.15 if name == "eyes" else 0.8)
        dashed(ov, a, b, LINE, th)
        labels.append((at(name, q[1], h), min(a[0], b[0]), q[1]))
    return labels


NO_GRID = {"eyes", "nose", "caricature"}

GUIDES = {"caricature": caricature_guides, "portrait": face_guides, "object": frame_guides, "hands": hand_guides,
          "body": body_guides, "eyes": eye_guides, "nose": nose_guides}


def draw_guides(sketch, mode, style_key=None, landmarks=(), crop_shape=None, box=None, source_img=None,
                thirds=True):
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
    for i in (1, 2) if mode not in NO_GRID and thirds else ():   # the worksheet has its own grid
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
