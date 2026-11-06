"""Fetch the ONNX models into sketch_assistant/assets/models/.

    python scripts/download_models.py

About 23 MB in total. They are not committed to the repository; the release workflow runs
this before building, and the app degrades gracefully if any of them is missing.

All three come from OpenCV Zoo and are Apache 2.0 licensed. Note the host: the models are
stored with Git LFS, so `github.com/.../raw/...` returns a small text pointer rather than
the model. `media.githubusercontent.com/media/...` serves the real file.
"""
import sys
import urllib.request
from pathlib import Path

ZOO = "https://media.githubusercontent.com/media/opencv/opencv_zoo/main/models"
OUT = Path(__file__).resolve().parent.parent / "sketch_assistant" / "assets" / "models"

MODELS = [
    # (url, filename, minimum plausible size, what it is for)
    (f"{ZOO}/face_detection_yunet/face_detection_yunet_2023mar.onnx",
     "face_detection_yunet_2023mar.onnx", 100_000, "faces, with 5 landmarks"),
    (f"{ZOO}/palm_detection_mediapipe/palm_detection_mediapipe_2023feb_int8.onnx",
     "palm_detection_mediapipe_2023feb_int8.onnx", 900_000, "finds hands"),
    # the landmark model is kept at full precision: its int8 build is three times faster
    # but puts landmarks ~30px out on a 1000px hand, which is visible in a drawing guide.
    # The detector only has to find a rough box, so int8 is fine there.
    (f"{ZOO}/handpose_estimation_mediapipe/handpose_estimation_mediapipe_2023feb.onnx",
     "handpose_estimation_mediapipe_2023feb.onnx", 3_000_000, "21 hand landmarks"),
    # Posture needs a detector of its own: several people can be in one photo and the
    # user chooses between them, which the pose model alone cannot do.
    (f"{ZOO}/person_detection_mediapipe/person_detection_mediapipe_2023mar.onnx",
     "person_detection_mediapipe_2023mar.onnx", 8_000_000, "finds people"),
    (f"{ZOO}/pose_estimation_mediapipe/pose_estimation_mediapipe_2023mar.onnx",
     "pose_estimation_mediapipe_2023mar.onnx", 4_000_000, "33 body landmarks + body mask"),
]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    failed = []
    for url, name, min_size, what in MODELS:
        dest = OUT / name
        if dest.exists() and dest.stat().st_size >= min_size:
            print(f"  have  {name}  ({what})")
            continue
        try:
            data = urllib.request.urlopen(url, timeout=120).read()
        except Exception as e:                       # noqa: BLE001 - report and carry on
            failed.append((name, str(e)))
            continue
        if len(data) < min_size or data.startswith(b"version https://git-lfs"):
            failed.append((name, f"got {len(data)} bytes, expected at least {min_size}"))
            continue
        dest.write_bytes(data)
        print(f"  saved {name}  {len(data):,} bytes  ({what})")
    if failed:
        print("\nCould not download:", file=sys.stderr)
        for name, why in failed:
            print(f"  {name}: {why}", file=sys.stderr)
        print("\nThe app still runs without these -- face detection falls back to the Haar\n"
              "cascade and Hands mode falls back to reading the silhouette -- but both are\n"
              "noticeably worse. Re-run this script, or download the files by hand into\n"
              f"{OUT}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
