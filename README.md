# Sketch Assistant

Offline photo -> pencil-sketch helper for drawing learners. Python + Kivy + OpenCV; no cloud calls.

Everything reported against the app since v1.0.0, in the tester's own words, is in
[`TESTER_COMMENTS.md`](TESTER_COMMENTS.md).

## Run
    pip install -r requirements.txt
    python scripts/download_models.py        # ONNX models for faces, hands and bodies (~23 MB)
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
- **Eyes**: 5 styles on one eye, framed with the box picker. Construction and a fourteen-stage ladder are its own.
- **Nose**: 5 styles on one nose, framed with the box picker. Construction (envelope, wedge, three balls, light plan) and a thirteen-stage ladder are its own.
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
| **Portrait** | Solid. A face was found in all 27 test portraits, 26 with landmarks, and every one produces the full nine-stage sequence. Where MediaPipe's face mesh is available the guide oval is fitted to the face's own outline: on 15 hand-marked close-up faces it runs through the chin with the face inside on 10, against 2 when scaled from the detector box. See below. |
| **Object** | The user draws a box round the object they want; see below for why. |
| **Cartoon** (key `caricature`) | Newest. Portraits only: the face mesh is compared, in 3D, with MediaPipe's average face, and this face's differences are pushed as far as the slider says, then drawn as clean lines from the mesh (no tracing) with hair from the person segmentation. On 8 faces, 26 of 29 distinctive proportions move the face's own way at full strength. Glasses aren't drawn, beards are rough, side profiles weak. See below. |
| **Nose** | Recent. The face detector, given room by padding the photo, anchors the nose; the nostrils (face-on) or the nose's outline (side-on) are then read locally. On 16 hand-marked tester photos -- close-ups, three-quarter and side views -- found on 13, against 1 for the first version. The box picker starts on the nose; where MediaPipe's face mesh is available the wings and the line down the bridge come from it. See below. |
| **Eyes** | Two halves. On a photo with a face, MediaPipe's face mesh and iris model find the eye and the box starts on it: on ten hand-marked eyes the iris size is within 21% every time, where reading a loose box alone was 2.7 to 4 times too big on six. Close-ups of one eye (no face) are still read by a circle search and a lid template: right on 10 of 19 close-ups. See below. |
| **Posture** | Figures found by MediaPipe Pose. Tap one, or several -- two people interacting are one composition, so choosing both gives a region spanning them and the gap. |

### Portrait's oval on close-ups

A tester, with nineteen close-up portraits: "the guiding circle for some of these faces is
smaller than the face itself". The oval was scaled from YuNet's box, which on a close-up
is too small or in the wrong place. Now (`faces._with_outlines`), where the face mesh is
available, the oval is an ellipse fitted to the mesh's 36 outline points -- forehead,
temples, cheeks, jaw, chin -- expressed as the box the guides' own constants turn into
that ellipse, so the guide lines, the steps' contour ring and the ear placement all
follow without other changes. The mesh is started from the padded face finder's points
where it found the same face (YuNet, unpadded, reads a close-up face small and the mesh
follows it), and is used only where its face-present flag is positive, which leaves side
profiles on the box. The same finder recovers faces YuNet misses: on the tester's photos
at full size an extreme close-up and a face in heavy sunglasses, and one where YuNet took
the mouth and chin for the face.

Measured on the fifteen faces whose chin and widest points could be marked by hand
(`tests/fixtures/portraits_close/marks.json`): the oval passes within 12% of the chin
with the sides of the face inside on 10 (11 on the 900 px fixture copies), against 2 (3)
for the box-scaled oval. The start point and the number of mesh passes were chosen on
those same photos. The no-landmark fallback still scales from the box, and
`test_fallback_proportions_match_real_faces` measures it on that box.

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
then for Photorealism the shared bridge (below) followed by the iris, the lids and corners,
and the lashes and brow -- fourteen stages against Portrait's twelve, because the distance
from an outline to a convincing eye is where beginners stop. From the blend on, each stage
is the finished rendering with something still missing, so the sequence converges on the
finish and `test_the_tonal_stages_only_ever_approach_the_finish` holds it to that.

**Finding the eye.** A tester sent an eye whose construction circle was "way bigger than
the eye itself" and asked for the eye to be found automatically. The rules read a crop on
their own, so they take the eye's scale from the box. On ten hand-marked eyes in face
photos, shown a box three eye-widths across they read the iris 2.7 to 4 times too big on
six; a tighter box of two eye-widths, 40% or more off on five and over three times too
big on two.

On a photo with a face, Eyes now works the way MediaPipe does (`core/landmarks.py`): the
face detector (`noses.find_face`), then the 468-point face mesh, whose points round each
eye frame a crop 2.3 eye-widths across for the iris model, turned level and mirrored for
the eye on the image's right, as the model expects. The iris model gives 16 lid points and
the iris; the face says which corner is the tear duct. That reading is made once per photo
and moved into whatever box the user settles on (`Mode.locate` -> `eyes.propose_box`,
`Mode.on_crop` -> `eyes.note_crop`), exactly as Nose does. The box starts on the larger eye.

On ten eyes marked by hand in face photos (`tests/fixtures/eyes_in_faces/marks.json`,
marked on crops with nothing drawn on them), through the app's own flow: iris size within
21% of the mark on all ten, median 6%, the same for a box of two or three eye-widths.
The centre is weaker: within 0.55 iris radii on every eye, within 0.3 on six. Ten eyes in
eight photos is a small set.

**Where the face gives no eye.** On a side profile the face mesh declines, so the face
path has no eye to give -- but the face still sets the scale. The iris radius runs at
0.078-0.105 of the eye-to-mouth length on the ten marked eyes (0.09 typically), a length
a turned head doesn't foreshorten. When the crop came from a photo with a face but no
face-path eye, the rules look for an iris no bigger than 1.15 times 0.09 of that length
(no smaller than half of it) and within 1.5 of it of a detector eye point; finding none,
they draw it at that size on the eye point. With the face path switched off on the ten
marked eyes: size within 14% typically, from 51% too small (a pupil taken for the iris)
to 33% too big, against the rules alone at up to four times the size. The limits were
chosen on those ten eyes; the irises in the tester's two profiles are hidden by lids and
lashes, so the profile case itself couldn't be measured.

**The iris model on a close-up, alone, measured worse than the rules** -- 7 of 19 close-ups
against 10 -- because its iris comes out the size of whatever crop it is given: 19% small
on a crop 9 iris-radii across, 8% large on one 14 across, and on an eye that fills the
photo no crop is right. Its own eye-to-iris proportions don't reveal when it's wrong, so
no rule picking between it and the rules beat the rules alone. So close-ups of one eye,
17 of the 19 test photographs, are still read by the rules, and the face path is used only
when a face is really there: the detector "finds" a face inside five of the close-ups, so
it must agree with itself across most of its paddings (support 3.0; invented faces reached
2.7, real ones 3.6 and up) and the face mesh must say a face is present. Both thresholds
were set on these photos.

### Cartoon (Caricature), specifically

Shown in the app as **Cartoon**: the first version was called Caricature, and the tester
found it stripped too much from the face and asked for "a more cartoonized version" with
"some soul" -- lashes, brow lines and nose lines like the app icon, and more hair. The
internal key is still `caricature`, and the slider still runs from no exaggeration to a
full caricature; it starts a third of the way up.

**The second pass, for expression.** Eyes: a grey iris with a dark rim, fibres, a shadow
from the upper lid, a big pupil and a catchlight; a heavy upper lid, heavier over its
outer two-thirds; a crease above it; six lashes sweeping out from the outer half, longest
at the corner; three short lower lashes; the tear duct. Brows: a soft tapered shape (thin
outside, full and rounded inside) filled with thirty short hair strokes leaning outwards.
Nose: face-on, the mesh's lower edge of the nose is nearly straight and drew as two
dashes, so the nose is now a cartoonist's -- a curl round each wing and a curve under the
tip, placed and sized from the mesh's wings, tip and base and turned with the head -- plus
one line down the side away from the light. Mouth and chin (a third pass, on request): the
whole lower lip, a tick at each corner, the philtrum ridges to the peaks of the upper lip,
three strokes across the lower lip, the dip under it and the chin's curve above its
outline; a hair outline running within 3% of a face height of the jaw is dropped, as it
drew a second chin line. Hair: up to 26 strands, closer together and
shorter at the minimum. Hatching is clipped to inside the drawing's outline. Measured:
round the eyes and nose, half as much ink again as the plain version at least (tested),
and still under a third of Portrait's Cross-Hatch overall.


A tester asked for a mode that turns a portrait into a simple caricature: head only, no
surroundings, far simpler to draw than Photorealism, light hatching at most, in the
style of the app icon, with a slider for how far to exaggerate.

**What's exaggerated, and how.** A caricature is recognisable because it pushes what is
already distinctive about one face, not because every face gets the same big head. So
(`core/caricature.py`):

1. The face mesh gives 468 points in 3D (`landmarks.face_mesh(..., with_z=True)`).
2. MediaPipe's canonical face (`core/face_average.py`) is fitted to them by rotation,
   uniform scale and translation only (Umeyama), so it sits in the same pose.
3. The leftover difference -- this face's shape -- is smoothed over each point's eight
   neighbours (three passes; unsmoothed, the mesh's jitter made every outline wavy),
   multiplied by the slider (0 to 2.5) and added back. In 3D, so a turned head is not
   taken for a lopsided face.

Anything off the mesh (hair, hatching) moves by inverse-distance blending of the nearest
24 mesh points' movement. Measured on 8 near face-on faces, for four proportions a
caricaturist pushes (face width to height, nose width and mouth width to eye span,
eye-to-mouth to face height): of the 29 that differ from the average by more than 3%,
26 move further the face's own way at full strength. A fixed cartoon push (every
proportion 10% larger) agrees 21 times -- the control in the test.

**Drawn from the points, not traced.** Every line is a mesh contour: the jaw (only where
it isn't under the hair; above the eyes only against the background; always below the
mouth, so a beard doesn't erase the chin), the lids, an iris circle from the iris model
clipped to the lids, brows as tapered shapes, two hooks for the nostrils, the top of the
upper lip, the line between the lips and a short curve under the lower one. Corner-cut
smoothing turns the few points per feature into curves. That is what keeps it as clean
as the icon.

**Hair and head.** MediaPipe's person segmentation (`selfie_segmentation.tflite`, 0.25 MB)
gives the person; less the face and, below the eyes, skin-coloured pixels (ears, neck),
it is the hair. Above the eyes everything beyond the face counts: colour alone mistook
blonde and pink hair for skin. Below the mouth hair is kept only within a quarter of a
face width of the face, and a patch must reach eye level (collars don't). Its outline is
drawn except along the photo's edge and the cut just under the chin. A bald head is
skin-coloured above the face *and* smoother than the cheek (fine texture under 0.8 of the
cheek's: 0.43 and 0.73 on the two bald test heads, hair 0.91 and up; set on those
photos): it keeps its outline but gets no hairline. Strands are traced along the hair's
direction -- the structure tensor where the hair has texture, parallel to its outline
where it doesn't -- deepest first, at most 14, each stopping short of its ends.

**Light hatching.** One layer of parallel strokes over the darkest fifth of the face
(away from the features) and the darkest 30% of the hair, angled from the lit side,
stopping short of each edge. Light Hatching puts down under a third of the ink of
Portrait's Cross-Hatch on the same crop; Clean Lines less again (tested).

**Portraits only, said up front.** `Mode.note` is shown on the status line as soon as the
mode is chosen ("Cartoon works on portraits only - add a photo of a face"), and the found,
not-found and hint lines repeat it.

**Styles and steps.** Light Hatching (default), Clean Lines, Shapes. The slider is the
exaggeration in all three -- its ends say so (`Mode.slider_labels`). Steps: head shape
and guide lines, features as shapes, then over the fading shapes the outline, eyes and
brows, nose and mouth, strands, the hatching, the finish. The guides are the
caricature's own proportions, not the photo's.

**Where it falls short.** Glasses aren't drawn (the eyes behind them are). Beards are
outlined only where they show beside the jaw. Side profiles keep their mesh outline,
which is weak there; a hat is drawn as hair. Measuring takes about 0.3-0.9 s per photo on
a desktop, once per photo; the slider re-draws without re-measuring.

### Nose, specifically

Built like Eyes -- a box picker, `core/noses.py` reading the structure -- except that the
box starts on the nose the app found (below). The ladder runs construction in four passes
-- length, width and tilt; the wedge of planes; tip ball, wing balls and nostrils; the
light plan -- then the nostrils and wings (the only real lines on a nose; the sides of the
bridge have none), the surroundings, values, the shared hatching bridge, the bridge and
side planes, the nostrils and the shadow below, and the finish. Thirteen stages for
Photorealism.

**Finding the nose.** The first version assumed the user had framed the nose and looked for
nostrils in the lower middle of the frame. The box picker starts on 85% of the photo, so
on a close-up that hands it the mouth and chin as well, and on the sixteen photos a tester
sent next it found the nose on one -- "an awful job detecting the nose in the first
place". Even with a box drawn tightly round each nose it found five.

It now starts from the face detector's nose point. On its own the detector found a face on
five of the sixteen, since most were close-ups with the face cut off; padded out with
plain border it finds one on all sixteen, and on eight of nine tightly framed noses. Its
threshold is lower than Portrait mode's because here a face is known to be present, and
`find_face` only accepts an answer that at least two of five paddings agree on.

Everything after that happens in a patch cut round the nose point, turned so the face's
axis is vertical and scaled so the eye-to-mouth length is 160 px -- so every threshold is
in fixed units whether the nose filled the photo or was a speck in it. Contrast is
equalised on the real pixels before warping and measured only inside the photo, because
where the patch runs past the photo's edge the warp smears the edge out.

- **How turned the head is** comes from the detector's five points: how far the nose sits
  off the line from between the eyes to the middle of the mouth, plus how foreshortened
  the eyes are. Front, three-quarter or profile; the boundaries were calibrated on these
  sixteen photos.
- **Face-on**, the nostril pair is looked for under the nose point, scored on contrast,
  symmetry about the face's centre line, position and *darkness* -- a cluster of freckles
  beside the nose is dark and compact too, and out-scored the nostrils on one photo until
  darkness counted. A fainter partner is looked for beside a lone nostril; failing that a
  plausibly placed lone nostril is mirrored across the centre line. The width is held to
  0.3-0.75 of the eye-to-mouth length (0.46-0.56 measured face-on).
- **Side-on**, the tip is the furthest point of the nose's outline, found by following
  each row outward from the nose point to the first strong edge -- the first, because a
  lock of hair beside one nose was a stronger edge than the nose -- and only from a little
  above the nose point down, because on a head tipped back the bridge reaches further
  forward than the tip. In three-quarter the tip goes halfway between the nose point and
  the outline: there the outline is the far side of the nose on a strong turn and only the
  edge of the tip ball on a mild one, and nothing in the detector's points tells the two
  apart. The near nostril is the darkest nostril-sized shape behind and below the tip.
- **The root** of the nose sits at eye level, between the eyes face-on and moving forward
  to the bridge's silhouette as the head turns.

**The box picker starts on the nose** (`Mode.locate` -> `noses.propose_box`): from the root
to the upper lip, wing to tip, with room round it. The status line says the nose was found
and that a new box can be dragged if it is wrong.

**A crop gets the whole photo's reading.** Inside a box drawn round the nose the detector
does worse -- 10 of 16 found reading the crop alone against 13 -- because it needs the
eyes and mouth. So the nose is read once per photo, and the app tells the analysis where
each crop came from (`Mode.on_crop` -> `noses.note_crop`); the crop, recognised by a
thumbnail since renderers only resize it, gets that reading moved into its own pixels.
Any other image is read on its own; with no face found anywhere, the first version's
crop-only reading is the fallback.

**Side views get a side construction.** The face-on wedge drawn on a profile spreads planes
and a second wing in front of the nose. Side-on the nose is built as drawing books do it:
a triangle from root to tip to the back of the wing, the underside as a sliver, one wing
ball behind the tip with the nostril under it, and in three-quarter a narrow front plane
along the bridge with the far wing just showing past the tip.

**The face mesh draws the wings and the bridge.** A tester: "the circles don't always land
on the edges of the nose curvature and the purple line doesn't always follow the nose
line". The wing balls were placed by proportion from the nostrils and the bridge line was
one straight stroke from root to tip. Where MediaPipe's face mesh is available (it is
already run for Eyes) the reading takes from it: the wing balls from the rings of mesh
points round each wing, the tip ball from the two tip points, and the bridge as the mesh's
five points down the ridge, root to tip, which the guide and every construction level now
follow. Face-on, the mesh's wings run about a fifth wider than the marked nose, so they
are scaled by 1/1.2 -- fitted on the six face-on photos it is then measured on. Outer wing
edges, in nose-widths from the marks on those six: median 0.10, worst 0.16, against median
0.12 and worst 0.24 for the proportional template. On the three known misses the mesh's
wings are worse than the template's (the template was right there by accident). The tip
and base still come from the image reading -- on side views the mesh's tip sits inside the
outline -- so the 13 of 16 below is unchanged; the mesh alone finds 11. If the mesh is
missing, the reading is the template one.

**Where it stands**, on the sixteen tester photos (`tests/fixtures/noses/photos`, with the
tip, base, extent and facing of each marked by eye in `marks.json`): tip and base within
0.35 nose-widths of the marks on 13 -- the same whether the photo is read whole, through
a tight box, or through the box the app proposes, and from 600 to 1600 px. The first
version: 1 whole, 5 with a box. The three misses are fixtures in
`test_the_known_misses_stay_on_the_face`: two heads turned only slightly, read as
three-quarter so the tip lands on the edge of the nose (on one the eyes are cut off and
the turn comes out the wrong way), and one photo on which the detector agrees with itself
across paddings about a face that is not there. Sixteen photos is a small set, and the
view boundaries were set on them. The lit side is guessed from which side plane is
brighter, and assumed from the front when unclear; the step text says to check it.

### From hatching to a realistic finish (every mode)

A tester found hatching easy and the realistic finish a leap. Every Photorealism ladder
now goes values -> hatching -> blended hatching -> lights and darks -> finish
(`steps._hatch_to_real`), which is a real way artists get from one to the other:

- **Blend the hatching** blurs the hatching by most of a stroke spacing, then lays the
  outline back over it, so the result is smooth tone that is still a drawing. One gamma
  brings its average to the finish's (a 1-8 grey-level correction on the test photos).
  Two earlier versions failed and are recorded in the code: too little blur left a
  criss-cross; quantile-by-quantile tone matching turned the layers into stencil bands.
- **Lift the lights, deepen the shadows** outlines the finished drawing's brightest small
  shapes in blue (keep or lift with an eraser) and its darkest small shapes in red (press
  to full dark), and brings those in. Taken from the finish alone: marking where finish
  and blend differed covered up to a third of the picture. The step text names the kinds
  of light and shadow -- highlight, light side, core shadow, reflected light, cast shadow,
  contact shadow -- and how each is drawn.

This replaces the blurred "Soft Tone" base the eye ladder used, which was withdrawn as a
style and then as a step: on its own it read as the photograph out of focus.

### The value step's key

The value step, and a Value Study finish, print a key underneath: every flat grey in the
picture and the pencil for it (`steps.VALUE_PENCILS`, greys from `styles.value_levels` so
the two cannot drift apart). The Value styles' tips now open with what value is and what
the study is for.

### Detail slider on the steps page

The steps page has the detail slider too. Rebuilding a ladder takes 0.1-0.6 s on a desktop
(measured, warm caches) and should be several times that on a phone (not measured), so it
runs off the UI thread once per release, one build at a time: a release during a build
replaces the waiting value rather than queuing another build, and the step being viewed
stays put. The new detail carries back to the guide and main pages.

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

**Lopsided circles are re-centred on the pupil.** On a side-lit photograph a tester sent,
the iris's shadowed limbus was too weak to win, and the search settled on a circle whose
bright side was on the limbus and whose shadowed side was on the pupil's edge: two-thirds
the iris's size and pushed toward the light. `_recentre_on_pupil` runs on the final
circle: if a compact, round, black blob sits well off its centre, it re-searches round
that blob, between one and 2/1.2 times the original radius, and takes the result only if
its edge is at least 70% as strong. Every guard is there because a looser version broke
something: taking the largest black patch as the pupil moved the iris on 27 of 38 photos
(lashes and crease shadows are black too); re-centring before the pupil-to-limbus step
spoiled `amber_reflection`; and without the size limit two crops had the circle grow onto
the lids. Measured on 38 images (the 19 test photos, crops of them, the portrait-derived
crops and the fixtures), the final version changes six readings, all for the better by
eye, and leaves the rest exactly as they were. The size limit has an anatomical
derivation (a pupil is at least a fifth of its iris) but was confirmed on that same set,
which is all the evidence there is. The tester's photo is not a fixture, since where it
came from is not known; `test_a_lopsided_circle_is_recentred_on_its_pupil` checks the
mechanism on exact geometry instead.

**The eye guides are laid out as a dimensioned drawing.** The eye carries only markers --
the iris circle, a cross at the pupil, dots at the corners, ticks at the top and bottom of
the lids -- and every number sits in the margin: across along the top edge, down along
the left. The thirds grid is off in this mode (`guides.NO_GRID`).

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
5. **Tiles** -- regenerate with `python scripts/make_examples.py portrait.jpg object.jpg hand.jpg body.jpg eye.jpg nose.jpg`.
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
