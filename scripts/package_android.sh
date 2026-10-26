#!/usr/bin/env bash
# Local Android build (Ubuntu / macOS / WSL2). CI is easier - see PLAYSTORE.md.
set -e
pip install "buildozer==1.6.0" "cython<3"
python scripts/download_models.py

buildozer android debug        # -> bin/*.apk   (sideload and test)

# Signed bundle for the Play Console. Set these first, pointing at the key from
# scripts/make_keystore.sh, then uncomment:
# export P4A_RELEASE_KEYSTORE="$PWD/upload.keystore"
# export P4A_RELEASE_KEYSTORE_PASSWD="..."
# export P4A_RELEASE_KEYALIAS="sketchassistant"
# export P4A_RELEASE_KEYALIAS_PASSWD="..."
# buildozer android release    # -> bin/*.aab
