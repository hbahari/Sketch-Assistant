# Vendored code

| File | Source | Licence |
|---|---|---|
| `mp_palmdet.py` | [OpenCV Zoo](https://github.com/opencv/opencv_zoo) `models/palm_detection_mediapipe` | Apache 2.0 |
| `mp_handpose.py` | [OpenCV Zoo](https://github.com/opencv/opencv_zoo) `models/handpose_estimation_mediapipe` | Apache 2.0 |

`mp_handpose.py` is byte-identical to upstream. `mp_palmdet.py` differs in one respect:
upstream's `_load_anchors` returns a literal table of 2016 anchor pairs (about 2000 lines);
here the same grid is generated in a few lines. `tests/test_handpose.py` checks the
generated grid against the published values and checks that this package's landmarks match
the upstream implementation on the test photographs.

The ONNX model files themselves are **not** committed. `scripts/download_models.py`
fetches them, and the release workflow runs it before building.

The models are also Apache 2.0, from the same repository:

- `palm_detection_mediapipe_2023feb_int8.onnx` (1.1 MB)
- `handpose_estimation_mediapipe_2023feb.onnx` (4.1 MB)

## Posture

| File | Source | Licence |
|---|---|---|
| `mp_persondet.py` | [OpenCV Zoo](https://github.com/opencv/opencv_zoo) `models/person_detection_mediapipe` | Apache 2.0 |
| `mp_pose.py` | [OpenCV Zoo](https://github.com/opencv/opencv_zoo) `models/pose_estimation_mediapipe` | Apache 2.0 |

`mp_pose.py` is byte-identical to upstream. `mp_persondet.py` differs only in
`_load_anchors`, which generates the 2254-anchor grid rather than listing it as ~2250
lines; `tests/test_bodies.py` checks the generated grid against the published values.

Models, also Apache 2.0 from the same repository and fetched by
`scripts/download_models.py`:

- `person_detection_mediapipe_2023mar.onnx` (12 MB)
- `pose_estimation_mediapipe_2023mar.onnx` (5.6 MB)

## Eyes, Nose and Caricature

No code is vendored: `core/landmarks.py` runs the models through OpenCV's TFLite reader.
The models are MediaPipe's own, Apache 2.0, from
[google-ai-edge/mediapipe](https://github.com/google-ai-edge/mediapipe), fetched by
`scripts/download_models.py` and checked by SHA-256:

- `iris_landmark.tflite` (2.6 MB) -- the eye's lids and iris
- `face_landmark.tflite` (1.2 MB) -- the 468-point face mesh
- `selfie_segmentation.tflite` (0.25 MB) -- the person, hair included (Caricature)

`core/face_average.py` holds the vertex positions of MediaPipe's canonical face
(`mediapipe/modules/face_geometry/data/canonical_face_model.obj`), unchanged.

The licence text and these notices ship inside the app as `assets/LICENSES.txt`.
