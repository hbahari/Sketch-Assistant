# Play Console content — Sketch Assistant

Copy-paste material for the store listing and the declaration forms. Every answer below
matches what the app actually does, so it should survive review.

---

## Store listing

**App name** (30 characters max)

```
Sketch Assistant
```

**Short description** (80 characters max — this is the line people see in search results)

```
Turn any photo into a pencil sketch and a step-by-step drawing guide.
```

**Full description** (4000 characters max)

```
Sketch Assistant turns a photo into something you can actually draw from.

Pick a photo, choose a sketch style, and the app gives you a clean reference plus a
step-by-step guide: which pencil grades to use, how much pressure to apply, what to draw
first, and where the shading goes. Built for people learning to draw, not for people who
already know how.

PORTRAIT MODE
Point it at a photo of a person and the app finds the faces for you. Tap the one you want
and pick a style:

• Line Art — clean outlines only, nothing else to distract you
• Technical — light construction lines, proportion guides and gentle hatching
• Value Study — the face reduced to flat tones, so you can see the big shapes
• Cross-Hatch — shading built from layered pen strokes
• Photorealism — smooth graphite shading with real pencil texture

OBJECT MODE
The same idea for still life. Contour, Basic Shapes, Value Study, Cross-Hatch and
Photorealism, applied to the whole photo.

THE DRAWING GUIDE
Tap through to the guide and you get the sketch enlarged, with optional proportion lines
over it — eye line, nose line, mouth line, centre axis and a rule-of-thirds grid — plus:

• which pencils to reach for, from 2H through 6B
• how hard to press, and when to build up layers instead
• numbered steps, in order, from first construction line to final detail
• common mistakes for each style
• a material guide for objects: matte, glossy, glass, fabric and wood each shade
  differently, and the app shows how

A detail slider lets you dial any style up or down, from a few guide lines for your first
attempt to full detail once you are confident.

Save any sketch to your gallery to print it, trace it, or work from it on screen.

PRIVATE AND OFFLINE
Everything runs on your phone. Your photos are never uploaded. There are no accounts, no
ads, no trackers and no internet connection required — it works the same in aeroplane mode.
```

---

## Data safety form

Google asks this in Policy → App content → Data safety. The honest answers are also the
simplest ones.

| Question | Answer |
|---|---|
| Does your app collect or share any of the required user data types? | **No** |
| Is all of the user data encrypted in transit? | n/a — no data is transmitted |
| Do you provide a way for users to request that their data is deleted? | n/a — no data is collected |

Why this is accurate: photos are chosen through Android's system picker, processed on the
device and never transmitted. The app makes no network requests, has no analytics or ad
SDKs, and stores nothing beyond a working copy of the current photo in its own private
cache, plus any sketch the user deliberately saves to their own gallery.

**Photos are not "collected"** under Google's definition, because they are never transmitted
off the device. Collection means sending data off the device; on-device-only processing is
explicitly excluded.

---

## Other App content declarations

| Section | Answer |
|---|---|
| Privacy policy | URL of `PRIVACY_POLICY.md` in your GitHub repo |
| Ads | **No**, the app contains no ads |
| App access | All functionality is available without an account — no login details needed |
| Content rating | Complete the questionnaire. Everything is "no": no violence, no sexual content, no profanity, no gambling, no user-to-user communication. Expect **Everyone / PEGI 3**. |
| Target audience | Choose 13+ or 18+ unless you want the stricter Families policy rules. The app is not designed for children. |
| News app | **No** |
| Government app | **No** |
| Financial features | **None** |
| Health | **None** |
| Data deletion | n/a — no account and no collected data |

---

## Graphics

Already generated in `sketch_assistant/assets/brand/`:

| Asset | File | Size |
|---|---|---|
| App icon (Play listing) | `play_store_icon.png` | 512 × 512 |
| Feature graphic | `feature_graphic.png` | 1024 × 500 |

Upload **`play_store_icon.png`**, not `icon.png`. The listing icon must be a full opaque
square: Google masks the corners at a 30% radius and adds its own drop shadow, so a
pre-rounded asset gets double-rounded and transparent corners show the Play UI through.
`icon.png` is the pre-rounded in-app launcher icon and is used by `buildozer.spec` instead.

**Phone screenshots — you still need these.** Google requires at least 2 (up to 8), between
320 px and 3840 px on the shorter side. Take them on the phone once the APK installs:

1. Main page with a photo loaded and a sketch showing beside it
2. The drawing guide page with the proportion lines on
3. The style tiles, to show the range
4. Object mode with the material guide open

---

## Pre-launch checklist

- [ ] Application ID decided — it can never change after the first upload
- [ ] Privacy policy published at a public URL and pasted into the console
- [ ] Data safety form completed
- [ ] Content rating questionnaire completed
- [ ] At least 2 phone screenshots uploaded
- [ ] App icon and feature graphic uploaded
- [ ] Release tested from the signed `.apk` on a real phone
- [ ] Uploaded to **Internal testing** first, never straight to production
