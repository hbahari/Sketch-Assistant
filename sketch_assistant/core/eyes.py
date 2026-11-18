"""The structure of one eye: iris, pupil, catchlight, corners, lids and crease.

`analyze(img)` reads a close crop of one eye. Everything the Construction style, the
guides and the step ladder draw comes from it.

When the photo has a face in it, the face finds the eye: the face mesh frames each eye
for MediaPipe's iris model, which then gives the iris and both lids, and the picker's box
starts on the eye (see "the face" at the end). The reading is made once on the whole
photo and moved into whatever box the user settles on.

Close-ups of a single eye -- seventeen of the nineteen test photographs -- have no face to
find, and there the user frames the eye with the same drag-a-box picker Object mode uses
and the crop is read by the rules below. The face detector reports a "face" somewhere
inside several of those close-ups, so the face path has to pass two checks first.

The iris model was tried on the close-ups too and measured worse than the rules (see
the end), so on a crop read alone this is classical vision, and classical vision on an
eye is fragile: lashes, reflections, make-up and a squint all break edge-following. The design answer is that nothing here
follows edges. The iris is found with a circle search that reads only the left and right
arcs (the lids cover the top and bottom), and the lids by fitting a *template*: an almond
with a handful of parameters, each confined to the range real eyes occupy, scored against
the image and pulled toward average proportions where the image says nothing. The result
is therefore always a plausible eye. When the evidence is weak it degrades to an average
eye sitting on the iris, which is approximately right, rather than to a confident shape
drawn round an eyebrow, which is not. `Eye.found` says which it was.
"""
from dataclasses import dataclass, field

import cv2
import numpy as np


WORK_W = 320                      # everything is measured on a copy this wide
R_RANGE = (0.04, 0.36)            # iris radius, as a fraction of the crop's width: a face-width
                                  # crop at one end, a macro shot at the other
PROMOTE, PROMOTE_ABS = 0.4, 0.8   # an outer circle this strong -- relative to the first, and in
                                  # units of the image's contrast -- is the limbus
PUPIL_BLACK = 15                  # grey level (after contrast equalisation) a pupil's darkest quarter is under
MAX_RATIO = 4.6                   # an iris is at most this many times its pupil
RECENTRE = 0.2                    # a pupil further off-centre than this many radii means a lopsided circle
RECENTRE_KEEP = 0.7               # ...and the circle round the pupil must score this well against it
RECENTRE_GROW = 2 / 1.2           # ...and be at most this much bigger (see _recentre_on_pupil)
MIN_PUPIL_AREA = 8                # pixels (at WORK_W) of black that count as a pupil
ARC = 40                          # degrees either side of horizontal that the iris search reads

# Average proportions, in iris radii. The palpebral fissure is about 2.5 iris diameters
# wide; the upper lid normally covers the top of the iris and the lower lid touches the
# bottom of it. These are the prior the lid fit is pulled toward, and the whole answer
# when there is no usable evidence.
PRIOR = dict(inner=2.45, outer=2.45, up=1.05, low=0.95)
RANGES = dict(inner=(1.5, 3.5), outer=(1.5, 3.5), up=(0.25, 1.6), low=(0.45, 1.5))
TILT_COST = 0.012                 # per degree squared: a tilt has to be earned, since a level eye
                                  # read as tilted looks worse than a tilted one read as level
AXIS_DROP = 0.18                  # the corner-to-corner line passes this far below the pupil


@dataclass
class Eye:
    """One eye, in the pixel coordinates of the image `analyze` was given."""
    iris: tuple                   # centre of the iris
    r: float                      # its radius
    pupil_r: float
    highlight: tuple = None       # centre of the catchlight, if there is one
    left: tuple = (0.0, 0.0)      # the corner on the left of the image
    right: tuple = (0.0, 0.0)
    upper: np.ndarray = None      # the upper lid margin, left corner to right, Nx2
    lower: np.ndarray = None
    crease: np.ndarray = None     # the fold above the upper lid, if one could be found
    tilt: float = 0.0             # of the corner-to-corner line, degrees, +ve = right side lower
    inner: str = None             # "left" / "right": which corner is the tear duct. None = unknown
    found: bool = False           # the iris was measured, not assumed
    score: float = 0.0            # how strongly the image supported the iris (for tests)
    notes: dict = field(default_factory=dict)

    @property
    def width(self):
        return float(np.hypot(self.right[0] - self.left[0], self.right[1] - self.left[1]))

    @property
    def opening(self):
        """Polygon of the visible eye: upper lid then lower lid back again."""
        return np.vstack([self.upper, self.lower[::-1]]).astype(np.int32)

    @property
    def inner_corner(self):
        return None if self.inner is None else (self.left if self.inner == "left" else self.right)

    @property
    def irises_wide(self):
        """Eye width in iris diameters -- the measurement a drawing book gives (about 2.5)."""
        return self.width / max(2 * self.r, 1e-6)


# --------------------------------------------------------------------------- the iris
def _ring_means(g, cx, cy, r, angles):
    """Mean of `g` on arcs of radius r about many centres at once. cx, cy: arrays."""
    h, w = g.shape
    xs = np.clip((cx[..., None] + r * np.cos(angles)).astype(np.int32), 0, w - 1)
    ys = np.clip((cy[..., None] + r * np.sin(angles)).astype(np.int32), 0, h - 1)
    return g[ys, xs].mean(axis=-1)


def _limbus_score(g, cxs, cys, r, sd, mean, a, full):
    """How much a circle looks like the edge of an iris: darker inside than out along
    its left and right arcs, and dark at its core -- which is what tells an iris from
    the bright ring of a reflection or a spectacle lens."""
    edge = (_ring_means(g, cxs, cys, r * 1.18, a) - _ring_means(g, cxs, cys, r * 0.85, a)) / sd
    core = (mean - _ring_means(g, cxs, cys, r * 0.5, full)) / sd
    return edge + 0.6 * core, edge


def _pupil_blob(g, cx, cy, r):
    """A pupil inside the circle: a black blob that is also compact, round and filled.

    Black alone is not enough -- the first attempt took the largest black patch inside
    the circle for the pupil and it was as often a clump of lashes or a crease shadow,
    which moved the iris on 27 of 38 test photographs. Lashes are long and thin, a crease
    is an arc; a pupil, even with a highlight biting into it, is neither.
    Returns (x, y, radius) or None.
    """
    h, w = g.shape
    ys, xs = np.mgrid[0:h, 0:w]
    m = ((xs - cx) ** 2 + (ys - cy) ** 2 <= (0.9 * r) ** 2) & (g <= PUPIL_BLACK)
    n, _lab, st, ce = cv2.connectedComponentsWithStats(m.astype(np.uint8), connectivity=8)
    best = None
    for k in range(1, n):
        area = float(st[k, cv2.CC_STAT_AREA])
        bw, bh = float(st[k, cv2.CC_STAT_WIDTH]), float(st[k, cv2.CC_STAT_HEIGHT])
        if area < MIN_PUPIL_AREA or max(bw, bh) > 1.6 * min(bw, bh) or area < 0.55 * bw * bh:
            continue
        if best is None or area > best[0]:
            best = (area, float(ce[k][0]), float(ce[k][1]), max(bw, bh) / 2)
    return None if best is None else best[1:]


def _recentre_on_pupil(g, cx, cy, r, sd, mean, a, full):
    """Fix a lopsided circle: the iris re-found round its pupil, or None to keep it.

    An iris is centred on its pupil. When one side of the iris is in shadow its limbus
    is weak there, and the search can settle on a circle whose bright side lies on the
    limbus and whose shadowed side lies on the pupil's own edge -- smaller than the iris
    and pushed toward the light. If a pupil sits well off the circle's centre, try the
    best circle centred on that pupil instead, and take it only if it fits the image
    nearly as well: re-centring is a correction for one failure, not a second opinion on
    every eye.
    """
    h, w = g.shape
    pb = _pupil_blob(g, cx, cy, r)
    if pb is None:
        return None
    px, py, _rp = pb
    if np.hypot(px - cx, py - cy) <= RECENTRE * r:
        return None
    # The size comes from the lopsided circle, not from the pupil: blur and contrast
    # equalisation leave only a pupil's core black, so its measured radius runs at under
    # half the real one. A circle spanning from the far edge of the pupil to the limbus
    # has a diameter of iris radius R plus pupil radius p, so R = 2r - p; and a pupil,
    # even constricted in bright light, is at least a fifth of its iris, so R <= 2r / 1.2.
    # The limit matters: without it two test photographs had the re-centred circle grow
    # past the iris onto the lids, and both had grown by more than 1.7 times.
    hi = min(RECENTRE_GROW * r, w * R_RANGE[1])
    best = None
    for rr in np.arange(r, hi + 0.5, 1.5):
        span = max(2.0, 0.08 * rr)                  # the pupil is the centre, give or take
        xs, ys = np.meshgrid(np.arange(px - span, px + span + 0.5, 1.0),
                             np.arange(py - span, py + span + 0.5, 1.0))
        s, edge = _limbus_score(g, xs, ys, rr, sd, mean, a, full)
        s = np.where((xs - 1.18 * rr < 0) | (xs + 1.18 * rr > w - 1), -1e9, s)
        i = int(np.argmax(s))
        if best is None or s.flat[i] > best[0]:
            best = (float(s.flat[i]), float(edge.flat[i]), float(xs.flat[i]), float(ys.flat[i]), float(rr))
    # Compared on the edge alone. The full score also rewards a dark core, which is what
    # tells an iris from a bright spectacle ring -- but a circle centred on a pupil is
    # known not to be a spectacle ring, and a pale iris round a small pupil has a
    # mid-grey core that would lose to a lopsided circle on that term every time.
    _, e0 = _limbus_score(g, np.array([cx]), np.array([cy]), r, sd, mean, a, full)
    if best is None or best[1] < RECENTRE_KEEP * float(e0[0]):
        return None
    if best[4] >= hi - 1.5:
        return None             # still climbing at the limit: no limbus inside it
    return best[2], best[3], best[4]


def _find_iris(g):
    """Best circle for the iris on a smoothed grey image. Returns (cx, cy, r, score).

    Reads only the arcs to the left and right of each candidate. The lids cut across the
    top and bottom of nearly every iris, so a full-circle fit is dragged about by them;
    the sides are the part of the limbus that is reliably visible.

    Two passes, because the strongest dark-inside circle in a pale eye is the pupil, not
    the iris. The first pass finds the best circle of any size. The second sweeps outward
    from it for the *largest* concentric circle that is still a strong edge: in a pale
    eye that is the limbus round the pupil just found, and in a dark eye, where the first
    pass already found the limbus, there is nothing further out to promote to.
    """
    h, w = g.shape
    sd, mean = float(g.std()) + 1e-6, float(g.mean())
    a = np.deg2rad(np.r_[np.arange(-ARC, ARC + 1, 8), np.arange(180 - ARC, 180 + ARC + 1, 8)])
    full = np.deg2rad(np.arange(0, 360, 20))
    cxs, cys = np.meshgrid(np.arange(w * 0.15, w * 0.85, 3.0), np.arange(h * 0.15, h * 0.85, 3.0))
    best = (-1e9, 0.0, 0.0, 0.0)
    for r in np.arange(w * R_RANGE[0], w * R_RANGE[1], 3.0):
        s, _ = _limbus_score(g, cxs, cys, r, sd, mean, a, full)
        # Both side arcs have to be on the image. Off the edge the samples repeat the
        # border pixel, and a patch of deep shadow in a corner then scores as a perfect
        # dark disc -- which is what the first version chose on one test photograph.
        s = np.where((cxs - 1.18 * r < 0) | (cxs + 1.18 * r > w - 1), -1e9, s)
        i = int(np.argmax(s))
        if s.flat[i] > best[0]:
            best = (float(s.flat[i]), float(cxs.flat[i]), float(cys.flat[i]), float(r))
    score, cx, cy, r = best


    def local(cx, cy, r, span):
        """Best centre and its edge strength for one radius, near (cx, cy)."""
        xs, ys = np.meshgrid(np.arange(cx - span, cx + span + 0.5, 1.5),
                             np.arange(cy - span, cy + span + 0.5, 1.5))
        s, edge = _limbus_score(g, xs, ys, r, sd, mean, a, full)
        edge = np.where((xs - 1.18 * r < 0) | (xs + 1.18 * r > w - 1), -1e9, edge)
        i = int(np.argmax(edge))
        return float(edge.flat[i]), float(s.flat[i]), float(xs.flat[i]), float(ys.flat[i])

    e0 = local(cx, cy, r, 2.0)[0]
    cand = (e0, score, cx, cy, r)
    rings = []
    for rr in np.arange(r * 1.5, min(r * 5.0, w * R_RANGE[1]) + 0.5, 2.0):
        e, sc, x, y = local(cx, cy, rr, max(2.0, r * 0.35))
        # Judged against the image, not only against the first circle: a black pupil in
        # an amber iris is so strong an edge that a perfectly clear limbus is under half
        # of it, and a purely relative test left that eye with its pupil as its iris.
        if e >= max(PROMOTE_ABS, PROMOTE * e0):
            rings.append((e, sc, x, y, float(rr)))
    # ...but only when the first circle is a pupil. A brown iris is a strong dark circle in
    # its own right, and promoting from one lands on the curve of the lids round it --
    # the commonest failure on the test photographs until this check went in. Six cues
    # were measured for telling the two apart (size ratio, edge strength, evenness of the
    # band between, whiteness outside, the top arc, tone steps) and only one separated
    # them: a pupil is black. A quarter of it is darker than PUPIL_BLACK even with a
    # window reflected in it, where the darkest quarter of a dark-brown iris is not.
    ys, xs = np.mgrid[0:h, 0:w]
    disc = g[(xs - cx) ** 2 + (ys - cy) ** 2 <= (0.6 * r) ** 2]
    if disc.size == 0 or float(np.percentile(disc, 25)) > PUPIL_BLACK:
        rings = []
    rings = [k for k in rings if k[4] <= MAX_RATIO * r]
    if rings:
        # the outermost ring that is nearly as strong as the strongest: reflections and
        # the pupil's own soft edge make rings inside the iris, nothing makes one outside
        top = max(k[0] for k in rings)
        cand = max((k for k in rings if k[0] >= 0.8 * top), key=lambda k: k[4])
    cx, cy, r = cand[2], cand[3], cand[4]
    # single-pixel refinement of whichever circle won
    for rr in np.arange(r - 2, r + 2.5, 1.0):
        e, sc, x, y = local(cx, cy, rr, 2.0)
        if e > cand[0]:
            cand = (e, sc, x, y, float(rr))
    cx, cy, r = cand[2], cand[3], cand[4]
    # Last, once the circle is final: is it centred on its pupil? Checked on the final
    # circle rather than the first pass's, because in a pale eye the first pass is often
    # the pupil itself -- partly hidden by a reflection, so its black part sits off its
    # centre -- and re-centring that before it had been grown out to the limbus turned a
    # correct iris into a wrong one.
    alt = _recentre_on_pupil(g, cx, cy, r, sd, mean, a, full)
    if alt is not None:
        # the score stays as it was: it is the evidence that there is an eye here at
        # all, and moving the circle does not make that evidence weaker
        cx, cy, r = alt
    return cx, cy, r, max(score, cand[1])


def _find_pupil(g, cx, cy, r):
    """Pupil radius: the concentric circle with the sharpest dark-inside edge."""
    full = np.deg2rad(np.arange(0, 360, 15))
    c = (np.array([cx]), np.array([cy]))
    best, best_r = 0.0, 0.42 * r
    for f in np.arange(0.22, 0.66, 0.04):
        edge = float(_ring_means(g, *c, r * (f + 0.10), full)[0] - _ring_means(g, *c, r * max(f - 0.10, 0.05), full)[0])
        if edge > best:
            best, best_r = edge, f * r
    return best_r


def _find_highlight(g, cx, cy, r):
    """The catchlight: the brightest compact spot on the iris, if it stands out."""
    h, w = g.shape
    ys, xs = np.mgrid[0:h, 0:w]
    disc = (xs - cx) ** 2 + (ys - cy) ** 2 <= (r * 0.95) ** 2
    if disc.sum() < 20:
        return None
    vals = g[disc]
    thr = max(float(np.percentile(vals, 97)), float(np.median(vals)) + 45)
    spot = (disc & (g >= thr)).astype(np.uint8)
    n, lab, stats, cents = cv2.connectedComponentsWithStats(spot, connectivity=8)
    if n < 2:
        return None
    i = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    if not (3 <= stats[i, cv2.CC_STAT_AREA] <= disc.sum() * 0.25):
        return None
    return float(cents[i][0]), float(cents[i][1])


# --------------------------------------------------------------------------- the lids
def _lid_curves(cx, cy, r, p, tilt, n=25):
    """The almond for one set of parameters: (left corner, right corner, upper, lower).

    Two quadratic curves between the corners, in a frame rotated by `tilt` about the
    pupil. Parameters are in iris radii so one template fits any size of crop.
    """
    k = AXIS_DROP * r
    A, B = np.array([-p["l"] * r, k]), np.array([p["r"] * r, k])
    # the apex sits between the middle of the fissure and the pupil: lids ride the eyeball
    mx = (A[0] + B[0]) / 2 * 0.5
    t = np.linspace(0, 1, n)[:, None]
    up = (1 - t) ** 2 * A + 2 * t * (1 - t) * np.array([mx, k - 2 * (p["up"] * r + k)]) + t ** 2 * B
    lo = (1 - t) ** 2 * A + 2 * t * (1 - t) * np.array([mx, k + 2 * (p["low"] * r - k)]) + t ** 2 * B
    th = np.deg2rad(tilt)
    R = np.array([[np.cos(th), -np.sin(th)], [np.sin(th), np.cos(th)]])
    o = np.array([cx, cy])
    return A @ R.T + o, B @ R.T + o, up @ R.T + o, lo @ R.T + o


def _sample(m, pts):
    h, w = m.shape
    x = np.clip(pts[:, 0].astype(np.int32), 0, w - 1)
    y = np.clip(pts[:, 1].astype(np.int32), 0, h - 1)
    return m[y, x]


def _fit_lids(img, g, cx, cy, r, tilt_hint=None):
    """Fit the almond template. Returns (params, tilt, evidence).

    Scored on three things an eye has whatever the lighting: a dark line along the upper
    lid (the lashes and their shadow), a weaker one along the lower, and an opening that
    is whiter than the skin around it. A quadratic penalty pulls every parameter toward
    the average eye, so where the image offers nothing the template stays average.
    """
    h, w = g.shape
    gf = g.astype(np.float32)
    ridge = cv2.GaussianBlur(gf, (0, 0), 0.34 * r) - cv2.GaussianBlur(gf, (0, 0), 0.09 * r)
    ridge = ridge / (float(ridge.std()) + 1e-6)                 # +ve where locally dark
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV).astype(np.float32)
    white = (hsv[..., 2] / 255.0) * (1 - hsv[..., 1] / 255.0)
    white = cv2.GaussianBlur(white, (0, 0), 0.12 * r)
    white = (white - float(white.mean())) / (float(white.std()) + 1e-6)
    ys, xs = np.mgrid[0:h, 0:w]
    not_iris = (xs - cx) ** 2 + (ys - cy) ** 2 > (r * 1.05) ** 2

    tilts = [tilt_hint] if tilt_hint is not None else [-12.0, -6.0, 0.0, 6.0, 12.0]
    PL, PR, PU, PLO = [v.ravel() for v in np.meshgrid(
        np.linspace(*RANGES["inner"], 7), np.linspace(*RANGES["outer"], 7),
        np.linspace(*RANGES["up"], 7), np.linspace(*RANGES["low"], 6), indexing="ij")]
    prior = sum(((v - PRIOR[k]) / (RANGES[k][1] - RANGES[k][0])) ** 2
                for k, v in (("inner", PL), ("outer", PR), ("up", PU), ("low", PLO)))
    # every template at once: (models, points along the lid, xy)
    n, k = 15, AXIS_DROP * r
    t = np.linspace(0, 1, n)[None, :, None]
    A = np.stack([-PL * r, np.full_like(PL, k)], 1)[:, None, :]
    B = np.stack([PR * r, np.full_like(PR, k)], 1)[:, None, :]
    mx = (A[..., 0] + B[..., 0]) / 4
    Cu = np.stack([mx[:, 0], k - 2 * (PU * r + k)], 1)[:, None, :]
    Cl = np.stack([mx[:, 0], k + 2 * (PLO * r - k)], 1)[:, None, :]
    up0 = (1 - t) ** 2 * A + 2 * t * (1 - t) * Cu + t ** 2 * B
    lo0 = (1 - t) ** 2 * A + 2 * t * (1 - t) * Cl + t ** 2 * B
    mid0 = (A + B) / 2

    def read(m, pts):
        x = np.clip(pts[..., 0].astype(np.int32), 0, w - 1)
        y = np.clip(pts[..., 1].astype(np.int32), 0, h - 1)
        return m[y, x]

    best = (-1e9, None, 0.0, 0.0)
    o = np.array([cx, cy])
    for tilt in tilts:
        th = np.deg2rad(tilt)
        R = np.array([[np.cos(th), -np.sin(th)], [np.sin(th), np.cos(th)]])
        up, lo, mid = up0 @ R.T + o, lo0 @ R.T + o, mid0 @ R.T + o
        both = np.concatenate([up, lo], 1)
        # A macro shot often runs the corners off the frame, so the template may too --
        # but most of it has to be on the image, or there is nothing to score it against.
        on = ((both[..., 0] >= 1) & (both[..., 0] <= w - 2)
              & (both[..., 1] >= 1) & (both[..., 1] <= h - 2)).mean(1)
        e_up = read(ridge, up[:, 2:-2]).mean(1)
        e_lo = read(ridge, lo[:, 2:-2]).mean(1)
        # whiteness just inside the lids against just outside them
        inside = np.concatenate([up + (mid - up) * 0.22, lo + (mid - lo) * 0.22], 1)
        outside = np.concatenate([up - (mid - up) * 0.28, lo - (mid - lo) * 0.28], 1)
        keep = read(not_iris, inside)
        w_in = (read(white, inside) * keep).sum(1) / np.maximum(keep.sum(1), 1)
        evidence = 1.0 * e_up + 0.5 * e_lo + 0.8 * (w_in - read(white, outside).mean(1))
        sc = evidence - 1.6 * prior - TILT_COST * tilt * tilt * (tilt_hint is None)
        sc = np.where(on < 0.6, -1e9, sc)
        i = int(np.argmax(sc))
        if sc[i] > best[0]:
            best = (float(sc[i]), dict(l=float(PL[i]), r=float(PR[i]), up=float(PU[i]), low=float(PLO[i])),
                    tilt, float(evidence[i]))
    if best[1] is None:                                  # crop too tight for any template
        return dict(l=PRIOR["inner"], r=PRIOR["outer"], up=PRIOR["up"], low=PRIOR["low"]), \
            (tilt_hint or 0.0), 0.0
    return best[1], best[2], best[3]


def _find_crease(g, upper, cx, cy, r):
    """The fold above the upper lid: the darkest curve parallel to the lid, if clear."""
    gf = g.astype(np.float32)
    ridge = cv2.GaussianBlur(gf, (0, 0), 0.30 * r) - cv2.GaussianBlur(gf, (0, 0), 0.08 * r)
    ridge = ridge / (float(ridge.std()) + 1e-6)
    mid = upper[len(upper) // 2]
    up_dir = (mid - np.array([cx, cy]))
    up_dir = up_dir / (np.linalg.norm(up_dir) + 1e-6)
    best, best_off = 0.35, None
    core = upper[3:-3]
    for off in np.arange(0.30, 1.05, 0.08):
        # a crease rides higher over the middle of the eye than at the corners
        bow = np.sin(np.linspace(0, np.pi, len(core)))[:, None]
        pts = core + up_dir * off * r * (0.45 + 0.55 * bow)
        if pts[:, 1].min() < 1:
            break
        e = float(_sample(ridge, pts).mean())
        if e > best:
            best, best_off = e, off
    if best_off is None:
        return None
    bow = np.sin(np.linspace(0, np.pi, len(core)))[:, None]
    return core + up_dir * best_off * r * (0.45 + 0.55 * bow)


# --------------------------------------------------------------------------- analysis
_cache = {}
MIN_IRIS_SCORE = 1.1          # below this the "iris" is noise; see tests/test_eyes.py


def _work(img):
    """The copy everything is measured on: WORK_W wide, contrast-equalised and smoothed."""
    H, W = img.shape[:2]
    s = WORK_W / W
    small = cv2.resize(img, (WORK_W, max(8, int(round(H * s)))),
                       interpolation=cv2.INTER_AREA if s < 1 else cv2.INTER_CUBIC)
    g = cv2.GaussianBlur(cv2.createCLAHE(2.0, (4, 4)).apply(cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)), (0, 0), 2.0)
    return s, small, g, cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)


def _details(eye, s, g, sharp):
    """Pupil, catchlight and crease, measured round an iris already placed."""
    cx, cy, r = eye.iris[0] * s, eye.iris[1] * s, eye.r * s
    eye.pupil_r = _find_pupil(g, cx, cy, r) / s
    hl = _find_highlight(sharp, cx, cy, r)
    eye.highlight = None if hl is None else (hl[0] / s, hl[1] / s)
    cr = _find_crease(g, eye.upper * s, cx, cy, r)
    eye.crease = None if cr is None else cr / s


def analyze(img):
    """Read one eye crop. Always returns an Eye; `found` says whether the iris was real.

    When the crop is the box the app cut from a photo with a face in it, the reading made
    on the whole face (see "the face" below) is used, moved into the crop's pixels;
    otherwise the crop is read on its own by the rules above.
    """
    key = (img.shape, hash(img.tobytes()[::97]), id(_context))
    if key in _cache:
        return _cache[key]
    eye = _from_context(img)
    if eye is not None:
        s, small, g, sharp = _work(img)
        _details(eye, s, g, sharp)
        _cache[key] = eye
        return eye
    s, small, g, sharp = _work(img)
    h, w = g.shape

    cx, cy, r, score = _find_iris(g)
    found = score >= MIN_IRIS_SCORE
    if not found:
        # nothing circular and dark: a closed eye, a squint, a crop that missed. Assume
        # an eye in the middle of the frame, sized so the whole of it would fit.
        cx, cy, r = w * 0.5, h * 0.5, min(w * 0.14, h * 0.3)
    p, tilt, evidence = _fit_lids(small, g, cx, cy, r)
    A, B, upper, lower = _lid_curves(cx, cy, r, p, tilt)
    eye = Eye(
        iris=(cx / s, cy / s), r=r / s,
        pupil_r=_find_pupil(g, cx, cy, r) / s if found else 0.42 * r / s,
        highlight=None, left=tuple(A / s), right=tuple(B / s),
        upper=upper / s, lower=lower / s, tilt=float(tilt), inner=None,
        found=bool(found), score=float(score),
        notes=dict(lid_evidence=float(evidence), params=p),
    )
    if found:
        _details(eye, s, g, sharp)
    _cache[key] = eye
    if len(_cache) > 24:
        _cache.pop(next(iter(_cache)))
    return eye



# --------------------------------------------------------------------------- the face
# When the photo has a face in it, the eye is found the way MediaPipe finds it: the face
# detector, then the face mesh (core/landmarks.py), whose points round each eye frame a
# crop for the iris model at the size it was trained on. The iris model on its own, shown
# a close-up of one eye, was tried first and measured worse than the rules above (7 of 19
# test close-ups against 10): its iris comes out the size of whatever crop it is given,
# so it cannot set the scale itself. The face sets the scale. On ten eyes marked by hand
# in face photos, the face path's iris was within 21% of the marked size every time
# (median 6%), whatever box was drawn; the rules, shown a box three eye-widths across
# round the same eye, read it 2.7 to 4 times too big on six of the ten -- the fault a
# tester reported. Its centre is less good than its size: within 0.55 iris radii of the
# mark on every eye, within 0.3 on six.
#
# The face detector also "finds" a face in some close-ups of a single eye (five of the
# nineteen test close-ups). The detector must agree with itself across most of its
# paddings to count (support 3.0): the invented faces reached 2.7 at most, real faces 3.6
# and up wherever an eye was visible. That margin is not wide, so the face mesh must also
# say a face is there; on its own that verdict rejected four of the five invented faces.
# Both thresholds were set on these same photographs.
EYE_FACE_SUPPORT = 3.0
EYE_CROP = 2.3            # the iris model's crop, in eye widths, as MediaPipe crops it

_photos = {}
_context = None


def _key(img):
    return (img.shape, hash(img.tobytes()[::97]))


def _thumb(img):
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img
    return cv2.resize(g, (16, 16), interpolation=cv2.INTER_AREA).astype(np.float32)


def _resample(curve, n=25):
    d = np.r_[0, np.cumsum(np.hypot(*np.diff(curve, axis=0).T))]
    t = np.linspace(0, d[-1], n)
    return np.c_[np.interp(t, d, curve[:, 0]), np.interp(t, d, curve[:, 1])]


def _model_eye(res, inner):
    """An Eye from the iris model's points: 0 and 8 the corners, 1-7 one lid, 9-15 the other."""
    lids = res["lids"]
    a, b = lids[0], lids[8]
    one, two = lids[1:8], lids[9:16]
    if one[:, 1].mean() < two[:, 1].mean():
        one, two = two, one                      # `one` is now the lower lid
    left, right = (a, b) if a[0] <= b[0] else (b, a)
    order = lambda pts: pts[np.argsort(pts[:, 0])]
    upper = _resample(np.vstack([left, order(two), right]))
    lower = _resample(np.vstack([left, order(one), right]))
    tilt = float(np.degrees(np.arctan2(right[1] - left[1], right[0] - left[0])))
    return Eye(iris=res["iris"], r=res["r"], pupil_r=0.42 * res["r"],
               left=(float(left[0]), float(left[1])), right=(float(right[0]), float(right[1])),
               upper=upper, lower=lower, tilt=tilt, inner=inner, found=True, score=float(res["score"]),
               notes=dict(source="face"))


def photo_eyes(photo):
    """The eyes of the face in a whole photo, read once per photo: a list of up to two
    Eyes in the photo's pixels, image-left eye first. Empty if there is no face, or the
    models are missing, or the eyes lie outside the picture."""
    k = _key(photo)
    if k in _photos:
        return _photos[k]
    from . import landmarks, noses
    eyes = []
    face = noses.find_face(photo) if landmarks.iris_available() else None
    if face is not None and face.score >= EYE_FACE_SUPPORT:
        mesh, flag = landmarks.face_mesh(photo, face.eye_mid, face.mouth_mid, with_flag=True)
        H, W = photo.shape[:2]
        for n, (i, j) in enumerate(landmarks.MESH_EYES if mesh is not None and flag > 0 else ()):
            a, b = mesh[i], mesh[j]
            if not all(0 <= q[0] < W and 0 <= q[1] < H for q in (a, b)):
                continue                         # an eye off the edge of the photo
            c, w = (a + b) / 2, float(np.linalg.norm(b - a))
            if w < 12:
                continue
            # the model was trained on the eye on the image's left; the other is mirrored
            res = landmarks.iris_landmarks(photo, start=(c[0], c[1], EYE_CROP * w), iterations=2, flip=n == 1)
            if res is None:
                continue
            eye = _model_eye(res, inner="right" if n == 0 else "left")
            eye.notes["mesh_width"] = w
            eyes.append(eye)
    _photos[k] = eyes
    while len(_photos) > 4:
        _photos.pop(next(iter(_photos)))
    return eyes


def note_crop(photo, crop, origin):
    """The app has cut `crop` out of `photo`, with its top-left corner at `origin`."""
    global _context
    eyes = photo_eyes(photo)
    _context = (_thumb(crop), crop.shape[:2], tuple(origin), eyes) if eyes else None


def forget_crop():
    global _context
    _context = None


def _moved(e, ox, oy, s):
    P = lambda q: ((q[0] - ox) * s, (q[1] - oy) * s)
    return Eye(iris=P(e.iris), r=e.r * s, pupil_r=e.pupil_r * s, left=P(e.left), right=P(e.right),
               upper=(e.upper - (ox, oy)) * s, lower=(e.lower - (ox, oy)) * s, tilt=e.tilt,
               inner=e.inner, found=e.found, score=e.score, notes=dict(e.notes, moved=True))


def _from_context(img):
    """The face's reading of the eye in this image, if this image is the noted crop: the
    eye whose iris is in it, the one nearest the middle if both are."""
    if _context is None:
        return None
    thumb, (ch, cw), (ox, oy), eyes = _context
    h, w = img.shape[:2]
    # the aspect ratio, allowing for a pixel's rounding when a small crop is resized
    if abs(w / h - cw / ch) > 0.02 + 2.0 / min(h, w) or float(np.abs(_thumb(img) - thumb).mean()) > 6.0:
        return None
    moved = [_moved(e, ox, oy, w / cw) for e in eyes]
    inside = [m for m in moved if 0 <= m.iris[0] < w and 0 <= m.iris[1] < h]
    if not inside:
        return None                    # the box was drawn somewhere else: read it on its own
    return min(inside, key=lambda m: np.hypot(m.iris[0] - w / 2, m.iris[1] - h / 2))


def propose_box(photo):
    """A box round one eye for the box picker to start from, or None without a face.
    The larger of the two (the nearer, on a turned head), with its brow above."""
    eyes = photo_eyes(photo)
    if not eyes:
        return None
    e = max(eyes, key=lambda e: e.width)
    w = e.width
    cx, cy = (e.left[0] + e.right[0]) / 2, (e.left[1] + e.right[1]) / 2
    x0, x1, y0, y1 = cx - 1.0 * w, cx + 1.0 * w, cy - 0.85 * w, cy + 0.6 * w
    H, W = photo.shape[:2]
    x0, y0, x1, y1 = max(0.0, x0), max(0.0, y0), min(float(W), x1), min(float(H), y1)
    if x1 - x0 < 16 or y1 - y0 < 16:
        return None
    return (x0, y0, x1 - x0, y1 - y0)
