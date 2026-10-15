"""Offline face detection (OpenCV Haar cascade, bundled in assets/)."""
from dataclasses import dataclass
from pathlib import Path
import cv2

CASCADE_PATH = Path(__file__).resolve().parent.parent / "assets" / "haarcascade_frontalface_default.xml"
_cascade = None
MARGIN = 0.35  # crop margin around the detected face box


@dataclass
class Face:
    x: int
    y: int
    w: int
    h: int

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


def detect_faces(img):
    """Return faces sorted left-to-right."""
    global _cascade
    if _cascade is None:
        _cascade = cv2.CascadeClassifier(str(CASCADE_PATH))
    gray = cv2.equalizeHist(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY))
    min_size = max(40, min(img.shape[:2]) // 12)
    found = _cascade.detectMultiScale(gray, 1.1, 5, minSize=(min_size, min_size))
    faces = [Face(int(x), int(y), int(w), int(h)) for x, y, w, h in found]
    return sorted(faces, key=lambda f: f.x)


def crop_face(img, face, margin=MARGIN):
    """Crop a face with extra room for hair/chin/ears."""
    H, W = img.shape[:2]
    mx, my = int(face.w * margin), int(face.h * margin)
    x0, y0 = max(0, face.x - mx), max(0, face.y - my)
    x1, y1 = min(W, face.x + face.w + mx), min(H, face.y + face.h + my)
    return img[y0:y1, x0:x1].copy()
