"""Download the YuNet face model (230 KB) into sketch_assistant/assets/models/.  Run once:  python scripts/download_models.py"""
import sys
import urllib.request
from pathlib import Path

URL = "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx"
OUT = Path(__file__).resolve().parent.parent / "sketch_assistant" / "assets" / "models" / "face_detection_yunet_2023mar.onnx"
OUT.parent.mkdir(parents=True, exist_ok=True)
data = urllib.request.urlopen(URL, timeout=60).read()
if len(data) < 100_000 or data.startswith(b"version https://git-lfs"):
    sys.exit(f"Download failed (got {len(data)} bytes). Download the file manually from {URL}")
OUT.write_bytes(data)
print("saved", OUT, len(data), "bytes")
