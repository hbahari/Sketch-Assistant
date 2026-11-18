"""Fetch the models into sketch_assistant/assets/models/.

    python scripts/download_models.py

About 27 MB in total. They are not committed to the repository; the release workflow runs
this before building, and the app degrades gracefully if any of them is missing.

All three come from OpenCV Zoo and are Apache 2.0 licensed. Note the host: the models are
stored with Git LFS, so `github.com/.../raw/...` returns a small text pointer rather than
the model. `media.githubusercontent.com/media/...` serves the real file.

The TFLite models (Eyes, Nose and Caricature) are MediaPipe's own iris model, face mesh
and person segmentation,
also Apache 2.0, from Google's MediaPipe asset store. They are checked against a SHA-256
as well as a size, because the same names have been reused for other versions over the
years. If the store is unreachable they are taken out of the `mediapipe==0.10.14` wheel,
which bundles exactly these files (later wheels don't).
"""
import hashlib
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
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

MP = "https://storage.googleapis.com/mediapipe-assets"
TFLITE = [
    # (url, filename, sha256, what it is for)
    (f"{MP}/iris_landmark.tflite", "iris_landmark.tflite",
     "d1744d2a09c25f501d39eba4faff47e53ecca8852c5ce19bce8eeac39357521f", "eye lids and iris (Eyes)"),
    (f"{MP}/face_landmark.tflite", "face_landmark.tflite",
     "1055cb9d4a9ca8b8c688902a3a5194311138ba256bcc94e336d8373a5f30c814", "468-point face mesh (Eyes, Nose, Caricature)"),
    (f"{MP}/selfie_segmentation.tflite", "selfie_segmentation.tflite",
     "9ee168ec7c8f2a16c56fe8e1cfbc514974cbbb7e434051b455635f1bd1462f5c", "person and hair outline (Caricature)"),
]
WHEEL = "mediapipe==0.10.14"


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _from_wheel(wanted):
    """{filename: bytes} for the wanted TFLite files, out of the MediaPipe wheel."""
    got = {}
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run([sys.executable, "-m", "pip", "download", WHEEL, "--no-deps", "-d", tmp,
                        "--only-binary=:all:", "--python-version", "3.11", "--platform",
                        "manylinux_2_17_x86_64"], check=True, capture_output=True)
        for whl in Path(tmp).glob("*.whl"):
            with zipfile.ZipFile(whl) as z:
                for n in z.namelist():
                    if Path(n).name in wanted:
                        got[Path(n).name] = z.read(n)
    return got


def _tflite(failed):
    need = []
    for url, name, sha, what in TFLITE:
        dest = OUT / name
        if dest.exists() and _sha(dest.read_bytes()) == sha:
            print(f"  have  {name}  ({what})")
            continue
        try:
            data = urllib.request.urlopen(url, timeout=120).read()
        except Exception:                            # noqa: BLE001 - try the wheel below
            data = b""
        if _sha(data) == sha:
            dest.write_bytes(data)
            print(f"  saved {name}  {len(data):,} bytes  ({what})")
        else:
            need.append((name, sha, what))
    if not need:
        return
    why = f"not on {MP} or in the {WHEEL} wheel"
    try:
        got = _from_wheel({name for name, _, _ in need})
    except Exception as e:                           # noqa: BLE001 - report and carry on
        got = {}
        why = f"not on {MP} and the {WHEEL} wheel could not be fetched ({e})"
    for name, sha, what in need:
        data = got.get(name, b"")
        if _sha(data) == sha:
            (OUT / name).write_bytes(data)
            print(f"  saved {name}  {len(data):,} bytes, from the {WHEEL} wheel  ({what})")
        else:
            failed.append((name, why if name not in got else "checksum did not match"))


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
    _tflite(failed)
    if failed:
        print("\nCould not download:", file=sys.stderr)
        for name, why in failed:
            print(f"  {name}: {why}", file=sys.stderr)
        print("\nThe app still runs without these -- face detection falls back to the Haar\n"
              "cascade, Hands mode falls back to reading the silhouette, Eyes and Nose fall\n"
              "back to image rules -- but all are noticeably worse. Re-run this script, or\n"
              "download the files by hand into\n"
              f"{OUT}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
