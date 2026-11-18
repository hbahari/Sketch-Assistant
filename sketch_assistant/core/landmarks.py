"""Trained landmark models: MediaPipe's iris model and face mesh, run through OpenCV.

Eyes and Nose modes were first built on hand-written image rules, and the rules' weak
point is that one bad measurement scales the whole construction -- an iris read at twice
its size drew an eyeball twice the size of the eye. These two models were trained on a
very large number of faces and are what MediaPipe itself uses:

* `iris_landmark.tflite` -- a 64 x 64 crop round one eye in, 71 points round the lids and
  brow plus 5 on the iris out. Needs no face, so it works on a close-up of a single eye.
* `face_landmark.tflite` -- a 192 x 192 crop round a face in, 468 points out, including
  the nose's tip, wings and bridge and the outline of each eye.

Both are Apache 2.0, about 4 MB together, and run on the phone like the other models --
OpenCV reads the TFLite format directly from 4.8, and the Android build uses 4.12
(checked: identical output under 4.12 and 4.14). `scripts/download_models.py` fetches
them. Without them every caller falls back to the rules.
"""
from pathlib import Path

import cv2
import numpy as np

MODELS = Path(__file__).resolve().parent.parent / "assets" / "models"
IRIS_PATH = MODELS / "iris_landmark.tflite"
MESH_PATH = MODELS / "face_landmark.tflite"

_nets = {}


def _net(path):
    if path not in _nets:
        net = None
        if path.exists() and hasattr(cv2.dnn, "readNetFromTFLite"):
            try:
                net = cv2.dnn.readNetFromTFLite(str(path))
            except Exception:                      # old OpenCV, damaged download
                net = None
        _nets[path] = net
    return _nets[path]


def iris_available():
    return _net(IRIS_PATH) is not None


def mesh_available():
    return _net(MESH_PATH) is not None


def _crop(img, cx, cy, side, size, angle=0.0):
    """A square crop of `side` image pixels centred on (cx, cy), turned by `angle` degrees
    and resampled to `size`. Returns (crop, affine image->crop). Past the photo's edge it
    is filled with the photo's mean colour, not smeared edge pixels."""
    s = size / max(side, 1e-6)
    pre = 1.0
    if s < 0.5:                                    # area-average first when shrinking a lot
        pre = min(1.0, s * 2)
        img = cv2.resize(img, None, fx=pre, fy=pre, interpolation=cv2.INTER_AREA)
        cx, cy, side = cx * pre, cy * pre, side * pre
        s = size / side
    M = cv2.getRotationMatrix2D((cx, cy), angle, s)
    M[0, 2] += size / 2 - cx
    M[1, 2] += size / 2 - cy
    fill = tuple(int(v) for v in img.reshape(-1, 3).mean(0))
    crop = cv2.warpAffine(img, M, (size, size), flags=cv2.INTER_LINEAR,
                          borderMode=cv2.BORDER_CONSTANT, borderValue=fill)
    M = M @ np.array([[pre, 0, 0], [0, pre, 0], [0, 0, 1]], float)
    return crop, M


def _back(M, pts):
    inv = cv2.invertAffineTransform(M)
    return pts @ inv[:, :2].T + inv[:, 2]


def _blob(crop):
    x = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    return x.transpose(2, 0, 1)[None]


# --------------------------------------------------------------------------- the eye
IRIS_SCALE = 2.3        # crop side / corner-to-corner width, as MediaPipe crops for this model
EYE_CORNERS = (0, 8)    # indices of the two corners among the first 16 (lid) points


def _iris_once(img, cx, cy, side, flip, angle=0.0):
    net = _net(IRIS_PATH)
    crop, M = _crop(img, cx, cy, side, 64, angle)
    if flip:
        crop = crop[:, ::-1]
    net.setInput(_blob(np.ascontiguousarray(crop)))
    eye, iris = net.forward(["output_eyes_contours_and_brows", "output_iris"])
    pts = np.r_[eye.reshape(-1, 3)[:, :2], iris.reshape(-1, 3)[:, :2]].astype(np.float64)
    if flip:
        pts[:, 0] = 64.0 - pts[:, 0]
    return _back(M, pts)


def _limbus_strength(g, c, r):
    """Darker just inside the circle than just outside, on the left and right arcs."""
    a = np.deg2rad(np.r_[np.arange(-40, 41, 8), np.arange(140, 221, 8)])
    h, w = g.shape

    def ring(rr):
        xs = np.clip((c[0] + rr * np.cos(a)).astype(int), 0, w - 1)
        ys = np.clip((c[1] + rr * np.sin(a)).astype(int), 0, h - 1)
        return float(g[ys, xs].mean())
    return (ring(1.15 * r) - ring(0.85 * r)) / (float(g.std()) + 1e-6)


def iris_landmarks(img, start=None, iterations=3, flip=None):
    """The eye's lid outline and iris, or None without the model.

    `start` is (cx, cy, side) to begin from; by default the whole image, padded to twice
    its size, which is about right for a close-up that the eye fills. Each pass re-crops
    round the corners the last pass found, at MediaPipe's own 2.3 eye-widths. The model was
    trained on one eye (the subject's right, on the left of the picture), so the other eye is
    mirrored before it is shown the model. `flip` says which; when it isn't known (a
    close-up of one eye) both are tried and the answer whose iris circle sits on the
    stronger dark-to-light edge is kept.

    Returns dict(lids=16x2 (corner, lower lid, corner, upper lid), brow=..., iris=(x, y),
    r=radius, corners=(a, b), score=edge strength, flipped=bool).
    """
    if _net(IRIS_PATH) is None:
        return None
    H, W = img.shape[:2]
    if start is None:
        start = (W / 2.0, H / 2.0, 2.0 * max(W, H))
    g = cv2.GaussianBlur(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), (0, 0), max(1.0, W / 400))
    best = None
    for flip in ((False, True) if flip is None else (bool(flip),)):
        cx, cy, side = start
        angle = 0.0
        for _ in range(iterations):
            pts = _iris_once(img, cx, cy, side, flip, angle)
            a, b = pts[EYE_CORNERS[0]], pts[EYE_CORNERS[1]]
            width = float(np.linalg.norm(b - a))
            if width < 4:
                break
            cx, cy = (a + b) / 2
            side = IRIS_SCALE * width
            angle = float(np.degrees(np.arctan2(b[1] - a[1], b[0] - a[0])))
            if a[0] > b[0]:
                angle += 180.0
            angle = (angle + 180.0) % 360.0 - 180.0
            # the crop is turned so the eye is level, as MediaPipe does; warpAffine's
            # angle is anticlockwise, the eye's is measured clockwise on screen
            angle = -angle
        iris = pts[71]
        r = float(np.mean([np.linalg.norm(q - iris) for q in pts[72:76]]))
        score = _limbus_strength(g, iris, r)
        res = dict(lids=pts[:16], brow=pts[16:71], iris=(float(iris[0]), float(iris[1])), r=r,
                   corners=(tuple(pts[EYE_CORNERS[0]]), tuple(pts[EYE_CORNERS[1]])),
                   score=float(score), flipped=flip)
        if best is None or score > best["score"]:
            best = res
    return best


# --------------------------------------------------------------------------- the face
MESH_SCALE = 1.6        # crop side / the face's eye-to-mouth length x 2.6, see face_mesh
MESH_EYES = ((33, 133), (362, 263))   # outer, inner corner of the eye on the image's left, then right

def face_mesh(img, eye_mid, mouth_mid, iterations=2, with_flag=False):
    """468 face points, or None. Started from the face detector's eye and mouth centres.
    With `with_flag`, (points, flag): the model's own face-present score, positive when it
    thinks a face fills its crop.

    MediaPipe crops the face from its own detector, turned so the face is upright and
    scaled up 1.5 times; this does the same from the five-point detector already in the
    app, then crops again round the mesh's own points, which is how MediaPipe tracks.
    """
    net = _net(MESH_PATH)
    if net is None:
        return (None, 0.0) if with_flag else None
    eye_mid, mouth_mid = np.asarray(eye_mid, float), np.asarray(mouth_mid, float)
    up = eye_mid - mouth_mid
    d = float(np.linalg.norm(up))
    if d < 4:
        return (None, 0.0) if with_flag else None
    angle = float(np.degrees(np.arctan2(up[0], -up[1])))      # 0 when the face is upright
    centre = (eye_mid + mouth_mid) / 2
    side = 2.6 * d * MESH_SCALE / 1.6
    pts, first = None, None
    for _ in range(iterations):
        crop, M = _crop(img, centre[0], centre[1], side, 192, angle)
        net.setInput(_blob(crop))
        outs = dict(zip(net.getUnconnectedOutLayersNames(), net.forward(net.getUnconnectedOutLayersNames())))
        flag, mesh = outs["conv2d_31"], outs["conv2d_21"]
        first = float(flag.ravel()[0]) if first is None else first
        p = mesh.reshape(-1, 3)[:, :2].astype(np.float64)
        pts = _back(M, p)
        lo, hi = pts.min(0), pts.max(0)
        centre = (lo + hi) / 2
        side = 1.5 * float(max(hi - lo))
    # the flag from the first crop, made from the detector alone: the later crops are
    # framed by the mesh itself, and it will frame a non-face as confidently as a face
    return (pts, first) if with_flag else pts
