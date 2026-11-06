"""Figure structure: 33 body landmarks and a body mask, from MediaPipe Pose.

Posture is the one subject where the abstract version is not a simplification. Gesture --
the line of action in thirty seconds -- and the mannequin block-in are what figure drawing
courses actually drill; full rendering comes later if at all. So what this module exposes
is aimed at those: the line of action, the shoulder and hip bars whose opposing tilt is
contrapposto, the ribcage and pelvis masses, and proportion measured in heads.

Hands and faces are deliberately not detailed here. At full-body scale a hand is a few
dozen pixels, drawing it in detail is wrong, and the app has dedicated modes for both.

Two Apache 2.0 models from OpenCV Zoo, run through cv2.dnn: a person detector (so several
people can be found and chosen between) and the pose model, which returns the landmarks
*and* a body segmentation mask. The mask matters -- it is far better than the GrabCut
silhouette the other modes fall back on, so figure masking comes free and accurate.
"""
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

MODELS = Path(__file__).resolve().parent.parent / "assets" / "models"
PERSON_MODEL = MODELS / "person_detection_mediapipe_2023mar.onnx"
POSE_MODEL = MODELS / "pose_estimation_mediapipe_2023mar.onnx"

# MediaPipe's 33-point body model. Only the ones that carry drawing information are named.
NOSE = 0
L_SHOULDER, R_SHOULDER = 11, 12
L_ELBOW, R_ELBOW = 13, 14
L_WRIST, R_WRIST = 15, 16
L_HIP, R_HIP = 23, 24
L_KNEE, R_KNEE = 25, 26
L_ANKLE, R_ANKLE = 27, 28
L_EAR, R_EAR = 7, 8

LIMBS = {
    "left arm": (L_SHOULDER, L_ELBOW, L_WRIST),
    "right arm": (R_SHOULDER, R_ELBOW, R_WRIST),
    "left leg": (L_HIP, L_KNEE, L_ANKLE),
    "right leg": (R_HIP, R_KNEE, R_ANKLE),
}
TORSO = (L_SHOULDER, R_SHOULDER, R_HIP, L_HIP)

# Detection threshold. At 0.5 the detector misses the second person in a two-figure shot;
# at 0.2 it starts inventing people in empty background. Measured over twenty photographs,
# 0.35 recovers the real second figures without any of the false ones.
PERSON_SCORE, NMS_IOU, POSE_CONF = 0.35, 0.3, 0.5
DETECT_MAX = 1000        # long side used for detection; landmarks scale back afterwards
# The detector wants some room around the figure and finds nothing when one fills the
# frame -- which is exactly what happens after the UI crops to a chosen figure and the
# styles re-detect inside that crop. Padding fixes it, but no single amount suits every
# photo: measured over eight tight crops, no padding found seven of them and 0.2 found the
# eighth while losing two others. So a couple are tried in turn and the first that finds a
# figure wins. Most photos are done on the first attempt.
DETECT_PADS = (0.0, 0.2, 0.45)
VISIBLE = 0.5            # a landmark below this is inferred rather than seen

_person_net = _pose_net = None
_tried = False


@dataclass
class Body:
    """One figure. Points are (x, y) in image pixels."""
    landmarks: np.ndarray                  # (33, 2)
    visible: np.ndarray                    # (33,) bool
    box: tuple                             # (x, y, w, h) around the whole figure
    mask: np.ndarray = None                # body segmentation, same size as the image
    score: float = 0.0

    # `Mode.detect` promises the UI a list of tappable regions, and the selector widget
    # reads them as .x/.y/.w/.h with a .contains(). Face satisfies that already; Body has
    # to as well, or the selector would need to know which subject it is showing.
    @property
    def x(self):
        return self.box[0]

    @property
    def y(self):
        return self.box[1]

    @property
    def w(self):
        return self.box[2]

    @property
    def h(self):
        return self.box[3]

    def contains(self, px, py):
        x, y, w, h = self.box
        return x <= px <= x + w and y <= py <= y + h

    def p(self, i):
        return tuple(float(v) for v in self.landmarks[i])

    @property
    def shoulders(self):
        return self.p(L_SHOULDER), self.p(R_SHOULDER)

    @property
    def hips(self):
        return self.p(L_HIP), self.p(R_HIP)

    @property
    def head_height(self):
        """Roughly one head, measured from the torso.

        The landmark set has no crown or chin, so the head has to be inferred. The obvious
        candidates -- the span across the ears, or the shoulder width -- are both measured
        *across* the body, and they collapse the moment the figure turns or is
        foreshortened: across twenty-two figures the ear-span estimate gave a plausible
        answer eight times and once claimed a figure was 68 heads tall.

        Shoulder-midpoint to hip-midpoint is measured *along* the body instead, so it
        survives rotation. It spans about 2.2 heads on an adult, which agrees with the
        classical scale (shoulders at 1.4 heads, hip joints at about 3.6). That estimate
        was plausible on all twenty-two.
        """
        lm, vis = self.landmarks, self.visible
        if vis[L_SHOULDER] and vis[R_SHOULDER] and vis[L_HIP] and vis[R_HIP]:
            chest = (lm[L_SHOULDER] + lm[R_SHOULDER]) / 2
            pelvis = (lm[L_HIP] + lm[R_HIP]) / 2
            torso = float(np.hypot(*(chest - pelvis)))
            if torso > 1.0:
                return torso / 2.2
        if vis[L_SHOULDER] and vis[R_SHOULDER]:        # no hips: nose to the shoulder line
            chest = (lm[L_SHOULDER] + lm[R_SHOULDER]) / 2
            neck = float(np.hypot(*(lm[NOSE] - chest)))
            if neck > 1.0:
                return neck / 0.85
            return max(float(np.hypot(*(lm[L_SHOULDER] - lm[R_SHOULDER]))) / 1.4, 1.0)
        return max(self.box[3] / 7.5, 1.0)             # nothing to measure: assume average

    @property
    def heads_tall(self):
        """The figure's height in head units. The classic proportion check: about 7.5 on
        an adult standing upright, less when seated or foreshortened."""
        return self.box[3] / self.head_height

    @property
    def line_of_action(self):
        """The curve the whole pose hangs off: head, chest, pelvis, and on to the feet.

        The first thing drawn in any gesture study, and the thing that makes a figure look
        like it is doing something rather than standing to attention.
        """
        ls, rs = np.array(self.shoulders[0]), np.array(self.shoulders[1])
        lh, rh = np.array(self.hips[0]), np.array(self.hips[1])
        chest, pelvis = (ls + rs) / 2, (lh + rh) / 2
        pts = [self.p(NOSE), tuple(chest), tuple(pelvis)]
        feet = [self.landmarks[i] for i in (L_ANKLE, R_ANKLE) if self.visible[i]]
        if feet:
            pts.append(tuple(np.mean(feet, axis=0)))
        return pts

    @property
    def tilts(self):
        """Shoulder-line and hip-line angles in degrees.

        In any weighted standing pose these tilt in opposite directions -- contrapposto --
        and seeing that is the single biggest step from a stiff figure to a live one.
        """
        def ang(a, b):
            d = np.array(b) - np.array(a)
            a_deg = float(np.degrees(np.arctan2(d[1], d[0])))
            # a line has no direction: -178 and +2 are the same tilt, and reporting one as
            # nearly upside-down made the shoulder and hip bars look wildly disagreeing
            # when they were almost parallel
            while a_deg <= -90:
                a_deg += 180
            while a_deg > 90:
                a_deg -= 180
            return a_deg
        return ang(*self.shoulders), ang(*self.hips)

    @property
    def contrapposto(self):
        """How far the shoulder and hip lines disagree, in degrees, and which way.

        Positive means they tilt in opposite directions, which is what a weighted standing
        pose does. Near zero means the figure is square-on or symmetrical.
        """
        sh, hp = self.tilts
        return sh - hp

    def limb_chains(self):
        """Each limb as its chain of points, skipping any that was never seen."""
        out = {}
        for name, idx in LIMBS.items():
            pts = [self.p(i) for i in idx if self.visible[i]]
            if len(pts) >= 2:
                out[name] = pts
        return out


def models_available():
    return PERSON_MODEL.exists() and POSE_MODEL.exists()


def _nets():
    global _person_net, _pose_net, _tried
    if _tried:
        return _person_net, _pose_net
    _tried = True
    if not models_available():
        return None, None
    try:
        from .vendor.mp_persondet import MPPersonDet
        from .vendor.mp_pose import MPPose
        _person_net = MPPersonDet(modelPath=str(PERSON_MODEL), nmsThreshold=NMS_IOU,
                                  scoreThreshold=PERSON_SCORE, topK=5000)
        _pose_net = MPPose(modelPath=str(POSE_MODEL), confThreshold=POSE_CONF)
    except Exception:
        _person_net = _pose_net = None
    return _person_net, _pose_net


_cache = {}
CACHE_MAX = 4


def detect(img):
    """Every figure in the photo, left to right. Empty list if none or no models.

    Cached per image: the UI asks for this once to draw the tappable boxes and again for
    each style, and running both models twice over is a visible pause on a phone.
    """
    key = (img.shape, hash(img.tobytes()[::97]))
    if key in _cache:
        return _cache[key]
    bodies = _detect_uncached(img)
    if len(_cache) >= CACHE_MAX:
        _cache.clear()
    _cache[key] = bodies
    return bodies


def _detect_uncached(img):
    person_net, pose_net = _nets()
    if person_net is None or pose_net is None:
        return []
    h, w = img.shape[:2]
    scale = min(1.0, DETECT_MAX / max(h, w))
    base = (cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
            if scale < 1.0 else img)
    for frac in DETECT_PADS:
        pad = int(max(base.shape[:2]) * frac)
        small = (cv2.copyMakeBorder(base, pad, pad, pad, pad, cv2.BORDER_REPLICATE)
                 if pad else base)
        found = _read(person_net, pose_net, small, pad, scale, (h, w))
        if found:
            return found
    return []


def _read(person_net, pose_net, small, pad, scale, shape):
    """Detect and pose on one padded copy. Returns [] if nothing is found."""
    h, w = shape
    try:
        people = person_net.infer(small)
    except Exception:
        return []
    if people is None or len(people) == 0:
        return []

    out = []
    for p in people:
        try:
            res = pose_net.infer(small, p)
        except Exception:
            continue
        if res is None:
            continue
        bbox, lms, _world, mask, _heat, conf = res
        lm = np.asarray(lms)[:-6]                    # 33 keypoints; the rest are auxiliary
        xy = (lm[:, :2].astype(np.float32) - pad) / scale
        vis = (lm[:, 4] > VISIBLE)
        if not np.isfinite(xy).all() or vis.sum() < 6:
            continue
        seen = xy[vis]
        x0, y0 = seen.min(axis=0)
        x1, y1 = seen.max(axis=0)
        # the figure's own extent, not the detector's anchor box, which covers only the
        # head and chest and reads as a strange thing to tap
        box = (float(max(0, x0)), float(max(0, y0)),
               float(min(w, x1) - max(0, x0)), float(min(h, y1) - max(0, y0)))
        if box[2] < 8 or box[3] < 8:
            continue
        full = None
        if mask is not None and mask.size:
            if pad:                                  # undo the padding before rescaling
                mask = mask[pad:mask.shape[0] - pad, pad:mask.shape[1] - pad]
            full = cv2.resize(mask, (w, h), interpolation=cv2.INTER_NEAREST) \
                if mask.shape[:2] != (h, w) else mask
        out.append(Body(xy, vis, box, full, float(conf)))
    out.sort(key=lambda b: b.box[0])
    return out


def union_box(bodies, img_shape, margin=0.15):
    """One region covering every chosen figure and the space between them.

    Two people interacting are a single composition -- the gap between them carries the
    relationship -- so selecting several gives one crop spanning them all rather than
    several separate drawings.

    The margin is not just for looks. The styles re-detect inside the crop, and the person
    detector finds nothing when a figure fills the frame edge to edge: cropped flush, two
    of twenty photographs stopped being recognised as figures at all and fell back to
    plain line art. At 15% all twenty survive. A figure jammed against the frame is poor
    composition to draw from anyway.
    """
    if not bodies:
        return None
    H, W = img_shape[:2]
    x0 = min(b.box[0] for b in bodies)
    y0 = min(b.box[1] for b in bodies)
    x1 = max(b.box[0] + b.box[2] for b in bodies)
    y1 = max(b.box[1] + b.box[3] for b in bodies)
    mx, my = (x1 - x0) * margin, (y1 - y0) * margin
    x0, y0 = max(0.0, x0 - mx), max(0.0, y0 - my)
    x1, y1 = min(float(W), x1 + mx), min(float(H), y1 + my)
    return (x0, y0, x1 - x0, y1 - y0)


def combined_mask(bodies, img_shape):
    """The chosen figures' own segmentation masks, merged. None if the models gave none."""
    masks = [b.mask for b in bodies if b.mask is not None]
    if not masks:
        return None
    out = np.zeros(img_shape[:2], np.uint8)
    for m in masks:
        mm = cv2.resize(m, (img_shape[1], img_shape[0]), interpolation=cv2.INTER_NEAREST) \
            if m.shape[:2] != img_shape[:2] else m
        out = np.maximum(out, mm)
    return out
