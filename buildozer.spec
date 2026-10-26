[app]
title = Sketch Assistant
package.name = golemapps.sketchassistant.app
# Change this to a domain you control before publishing; it becomes the Play Store app ID
# (org.sketchassistant.sketchassistant) and can never be changed after the first upload.
package.domain = golemapps.sketchassistant

source.dir = .
source.include_exts = py,png,jpg,kv,xml,onnx
source.exclude_dirs = tests,scripts,bin,.buildozer,venv,.venv,.github,.idea,shots

# versionName shown in the Play listing
version = 0.1.0
# versionCode: MUST increase on every upload to the Play Console
android.numeric_version = 1

requirements = python3,kivy==2.3.0,numpy,opencv,plyer,pyjnius,android

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

# 64-bit is mandatory on Play; 32-bit is included so older phones are still covered.
# An .aab ships only the slice each device needs, so this does not bloat the download.
android.archs = arm64-v8a, armeabi-v7a

# `buildozer android release` -> bin/*.aab (what the Play Console wants)
# `buildozer android debug`   -> bin/*.apk (what you sideload to test)
android.release_artifact = aab
android.debug_artifact = apk

[buildozer]
log_level = 2
warn_on_root = 1
