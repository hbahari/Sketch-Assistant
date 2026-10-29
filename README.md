# Sketch Assistant (MVP - Portrait mode)

Offline photo -> pencil-sketch helper for drawing learners. Python + Kivy + OpenCV; no cloud calls.

## Run
    pip install -r requirements.txt
    python main.py                                  # desktop app
    python -m sketch_assistant.cli photo.jpg        # no UI: writes all styles to ./out
    pytest

## Layout
    main.py                      entry point
    sketch_assistant/app.py      App + screen manager
    sketch_assistant/ui/         home.py (main page), guide.py (tips page), widgets.py
    sketch_assistant/core/       faces.py (detect/crop), styles.py (5 sketch styles: line art, technical, value study, cross-hatch, photorealism)
    sketch_assistant/data/       tips.py (pencil tips + steps per style)
    sketch_assistant/platform_utils.py   camera / gallery / save (plyer)
    scripts/                     package_android.sh, package_ios.sh
    buildozer.spec               Android config

## Packaging
- Android: `scripts/package_android.sh` (Buildozer; Linux/macOS/WSL2).
- iOS: `scripts/package_ios.sh` (kivy-ios; needs a Mac with Xcode).
- Riskiest part is the OpenCV recipe on mobile. If it fails, the fallback is replacing OpenCV
  with numpy/Pillow in core/ (all code is isolated there).

## Next steps (ideas)
Object mode, PDF export, better face/landmark detection (YuNet ONNX), per-style tuning sliders.

## Build for Android / Google Play
Everything builds on GitHub Actions - nothing to install locally.
- **Android release (AAB + APK)** workflow -> signed `.aab` for the Play Console + a signed universal `.apk`.
- **Android debug APK** workflow -> unsigned `.apk` for sideloading and testing.

Full walkthrough, including the signing key, the four GitHub secrets and the Play Console
checklist: **[PLAYSTORE.md](PLAYSTORE.md)**.

Store listing copy, data-safety answers and the declaration forms: **[PLAY_LISTING.md](PLAY_LISTING.md)**.
Privacy policy to publish: **[PRIVACY_POLICY.md](PRIVACY_POLICY.md)**.

Local alternative (Ubuntu / WSL2): `scripts/package_android.sh`.

## Drawing steps
"Generate drawing steps" on the guide page builds the sketch stage by stage - construction
lines, then one facial feature at a time, then the outline, values and finish. Each stage
carries its own pencil grade, technique and instruction.

- `core/steps.py` composes the stages from the existing renderers; no new image processing.
  Portrait stages reveal features through soft masks on the YuNet landmarks; object stages are
  masked to the GrabCut silhouette so the background stays out of the early passes.
- A stage that would add almost no new ink (ears hidden by hair) is dropped automatically.
- `data/steps_text.py` holds the per-stage text, keyed by stage id so words and pictures match.
- Generation runs off the UI thread behind a progress popup. "Save sheet" writes all stages
  as one printable image.

## Modes, detail slider, face model
- **Portrait**: 5 styles on a selected face. **Object**: 5 styles on the whole photo (Contour, Basic Shapes, Value, Cross-Hatch, Realistic).
- **Detail slider** (main page + guide page): per-style, applied when you lift your finger; each style keeps its own value.
- **Face detection**: YuNet (ONNX, with eye/nose/mouth landmarks that tilt the guide lines) when the model file is present and OpenCV supports it, otherwise the Haar cascade.
  Get the model once with `python scripts/download_models.py` (the GitHub workflow does this automatically).

## Saving, Basic Shapes, material guide
- **Save PNG** writes to `Pictures/SketchAssistant` (Windows/macOS/Linux and Android) and shows where, with an "Open folder" button on desktop.
- **Basic Shapes** (object mode) cuts out the main object with GrabCut, then draws its angular silhouette, shadow shapes, bounding box and W:H proportion.
- **Material guide** (object guide page): Matte, Glossy, Glass, Fabric, Wood - labelled example images (`scripts/make_material_examples.py`) plus steps, pencils and common mistakes (`data/materials.py`).

## Look & feel
- Theme in `ui/theme.py`: black ink, white paper, amber accent (matches the icon). Change colours there.
- Branding is built from one source drawing: `assets/brand/source/portrait.png`.
  Replace that file and run `python scripts/make_brand.py` to regenerate `icon.png`, `mark.png`, `logo.png`
  and `presplash.png`. The script tints the pencil amber by picking the enclosed shapes along
  `PENCIL_AXIS` - adjust that line (and `MARGIN`) at the top of the script if you swap in different art.
- `buildozer.spec` points at `icon.png` and `presplash.png`.
- Pages slide in/out (SlideTransition). On the guide page: back arrow, swipe from the left edge, or the
  Android back button return to the main page.
