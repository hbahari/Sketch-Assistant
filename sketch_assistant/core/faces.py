"""Offline face detection: YuNet (ONNX, gives 5 landmarks) when available, else the Haar cascade.

Where MediaPipe's face mesh is available (core/landmarks.py) each face's guide oval is
fitted to the mesh's outline of the face rather than scaled from the detector's box, and
a face the detector misses or misreads on a close-up is recovered (see "the face's own
outline" below).
"""
from dataclasses import dataclass
from pathlib import Path
import cv2
import numpy as np

ASSETS = Path(__file__).resolve().parent.parent / "assets"
CASCADE_PATH = ASSETS / "haarcascade_frontalface_default.xml"
YUNET_PATH = ASSETS / "models" / "face_detection_yunet_2023mar.onnx"
MARGIN = 0.35  # crop margin around the detected face box
_cascade = _yunet = None


@dataclass
class Face:
    x: int
    y: int
    w: int
    h: int
    # 5 points in image coords: right eye, left eye, nose tip, right mouth corner, left mouth corner (YuNet only)
    landmarks: tuple = ()
    # The box the guide oval is drawn from (guides._oval), when it comes from the face
    # mesh: (x, y, w, h) in image pixels, floats, and free to run past the photo's edge,
    # as a close-up's face does. None means the detector box above is used.
    oval_box: tuple = None

    def contains(self, px, py):
        return self.x <= px <= self.x + self.w and self.y <= py <= self.y + self.h


def load_image(path, max_side=1600):
    """Read an image (EXIF-rotated) and downscale so the long side <= max_side."""
    img = cv2.imread(str(path))
    if img is None:
        raise ValueError(f"Could not read image: {path}")
    scale = max_side / max(img.shape[:2])
    if scale < 1:
        img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    return img


def yunet_available():
    return hasattr(cv2, "FaceDetectorYN") and YUNET_PATH.exists()


def _yunet_faces(img):
    """Returns a list of Face (maybe empty) or None if YuNet can't be used here."""
    global _yunet
    if not yunet_available():
        return None
    try:
        H, W = img.shape[:2]
        s = min(1.0, 960 / max(H, W))
        small = cv2.resize(img, None, fx=s, fy=s, interpolation=cv2.INTER_AREA) if s < 1 else img
        sh, sw = small.shape[:2]
        if _yunet is None:
            _yunet = cv2.FaceDetectorYN.create(str(YUNET_PATH), "", (sw, sh), 0.7, 0.3, 100)
        _yunet.setInputSize((sw, sh))
        _, res = _yunet.detect(small)
    except Exception:  # old OpenCV build, bad model file, ...
        return None
    faces = []
    for r in (res if res is not None else []):
        x, y, fw, fh = [float(v) / s for v in r[:4]]
        if fw < min(H, W) / 14:
            continue
        x0, y0 = max(0, int(x)), max(0, int(y))
        lm = tuple((float(r[4 + 2 * i]) / s, float(r[5 + 2 * i]) / s) for i in range(5))
        faces.append(Face(x0, y0, min(int(fw), W - x0), min(int(fh), H - y0), lm))
    return faces


def _haar_faces(img):
    global _cascade
    if _cascade is None:
        _cascade = cv2.CascadeClassifier(str(CASCADE_PATH))
    gray = cv2.equalizeHist(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY))
    m = max(40, min(img.shape[:2]) // 12)
    return [Face(int(x), int(y), int(w), int(h)) for x, y, w, h in _cascade.detectMultiScale(gray, 1.1, 5, minSize=(m, m))]


def detect_faces(img):
    """Faces sorted left-to-right. YuNet first; Haar if YuNet is unavailable or finds nothing.
    Then each face's outline from the face mesh, where it is available."""
    faces = _yunet_faces(img) or _haar_faces(img)
    faces = _with_outlines(img, faces)
    return sorted(faces, key=lambda f: f.x)


# --------------------------------------------------------------------------- the face's own outline
# The guide oval used to be scaled from the detector's box (OVAL_W/OVAL_H in guides.py),
# and on close-ups the box is too small or in the wrong place: a tester found the circle
# "smaller than the face itself". The face mesh traces the outline of the face -- forehead,
# temples, cheeks, jaw and chin -- and the oval is now an ellipse fitted to that outline,
# expressed as the box that the guides' own constants turn into that ellipse, so nothing
# downstream changes. Measured on fifteen faces in the tester's photos, with the chin and
# the widest points of the face marked by hand: the chin on the oval (within 12%) and the
# sides inside it on 10 of 15, against 2 of 15 for the box-scaled oval (11 against 3 on
# the 900 px copies kept in tests/fixtures/portraits_close). Two choices were
# made on those same fifteen: the mesh starts from the padded face finder's points where
# it found the same face (from YuNet's, 6 of 15 -- unpadded, YuNet reads a close-up's face
# small and the mesh follows), and two mesh passes, not more (3 to 6 passes: 7 or 8).
# Side profiles keep the box: the mesh's outline of a profile is unreliable, and the mesh
# says so (its face-present flag goes negative), so it is only used where the flag is
# positive.
#
# The same padded face finder Nose and Eyes use also recovers a face YuNet misses at its
# stricter threshold (three of nineteen close-ups) or reads as only the mouth and chin (one).
FACE_OUTLINE = (10, 338, 297, 332, 284, 251, 389, 356, 454, 323, 361, 288, 397, 365, 379, 378,
                400, 377, 152, 148, 176, 149, 150, 136, 172, 58, 132, 93, 234, 127, 162, 21,
                54, 103, 67, 109)
MESH_NOSE = 4
OUTLINE_AGREE = 0.35        # mesh nose within this many eye-to-mouth lengths of the detector's
RECOVER_SUPPORT = 3.0       # as Eyes mode: the padded finder must agree with itself this much


def _oval_box(img, pts):
    """The oval box for the face whose five detector points are `pts`, or None."""
    from . import landmarks
    from .guides import OVAL_H, OVAL_RISE, OVAL_W
    pts = np.asarray(pts, float)
    eye, mouth = (pts[0] + pts[1]) / 2, (pts[3] + pts[4]) / 2
    d = float(np.linalg.norm(eye - mouth))
    if d < 8:
        return None
    mesh, flag = landmarks.face_mesh(img, eye, mouth, with_flag=True)
    if mesh is None or flag <= 0 or np.linalg.norm(mesh[MESH_NOSE] - pts[2]) > OUTLINE_AGREE * d:
        return None
    (cx, cy), (a, b), ang = cv2.fitEllipse(mesh[list(FACE_OUTLINE)].astype(np.float32))
    up = (eye - mouth) / d
    along_a = abs(np.cos(np.radians(ang)) * up[0] + np.sin(np.radians(ang)) * up[1])
    width, height = (b, a) if along_a > 0.7071 else (a, b)     # height runs up the face
    bw, bh = width / OVAL_W, height / OVAL_H
    return (cx - bw / 2, cy + bh * OVAL_RISE - bh / 2, bw, bh)


def _with_outlines(img, faces):
    from . import landmarks
    if not landmarks.mesh_available():
        return faces
    from .noses import find_face                     # here: noses imports this module
    found = find_face(img)
    if found is not None and found.score < RECOVER_SUPPORT:
        found = None
    for f in faces:
        if len(f.landmarks) == 5:
            # the padded finder's points, where it found this same face: on a close-up
            # YuNet, unpadded, reads the face smaller, and the mesh starts from them
            same = found is not None and f.contains(*found.pts[2])
            f.oval_box = _oval_box(img, found.pts if same else f.landmarks)
    if found is None:
        return faces
    nx, ny = found.pts[2]
    if any(f.contains(nx, ny) for f in faces):
        return faces                                 # already have it
    ob = _oval_box(img, found.pts)
    if ob is None:
        return faces
    H, W = img.shape[:2]
    x, y, w, h = ob
    x0, y0 = int(max(0, x)), int(max(0, y))
    x1, y1 = int(min(W, x + w)), int(min(H, y + h))
    if x1 - x0 < 8 or y1 - y0 < 8:
        return faces
    new = Face(x0, y0, x1 - x0, y1 - y0, tuple((float(px), float(py)) for px, py in found.pts), ob)
    # a box YuNet put on part of this face (the mouth and chin, on one photo) goes
    kept = [f for f in faces if not (new.contains(f.x + f.w / 2, f.y + f.h / 2) and f.w * f.h < 0.4 * w * h)]
    return kept + [new]


def crop_info(img, face, margin=MARGIN):
    """Crop a face with room for hair/chin/ears.

    Returns (crop, landmarks relative to the crop, face box relative to the crop).
    The box is returned explicitly rather than assumed to be centred, because the crop
    is clipped at the image edges when the face sits near one.
    """
    H, W = img.shape[:2]
    mx, my = int(face.w * margin), int(face.h * margin)
    x0, y0 = max(0, face.x - mx), max(0, face.y - my)
    x1, y1 = min(W, face.x + face.w + mx), min(H, face.y + face.h + my)
    box = (face.x - x0, face.y - y0, face.w, face.h)
    if face.oval_box is not None:
        # the crop also takes in the whole oval, as far as the photo goes
        ox, oy, ow, oh = face.oval_box
        x0, y0 = max(0, min(x0, int(ox - 0.08 * ow))), max(0, min(y0, int(oy - 0.08 * oh)))
        x1, y1 = min(W, max(x1, int(ox + 1.08 * ow))), min(H, max(y1, int(oy + 1.08 * oh)))
        box = (ox - x0, oy - y0, ow, oh)
    return (img[y0:y1, x0:x1].copy(),
            tuple((px - x0, py - y0) for px, py in face.landmarks),
            box)


def crop_face(img, face, margin=MARGIN):
    return crop_info(img, face, margin)[0]


BOX_MARGIN = 0.12


def crop_to_box(img, box, margin=BOX_MARGIN):
    """Crop to a user-drawn region, with a little room around it.

    The object counterpart of `crop_info`. Cropping is what makes a drawn selection work
    without threading it through every renderer: segmentation seeds itself from the middle
    of whatever image it is handed, so once the image *is* the selection, the seed is the
    selection. The margin leaves the object's own edge inside the frame rather than flush
    against it -- measured at 5%, 12% and 25%, all three isolate the object and 12% sits
    in the middle.
    """
    b = crop_bounds(img, box, margin)
    if b is None:                              # degenerate selection: use the whole frame
        return img
    x0, y0, x1, y1 = b
    return img[y0:y1, x0:x1].copy()


def crop_bounds(img, box, margin=BOX_MARGIN):
    """The pixel bounds `crop_to_box` cuts: (x0, y0, x1, y1), or None for the whole frame."""
    H, W = img.shape[:2]
    x, y, w, h = box
    mx, my = w * margin, h * margin
    x0, y0 = int(max(0, x - mx)), int(max(0, y - my))
    x1, y1 = int(min(W, x + w + mx)), int(min(H, y + h + my))
    if x1 - x0 < 8 or y1 - y0 < 8:
        return None
    return x0, y0, x1, y1
