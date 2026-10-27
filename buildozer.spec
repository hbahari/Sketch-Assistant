[app]
title = Sketch Assistant
package.name = sketchassistant
# Change this to a domain you control before publishing; it becomes the Play Store app ID
# (org.sketchassistant.sketchassistant) and can never be changed after the first upload.
package.domain = org.sketchassistant

source.dir = .
source.include_exts = py,png,jpg,kv,xml,onnx
source.exclude_dirs = tests,scripts,bin,.buildozer,venv,.venv,.github,.idea,shots

# versionName shown in the Play listing
version = 0.1.0
# versionCode: MUST increase on every upload to the Play Console
android.numeric_version = 1

# Versions come from the pinned python-for-android below, which ships a tested set:
# Python 3.14.2, Kivy 2.3.1, numpy 2.3.0, OpenCV 4.12.0, pyjnius 1.7.0.
# Do NOT pin kivy here: an older Kivy will not compile against Python 3.14.
requirements = python3,kivy,numpy,opencv,plyer,pyjnius,android

# Pin the toolchain. Buildozer otherwise tracks p4a's master branch, which moves and
# will eventually break the build without anything in this repo changing.
p4a.branch = v2026.05.09

orientation = portrait
fullscreen = 0

icon.filename = %(source.dir)s/sketch_assistant/assets/brand/icon.png
icon.adaptive_icon_foreground = %(source.dir)s/sketch_assistant/assets/brand/icon_fg.png
icon.adaptive_icon_background = %(source.dir)s/sketch_assistant/assets/brand/icon_bg.png
presplash.filename = %(source.dir)s/sketch_assistant/assets/brand/presplash.png
android.presplash_color = #FFFFFF

# No permissions: the gallery and camera both run through system intents (see platform_utils.py),
# and Save PNG writes through MediaStore. Declaring CAMERA would actually make the capture
# intent require a runtime grant, so it is deliberately left out.

# Google Play requires new apps and updates to target API 36 (since 31 Aug 2026).
android.api = 36
android.minapi = 24
android.accept_sdk_license = True

# ONE architecture only, deliberately. python-for-android's run_pymodules_install()
# loops over ctx.archs but creates its venv in the shared ctx.build_dir, so a second
# architecture re-runs `python -m venv` over the first one's venv. That re-seeds the
# hostpython-bundled pip (25.3) on top of the 26.2.2 the first pass upgraded to, leaving
# pip 26.2's build_env/ package beside pip 25.3's exceptions.py, and the build dies with
# "ImportError: cannot import name 'BuildDependencyInstallError'".
#
# arm64-v8a covers essentially every Android phone sold since 2017. Adding armeabi-v7a
# back means hitting that upstream bug, so leave it off unless you need 32-bit devices
# and have verified p4a has fixed it.
android.archs = arm64-v8a

# `buildozer android release` -> bin/*.aab (what the Play Console wants)
# `buildozer android debug`   -> bin/*.apk (what you sideload to test)
android.release_artifact = aab
android.debug_artifact = apk

[buildozer]
log_level = 2
warn_on_root = 1
