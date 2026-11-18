"""Where the nose is in a photo, and its structure: tip, nostrils, wings, root and light.

`analyze(img)` takes a whole photo or a box drawn round a nose and returns a `Nose`. The
Construction style, the guides and the step ladder all draw from it. `propose_box(photo)`
gives the box picker a starting box on the nose, and `note_crop` lets a crop be read with
the whole photo's analysis (see "the photo behind a box").

How it finds the nose: the face detector, given room by padding the photo, places the
nose; the nostrils (face-on) or the nose's outline against the background (side-on) are
then read in a patch cut round that point, turned upright and scaled to a fixed size. The
first version had no face detector and assumed the nose had been framed closely; it found
the nose on one of the sixteen photos a tester sent, and is kept as `_classical`, the
fallback for when no face can be found at all.

Nothing here follows edges for long or trusts a single cue: every measurement is checked
against the proportions of a real nose and pulled back toward them where the image is
unclear, so the answer is always a plausible nose. `Nose.found` says whether it was
located rather than assumed; `notes["source"]` says how.
"""
from dataclasses import dataclass, field

import cv2
import numpy as np

WORK_W = 320                     # everything is measured on a copy this wide

# Average proportions, in units of the nostril spacing s (centre to centre). The alar
# width, wing crease to wing crease, is about two spacings; the length from the root of
# the nose between the eyes to its base is about one and a half alar widths.
WING_HALF = 0.85                 # half the alar width, in s
LENGTH = 1.45                    # radix to base, in alar widths
TIP_R, TIP_RISE = 0.45, 0.55     # tip ball radius, and its centre's height above the base
WING_R, WING_RISE = 0.34, 0.32   # wing circle radius, and its centre's height above the base
PRIOR_W = 0.48                   # alar width as a fraction of the crop width, when nothing is found
PRIOR_BASE = 0.76                # base line as a fraction of the crop height, likewise

# What counts as a nostril: dark, compact, in the lower part of the crop, and a sensible
# size. Pupils are dark and compact too, which is why the vertical limit matters: a crop
# from the eye line down puts the pupils in its top third.
NOSTRIL_TOP = 0.38               # nostrils lie below this fraction of the crop height
NOSTRIL_AREA = (0.0006, 0.03)    # of the crop's area
DARK_PCTS = (3, 6, 10, 15)       # thresholds tried, as percentiles of the lower region
PAIR_DX = (0.12, 0.45)           # nostril spacing, as a fraction of the crop width
PARTNER_CONTRAST = 0.3           # the second nostril, looked for beside the first, may be fainter
MIN_CONTRAST = 0.6               # how much darker than its surroundings, in sd


@dataclass
class Nose:
    """One nose, in the pixel coordinates of the image `analyze` was given."""
    cx: float                    # centre of the base, across
    base_y: float                # the base line, through the bottom of the nostrils
    half_left: float             # wing extent left and right of the centre
    half_right: float
    tilt: float                  # degrees, +ve = right side lower
    spacing: float               # nostril spacing (or its estimate)
    nostrils: list = field(default_factory=list)   # [(x, y, half-width, half-height)]
    tip: tuple = (0.0, 0.0, 1.0)                  # (x, y, r) of the tip ball
    highlight: tuple = None                        # tip highlight, if found
    wings: list = field(default_factory=list)      # [(x, y, r), (x, y, r)] left then right
    radix: tuple = (0.0, 0.0)                      # the root of the nose, between the eyes
    bridge: np.ndarray = None                      # polyline from radix to tip, Nx2
    light: str = None                              # "left" / "right": the lit side, if clear
    found: bool = False                            # the nose was located, not assumed
    view: str = "front"                            # "front", "three-quarter" or "profile"
    side: int = 0                                  # which way the tip points: -1 left, +1 right, 0 front
    yaw: float = 0.0                               # how far the head is turned, 0 front .. ~0.6 profile
    notes: dict = field(default_factory=dict)

    @property
    def width(self):
        return self.half_left + self.half_right

    @property
    def length(self):
        return float(self.base_y - self.radix[1])

    def along(self, dx, dy):
        """A point offset (dx across, dy up) from the base centre, in the nose's own tilt."""
        t = np.deg2rad(self.tilt)
        return (self.cx + dx * np.cos(t) + dy * np.sin(t), self.base_y + dx * np.sin(t) - dy * np.cos(t))


# --------------------------------------------------------------------------- nostrils
def _candidates(g):
    """Dark compact blobs in the lower part of the crop: [(x, y, hw, hh, area, contrast)]."""
    h, w = g.shape
    top = int(h * NOSTRIL_TOP)
    region = g[top:]
    sd = float(g.std()) + 1e-6
    seen, out = set(), []
    for pct in DARK_PCTS:
        thr = float(np.percentile(region, pct))
        m = np.zeros_like(g, np.uint8)
        m[top:] = (region <= thr).astype(np.uint8)
        m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
        n, lab, st, ce = cv2.connectedComponentsWithStats(m, connectivity=8)
        for k in range(1, n):
            area = float(st[k, cv2.CC_STAT_AREA])
            if not (NOSTRIL_AREA[0] * g.size <= area <= NOSTRIL_AREA[1] * g.size):
                continue
            x0, y0, bw, bh = (int(v) for v in st[k, :4])
            if bw < 3 or bh < 2 or bw > 5.0 * bh or bh > 2.5 * bw:
                continue
            if area < 0.45 * bw * bh:                         # not compact: a crease or a hair
                continue
            if x0 <= 0 or x0 + bw >= w or y0 + bh >= h:       # cut by the frame: background
                continue
            key = (int(ce[k][0] // 4), int(ce[k][1] // 4))
            if key in seen:
                continue
            seen.add(key)
            inside = float(g[lab == k].mean())
            pad = max(3, int(0.6 * max(bw, bh)))
            ring = g[max(0, y0 - pad):y0 + bh + pad, max(0, x0 - pad):x0 + bw + pad]
            contrast = (float(np.median(ring)) - inside) / sd
            if contrast >= MIN_CONTRAST:
                out.append((float(ce[k][0]), float(ce[k][1]), bw / 2.0, bh / 2.0, area, contrast))
    return out


def _best_pair(cands, w, h):
    """The two nostrils, or one, or none: (list of candidates, score)."""
    def place(c):
        # nostrils sit near the middle across, in the lower part of the frame
        return -0.8 * abs(c[0] / w - 0.5) - 0.8 * max(0.0, abs(c[1] / h - 0.72) - 0.12)
    best, best_s = [], 0.0
    for c in cands:
        s = c[5] + place(c)
        if s > best_s:
            best, best_s = [c], s
    for i, a in enumerate(cands):
        for b in cands[i + 1:]:
            l, r = (a, b) if a[0] < b[0] else (b, a)
            dx, dy = r[0] - l[0], r[1] - l[1]
            if not (PAIR_DX[0] * w <= dx <= PAIR_DX[1] * w) or abs(dy) > 0.3 * dx:
                continue
            size = max(l[4], r[4]) / max(min(l[4], r[4]), 1.0)
            if size > 4.0:
                continue
            mid = (l[0] + r[0]) / 2
            s = (l[5] + r[5]) - 0.3 * np.log(size) - 3.0 * abs(mid / w - 0.5) \
                - 0.8 * max(0.0, abs(((l[1] + r[1]) / 2) / h - 0.72) - 0.12) + 0.8   # a pair is more convincing
            if s > best_s:
                best, best_s = [l, r], s
    return best, best_s


def _partner(g, c):
    """Look for a fainter second nostril level with a found one.

    On a face lit from the front a nostril can be only a little darker than the skin
    round it; one passes the threshold and its partner does not, and treating the face
    as turned then moved the whole construction off-centre on six front-on test photos.
    So the row through the nostril is searched for a second, fainter dip, placed so that
    the pair is centred in the frame give or take a fifth.
    """
    h, w = g.shape
    x, y, hw, hh = c[0], c[1], c[2], c[3]
    band = g[int(max(0, y - max(2, hh))):int(min(h, y + max(2, hh) + 1))].astype(np.float32)
    prof = cv2.GaussianBlur(band.mean(axis=0).reshape(1, -1), (0, 0), max(1.5, 0.6 * hw)).ravel()
    sd = float(g.std()) + 1e-6
    best = None
    for side in (-1, 1):
        for d in np.arange(PAIR_DX[0] * w, PAIR_DX[1] * w, 1.0):
            px = int(round(x + side * d))
            if not (2 <= px < w - 2):
                continue
            mid = (x + px) / 2
            if abs(mid / w - 0.5) > 0.2:
                continue
            lo = prof[px]
            if lo > prof[px - 2] or lo > prof[px + 2]:
                continue                                    # not a local minimum
            pad = int(max(3, 1.5 * hw))
            around = np.r_[prof[max(0, px - 3 * pad):max(0, px - pad)], prof[px + pad:px + 3 * pad]]
            if around.size < 4:
                continue
            depth = (float(np.median(around)) - lo) / sd
            if depth >= PARTNER_CONTRAST and (best is None or depth > best[1]):
                best = ((float(px), y, hw, hh, c[4], depth), depth)
    return None if best is None else best[0]


# --------------------------------------------------------------------------- the rest
def _wing_extent(g, cx, y, side, s, tilt, sd=None):
    """Distance from the centre to the alar crease on one side, or None.

    Scans outward along the base line from just past the nostril for the darkest valley:
    the crease where the wing meets the cheek.
    """
    h, w = g.shape
    t = np.deg2rad(tilt)
    ds = np.arange(0.55 * s, 1.6 * s, 1.0)
    xs = cx + side * ds * np.cos(t)
    ys = y - 0.25 * s + side * ds * np.sin(t)
    ok = (xs >= 1) & (xs < w - 1) & (ys >= 1) & (ys < h - 1)
    if ok.sum() < 6:
        return None
    prof = g[ys[ok].astype(int), xs[ok].astype(int)].astype(np.float32)
    prof = cv2.GaussianBlur(prof.reshape(-1, 1), (1, 0), max(1.0, 0.08 * s)).ravel()
    d = ds[ok]
    i = int(np.argmin(prof))
    if i == 0 or i == len(prof) - 1:
        return None
    depth = min(prof[:i].max(), prof[i:].max()) - prof[i]
    return float(d[i]) if depth > 0.25 * (sd or float(g.std()) + 1e-6) else None


def _highlight(g, x, y, s, sd=None):
    """The brightest compact spot near the tip, if it stands out."""
    h, w = g.shape
    x0, x1 = int(max(0, x - 0.55 * s)), int(min(w, x + 0.55 * s))
    y0, y1 = int(max(0, y - 1.2 * s)), int(min(h, y - 0.15 * s))
    if x1 - x0 < 4 or y1 - y0 < 4:
        return None
    win = g[y0:y1, x0:x1]
    thr = float(np.percentile(win, 96))
    if thr - float(np.median(win)) < 0.35 * (sd or float(g.std()) + 1e-6):
        return None
    m = (win >= thr).astype(np.uint8)
    n, lab, st, ce = cv2.connectedComponentsWithStats(m, connectivity=8)
    if n < 2:
        return None
    k = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
    return float(ce[k][0] + x0), float(ce[k][1] + y0)


def _lit_side(g, nose):
    """Which side plane is brighter, if clearly."""
    h, w = g.shape
    top = int(max(0, nose.radix[1] + 0.35 * nose.length))
    bot = int(min(h, nose.base_y - 0.4 * nose.spacing))
    if bot - top < 4:
        return None
    xb = nose.bridge[0, 0]
    lw = (int(max(0, xb - nose.half_left * 0.9)), int(max(0, xb - 0.15 * nose.spacing)))
    rw = (int(min(w, xb + 0.15 * nose.spacing)), int(min(w, xb + nose.half_right * 0.9)))
    if lw[1] - lw[0] < 3 or rw[1] - rw[0] < 3:
        return None
    left = float(np.median(g[top:bot, lw[0]:lw[1]]))
    right = float(np.median(g[top:bot, rw[0]:rw[1]]))
    if abs(left - right) < 0.25 * (float(g.std()) + 1e-6):
        return None
    return "left" if left > right else "right"


# --------------------------------------------------------------------------- analysis
_cache = {}


def _classical(img):
    """The nose read from the crop alone, with no face to anchor it.

    The first version of Nose mode was only this, and it assumed the user had framed the
    nose closely: it looks for nostrils in the lower middle of the frame. On a whole photo,
    which is what the default box hands it, it found the nose on one of sixteen test
    photos. It is now the fallback for when no face can be found at all.
    """
    H, W = img.shape[:2]
    sc = WORK_W / W
    small = cv2.resize(img, (WORK_W, max(8, int(round(H * sc)))),
                       interpolation=cv2.INTER_AREA if sc < 1 else cv2.INTER_CUBIC)
    g = cv2.GaussianBlur(cv2.createCLAHE(2.0, (4, 4)).apply(cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)), (0, 0), 1.5)
    h, w = g.shape

    pair, score = _best_pair(_candidates(g), w, h)
    partnered = False
    if len(pair) == 1:
        mate = _partner(g, pair[0])
        if mate is not None:
            pair, partnered = sorted([pair[0], mate], key=lambda c: c[0]), True
    notes = {"pair_score": float(score), "nostrils_seen": len(pair), "partnered": partnered}
    if len(pair) == 2:
        l, r = pair
        s = r[0] - l[0]
        tilt = float(np.degrees(np.arctan2(r[1] - l[1], r[0] - l[0])))
        cx = (l[0] + r[0]) / 2
        base_y = (l[1] + l[3] + r[1] + r[3]) / 2
    elif len(pair) == 1:
        # one nostril: a turned head. Its partner is hidden behind the tip, so the centre
        # sits toward the middle of the frame from it by about half a spacing
        c = pair[0]
        s = PRIOR_W * w / (2 * WING_HALF)       # not from the nostril's size: seen from the side it is huge
        side = 1 if c[0] < w / 2 else -1
        cx, tilt = c[0] + side * 0.5 * s, 0.0
        base_y = c[1] + c[3]
    else:
        s = PRIOR_W * w / (2 * WING_HALF)
        cx, base_y, tilt = w / 2, h * PRIOR_BASE, 0.0

    nose = Nose(cx=cx, base_y=base_y, half_left=WING_HALF * s, half_right=WING_HALF * s,
                tilt=tilt, spacing=s, found=bool(pair), notes=notes)
    if len(pair) == 2:
        # each wing from its crease where the image shows one, pulled halfway to average
        for side, attr in ((-1, "half_left"), (1, "half_right")):
            m = _wing_extent(g, cx, base_y, side, s, tilt)
            if m is not None:
                setattr(nose, attr, float(0.5 * m + 0.5 * WING_HALF * s))
    # the user framed the nose, so it does not run off the frame: a misread pair far to one
    # side otherwise put a wing past the edge of the picture
    nose.half_left = float(min(nose.half_left, max(0.25 * s, cx - 1)))
    nose.half_right = float(min(nose.half_right, max(0.25 * s, w - 1 - cx)))
    nose.nostrils = [(c[0], c[1], c[2], c[3]) for c in pair]

    tx, ty = nose.along(0.0, TIP_RISE * s)
    hl = _highlight(g, tx, base_y, s) if pair else None
    if hl is not None:
        nose.highlight = hl
        tx = 0.5 * tx + 0.5 * hl[0]                  # the tip ball follows its highlight across
    nose.tip = (tx, ty, TIP_R * s)
    nose.wings = []
    for side, half in ((-1, nose.half_left), (1, nose.half_right)):
        wx, wy = nose.along(side * (half - WING_R * s), WING_RISE * s)
        nose.wings.append((wx, wy, WING_R * s))
    radix_y = max(2.0, base_y - LENGTH * nose.width)
    # The bridge runs straight up the nose's axis, square to the base line. It used to be
    # measured, from the brightest ridge above the tip, and on a third of the test crops
    # that ridge was a cheek, a lit eyelid or a glasses rim, so the bridge leaned the wrong
    # way -- on front-on noses too. In a three-quarter view a real bridge does lean toward
    # the far eye, and with no eyes to measure from that lean is not modelled: a straight
    # bridge is a little off there, where a measured one was badly off anywhere.
    t = np.deg2rad(tilt)
    nose.bridge = np.array([[tx, ty], [tx + (ty - radix_y) * np.tan(t), radix_y]])
    nose.radix = (float(nose.bridge[1, 0]), float(radix_y))
    nose.light = _lit_side(g, nose)

    # back to the caller's pixels
    k = 1 / sc
    nose.cx, nose.base_y, nose.spacing = nose.cx * k, nose.base_y * k, nose.spacing * k
    nose.half_left, nose.half_right = nose.half_left * k, nose.half_right * k
    nose.nostrils = [(x * k, y * k, a * k, b * k) for x, y, a, b in nose.nostrils]
    nose.tip = (nose.tip[0] * k, nose.tip[1] * k, nose.tip[2] * k)
    nose.highlight = None if nose.highlight is None else (nose.highlight[0] * k, nose.highlight[1] * k)
    nose.wings = [(x * k, y * k, r * k) for x, y, r in nose.wings]
    nose.radix = (nose.radix[0] * k, nose.radix[1] * k)
    nose.bridge = nose.bridge * k
    nose.notes["source"] = "classical"
    return nose


# --------------------------------------------------------------------------- the face
# The face detector, used here for its nose landmark. On its own it only finds faces that
# are whole and comfortably inside the frame -- five of the sixteen test photos -- but
# given room it does much better: padded out with plain border it found a face on all
# sixteen, close-ups of a nose and mouth included, and on eight of nine noses framed as
# tightly as a person would draw the box. Its threshold is lower than Portrait mode's
# because here the photo is known to contain a face; the price is the odd false face,
# which agreement across paddings guards against.
PADS = (0.0, 0.25, 0.5, 0.75, 1.0)   # border added on every side, as a fraction of the longer side
DET_SCORE = 0.5
DET_SIDE = 640                       # the detector sees the padded photo at this size
AGREE = 0.3                          # nose points this close (in eye-to-mouth lengths) are one face
MIN_AGREE = 2                        # ...and at least this many paddings must find it

# How turned the head is, from the detector's five points: how far the nose sits off the
# line from between the eyes to the middle of the mouth, plus how foreshortened the eyes
# are. Calibrated on the sixteen test photos, so treat the boundaries as approximate.
YAW_3Q, YAW_PROFILE = 0.15, 0.34

E = 160.0                            # eye-to-mouth length in the working patch, pixels
DEPTH_COST = 1.0                     # how much a nostril candidate is marked down per unit short of the darkest tone
PATCH = (352, 272)                   # its size; the detector's nose point lands at (176, 160)
PC = (176.0, 160.0)

_det = None


def _detector():
    global _det
    if _det is None:
        from .faces import YUNET_PATH, yunet_available
        if not yunet_available():
            return None
        try:
            _det = cv2.FaceDetectorYN.create(str(YUNET_PATH), "", (320, 320), DET_SCORE, 0.3, 50)
        except Exception:                      # old OpenCV build, bad model file
            return None
    return _det


@dataclass
class Face:
    """The detector's five points, agreed across paddings, in the image's own pixels."""
    pts: np.ndarray        # eye on the image's left, eye on the right, nose, mouth left, mouth right
    score: float           # summed over the paddings that agreed
    agree: int             # how many paddings found it

    @property
    def eye_mid(self):
        return (self.pts[0] + self.pts[1]) / 2

    @property
    def mouth_mid(self):
        return (self.pts[3] + self.pts[4]) / 2

    @property
    def nose(self):
        return self.pts[2]

    @property
    def d_em(self):
        return float(np.linalg.norm(self.eye_mid - self.mouth_mid))

    @property
    def up(self):
        v = self.eye_mid - self.mouth_mid
        return v / (np.linalg.norm(v) + 1e-6)

    @property
    def across(self):
        u = self.up
        return np.array([-u[1], u[0]])

    @property
    def tilt(self):
        a = self.across
        return float(np.degrees(np.arctan2(a[1], a[0])))

    @property
    def offset(self):
        """The nose's distance off the eye-to-mouth centre line, in eye-to-mouth lengths."""
        return float(np.dot(self.nose - self.eye_mid, self.across) / max(self.d_em, 1e-6))

    @property
    def yaw(self):
        iod = float(np.linalg.norm(self.pts[1] - self.pts[0]))
        return abs(self.offset) + 0.5 * max(0.0, 0.9 - iod / max(self.d_em, 1e-6))


def find_face(img):
    """The face the nose belongs to, or None. Several paddings, and only an answer that
    at least two of them agree on: a single detection on its own is too often a false face
    in a close-up, where the detector has only a nose and a mouth to go on."""
    det = _detector()
    if det is None:
        return None
    H, W = img.shape[:2]
    fill = tuple(int(c) for c in img.reshape(-1, 3).mean(0))
    found = []
    for i, pad in enumerate(PADS):
        P = int(pad * max(H, W))
        big = cv2.copyMakeBorder(img, P, P, P, P, cv2.BORDER_CONSTANT, value=fill) if P else img
        s = DET_SIDE / max(big.shape[:2])
        small = cv2.resize(big, None, fx=s, fy=s, interpolation=cv2.INTER_AREA if s < 1 else cv2.INTER_CUBIC)
        try:
            det.setInputSize((small.shape[1], small.shape[0]))
            _, res = det.detect(small)
        except Exception:
            return None
        for r in (res if res is not None else [])[:3]:
            pts = np.array([[r[4 + 2 * j] / s - P, r[5 + 2 * j] / s - P] for j in range(5)])
            found.append((float(r[14]), pts, i))
    best = None
    for score, pts, _i in found:
        em = np.linalg.norm((pts[0] + pts[1]) / 2 - (pts[3] + pts[4]) / 2)
        group = [f for f in found if np.linalg.norm(f[1][2] - pts[2]) <= AGREE * em]
        pads = len({f[2] for f in group})
        support = sum(f[0] for f in group)
        if pads >= MIN_AGREE and (best is None or support > best[0]):
            best = (support, pads, group)
    if best is None:
        return None
    support, pads, group = best
    w = np.array([f[0] for f in group])
    pts = np.tensordot(w, np.array([f[1] for f in group]), axes=1) / w.sum()
    return Face(pts=pts, score=float(support), agree=int(pads))


# --------------------------------------------------------------------------- the patch
def _patch(img, face):
    """The region round the nose, turned upright and scaled so every nose is one size.

    Returns (grey patch, contrast measure, affine image->patch, affine patch->image). In the
    patch the face's axis is vertical and the eye-to-mouth length is E pixels, so every
    threshold below is in fixed units whether the nose filled the photo or was a speck in
    it. Where the patch runs past the photo's edge the warp smears the edge pixels out; the
    contrast equalisation is therefore done on the real pixels before warping, and the
    contrast measure is taken only over the part of the patch inside the photo -- on a
    tightly framed nose the smear was a third of the patch and doubled the measure.
    """
    k = E / max(face.d_em, 1e-6)
    pre = 1.0
    src = img
    if k < 0.5:                                    # shrink with area averaging first, then warp
        pre = k * 1.6
        src = cv2.resize(img, None, fx=pre, fy=pre, interpolation=cv2.INTER_AREA)
    kk = k / pre
    a, u = face.across, face.up
    n = face.nose * pre
    M = np.array([[kk * a[0], kk * a[1], PC[0] - kk * (a[0] * n[0] + a[1] * n[1])],
                  [-kk * u[0], -kk * u[1], PC[1] + kk * (u[0] * n[0] + u[1] * n[1])]], np.float64)
    inv_src = cv2.invertAffineTransform(M)
    corners = np.array([_to(inv_src, x, y) for x, y in ((0, 0), (PATCH[0], 0), (0, PATCH[1]), PATCH)])
    sh, sw = src.shape[:2]
    x0, y0 = (int(max(0, np.floor(v))) for v in corners.min(0))
    x1, y1 = int(min(sw, np.ceil(corners[:, 0].max()) + 1)), int(min(sh, np.ceil(corners[:, 1].max()) + 1))
    grey = cv2.cvtColor(src, cv2.COLOR_BGR2GRAY)
    if x1 - x0 >= 8 and y1 - y0 >= 8:
        sub = grey[y0:y1, x0:x1]
        tiles = int(np.clip(round(max(sub.shape) * kk / (0.55 * E)), 2, 8))
        grey = grey.copy()
        grey[y0:y1, x0:x1] = cv2.createCLAHE(2.0, (tiles, tiles)).apply(sub)
    grey = cv2.GaussianBlur(grey, (0, 0), max(0.6, 1.2 / kk))
    g = cv2.warpAffine(grey, M, PATCH, flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    valid = cv2.warpAffine(np.ones((sh, sw), np.uint8), M, PATCH, flags=cv2.INTER_NEAREST,
                           borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    sd = float(g[valid > 0].std()) + 1e-6 if valid.any() else float(g.std()) + 1e-6
    M_img = M @ np.array([[pre, 0, 0], [0, pre, 0], [0, 0, 1]], np.float64)    # from original pixels
    return g, sd, M_img, cv2.invertAffineTransform(M_img)


def _to(M, x, y):
    return (float(M[0, 0] * x + M[0, 1] * y + M[0, 2]), float(M[1, 0] * x + M[1, 1] * y + M[1, 2]))


# --------------------------------------------------------------------------- reading the patch
def _blobs(g, x0, x1, y0, y1, max_aspect=4.0, sd=None):
    """Dark compact shapes in a window of the patch: [(x, y, hw, hh, area, contrast, depth)].

    `depth` is how close the shape's mean is to the darkest tone in the window, in units
    of the contrast measure: 0 for the very darkest. A nostril is a hole and among the
    darkest things on a face; a cluster of freckles beside the nose is dark and compact
    too, but nowhere near as dark, and on one test photo it out-scored the nostrils.
    """
    h, w = g.shape
    x0, x1, y0, y1 = int(max(0, x0)), int(min(w, x1)), int(max(0, y0)), int(min(h, y1))
    if x1 - x0 < 6 or y1 - y0 < 6:
        return []
    win = g[y0:y1, x0:x1]
    sd = sd or float(g.std()) + 1e-6
    floor = float(np.percentile(win, 1))
    seen, out = set(), []
    for pct in (3, 6, 10, 15, 22):
        thr = float(np.percentile(win, pct))
        m = (win <= thr).astype(np.uint8)
        m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
        n, lab, st, ce = cv2.connectedComponentsWithStats(m, connectivity=8)
        for k in range(1, n):
            area = float(st[k, cv2.CC_STAT_AREA])
            bx, by, bw, bh = (int(v) for v in st[k, :4])
            if not (18 <= area <= 0.06 * E * E) or bw < 3 or bh < 2:
                continue
            if bw > max_aspect * bh or bh > 2.5 * bw or area < 0.4 * bw * bh:
                continue
            cx, cy = float(ce[k][0]) + x0, float(ce[k][1]) + y0
            key = (int(cx // 4), int(cy // 4))
            if key in seen:
                continue
            seen.add(key)
            inside = float(win[lab == k].mean())
            pad = max(3, int(0.6 * max(bw, bh)))
            ring = g[max(0, y0 + by - pad):y0 + by + bh + pad, max(0, x0 + bx - pad):x0 + bx + bw + pad]
            contrast = (float(np.median(ring)) - inside) / sd
            if contrast >= 0.5:
                out.append((cx, cy, bw / 2.0, bh / 2.0, area, contrast, (inside - floor) / sd))
    return out


def _front_nostrils(g, sd=None):
    """The nostril pair under the detector's nose point, in an upright, scaled patch."""
    cands = _blobs(g, PC[0] - 0.42 * E, PC[0] + 0.42 * E, PC[1] - 0.12 * E, PC[1] + 0.36 * E, sd=sd)
    expect_y = PC[1] + 0.12 * E
    best, best_s = [], 0.0
    for c in cands:                                    # one, if nothing pairs up
        s = c[5] - 3.0 * abs(c[0] - PC[0]) / E - 2.0 * abs(c[1] - expect_y) / E - DEPTH_COST * c[6]
        if s > best_s:
            best, best_s = [c], s
    for i, a in enumerate(cands):
        for b in cands[i + 1:]:
            l, r = (a, b) if a[0] < b[0] else (b, a)
            dx, dy = r[0] - l[0], r[1] - l[1]
            # nostril centres sit 0.25-0.4 of E apart face-on on the test photos; closer
            # than 0.16 is two specks of one nostril, or a nostril and its own shadow
            if not (0.16 * E <= dx <= 0.42 * E) or abs(dy) > 0.3 * dx:
                continue
            ratio = max(l[4], r[4]) / max(min(l[4], r[4]), 1.0)
            if ratio > 4.0:
                continue
            mx, my = (l[0] + r[0]) / 2, (l[1] + r[1]) / 2
            if abs(mx - PC[0]) > 0.22 * E or not (-0.08 * E <= my - PC[1] <= 0.3 * E):
                continue
            s = l[5] + r[5] - 0.3 * np.log(ratio) - 3.0 * abs(mx - PC[0]) / E - 2.0 * abs(my - expect_y) / E + 0.8 \
                - DEPTH_COST * (l[6] + r[6])
            if s > best_s:
                best, best_s = [l, r], s
    return best


def _front_partner(g, c, sd=None):
    """A fainter second nostril level with a found one, placed so that the pair centres on
    the detector's nose point. The same reason as `_partner`: on a front-lit face one
    nostril passes the darkness threshold and its partner does not."""
    h, w = g.shape
    x, y, hw, hh = c[0], c[1], c[2], c[3]
    band = g[int(max(0, y - max(2, hh))):int(min(h, y + max(2, hh) + 1))].astype(np.float32)
    prof = cv2.GaussianBlur(band.mean(axis=0).reshape(1, -1), (0, 0), max(1.5, 0.6 * hw)).ravel()
    sd = sd or float(g.std()) + 1e-6
    best = None
    for d in np.arange(0.1 * E, 0.42 * E, 1.0):
        for side in (-1, 1):
            px = int(round(x + side * d))
            if not (2 <= px < w - 2) or abs((x + px) / 2 - PC[0]) > 0.15 * E:
                continue
            lo = prof[px]
            if lo > prof[px - 2] or lo > prof[px + 2]:
                continue
            pad = int(max(3, 1.5 * hw))
            around = np.r_[prof[max(0, px - 3 * pad):max(0, px - pad)], prof[px + pad:px + 3 * pad]]
            if around.size < 4:
                continue
            depth = (float(np.median(around)) - lo) / sd
            if depth >= PARTNER_CONTRAST and (best is None or depth > best[1]):
                best = ((float(px), y, hw, hh, c[4], depth, c[6]), depth)
    return None if best is None else best[0]


def _silhouette_tip(g, side, sd=None):
    """Where the nose ends, side-on: the most forward point of its outline.

    Each row through the nose is followed outward from the detector's nose point, which
    sits a little inside the tip on a turned head, to the first strong edge -- nose
    against background, or against the far cheek. The first, not the strongest: a lock of
    hair beside the nose makes a stronger edge than the nose itself on one test photo.
    The tip is the row whose edge reaches furthest, after a running median so that one
    stray row cannot pull it out -- looked for only from a little above the detector's
    nose point down. On a head tipped back the bridge reaches further forward than the
    tip does, and with the whole band searched the tip of one test nose went up onto it.
    """
    h, w = g.shape
    f = g.astype(np.float32)
    rows = np.arange(int(PC[1] - 0.3 * E), int(PC[1] + 0.16 * E), 2)
    start = PC[0] - side * 0.12 * E
    stop = PC[0] + side * 0.55 * E
    xs = np.arange(start, stop, side * 1.0)
    xs = xs[(xs >= 1) & (xs < w - 1)]
    if len(xs) < 10:
        return None
    sd = sd or float(g.std()) + 1e-6
    edges = []
    for y in rows:
        if not (1 <= y < h - 1):
            edges.append(np.nan)
            continue
        prof = cv2.GaussianBlur(f[y - 1:y + 2, :].mean(axis=0).reshape(1, -1), (0, 0), 2.0).ravel()[xs.astype(int)]
        grad = np.abs(np.gradient(prof))
        top = grad.max()
        if top < 0.04 * sd:
            edges.append(np.nan)
            continue
        hits = np.where((grad >= 0.55 * top) & (grad >= np.roll(grad, 1)) & (grad >= np.roll(grad, -1)))[0]
        hits = hits[hits > 2]
        edges.append(float(xs[hits[0]]) if len(hits) else np.nan)
    e = np.array(edges)
    if np.isfinite(e).sum() < 5:
        return None
    med = np.array([np.nanmedian(e[max(0, i - 2):i + 3]) if np.isfinite(e[max(0, i - 2):i + 3]).any() else np.nan
                    for i in range(len(e))])
    reach = side * (med - PC[0])
    reach[rows < PC[1] - 0.12 * E] = np.nan
    if not np.isfinite(reach).any():
        return None
    i = int(np.nanargmax(reach))
    return float(med[i] - side * 0.02 * E), float(rows[i])


def _side_nostril(g, tip, side, sd=None):
    """The near nostril on a turned head: dark, behind and below the tip.

    Size-limited and placed: on one bearded test face the darkest compact shape behind
    the tip was the shadow of the moustache, three times a nostril's area and lower down.
    Measured side-on, nostrils run 0.007 to 0.017 of E squared.
    """
    tx, ty = tip
    lo, hi = sorted((tx - side * 0.55 * E, tx - side * 0.03 * E))
    cands = [c for c in _blobs(g, lo, hi, ty - 0.04 * E, ty + 0.3 * E, max_aspect=6.0, sd=sd)
             if c[4] <= 0.03 * E * E]
    if not cands:
        return None
    ex, ey = tx - side * 0.2 * E, ty + 0.08 * E
    return max(cands, key=lambda c: c[5] - 2.5 * np.hypot(c[0] - ex, c[1] - ey) / E)


def _guided(img, face):
    """Read the nose with the face to anchor it. Returns a Nose in the image's pixels."""
    g, sd, M, inv = _patch(img, face)
    yaw = face.yaw
    side = 0
    view = "front"
    if yaw >= YAW_3Q:
        side = 1 if face.offset > 0 else -1
        view = "profile" if yaw >= YAW_PROFILE else "three-quarter"
    notes = {"source": "face", "agree": face.agree, "yaw": float(yaw), "em": face.d_em}

    # Everything below is in patch pixels, upright, with the eye-to-mouth length E.
    nostrils = []
    found_tip = None
    if view == "front":
        pair = _front_nostrils(g, sd)
        if len(pair) == 1:
            mate = _front_partner(g, pair[0], sd)
            if mate is not None:
                pair = sorted([pair[0], mate], key=lambda c: c[0])
                notes["partnered"] = True
        if len(pair) == 1:
            # Face-on, both nostrils are there even when one is too faint to find, and the
            # face gives the centre line: the missing one is the found one's mirror image --
            # but only when the found one sits where a nostril can. Mirroring doubles any
            # error, and a "nostril" found out on a wing crease made a nose twice as wide.
            c = pair[0]
            off = abs(c[0] - PC[0])
            if 0.05 * E <= off <= 0.21 * E and -0.06 * E <= c[1] - PC[1] <= 0.3 * E:
                pair = sorted([c, (2 * PC[0] - c[0], c[1], c[2], c[3], c[4], 0.0, c[6])], key=lambda q: q[0])
                notes["mirrored"] = True
            else:
                pair = []                          # not where a nostril would be
        nostrils = list(pair)
        if len(pair) == 2:
            l, r = pair
            s = r[0] - l[0]
            cx = (l[0] + r[0]) / 2
            base = (l[1] + l[3] + r[1] + r[3]) / 2
            ptilt = float(np.degrees(np.arctan2(r[1] - l[1], r[0] - l[0])))
            ptilt = ptilt if abs(ptilt) < 8 else 0.0  # a pair at a steep angle is not trusted
        else:                                      # nothing found: the face's own proportions
            s = 0.5 * E / (2 * WING_HALF)
            cx, base, ptilt = PC[0], PC[1] + 0.15 * E, 0.0
        half_l = half_r = WING_HALF * s
        if len(pair) == 2:
            for sd_, attr in ((-1, "l"), (1, "r")):
                m = _wing_extent(g, cx, base, sd_, s, 0.0, sd)
                if m is not None:
                    if attr == "l":
                        half_l = 0.5 * m + 0.5 * WING_HALF * s
                    else:
                        half_r = 0.5 * m + 0.5 * WING_HALF * s
        # a face-on nose is 0.46-0.56 of E wide on the test photos; held to a generous
        # range round that, so a misread wing cannot make it half the face
        width = half_l + half_r
        if not (0.3 * E <= width <= 0.75 * E):
            k_ = float(np.clip(width, 0.3 * E, 0.75 * E)) / width
            half_l, half_r = half_l * k_, half_r * k_
        tip = (cx, base - TIP_RISE * s)
        hl = _highlight(g, tip[0], base, s, sd) if len(pair) == 2 else None
        if hl is not None:
            tip = (0.5 * tip[0] + 0.5 * hl[0], tip[1])
        if len(pair) < 2:                              # the detector's point is the better tip
            tip = (0.5 * tip[0] + 0.5 * PC[0], 0.5 * tip[1] + 0.5 * PC[1])
        wings = [(cx - (half_l - WING_R * s), base - WING_RISE * s, WING_R * s),
                 (cx + (half_r - WING_R * s), base - WING_RISE * s, WING_R * s)]
    else:
        ptilt = 0.0
        found_tip = _silhouette_tip(g, side, sd)
        if found_tip is not None and abs(found_tip[0] - PC[0]) > 0.35 * E:
            found_tip = None                           # ran on past the nose
        if found_tip is None:
            tip = (PC[0] + side * 0.04 * E, PC[1])
        elif view == "three-quarter":
            # The outline is the far side of the nose on a strong turn and only the edge
            # of the tip ball on a mild one, and the detector's five points cannot tell
            # the two apart (see the README). Halfway hedges between them.
            tip = ((found_tip[0] + PC[0]) / 2, (found_tip[1] + PC[1]) / 2)
        else:
            tip = found_tip
        notes["tip_from_outline"] = found_tip is not None
        nos = _side_nostril(g, tip, side, sd)
        if nos is not None:
            nostrils = [nos]
            base = nos[1] + nos[3]
            wing_x = nos[0] - side * 0.13 * E
        else:
            base = tip[1] + 0.12 * E
            wing_x = tip[0] - side * 0.36 * E
        wing_r = 0.1 * E
        back = wing_x - side * wing_r                  # the back of the near wing
        cx = (tip[0] + back) / 2
        s = abs(tip[0] - back) / (2 * WING_HALF)
        half_front = abs(tip[0] - cx)
        half_l, half_r = (half_front, abs(back - cx)) if side < 0 else (abs(back - cx), half_front)
        wings = [(wing_x, base - 0.06 * E, wing_r)]
        if view == "three-quarter":                    # the far wing, mostly behind the tip
            wings.append((tip[0] + side * 0.02 * E, base - 0.05 * E, 0.6 * wing_r))
        hl = _highlight(g, tip[0], base, max(s, 0.1 * E), sd)

    # the root of the nose: at eye level, between the eyes face-on and moving forward
    # toward the bridge's silhouette as the head turns
    ex, ey = _to(M, *face.eye_mid)
    t = float(np.clip((yaw - 0.05) / (YAW_PROFILE - 0.05), 0.0, 1.0))
    rx = ex + (tip[0] - ex) * 0.75 * t
    ry = ey + 0.05 * E
    ridge = None

    # The face mesh, where it agrees with the detector, replaces the parts that were
    # placed by average proportions: the base line, the wings and the ridge of the bridge.
    # A tester found the wing circles off the curve of the wings and the bridge line off
    # the nose; both were templates. The tip side-on still comes from the outline, which
    # the mesh places inside the nose on a profile (measured: 11 of 16 with the mesh's tip
    # alone, 13 with the outline's).
    mesh = _mesh_in_patch(img, face, M)
    if mesh is not None:
        Q = lambda i: mesh[i]
        notes["mesh"] = True
        base = float(Q(MESH_BASE)[1])
        circles = [_wing_circle(mesh, ring) for ring in MESH_WING_RINGS]   # image-left, image-right
        if view == "front":
            # The mesh puts the wings' outer edges about a fifth too wide and unevenly
            # from side to side, so the width is taken across both and scaled: measured
            # on the six face-on test noses, 0.085 of the nose's width from the marked
            # edges, against 0.12 for the image-based edges -- with the scale fitted on
            # those same six, so expect less on new photos.
            lo = float(mesh[list(MESH_WING_RINGS[0]), 0].min())
            hi = float(mesh[list(MESH_WING_RINGS[1]), 0].max())
            cx, half = (lo + hi) / 2, (hi - lo) / 2 * MESH_WIDTH
            half_l = half_r = half
            rb = WING_BALL * half
            wings = [(cx - half + rb, circles[0][1], rb), (cx + half - rb, circles[1][1], rb)]
            s = (half_l + half_r) / (2 * WING_HALF)
            a, b = Q(MESH_TIP_TOP), Q(MESH_TIP)
            tip = (float((a[0] + b[0]) / 2), float((a[1] + b[1]) / 2))
            tip_ball = float(np.clip(1.1 * np.hypot(*(b - a)), 0.06 * E, 0.16 * E))
            notes["tip_ball"] = tip_ball
        else:
            near = circles[1] if side < 0 else circles[0]
            wx, wy, wr = near
            if found_tip is None:
                tip = tuple(float(v) for v in Q(MESH_TIP))
            back = wx - side * wr
            cx = (tip[0] + back) / 2
            s = abs(tip[0] - back) / (2 * WING_HALF)
            half_front = abs(tip[0] - cx)
            half_l, half_r = (half_front, abs(back - cx)) if side < 0 else (abs(back - cx), half_front)
            wings = [near]
            if view == "three-quarter":
                far = circles[0] if side < 0 else circles[1]
                # only where it would peek out past the tip ball, not hide inside it
                if (far[0] - wx) * side > 0 and np.hypot(far[0] - tip[0], far[1] - tip[1]) > 0.11 * E:
                    wings.append((far[0], far[1], 0.6 * far[2]))
        rx, ry = (float(v) for v in Q(MESH_ROOT))
        ridge = [tuple(float(v) for v in Q(i)) for i in MESH_RIDGE] + [tip]

    # back to the image's pixels
    k = 1.0 / np.hypot(M[0, 0], M[0, 1])               # patch pixels -> image pixels
    P = lambda x, y: _to(inv, x, y)
    cxi, basei = P(cx, base)
    nose = Nose(cx=cxi[0] if False else 0.0, base_y=0.0, half_left=half_l * k, half_right=half_r * k,
                tilt=face.tilt + ptilt, spacing=s * k, found=True, view=view, side=side,
                yaw=float(yaw), notes=notes)
    nose.cx, nose.base_y = P(cx, base)
    nose.nostrils = [(*P(c[0], c[1]), c[2] * k, c[3] * k) for c in nostrils]
    ti = P(*tip)
    tip_r = (TIP_R * s if view == "front" else 0.11 * E) * k
    nose.tip = (ti[0], ti[1], tip_r)
    nose.highlight = None if hl is None else P(*hl)
    nose.wings = [(*P(x, y), r * k) for x, y, r in wings]
    nose.radix = P(rx, ry)
    # the bridge from the root down to the tip: the mesh's ridge where there is one
    nose.bridge = np.array([P(*q) for q in ridge]) if ridge else np.array([nose.radix, ti])
    if "tip_ball" in notes:
        nose.tip = (ti[0], ti[1], notes.pop("tip_ball") * k)
    lit = _lit_side_patch(g, tip, base, s, sd)
    nose.light = lit
    notes["nostrils_seen"] = len(nostrils)
    notes.setdefault("partnered", False)
    return nose


# Face-mesh indices, chosen by drawing all 468 on the test noses: the ridge from between
# the eyes to just above the tip, the tip ball (top, bottom), where the columella meets the
# lip, and a ring of points round each wing (image-left, then image-right).
MESH_ROOT = 168
MESH_RIDGE = (168, 6, 197, 195, 5)
MESH_TIP_TOP, MESH_TIP = 4, 1
MESH_BASE = 2
MESH_WING_RINGS = ((64, 48, 98, 240, 219, 115), (294, 278, 327, 460, 439, 344))
MESH_AGREE = 0.35          # mesh tip this close to the detector's nose point, in E
MESH_WIDTH = 1 / 1.2       # the mesh's wing span runs about a fifth wide (see _guided)
WING_BALL = 0.4            # a wing ball's radius, as a share of half the nose's width


def _mesh_in_patch(img, face, M):
    """The face mesh in patch pixels, or None if unavailable or not agreeing with the
    detector's nose point (a mesh started from a false face lands on nothing useful)."""
    from . import landmarks
    if not landmarks.mesh_available():
        return None
    pts = landmarks.face_mesh(img, face.eye_mid, face.mouth_mid)
    if pts is None:
        return None
    q = pts @ M[:, :2].T + M[:, 2]
    if np.hypot(*(q[MESH_TIP] - np.array(PC))) > MESH_AGREE * E:
        return None
    return q


def _wing_circle(mesh, ring):
    """A ball for one wing: centred in its ring of mesh points, reaching the outermost."""
    P = mesh[list(ring)]
    c = P.mean(0)
    r = float(np.clip(np.max(np.hypot(*(P - c).T)), 0.05 * E, 0.13 * E))
    return (float(c[0]), float(c[1]), r)


def _lit_side_patch(g, tip, base, s, sd=None):
    """Which side of the nose is brighter, in the upright patch, if clearly."""
    h, w = g.shape
    y0, y1 = int(max(0, tip[1] - 0.45 * E)), int(min(h, base - 0.05 * E))
    if y1 - y0 < 4:
        return None
    lx0, lx1 = int(max(0, tip[0] - 1.3 * s)), int(max(0, tip[0] - 0.2 * s))
    rx0, rx1 = int(min(w, tip[0] + 0.2 * s)), int(min(w, tip[0] + 1.3 * s))
    if lx1 - lx0 < 3 or rx1 - rx0 < 3:
        return None
    left, right = float(np.median(g[y0:y1, lx0:lx1])), float(np.median(g[y0:y1, rx0:rx1]))
    if abs(left - right) < 0.25 * (sd or float(g.std()) + 1e-6):
        return None
    return "left" if left > right else "right"


# --------------------------------------------------------------------------- the photo behind a box
# The nose is found far more reliably on the whole photo than inside a box drawn round it
# -- measured, 13 of the 16 test photos against 10 -- because the face detector needs the
# eyes and the mouth to place the nose, and because statistics taken inside a tight box
# depend on where its edges fall. So the nose is read once, on the whole photo, and when
# the app crops the photo it says where the crop came from: the crop then gets that same
# reading, moved into its own pixels. The renderers only ever resize the crop, so a small
# thumbnail recognises it; any other image -- an example tile, a test fixture -- is read
# on its own.
_photos = {}
_context = None


def _key(img):
    return (img.shape, hash(img.tobytes()[::97]))


def _thumb(img):
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img
    return cv2.resize(g, (16, 16), interpolation=cv2.INTER_AREA).astype(np.float32)


def photo_nose(photo):
    """The nose on a whole photo, read once per photo; None if no face was found."""
    k = _key(photo)
    if k not in _photos:
        face = find_face(photo)
        _photos[k] = None if face is None else _guided(photo, face)
        while len(_photos) > 4:
            _photos.pop(next(iter(_photos)))
    return _photos[k]


def note_crop(photo, crop, origin):
    """The app has cut `crop` out of `photo`, with its top-left corner at `origin`."""
    global _context
    nose = photo_nose(photo)
    _context = None if nose is None else (_thumb(crop), crop.shape[:2], tuple(origin), nose)


def forget_crop():
    global _context
    _context = None


def _moved(n, ox, oy, s):
    """A copy of a reading in another frame: shifted by the origin, then scaled."""
    P = lambda q: ((q[0] - ox) * s, (q[1] - oy) * s)
    m = Nose(cx=(n.cx - ox) * s, base_y=(n.base_y - oy) * s, half_left=n.half_left * s,
             half_right=n.half_right * s, tilt=n.tilt, spacing=n.spacing * s, found=n.found,
             view=n.view, side=n.side, yaw=n.yaw, light=n.light, notes=dict(n.notes, moved=True))
    m.nostrils = [(*P(c[:2]), c[2] * s, c[3] * s) for c in n.nostrils]
    m.tip = (*P(n.tip[:2]), n.tip[2] * s)
    m.highlight = None if n.highlight is None else P(n.highlight)
    m.wings = [(*P(w_[:2]), w_[2] * s) for w_ in n.wings]
    m.radix = P(n.radix)
    m.bridge = np.array([P(q) for q in n.bridge])
    return m


def _from_context(img):
    """The whole photo's reading, in this image's pixels, if this image is the noted crop."""
    if _context is None:
        return None
    thumb, (ch, cw), (ox, oy), nose = _context
    h, w = img.shape[:2]
    # the aspect ratio, allowing for a pixel's rounding when a small crop is resized
    if abs(w / h - cw / ch) > 0.02 + 2.0 / min(h, w) or float(np.abs(_thumb(img) - thumb).mean()) > 6.0:
        return None
    m = _moved(nose, ox, oy, w / cw)
    if not (0 <= m.tip[0] < w and 0 <= m.tip[1] < h):
        return None                    # the box was drawn somewhere else: read it on its own
    return m


def propose_box(photo):
    """A box round the nose for the box picker to start from, or None if there is no face.

    Without it the picker starts from 85% of the photo, and on a close-up of a face that
    hands the analysis the mouth and the chin as well. From the root of the nose to the
    upper lip, wing to tip, with room round it.
    """
    n = photo_nose(photo)
    if n is None:
        return None
    em = n.notes.get("em", 4 * n.width)
    pts = [n.tip[:2], n.radix, (n.cx, n.base_y), n.along(-n.half_left, 0), n.along(n.half_right, 0)]
    pts += [w[:2] for w in n.wings] + [c[:2] for c in n.nostrils]
    P = np.array(pts, float)
    (x0, y0), (x1, y1) = P.min(0), P.max(0)
    x0, x1 = x0 - 0.2 * em, x1 + 0.2 * em
    y0, y1 = y0 - 0.1 * em, y1 + 0.25 * em             # a little brow above, the upper lip below
    H, W = photo.shape[:2]
    x0, y0, x1, y1 = max(0.0, x0), max(0.0, y0), min(float(W), x1), min(float(H), y1)
    if x1 - x0 < 16 or y1 - y0 < 16:
        return None
    return (x0, y0, x1 - x0, y1 - y0)


# --------------------------------------------------------------------------- entry point
def analyze(img):
    """Read the nose in an image: a whole photo, or a box drawn round the nose.

    Always returns a Nose. `found` says whether it was located (from the face, or from a
    pair of nostrils when there is no face to find) rather than assumed.
    """
    key = (img.shape, hash(img.tobytes()[::97]), id(_context))
    if key in _cache:
        return _cache[key]
    nose = _from_context(img)
    if nose is None:
        face = find_face(img)
        nose = _guided(img, face) if face is not None else _classical(img)
    _cache[key] = nose
    if len(_cache) > 24:
        _cache.pop(next(iter(_cache)))
    return nose
