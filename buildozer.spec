[app]
title = Sketch Assistant
package.name = sketchassistant
package.domain = org.sketchassistant
source.dir = .
source.include_exts = py,png,jpg,kv,xml
source.exclude_dirs = tests,scripts,bin,.buildozer,venv,.venv,.github,.idea,shots
version = 0.1
requirements = python3,kivy==2.3.0,numpy,opencv,plyer,pyjnius,android
orientation = portrait
fullscreen = 0
android.permissions = CAMERA,READ_MEDIA_IMAGES,READ_EXTERNAL_STORAGE
android.api = 33
android.minapi = 24
android.archs = arm64-v8a
android.accept_sdk_license = True
p4a.branch = v2024.01.21

[buildozer]
log_level = 2
warn_on_root = 1
