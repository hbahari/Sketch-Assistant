"""Offline face detection: YuNet (ONNX, gives 5 landmarks) when available, else the Haar cascade."""
from dataclasses import dataclass
from pathlib import Path
import cv2

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
    """Faces sorted left-to-right. YuNet first; Haar if YuNet is unavailable or finds nothing."""
    faces = _yunet_faces(img) or _haar_faces(img)
    return sorted(faces, key=lambda f: f.x)


def crop_info(img, face, margin=MARGIN):
    """Crop a face with room for hair/chin/ears -> (crop, landmarks relative to the crop)."""
    H, W = img.shape[:2]
    mx, my = int(face.w * margin), int(face.h * margin)
    x0, y0 = max(0, face.x - mx), max(0, face.y - my)
    x1, y1 = min(W, face.x + face.w + mx), min(H, face.y + face.h + my)
    return img[y0:y1, x0:x1].copy(), tuple((px - x0, py - y0) for px, py in face.landmarks)


def crop_face(img, face, margin=MARGIN):
    return crop_info(img, face, margin)[0]
