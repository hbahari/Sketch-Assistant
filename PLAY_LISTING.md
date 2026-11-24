# Play Console content — Sketch Assistant

Copy-paste material for the store listing and the declaration forms. Every answer below
matches what the app actually does, so it should survive review.

---

## Store listing

Rewritten 19 Nov 2026 for search: see "Keywords" below for what it targets and why.

**App name** (30 characters max — this is the field Google weighs most for search)

```
Sketch Assistant–Learn to Draw
```

Exactly 30 characters, with an en dash and no spaces around it. This only changes the
name on the Play listing; the name under the icon on the phone stays "Sketch Assistant".
If you'd rather keep the plain name, the short description still carries "drawing lesson".

**Short description** (80 characters max — the line people see in search results)

```
Turn any photo into a step-by-step drawing lesson. Faces, eyes, hands and more.
```

**Full description** (4000 characters max; this one is about 3,200)

```
Learn to draw from your own photos. Sketch Assistant turns any picture into a sketch you can actually copy, then teaches you how to draw it step by step: what to draw first, which pencil to pick up, how hard to press and where the shading goes. It's made for beginners and anyone getting back into drawing, not for people who already know how.

HOW IT WORKS
• Take a photo or choose one from your gallery
• The app finds the face, hand, person or object for you
• Pick a sketch style and see your drawing reference straight away
• Open the drawing guide for proportion lines you can measure on paper
• Tap "Generate drawing steps" and follow the lesson one stage at a time

WHAT YOU CAN LEARN TO DRAW

Portraits and faces
Five sketch styles for portrait drawing: Line Art, Technical (construction lines and proportion guides), Value Study, Cross-Hatch and Photorealism. The steps go from the first construction line to the eyes, nose, mouth and ears, then the outline and the shading.

Eyes
The part of a portrait people look at first, with a mode of its own. Load a portrait and the app finds the eye; load a close-up and drag a box round it. Then build it step by step: the eyeball and lids, the iris and pupil, where the highlight goes, the brow, the shading, and the lashes last.

Nose
How to draw a nose that looks solid rather than a hook and two dots. The app frames the nose for you, face-on or turned, then builds it from simple planes and balls before shading it.

Hands
Hands are where most people give up. The app works out the structure of the hand in your photo, from the palm block to the knuckles and every finger joint, and draws the construction lines for you.

Posture and figure drawing
Figure drawing the way a life class teaches it: the line of action, the tilt of the shoulders and hips, the mannequin, then the real outline. Tap one person, or several if they belong together.

Cartoon
Turn a portrait into a cartoon you can draw, in clean lines with expressive eyes and flowing hair, and nothing in the background. Push the slider and the cartoon becomes a caricature.

Objects and still life
Drag a box round the object you want to draw. A material guide shows how matte, glossy, glass, fabric and wood each take the light, and how to shade them.

EVERY STEP TELLS YOU
• Which pencil to use, from 2H to 6B
• The technique, and how much pressure to apply
• Exactly what to put on the paper next
• The common mistakes to avoid

DRAWING TOOLS
• A detail slider: start with a few guide lines, add more as your skills grow
• Proportion guides for the eye line, nose line, mouth line and centre line, each marked with its distance so you can measure it on your page
• Save any sketch, or the whole sequence of steps on one sheet, to print or trace
• Pencil tips and shading advice for every style

PRIVATE AND OFFLINE
Everything runs on your phone. Your photos are never uploaded, and there are no accounts, ads or trackers. The app works with no internet connection, even in airplane mode.

Whether you want to learn how to draw portraits, practise pencil drawing and shading, or finally get hands right, Sketch Assistant turns the photos you already have into drawing lessons.
```

### Keywords

What people type when they want to learn to draw, taken from competing learn-to-draw apps'
titles and descriptions and from ASO keyword data. Sources:
[AppGoblin keyword pages for learn-to-draw apps](https://appgoblin.info/apps/com.artloop.artworkout.drawing/keywords/discovery),
[a round-up of step-by-step drawing apps](https://freeappsforme.com/apps-to-draw-step-by-step/),
[AppTweak on Play keyword placement](https://www.apptweak.com/en/aso-blog/play-store-keyword-research),
and [Google's store listing best practices](https://support.google.com/googleplay/android-developer/answer/13393723).

| Keyword | Where it's used |
|---|---|
| learn to draw | title, full description (3 times) |
| how to draw | full description (3 times) |
| step by step / step-by-step | short description, full description |
| drawing lesson(s) | short description, full description |
| sketch, sketch from photo | throughout |
| portrait drawing, draw faces | full description |
| draw eyes, draw a nose, draw hands | full description |
| figure drawing | full description |
| pencil drawing, shading | full description |
| cartoon, caricature | full description |
| beginners | full description |

Google's rules, which the text follows: no keyword lists, no repeating the short
description in the full one, no irrelevant terms, no "free"/"#1"/"best" claims, no
emoji in the title, and no unattributed testimonials. Keywords appear 3-5 times at
most, in ordinary sentences.

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

| Asset | File | Size |
|---|---|---|
| App icon (Play listing) | `sketch_assistant/assets/brand/play_store_icon.png` | 512 × 512 |
| Feature graphic | `shots/feature_graphic.png` (new tagline: "Learn to draw from any photo, step by step") | 1024 × 500 |
| Phone screenshots | `shots/phone/01…08_*.png` | 1080 × 1920 |
| 7-inch tablet screenshots | `shots/tablet7/01…08_*.png` | 1080 × 1920 (9:16) |
| 10-inch tablet screenshots | `shots/tablet10/01…08_*.png` | 1440 × 2560 (9:16) |
| Walkthrough video | `shots/sketch_assistant_walkthrough.mp4` | 1920 × 1080, 1:51 |

**Which file goes where.** The feature graphic is exactly 1024 × 500, the one size Play
accepts, and goes only in Store listing → Graphics → **Feature graphic**. Put it in a
screenshot slot and Play rejects it as too small: the tablet slots need at least 1080 px on
every side. Tablet screenshots must also be exactly 9:16.

Upload **`play_store_icon.png`**, not `icon.png`. The listing icon must be a full opaque
square: Google masks the corners at a 30% radius and adds its own drop shadow, so a
pre-rounded asset gets double-rounded and transparent corners show the Play UI through.
`icon.png` is the pre-rounded in-app launcher icon and is used by `buildozer.spec` instead.

**Screenshots, in upload order** (phone): 1 photo to lesson (photo beside its realistic
study), 2 realistic portrait with proportion lines, 3 the finished portrait as the last of
twelve shading steps, 4 cross-hatching, 5 a realistic eye, 6 a realistic hand, 7 figure
drawing in cross-contour hatching, 8 cartoon. Play allows 8 per device, so they lead with
the rendered styles (realism and hatching), which are the app's strongest results. The
tablets get the same eight, with a realistic nose in place of cross-hatching. Every one is a
real screen from version 1.7.0, framed under a one-line caption. Google shows the first
three in search results, so those carry the main message.

**Video.** Play only takes a YouTube link. Upload the MP4 to YouTube as **Public** or
**Unlisted** (not Private), turn **ads off** for it, and paste the URL into Store listing →
Video. Once a video is set, Play draws a play button over the middle of the feature
graphic, so nothing important sits there.

`shots/` is git-ignored, so these files aren't committed: keep the delivered copies,
or regenerate them. **Regenerating.** All of it is built from the app itself, so it can be remade after any
change to the UI:

```
PYTHONPATH=. xvfb-run -a -s "-screen 0 1080x1920x24" python scripts/capture_listing.py /tmp/cap 1080 1920 2.625
PYTHONPATH=. xvfb-run -a -s "-screen 0 1200x1920x24" python scripts/capture_listing.py /tmp/cap7 1200 1920 2.0
PYTHONPATH=. xvfb-run -a -s "-screen 0 1600x2560x24" python scripts/capture_listing.py /tmp/cap10 1600 2560 2.0
python scripts/make_listing_assets.py /tmp/cap /tmp/cap7 /tmp/cap10 shots
python scripts/make_listing_video.py /tmp/cap shots/sketch_assistant_walkthrough.mp4
```

The photos are the test fixtures: Pexels photos, whose licence allows commercial use
without attribution (see `tests/fixtures/CREDITS.md`), and the owner's own hand photos.

---

## Pre-launch checklist

- [ ] Application ID decided — it can never change after the first upload
- [ ] Privacy policy published at a public URL and pasted into the console
- [ ] Data safety form completed
- [ ] Content rating questionnaire completed
- [ ] Phone (8) and tablet (8 + 8) screenshots uploaded from `shots/`
- [ ] Walkthrough video on YouTube (Public or Unlisted, ads off) and linked
- [ ] App icon and feature graphic uploaded
- [ ] Release tested from the signed `.apk` on a real phone
- [ ] Uploaded to **Internal testing** first, never straight to production
