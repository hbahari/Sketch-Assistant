# Sketch Assistant

Offline photo -> pencil-sketch helper for drawing learners. Python + Kivy + OpenCV; no cloud calls.

Everything reported against the app since v1.0.0, in the tester's own words, is in
[`TESTER_COMMENTS.md`](TESTER_COMMENTS.md).

## Run
    pip install -r requirements.txt
    python scripts/download_models.py        # ONNX models for faces and hands (~5.5 MB)
    python main.py                                  # desktop app
    python -m sketch_assistant.cli photo.jpg        # no UI: writes all styles to ./out
    pytest

## Layout
    main.py                      entry point
    sketch_assistant/app.py      App + screen manager
    sketch_assistant/ui/         home.py (main page), guide.py (tips page), widgets.py
    sketch_assistant/core/       modes.py (the subject registry), faces.py (detect/crop),
                                 hands.py (hand structure from a silhouette), styles.py
                                 (renderers), guides.py (construction lines), steps.py (stage ladders)
    sketch_assistant/data/       tips.py (pencil tips per style), steps_text.py (per-stage text)
    sketch_assistant/platform_utils.py   camera / gallery / save (plyer)
    scripts/                     package_android.sh, package_ios.sh
    buildozer.spec               Android config

## Packaging
- Android: `scripts/package_android.sh` (Buildozer; Linux/macOS/WSL2).
- iOS: `scripts/package_ios.sh` (kivy-ios; needs a Mac with Xcode).
- Riskiest part is the OpenCV recipe on mobile. If it fails, the fallback is replacing OpenCV
  with numpy/Pillow in core/ (all code is isolated there).

## Next steps (ideas)
PDF export, legs and full-body posture modes (see "Adding a subject" below).

## Build for Android / Google Play
Everything builds on GitHub Actions - nothing to install locally.
- **Android release (AAB + APK)** workflow -> signed `.aab` for the Play Console + a signed universal `.apk`.
- **Android debug APK** workflow -> unsigned `.apk` for sideloading and testing.

Full walkthrough, including the signing key, the four GitHub secrets and the Play Console
checklist: **[PLAYSTORE.md](PLAYSTORE.md)**.

Store listing copy, data-safety answers and the declaration forms: **[PLAY_LISTING.md](PLAY_LISTING.md)**.
Privacy policy to publish: **[PRIVACY_POLICY.md](PRIVACY_POLICY.md)**.

Local alternative (Ubuntu / WSL2): `scripts/package_android.sh`.

## Drawing steps
"Generate drawing steps" on the guide page builds the sketch stage by stage - construction
lines, then one facial feature at a time, then the outline, values and finish. Each stage
carries its own pencil grade, technique and instruction.

- `core/steps.py` composes the stages from the existing renderers; no new image processing.
  Portrait stages reveal features through soft masks on the YuNet landmarks; object stages are
  masked to the GrabCut silhouette so the background stays out of the early passes.
- A stage that would add almost no new ink (ears hidden by hair) is dropped automatically.
- `data/steps_text.py` holds the per-stage text, keyed by stage id so words and pictures match.
- Generation runs off the UI thread behind a progress popup. "Save sheet" writes all stages
  as one printable image.

## Modes, detail slider, face model
- **Eyes**: 5 styles on one eye, framed with the box picker. Construction and a twelve-stage ladder are its own.
- **Portrait**: 5 styles on a selected face. **Object**: 5 styles on the whole photo (Contour, Basic Shapes, Value, Cross-Hatch, Realistic). **Hands**: 5 styles on the whole photo, with guides and steps built from the hand's own structure.
- **Detail slider** (main page + guide page): per-style, applied when you lift your finger; each style keeps its own value.
- **Face detection**: YuNet (ONNX, with eye/nose/mouth landmarks that tilt the guide lines) when the model file is present and OpenCV supports it, otherwise the Haar cascade.
  Get the model once with `python scripts/download_models.py` (the GitHub workflow does this automatically).

## Guide fractions
Every guide that runs straight across or straight down the sketch is labelled with where it
sits, from 0 (top or left edge) to 1 (bottom or right): `eyes 0.43`, `centre 0.50`,
`shoulders 0.39`, `plumb 0.50`. The thirds grid is numbered in every mode. Tilted lines --
the eye line on a turned head, a shoulder bar -- are measured at their midpoint. Guides that
are not lines (the palm circle, finger joints) carry no number. See `guides.at`.

## Saving, Basic Shapes, material guide
- **Save PNG** writes to `Pictures/SketchAssistant` (Windows/macOS/Linux and Android) and shows where, with an "Open folder" button on desktop.
- **Basic Shapes** (object mode) cuts out the main object with GrabCut, then draws its angular silhouette, shadow shapes, bounding box and W:H proportion.
- **Material guide** (object guide page): Matte, Glossy, Glass, Fabric, Wood - labelled example images (`scripts/make_material_examples.py`) plus steps, pencils and common mistakes (`data/materials.py`).

## Look & feel
- Theme in `ui/theme.py`: black ink, white paper, amber accent (matches the icon). Change colours there.
- Branding is built from one source drawing: `assets/brand/source/portrait.png`.
  Replace that file and run `python scripts/make_brand.py` to regenerate `icon.png`, `mark.png`, `logo.png`
  and `presplash.png`. The script tints the pencil amber by picking the enclosed shapes along
  `PENCIL_AXIS` - adjust that line (and `MARGIN`) at the top of the script if you swap in different art.
- `buildozer.spec` points at `icon.png` and `presplash.png`.
- Pages slide in/out (SlideTransition). On the guide page: back arrow, swipe from the left edge, or the
  Android back button return to the main page.


## Where each mode stands

Measured against the photographs in `tests/fixtures/` (see `CREDITS.md` for sources).

| Mode | State |
|---|---|
| **Hands** | Strongest. Landmark models read 19 of 20 test photos, including a fist head-on, fingers round a mug and extreme foreshortening. The one miss falls back rather than guessing. |
| **Portrait** | Solid. A face was found in all 27 test portraits, 26 with landmarks, and every one produces the full nine-stage sequence. The guide oval encloses the features on 24 of 26. |
| **Object** | The user draws a box round the object they want; see below for why. |
| **Eyes** | Newest and roughest. No model: the iris is found by a circle search and the lids by fitting a template. On 18 close-up test photos the iris is right on 12, in the right place but the wrong size on 3, and wrong on 3. See below. |
| **Posture** | Figures found by MediaPipe Pose. Tap one, or several -- two people interacting are one composition, so choosing both gives a region spanning them and the gap. |

### How object mode picks the object

Segmentation cannot be told which object was meant. GrabCut is seeded from a rectangle;
left to guess it seeds the middle of the frame, which is right for one centred object and
wrong for a still life of several -- it returns some union of objects and background. On
twenty-five still lifes the result was unusable on roughly half.

So the user draws the rectangle. `ui.widgets.BoxSelector` shows the photo with a draggable
selection; `faces.crop_to_box` crops to it with a 12% margin, and everything downstream
runs on that crop. Nothing in the rendering pipeline had to change: segmentation seeds
itself from the middle of whatever image it is handed, so once the image *is* the
selection, the seed is the selection. It is the same shape of solution as Portrait mode
cropping to a tapped face.

The default selection covers 85% of the photo, so a photo that already worked still works
untouched and dragging is purely an improvement rather than a new thing to get right.

### Eyes, specifically

The mode with the longest ladder: four construction passes (width, height and tilt; the
ball and the lids; iris, pupil and lid thickness; planning the light), two outline passes,
then for the blended styles five tonal ones -- flat values, blended tone, the iris, the
lids and corners, lashes and brow -- before the finish. Twelve stages against Portrait's
nine, because the distance from an outline to a convincing eye is where beginners stop.
The tonal stages are each the finished rendering with something still missing -- blurred
everywhere, then sharp in the iris, then sharp along the lids and brow -- at whatever the
detail slider is set to, so the sequence converges on the finish and
`test_the_tonal_stages_only_ever_approach_the_finish` holds it to that. The blurred base
(`styles.soft_tone`) was offered as a style of its own for one build and withdrawn: alone
it reads as the photograph out of focus, and it only means something as a step.

**Outline steps follow the detail slider, in every mode.** They used to be held to a
minimum detail that the finish was not, so with the slider low the last outline step
showed up to 2.6 times the ink of the finished drawing after it. When the finish is an
outline the steps now use the slider's value exactly (`steps._outline_detail`); under a
shaded finish the floor stays, because there the outline is scaffolding.

**There is no detector.** The first design found eyes through the face detector. The first
real test set ended that: seventeen of nineteen photographs were close-ups of one eye, and
the face detector reported a face inside ten of them. So the user frames the eye with the
box picker, whose default already covers a close-up untouched.

**There is no landmark model either** -- OpenCV Zoo has none for the eye region -- so
`core/eyes.py` is classical vision, built so that it cannot produce something that is not
an eye:

- *Iris*: a circle search that reads only the left and right arcs, since the lids cover
  the top and bottom. In a pale eye the strongest dark circle is the pupil, so a second
  pass looks outward for the limbus -- but only if the first circle is black enough to be
  a pupil. Six cues were measured for telling a pupil from a dark iris (size ratio, edge
  strength, evenness of the band between, whiteness outside, the top arc, tone steps);
  blackness was the only one that separated them.
- *Lids*: a template -- an almond with four parameters, each confined to the range real
  eyes occupy -- scored against the image and pulled toward average proportions where the
  image says nothing. Weak evidence gives an average eye on the iris, not a confident
  shape round an eyebrow.

Where it stands, measured on the eighteen single-eye photographs: iris right on twelve;
right place, wrong size on three; wrong on three. The three misses are a catchlight
covering half the pupil (so it is not black enough to be recognised), a black-and-white
photo whose sclera is in shadow and darker than the iris, and an eye turned far to the
side. Two of them are fixtures, pinned by `test_the_known_misses_fail_small_not_wild`.
The lids are approximate everywhere: plausible, usually a little narrow, and level --
tilt is penalised hard because a level eye read as tilted looks worse than the reverse.
Which corner is the tear duct is not known, so the construction does not mark it and the
step text describes it instead.

A real fix is a landmark model (MediaPipe's face mesh has 71 points round each eye), which
would need a source with a licence that can ship, and a face in the photo.

### Posture, specifically

Abstract first, and not as a compromise: gesture and mannequin work *are* figure drawing,
and full rendering is a later and separate skill. So the mode leads with Gesture (the line
of action in one stroke) and Mannequin (ribcage and pelvis masses, limbs as tapering
volumes, a heads-tall ruler), then Contour, Value, Cross-Contour and Realistic.

**Cross-Contour** is this mode's Cross-Hatch: the bridge between a flat value study and a
finished drawing. Hatching that runs straight across a limb flattens it; hatching that
curves *around* it describes a cylinder. The strokes are iso-lines of two scalar fields
built from the pose landmarks -- distance along the nearest limb axis, and signed distance
across it -- so they wrap arms, legs and torso the way a life drawing does, and build
darkness by crossing layers rather than pressing harder. The step ladder has a matching
stage between the value blocks and the finish, because showing the tone appear without
showing how the pencil got there teaches nothing.

Every hatch in the app shares one rhythm (`_hatch_ink`): the same stroke spacing, the same
weight, four layers, and the same tone at which each layer starts. Only the direction
fields differ -- four planes at 45/135/0/90 where there is no structure to follow, the two
axis fields and their diagonals where there is. The first attempt gave Posture its own
spacing and weight, and the result read as a different style rather than the same
technique applied to a figure; `test_every_hatch_uses_the_same_stroke_rhythm` measures
stroke width off the render and pins it.

**The crop is built around the body, not the detector's box.** A person's outline runs
well outside the box the detector returns -- hair, loose clothing, a raised arm -- so a
margin taken off that box cut into the figure on four of the six test photographs.
`bodies.union_box` now grows the box to contain the figures' own segmentation and takes a
12% margin off that. A bigger flat margin was the obvious fix and was measured first: 25%
still clipped two of six, 30% one, and 35% cleared them only by padding every side for the
sake of the worst one. Fitting leaves nothing cut and the figure slightly larger in frame
(29.7% of the crop against 28.3%).

Hands and faces are deliberately left as a wedge and an egg. At full-body scale a hand is
a few dozen pixels, detailing it there is wrong, and the app has dedicated modes for both
-- the step text says so.

Two things the 33 landmarks buy that matter more than the skeleton:

- **Contrapposto.** The shoulder and hip bars tilt in opposite directions in any weighted
  standing pose. Seeing that is the biggest single step from a stiff figure to a live one.
- **Proportion in heads.** The head is inferred from the torso, not from the span across
  the ears or shoulders: those are measured across the body and collapse as soon as the
  figure turns. Shoulder-midpoint to hip-midpoint is measured along the body and spans
  about 2.2 heads. Across twenty-two figures the across-the-body estimate was plausible
  eight times and once claimed a figure was 68 heads tall; the along-the-body one was
  plausible on all twenty-two.

The pose model also returns a body segmentation mask, so figure masking is free and knows
what a person is -- no GrabCut, and a patterned floor does not end up shaded as anatomy.

## Adding a subject

Subjects live in one place. `core/modes.py` holds a `Mode` for each one, carrying its
styles, its detector, its guide function, its stage ladder and whether the material guide
applies. The UI reads that registry, so adding Legs or Full Body means adding a `Mode` and
the text it needs -- no screen, pipeline or widget has to change.

1. **Styles** -- add a dict to `core/styles.py`. Give every style a `family`
   (`line`, `construct`, `value`, `hatch`, `real`). The family is what lets the pencil
   tips, the finishing advice and the "does this style have tone" rule be inherited rather
   than restated, so most new styles need no new text at all.
2. **Guides** -- add a `*_guides(ov, w, h, th, ctx)` function to `core/guides.py` and
   register it in `GUIDES`. Fall back to `frame_guides` when the subject cannot be found.
3. **Stages** -- add a `*_stages(job)` builder to `core/steps.py`. Compose it from the
   existing renderers; the stage ladder is about ordering, not new image processing.
4. **Text** -- add entries to `data/steps_text.py` for the new stage ids, and to
   `data/tips.py` only where the advice differs from the family's.
5. **Tiles** -- regenerate with `python scripts/make_examples.py portrait.jpg object.jpg hand.jpg body.jpg eye.jpg`.
   A style with no tile falls back to a plain labelled button rather than failing. Use real
   photographs: a synthetic stand-in makes tiles that look nothing like what the style does
   to a photo.
6. **Register** the `Mode` in `MODES`.

`tests/test_core.py::test_registry_is_self_consistent` and
`test_every_mode_builds_a_usable_sequence` run against every registered mode, so a subject
that is only half wired up fails there rather than on a phone.

### Hands, specifically

Hands use two offline ONNX models from OpenCV Zoo (Apache 2.0, ~5.2 MB, run through
`cv2.dnn`): a palm detector to find the hand, then a landmark model giving the wrist, the
knuckles and all three joints of every finger. `scripts/download_models.py` fetches them and
the workflows run it before building; they are not committed.

Everything the guides draw -- the palm block, the knuckle arc, the finger axes -- comes from
those 21 points, so it bends with the hand instead of approximating it.

It did not start that way. The first version worked the structure out from the silhouette
alone: palm from a distance transform, fingertips from the outline's convex corners. That
passed every synthetic test and then lost whole fingers on real photographs, because an
outline does not separate fingers held together and a curled finger has no fingertip to
find. That code is still there as `_from_silhouette`, used when the models are missing,
and `tests/test_hands.py` keeps it honest -- but the lesson is in `tests/fixtures/`: the
synthetic tests could not have caught it, and a single real photo did immediately.

Hand styles are masked to the hand (`styles.on_hand`), so a hand photographed on a table
comes back with the hand shaded and the table left as paper.

If the models are absent the app still runs: detection falls back to the silhouette method
and, failing that, to the object guides.

Measured over twenty photographs (`tests/fixtures/` holds nine of them): the models read
nineteen, including a fist head-on, fingers wrapped round a mug, a pinch, darker skin and
a hand writing with a pen. The one they miss is a hand mostly off the frame gripping a
phone -- there the palm detector offers boxes and the landmark model rejects all of them,
and no padding or resolution recovers it. That case falls back rather than being forced
through by lowering the confidence threshold, because confidently wrong joints on the page
are worse for a learner than approximate ones.
