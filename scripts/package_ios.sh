#!/usr/bin/env bash
# macOS + Xcode only. Builds the Xcode project via kivy-ios.
set -e
pip install kivy-ios cython
toolchain build python3 kivy numpy opencv plyer pyobjus
toolchain create SketchAssistant "$(pwd)"
echo "Open SketchAssistant-ios/sketchassistant.xcodeproj in Xcode, set your team, add"
echo "NSCameraUsageDescription + NSPhotoLibraryUsageDescription to Info.plist, then Run."
