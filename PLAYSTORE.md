# Publishing Sketch Assistant to Google Play

The whole build runs on GitHub Actions, so you need nothing installed locally beyond `keytool`
(which ships with any JDK, and with Android Studio). Two workflows exist:

| Workflow | Produces | Use it for |
|---|---|---|
| **Android debug APK** | unsigned `.apk` | sideloading onto your own phone to test |
| **Android release (AAB + APK)** | signed `.aab` + signed universal `.apk` | the `.aab` goes to the Play Console |

Google Play only accepts `.aab` for new apps. The `.apk` the release workflow also produces is
the same build packaged for sideloading, which is handy for testing the exact release bits.

---

## Step 1 — Get an upload key

Android identifies an app by its package name, not by its key, so **one key can sign any number of
apps**. If you already publish something on Play, reuse that key and skip ahead.

Under Play App Signing (mandatory for anything published since 2021) the key you build with is an
*upload* key: Google holds the real app signing key and re-signs every upload. That means an upload
key can be **reset** by Google if it is ever lost or leaked, so this choice is not permanent.

### Option A — reuse the key from another app (simplest)

Find that project's `.jks` / `.keystore` file and turn it into the string GitHub needs:

```powershell
[Convert]::ToBase64String([IO.File]::ReadAllBytes("your-upload.jks")) | Set-Clipboard
```

You also need its **alias**. If you do not remember it, list the aliases (it will ask for the
keystore password):

```powershell
keytool -list -keystore "your-upload.jks"
```

The alias is the first value on each entry line — commonly `upload`.

The only real downside of sharing a key is that a leak affects both apps. Use a separate key when
the apps have different owners, or when you might sell or transfer one of them.

### Option B — create a new key

**macOS / Linux / Git Bash:**

```bash
bash scripts/make_keystore.sh
```

**Windows PowerShell:**

```powershell
keytool -genkeypair -v -keystore upload.keystore -alias sketchassistant `
  -keyalg RSA -keysize 2048 -validity 10000 -storetype PKCS12

# then print the base64 you will paste into GitHub:
[Convert]::ToBase64String([IO.File]::ReadAllBytes("upload.keystore")) | Set-Clipboard
```

It asks for a password and some identity details (name, organisation, country). The details are
not shown publicly; the password is the one you must not lose.

Either way: `.gitignore` already excludes `*.keystore` and `*.jks`, so the key will not be
committed. Keep a backup in a password manager or an encrypted drive, and never send the key file
and its password through the same channel.

## Step 2 — Add four repository secrets

On GitHub: **Settings → Secrets and variables → Actions → New repository secret**.

| Secret | Value |
|---|---|
| `KEYSTORE_BASE64` | the long base64 string from step 1 |
| `KEYSTORE_PASSWORD` | the keystore password |
| `KEY_ALIAS` | the alias inside the keystore — `upload` for a reused key, `sketchassistant` for one made with `make_keystore.sh` |
| `KEY_PASSWORD` | the key password (usually the same as the keystore password) |

A wrong alias is the most common cause of a failed release build, and it only shows up after the
full compile, so check it against `keytool -list` before you start the run.

## Step 3 — Build the bundle

**Actions → Android release (AAB + APK) → Run workflow.** Expect 40–90 minutes the first time,
because OpenCV is compiled from source; later runs reuse the cache and are much quicker.

When it finishes, download the `sketch-assistant-release` artifact. It contains:

- `sketchassistant-0.1.0-arm64-v8a_armeabi-v7a-release.aab` → upload this
- `sketch-assistant-universal.apk` → install this on a phone to check the release build

The workflow fails loudly if the bundle comes out unsigned, so a green run means it is ready.

## Step 4 — Set the app up in the Play Console

1. **Create a developer account** at <https://play.google.com/console> — a one-off $25 fee.
2. **Create the app**, then check the application ID before your first upload.
   It comes from `buildozer.spec` and is currently **`org.sketchassistant.sketchassistant`**.
   This can never be changed after the first upload, so if you own a domain, set
   `package.domain` to it now (reversed, e.g. `com.yourname`).
3. **Upload to Internal testing first**, not production. It is instant, has no review wait,
   and lets you install from the Play Store on your own device.
4. Work through everything under **Policy → App content**:
   - **Privacy policy** — a URL is mandatory. A GitHub Pages page or a public Gist is fine.
     The honest version is short: the app processes photos entirely on the device and sends
     nothing anywhere.
   - **Data safety** — answer **no data collected and no data shared**. That is accurate: there
     are no network calls, no analytics and no accounts, and photos never leave the phone.
   - **Content rating** questionnaire, **Target audience** (not aimed at children keeps things
     simpler), **Ads**: none, **Government apps**: no.
5. **Store listing** — assets are already generated in `sketch_assistant/assets/brand/`:
   - app icon 512×512 → `icon.png`
   - feature graphic 1024×500 → `feature_graphic.png`
   - **phone screenshots: at least 2**, which you take yourself. Run the app, screenshot the
     main page and the drawing-guide page.

   Short description (80 characters max), for example:
   *Turn any photo into a pencil sketch and a step-by-step drawing guide.*

## Step 5 — Getting to production

If your developer account is a **personal** account created after 13 November 2023, Google
requires a closed test with **at least 12 testers opted in for 14 consecutive days** before you
can apply for production access. Testers who drop out and rejoin reset the clock. Organisation
accounts are exempt. Plan for this — it is the slowest part of a first release, not the build.

## Step 6 — Shipping updates

Every upload needs a higher version code. In `buildozer.spec`:

```ini
version = 0.1.1              # the version name users see
android.numeric_version = 2  # must increase on EVERY upload
```

Then run the release workflow again. Tagging a commit `v0.1.1` also triggers it.

---

## If the build fails

- **OpenCV recipe errors** — the heaviest and most fragile part of the build. Send me the last
  ~50 lines of the failed step and I will work through it.
- **C errors compiling Kivy** mentioning `python3.14`, `_PyLong_AsByteArray`,
  `_PyUnicode_FastCopyCharacters` or "expected 6, have 5" — a toolchain mismatch, not an app bug.
  python-for-android builds against Python 3.14, and two things must line up with it:
  `buildozer.spec` must **not** pin `kivy==2.3.0` (the recipe's own 2.3.1 carries the 3.14
  patches), and the workflow must **not** install `cython<3` (each recipe installs the Cython
  version it needs; forcing 0.29 emits private C API calls Python 3.14 removed). Both are already
  correct in this repo — this note is here in case someone reintroduces either pin.
- **A build that used to work suddenly fails** — check `p4a.branch` is still pinned in
  `buildozer.spec`. Without it buildozer tracks python-for-android's `master`, which moves.
- **`ImportError: cannot import name 'BuildDependencyInstallError'`** — an upstream
  python-for-android bug that only fires when `android.archs` lists more than one architecture.
  p4a creates its build venv in the shared build directory but runs that step once per arch, so
  the second pass re-seeds the hostpython pip (25.3) over the 26.2.2 the first pass installed,
  mixing two pip versions in one `site-packages`. Keep `android.archs = arm64-v8a`.
  Two related guards are also in place: only `~/.buildozer` (the SDK/NDK) is cached, never the
  in-repo build tree, and the workflows `rm -rf .buildozer` before building.
- **`ubuntu-22.04` runner unavailable** — GitHub retires runner images over time. Change
  `runs-on:` to `ubuntu-latest` in both workflow files.
- **"The .aab came out unsigned"** — one of the four secrets is missing or misspelt. The names
  are case-sensitive.
- **Play rejects the target API level** — Google requires new apps to target API 36
  (`android.api = 36`, already set). If the requirement moves again, raise that number.

## Known risks on a real device

These are the parts I could not test without an Android phone:

- **The OpenCV build.** It is the one step most likely to fail outright.
- **Taking a photo.** The camera goes through a MediaStore entry and the system camera app.
  If it fails, the code falls back to the gallery picker.
- **Speed.** Sketch rendering was only ever timed on a desktop CPU. Technical, Cross-Hatch and
  Basic Shapes are the heaviest styles and may be slow on older phones.
