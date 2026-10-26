"""Regenerate style-button thumbnails:  python scripts/make_examples.py portrait.jpg object.jpg"""
import sys
from pathlib import Path
import cv2
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from sketch_assistant.core.faces import crop_face, detect_faces, load_image
from sketch_assistant.core.styles import OBJECT_STYLES, STYLES, render

out = Path(__file__).resolve().parent.parent / "sketch_assistant" / "assets" / "examples"
portrait = crop_face(load_image(sys.argv[1]), detect_faces(load_image(sys.argv[1]))[0])
obj = load_image(sys.argv[2])
for styles, src in ((STYLES, portrait), (OBJECT_STYLES, obj)):
    for key in styles:
        sk = render(key, src); h, w = sk.shape[:2]; s = min(h, w)
        sq = sk[(h - s) // 2:(h + s) // 2, (w - s) // 2:(w + s) // 2]
        cv2.imwrite(str(out / f"{key}.png"), cv2.resize(sq, (360, 360), interpolation=cv2.INTER_AREA))
print("wrote", len(list(out.iterdir())), "thumbnails")
