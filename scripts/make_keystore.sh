#!/usr/bin/env bash
# Create the upload key for Google Play, then print the four values to paste into GitHub secrets.
# Run once.  macOS/Linux/Git-Bash:  bash scripts/make_keystore.sh
# Windows PowerShell users: the equivalent commands are in PLAYSTORE.md, step 1.
set -euo pipefail

OUT="${1:-upload.keystore}"
ALIAS="${2:-sketchassistant}"

if [ -f "$OUT" ]; then
  echo "$OUT already exists - refusing to overwrite it. Losing this file means you can never"
  echo "update the app on Google Play again, so back it up rather than regenerating it."
  exit 1
fi

keytool -genkeypair -v \
  -keystore "$OUT" -alias "$ALIAS" \
  -keyalg RSA -keysize 2048 -validity 10000 -storetype PKCS12

echo
echo "================================================================"
echo " Created $OUT"
echo
echo " BACK THIS FILE UP somewhere safe and private (password manager,"
echo " encrypted drive). It is the only way to publish updates, and it"
echo " must NEVER be committed to the repository."
echo
echo " Now add these four repository secrets on GitHub"
echo " (Settings -> Secrets and variables -> Actions -> New secret):"
echo
echo "   KEYSTORE_BASE64    the long string printed below"
echo "   KEYSTORE_PASSWORD  the keystore password you just chose"
echo "   KEY_ALIAS          $ALIAS"
echo "   KEY_PASSWORD       the key password (same as above unless you changed it)"
echo "================================================================"
echo
echo "----- KEYSTORE_BASE64 (copy everything between the markers) -----"
base64 -w0 "$OUT" 2>/dev/null || base64 "$OUT" | tr -d '\n'
echo
echo "----- end -----"
