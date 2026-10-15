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

## Build the Android APK (no Linux needed) - GitHub Actions
1. Create a free GitHub repo and upload this folder (the `.gitignore` keeps `venv/` out).
2. Open the repo's **Actions** tab -> **Build Android APK** -> **Run workflow**.
3. Wait ~30-60 min (first build compiles OpenCV). Download the `sketch-assistant-apk` artifact (zip containing the .apk).
4. Copy the .apk to your phone, open it, and allow "install unknown apps" when asked.
Local alternative: Ubuntu / WSL2 -> `scripts/package_android.sh`.
