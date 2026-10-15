"""Regenerate the style-button thumbnails:  python scripts/make_examples.py portrait.jpg"""
import sys
from pathlib import Path
import cv2
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from sketch_assistant.core.faces import crop_face, detect_faces, load_image
from sketch_assistant.core.styles import STYLES, render

img = load_image(sys.argv[1]); face = detect_faces(img)[0]
crop = crop_face(img, face)
out = Path(__file__).resolve().parent.parent / "sketch_assistant" / "assets" / "examples"
for key in STYLES:
    sk = render(key, crop); h, w = sk.shape[:2]; s = min(h, w)
    sq = sk[(h - s) // 2:(h + s) // 2, (w - s) // 2:(w + s) // 2]
    cv2.imwrite(str(out / f"{key}.png"), cv2.resize(sq, (360, 360), interpolation=cv2.INTER_AREA))
print("wrote", list(out.iterdir()))
