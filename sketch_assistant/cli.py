"""Test the pipeline without the UI:  python -m sketch_assistant.cli photo.jpg --out out/"""
import argparse
from pathlib import Path
import cv2
from .core.faces import load_image, detect_faces, crop_face
from .core.styles import STYLES, render


def main():
    p = argparse.ArgumentParser()
    p.add_argument("photo"); p.add_argument("--out", default="out")
    a = p.parse_args()
    img = load_image(a.photo); faces = detect_faces(img)
    print(f"{len(faces)} face(s) found")
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    for i, f in enumerate(faces):
        for key in STYLES:
            cv2.imwrite(str(out / f"face{i}_{key}.png"), render(key, crop_face(img, f)))
    boxed = img.copy()
    for f in faces:
        cv2.rectangle(boxed, (f.x, f.y), (f.x + f.w, f.y + f.h), (0, 255, 0), 3)
    cv2.imwrite(str(out / "detected.png"), boxed)


if __name__ == "__main__":
    main()
