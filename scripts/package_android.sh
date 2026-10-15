#!/usr/bin/env bash
# Build a debug APK (run on Linux/macOS/WSL2). First build takes a long time.
set -e
pip install buildozer cython
buildozer -v android debug        # APK ends up in ./bin/
# buildozer android deploy run    # install + launch on a USB-connected phone
