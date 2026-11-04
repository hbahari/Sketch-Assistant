"""Hand structure: 21 landmarks from MediaPipe, with a silhouette fallback.

What a beginner needs for a hand is not a bounding box but where the palm sits, how the
knuckle arc curves and which way each finger runs. Two offline ONNX models give exactly
that -- a palm detector to find the hand, then a landmark model that returns the wrist,
the knuckles and all three joints of every finger.

An earlier version worked this out from the silhouette alone, using the distance transform
for the palm and the outline's curvature for the fingertips. It held up on synthetic hands
but not on photographs: with the fingers held together the outline simply does not separate
them, and a curled or partly hidden finger has no fingertip to find, so whole fingers went
missing from the guides. The models have no trouble with either -- they infer the joints
rather than tracing the edge. The old method is kept as `_from_silhouette` for when the
models are not installed, since it is better than nothing.

Both models are Apache 2.0 from OpenCV Zoo, run through cv2.dnn, and total about 5 MB.
`scripts/download_models.py` fetches them; everything here degrades gracefully if they are
absent. See core/vendor/ATTRIBUTION.md.
"""
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np

from .styles import _silhouette

MODELS = Path(__file__).resolve().parent.parent / "assets" / "models"
PALM_MODEL = MODELS / "palm_detection_mediapipe_2023feb_int8.onnx"
POSE_MODEL = MODELS / "handpose_estimation_mediapipe_2023feb.onnx"

# MediaPipe's landmark numbering. 0 is the wrist; each finger is four points running from
# the knuckle out to the tip.
WRIST = 0
FINGERS = {"thumb": (1, 2, 3, 4), "index": (5, 6, 7, 8), "middle": (9, 10, 11, 12),
           "ring": (13, 14, 15, 16), "little": (17, 18, 19, 20)}
MCP = (1, 5, 9, 13, 17)          # where each finger meets the palm
TIPS = (4, 8, 12, 16, 20)
PALM_POLY = (0, 1, 5, 9, 13, 17)  # the palm's outline, as a closed shape

# How much blank margin to add around the photo before running the palm detector, as a
# fraction of the long side, tried in this order until a hand is found.
#
# The model expects the hand to be a modest part of the frame and misses one shot close
# up, so the image is padded before detection. No single amount suits every photo -- a
# hand gripping a mug and a contact sheet of hands want different ones -- so a couple are
# tried in turn and the first that yields landmarks wins.
#
# Measured over the photographs in tests/fixtures, 0.25 and 0.6 each find eight of the
# nine on their own, and no combination of paddings finds the ninth: on that one the palm
# detector offers boxes but the landmark model rejects all of them, so it is not a framing
# problem. Longer lists were tried and bought nothing but time.
#
# The border is replicated rather than filled with a flat colour, which found fewer hands
# -- presumably a hard artificial edge reads as structure.
DETECT_PADS = (0.25, 0.6)
DETECT_MAX = 640
PALM_SCORE, NMS_IOU, POSE_CONF = 0.4, 0.3, 0.5

_palm_net = _pose_net = None
_tried = False


@dataclass
class Hand:
    """Hand structure in image pixels. All points are (x, y) floats."""
    palm: tuple                     # centre of the palm mass
    palm_r: float                   # radius of the palm circle
    wrist: tuple
    tips: list = field(default_factory=list)
    valleys: list = field(default_factory=list)   # webbing between adjacent fingers
    contour: np.ndarray = None      # silhouette, when one was computed
    landmarks: np.ndarray = None    # (21, 2) when the models supplied them, else None

    @property
    def from_model(self):
        return self.landmarks is not None

    @property
    def fingers(self):
        """Finger axes as (base, tip) pairs, base first."""
        if self.landmarks is not None:
            return [(tuple(self.landmarks[f[0]]), tuple(self.landmarks[f[-1]]))
                    for f in FINGERS.values()]
        return self._silhouette_fingers()

    @property
    def joints(self):
        """Every finger as its full chain of four points, knuckle to tip.

        Only the models can supply this; from a silhouette the joints are guesses, so
        this returns nothing rather than inventing them, and the caller falls back to
        marking joints at average proportions along the axis.
        """
        if self.landmarks is None:
            return []
        return [[tuple(self.landmarks[i]) for i in f] for f in FINGERS.values()]

    @property
    def knuckles(self):
        """The knuckle arc across the palm, in order."""
        if self.landmarks is not None:
            return [tuple(self.landmarks[i]) for i in (1, 5, 9, 13, 17)]
        bases = [b for b, _ in self.fingers]
        if len(bases) < 2:
            return []
        return sorted(bases, key=lambda p: np.arctan2(p[1] - self.wrist[1], p[0] - self.wrist[0]))

    @property
    def palm_quad(self):
        """The palm as a closed polygon: the block everything else hangs off."""
        if self.landmarks is not None:
            return [tuple(self.landmarks[i]) for i in PALM_POLY]
        kn = self.knuckles
        if len(kn) < 2:
            return []
        a, b = np.array(kn[0], float), np.array(kn[-1], float)
        axis = np.array(self.palm, float) - np.array(self.wrist, float)
        axis /= (np.linalg.norm(axis) + 1e-6)
        side = np.array([-axis[1], axis[0]]) * self.palm_r * 0.78
        wr = np.array(self.palm, float) - axis * self.palm_r * 0.95
        return [tuple(a), tuple(b), tuple(wr + side), tuple(wr - side)]

    def _silhouette_fingers(self):
        palm = np.array(self.palm, float)
        out = []
        for t in self.tips:
            d = np.array(t, float) - palm
            n = float(np.linalg.norm(d)) or 1.0
            base = tuple(palm + d / n * self.palm_r)
            near = sorted(self.valleys, key=lambda v: _dist(v, t))[:2]
            if len(near) == 2:
                mid = ((near[0][0] + near[1][0]) / 2, (near[0][1] + near[1][1]) / 2)
                if _dist(mid, base) < 0.6 * self.palm_r and _dist(mid, t) > 0.30 * n:
                    base = mid
            out.append((base, t))
        return out


def _dist(a, b):
    return float(np.hypot(a[0] - b[0], a[1] - b[1]))


def models_available():
    return PALM_MODEL.exists() and POSE_MODEL.exists()


def _nets():
    """Load the two models once. Returns (palm, pose) or (None, None)."""
    global _palm_net, _pose_net, _tried
    if _tried:
        return _palm_net, _pose_net
    _tried = True
    if not models_available():
        return None, None
    try:
        from .vendor.mp_handpose import MPHandPose
        from .vendor.mp_palmdet import MPPalmDet
        _palm_net = MPPalmDet(modelPath=str(PALM_MODEL), nmsThreshold=NMS_IOU,
                              scoreThreshold=PALM_SCORE)
        _pose_net = MPHandPose(modelPath=str(POSE_MODEL), confThreshold=POSE_CONF)
    except Exception:            # old OpenCV without dnn, corrupt download, ...
        _palm_net = _pose_net = None
    return _palm_net, _pose_net


def _from_model(img):
    """21 landmarks via MediaPipe, or None if no hand is found."""
    palm_net, pose_net = _nets()
    if palm_net is None or pose_net is None:
        return None
    scale = min(1.0, DETECT_MAX / max(img.shape[:2]))
    small = (cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
             if scale < 1.0 else img)
    h, w = small.shape[:2]
    for frac in DETECT_PADS:
        pad = int(max(h, w) * frac)
        padded = cv2.copyMakeBorder(small, pad, pad, pad, pad, cv2.BORDER_REPLICATE)
        try:
            palms = palm_net.infer(padded)
        except Exception:
            return None
        if palms is None or len(palms) == 0:
            continue
        # the biggest detection: with several hands in shot, the one being drawn is the
        # one filling the frame
        palms = sorted(palms, key=lambda p: -abs((p[2] - p[0]) * (p[3] - p[1])))
        for p in palms[:3]:
            try:
                res = pose_net.infer(padded, p)
            except Exception:
                continue
            if res is None:
                continue
            lm = np.asarray(res)[4:67].reshape(21, 3)[:, :2] - pad
            if not np.isfinite(lm).all():
                continue
            return (lm / scale).astype(np.float32)     # back to the original resolution
    return None


def _hand_from_landmarks(img, lm):
    pts = lm[list(PALM_POLY)]
    palm = tuple(float(v) for v in pts.mean(axis=0))
    # the palm circle: sized so it reaches the knuckles, which is what a learner blocks in
    palm_r = float(np.mean([_dist(palm, tuple(lm[i])) for i in MCP])) * 1.05
    valleys = [tuple((lm[a] + lm[b]) / 2) for a, b in ((5, 9), (9, 13), (13, 17))]
    sil = None
    try:
        sil = _silhouette(img)
    except Exception:
        pass
    return Hand(palm, palm_r, tuple(float(v) for v in lm[WRIST]),
                [tuple(float(v) for v in lm[i]) for i in TIPS], valleys, sil, lm)


def _hull_mask(shape, hand, grow):
    """The landmarks' convex hull, grown. Crude but certainly the hand and nothing else."""
    mask = np.zeros(shape[:2], np.uint8)
    cv2.drawContours(mask, [cv2.convexHull(hand.landmarks.astype(np.int32))], -1, 255, -1)
    k = max(3, int(hand.palm_r * grow)) | 1
    return cv2.dilate(mask, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)))


def hand_mask(img, hand, feather=0.012):
    """A soft mask covering the hand, for keeping the background out of a sketch.

    Neither available shape works on its own, which the test photographs make obvious:

    * the GrabCut silhouette follows the real edge of the hand beautifully, but it has no
      idea what a hand is. On a hand writing on a sheet of paper it returns hand *and*
      paper; on a hand round a mug it returns hand and mug.
    * the landmarks' convex hull is unquestionably the hand, but it is a hull of 21 points,
      so it cuts straight across the fingers and clips their tips off.

    So the two are intersected: GrabCut's edge, clipped to the region the landmarks say is
    hand. The hull is grown generously first, because it has to contain the fingers' real
    width, and the result is only trusted if it still covers most of the landmarks.

    Checking merely that the landmarks fall *inside* the GrabCut mask is not enough, and
    was the bug here before: the hand-plus-paper blob contains every landmark happily.
    """
    h, w = img.shape[:2]
    mask = None
    if hand.landmarks is not None:
        region = _hull_mask(img.shape, hand, 0.85)
        if hand.contour is not None:
            g = np.zeros((h, w), np.uint8)
            cv2.drawContours(g, [hand.contour], -1, 255, -1)
            both = cv2.bitwise_and(g, region)
            # if clipping removed nearly everything, GrabCut found something other than
            # the hand entirely; fall through to the hull on its own
            if both.sum() > region.sum() * 0.35:
                mask = both
        if mask is None:
            mask = region
    elif hand.contour is not None:
        mask = np.zeros((h, w), np.uint8)
        cv2.drawContours(mask, [hand.contour], -1, 255, -1)
    if mask is None:
        return None
    # Grow before softening. The hand's own outline sits exactly on the mask's edge, so a
    # mask that starts fading there fades the outline out with it -- the contour style
    # came back with the silhouette missing and the tone styles with a grey halo where
    # the edge used to be. Dilating first puts the whole edge safely inside.
    grow = max(3, int(min(h, w) * 0.018)) | 1
    mask = cv2.dilate(mask, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (grow, grow)))
    return cv2.GaussianBlur(mask, (0, 0), max(1.5, min(h, w) * feather * 0.5))


_cache = {}
CACHE_MAX = 6


def analyze(img, contour=None):
    """Return a Hand, or None when no hand can be read from the picture.

    Tries the landmark models first and falls back to the silhouette method, so the app
    still does something useful when the models are not installed.

    Results are cached per image. One screen asks for the same hand several times over --
    once per style tile, once for the guides, once per step -- and each call was redoing
    both the inference and a GrabCut, which is a quarter of a second each on a phone-sized
    photo. The key matches the one `styles._silhouette` uses.
    """
    key = None
    if contour is None:
        key = (img.shape, hash(img.tobytes()[::97]))
        if key in _cache:
            return _cache[key]
        lm = _from_model(img)
        hand = _hand_from_landmarks(img, lm) if lm is not None else _from_silhouette(img)
    else:
        hand = _from_silhouette(img, contour)
    if key is not None:
        if len(_cache) >= CACHE_MAX:
            _cache.clear()
        _cache[key] = hand
    return hand


# --------------------------------------------------------------------------- fallback
# Everything below works from the outline alone. It is the whole of the previous
# implementation, kept for when the ONNX models are missing. It finds fingertips as convex
# corners of the outline, which works on a splayed hand and not on a closed one.
SAMPLES = 320
CURV_SPAN = 0.045
CURV_MAX_ANGLE = 128.0
MERGE_SPAN = 0.035
# A fingertip stands out from the hand's mass, measured from the outline's centroid in
# units of the mean radius. Deliberately loose: on a real hand the fingertips sit at
# 1.10-1.19 and a threshold inside that range cuts through the middle of them, losing
# half the fingers. Candidates are ranked and capped at five afterwards, and the corners
# where the arm leaves the frame are excluded separately, so being generous costs nothing.
TIP_MIN_REACH = 0.95
BORDER_TOL = 0.055
PALM_TIE = 0.85
MIN_FINGERS, MAX_FINGERS = 2, 5


def _resample(contour, n=SAMPLES):
    """The outline as n evenly spaced points, so thresholds can be fractions of perimeter."""
    pts = contour[:, 0].astype(np.float64)
    pts = np.vstack([pts, pts[:1]])
    d = np.concatenate([[0.0], np.cumsum(np.hypot(*np.diff(pts, axis=0).T))])
    if d[-1] <= 0:
        return None
    u = np.linspace(0.0, d[-1], n, endpoint=False)
    return np.stack([np.interp(u, d, pts[:, 0]), np.interp(u, d, pts[:, 1])], axis=1)


def _corners(poly, centre):
    """Turns in the outline, split into convex (tips) and concave (webs).

    Which sign of the cross product means convex depends on the winding, and deriving it
    from the signed area is easy to get backwards -- which silently swaps fingertips for
    webs. It is calibrated from the shape instead: the points furthest from the centre are
    fingertips, so whichever sign dominates there is the convex one.
    """
    n = len(poly)
    k = max(2, int(round(CURV_SPAN * n)))
    v1, v2 = np.roll(poly, k, axis=0) - poly, np.roll(poly, -k, axis=0) - poly
    n1, n2 = np.linalg.norm(v1, axis=1), np.linalg.norm(v2, axis=1)
    ok = (n1 > 1e-6) & (n2 > 1e-6)
    cos = np.ones(n)
    cos[ok] = np.clip((v1[ok] * v2[ok]).sum(1) / (n1[ok] * n2[ok]), -1, 1)
    angle = np.degrees(np.arccos(cos))
    cross = v1[:, 0] * v2[:, 1] - v1[:, 1] * v2[:, 0]
    out = np.argsort(-np.hypot(*(poly - centre).T))[:max(8, n // 12)]
    sign = 1.0 if np.sum(np.sign(cross[out])) >= 0 else -1.0
    convex = cross * sign > 0
    turning = angle < CURV_MAX_ANGLE
    return (_group(poly, np.where(turning & convex)[0], angle, n),
            _group(poly, np.where(turning & ~convex)[0], angle, n))


def _group(poly, idx, angle, n):
    """One point per run of adjacent candidates: the sharpest in each run."""
    if len(idx) == 0:
        return []
    gap = max(1, int(round(MERGE_SPAN * n)))
    runs, cur = [], [idx[0]]
    for a, b in zip(idx, idx[1:]):
        if b - a <= gap:
            cur.append(b)
        else:
            runs.append(cur)       # a new list each time: appending `cur` and then
            cur = [b]              # clearing it would empty the run just stored
    runs.append(cur)
    if len(runs) > 1 and (idx[0] + n) - idx[-1] <= gap:
        runs[0] = runs[-1] + runs[0]
        runs.pop()
    best = [min(r, key=lambda i: angle[i]) for r in runs if r]
    return [(int(i), poly[i]) for i in best]


def _on_border(p, shape):
    h, w = shape[:2]
    tol = max(3.0, BORDER_TOL * min(h, w))
    return p[0] <= tol or p[0] >= w - 1 - tol or p[1] <= tol or p[1] >= h - 1 - tol


def _palm_circle(mask, exclude=None):
    """Largest inscribed circle, preferring the one furthest from the wrist on a tie."""
    dt = cv2.distanceTransform(mask, cv2.DIST_L2, 5)
    _, r, _, c = cv2.minMaxLoc(dt)
    if exclude is None or r <= 0:
        return (float(c[0]), float(c[1])), float(r)
    ys, xs = np.nonzero(dt >= r * PALM_TIE)
    if len(xs) == 0:
        return (float(c[0]), float(c[1])), float(r)
    far = int(np.argmax(np.hypot(xs - exclude[0], ys - exclude[1])))
    x, y = int(xs[far]), int(ys[far])
    return (float(x), float(y)), float(dt[y, x])


def _from_silhouette(img, contour=None):
    h, w = img.shape[:2]
    sil = _silhouette(img) if contour is None else contour
    if sil is None or len(sil) < 5:
        return None
    mask = np.zeros((h, w), np.uint8)
    cv2.drawContours(mask, [sil], -1, 255, -1)
    area = float(mask.sum()) / 255
    if not (0.02 * h * w < area < 0.92 * h * w):
        return None
    poly = _resample(sil)
    if poly is None:
        return None
    centre = poly.mean(axis=0)
    peaks, webs = _corners(poly, centre)
    if len(peaks) < MIN_FINGERS:
        return None
    mean_r = float(np.hypot(*(poly - centre).T).mean()) or 1.0
    # a real fingertip is never clipped by the frame, which is what separates fingers from
    # the corners where the forearm leaves the picture
    cand = [(i, p) for i, p in peaks
            if _dist(p, centre) / mean_r >= TIP_MIN_REACH and not _on_border(p, img.shape)]
    if len(cand) < MIN_FINGERS:
        return None
    cand.sort(key=lambda ip: -_dist(ip[1], centre))
    tips_i = [i for i, _ in cand[:MAX_FINGERS]]
    fc = np.mean([poly[i] for i in tips_i], axis=0)
    wrist = tuple(float(v) for v in poly[int(np.argmax(np.hypot(*(poly - fc).T)))])
    palm, palm_r = _palm_circle(mask, wrist)
    if palm_r < min(h, w) * 0.03:
        return None
    valleys = [tuple(float(v) for v in p) for _, p in webs
               if _dist(p, palm) < palm_r * 2.6 and _dist(p, wrist) > palm_r * 1.4
               and not _on_border(p, img.shape)]
    tips = sorted((tuple(float(v) for v in poly[i]) for i in tips_i),
                  key=lambda p: np.arctan2(p[1] - wrist[1], p[0] - wrist[0]))
    return Hand(palm, palm_r, wrist, tips, valleys, sil, None)
