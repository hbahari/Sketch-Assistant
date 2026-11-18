# Tester comments

Everything reported against the app since **v1.0.0**, written the way a tester would say
it rather than the way the code describes it. Source material for the reviewer-comments
write-up.

Newest round at the top. Each entry is what was noticed, then what changed in plain terms.
No file names, no library names, nothing that needs the source open to follow.

> **Version attribution is not filled in.** v1.0.0 is on Play and the current build is
> 1.2.0 (version code 3), so one release sits in between — but which of the rounds below
> shipped as 1.1.0 is not recorded anywhere in the repo. Fill in the `Shipped in:` lines
> from the Play Console release history before this goes to a reviewer.

---

## Round 23 — say that Cartoon mode is for portraits

*Shipped in: 1.6.0 (not yet uploaded)*

> "Also, add a text label saying that Cartoon mode only works for portraits."

**What changed.** As soon as Cartoon is chosen, before any photo is loaded, the line under
the photo reads "Cartoon works on portraits only - add a photo of a face". After a photo is
loaded the same words stay: "1 face(s) found - tap a box (Cartoon works on portraits
only)", or "No face found - Cartoon works on portraits only". Once a face is tapped, the
hint starts with "Portraits only".

---

## Round 22 — more to the lips, and the chin

*Shipped in: 1.6.0 (not yet uploaded)*

> "Can we add more details to the lips, and an outline of the chin as well?"

**What changed.** The mouth now has the whole lower lip, not just a short curve; a small
tick at each corner that turns up or down with the mouth; the two short ridges from the
nose down to the peaks of the upper lip; and a few light strokes across the lower lip to
show its fullness. The chin has a soft curve just above its outline, with a lighter line
in the dip under the lower lip. The steps now include the chin with the face outline.
Where the hair's edge ran right alongside the jaw (beside the neck), it used to draw a
second line just under the chin. That second line is gone now.

---

## Round 21 — the caricature needed more soul

*Shipped in: 1.6.0 (not yet uploaded)*

> "I think we're removing too many facial features when drawing the caricature. Maybe
> caricature isn't even the right name for it; I'm looking for a more cartoonized
> version. Let's add a few hair lines to show more of the flow of the hair. The eyes could
> use a bit more detail to express the feeling of the face. Right now they look creepy
> with these simple eyes. Maybe add a few feature lines for the eyebrows and eyelashes,
> similar to the app icon. Same with the nose: it looks too simple. Add a few nose lines?
> Let's give it some soul."

**What changed.** The mode is now called **Cartoon**. The slider still turns it into a
caricature if you push it, and it now starts lower. The eyes are where the change shows
most. Each has a shaded iris with a big dark pupil and a white catchlight, a heavier upper
lid with a crease above it, lashes sweeping out from the outer corner, a few small lower
lashes, and the inner corner. The brows are drawn hair by hair, full at the inner end and
thinning outwards, like the icon's. The nose is a curl round each nostril wing and a soft
curve under the tip, plus a line down the side in shadow, instead of two small dashes.
The hair has about twice as many strands, following its flow. Hatching no longer hangs
loose past the edge of the drawing.

**Process note.** The first version was built to be easy to draw, and it overshot. The
"simpler than photorealism" brief was read as "as few lines as possible". The icon,
which was the reference, is simple but not sparse: its eyes and brows carry most of
its detail.

---

## Round 20 — "No face found" on a face Caricature mode had just found

*Shipped in: 1.6.0 (not yet uploaded)*

> "It's buggy. When I upload a photo, even though it detects the face, the second screen
> says no face detected, try Portrait mode."

**What changed.** The face *was* found. What the app couldn't use was the face-mapping
piece Caricature mode draws from. It's a separate download, and on a computer it has to
be fetched once with the model download script. When it was missing, the app said "No
face found", which sent you looking at the photo when the problem was the setup. Now
the picture and the status line both say which piece is missing and how to get it, or
that the computer's image library is too old to read it. The message is also larger and
wraps to fit the picture instead of running off in tiny grey text. The app also reads
these models' results in a way that doesn't depend on the version of that image library.
On a phone the pieces come with the app, so this only shows on a computer.

**Process failure, owned.** Two different failures, "nothing to work with" and "no face
here", shared one message. The tests always ran with every model in place, so nothing
ever showed what a missing one looked like. The same silent fallback probably explains
the earlier report that eye detection felt "hit and miss" on the tester's computer. That
can't be confirmed from here.

---

## Round 19 — a caricature mode

*Shipped in: 1.6.0 (not yet uploaded)*

> "I think the next mode we add is going to be something like a caricature mode. I want
> it to only work for portraits and turn a portrait into a simple caricature with no
> surroundings — just the portrait itself. It should be a lot simpler than photorealism
> for the user to draw, shouldn't have too many shadings and shouldn't look too crowded:
> something in line with the app icon's art style."

Asked before building: how far to exaggerate (a slider), how much shading (light
hatching) and how much of the person (the head only).

**What changed.** A Caricature mode was added. Load a portrait, tap the face, and the
app draws just the head in clean, even lines like the app icon: the outline of the face
and hair, the eyes, brows, a small nose, the lips, and a few long strands of hair, with
nothing from the background. The caricature isn't a fixed cartoon face. The app works
out what makes this particular face different from an average one (a wider nose, a
longer chin, closer eyes) and pushes exactly that. The slider runs from no exaggeration
to strong, and its ends say so. There are three styles: Light Hatching, which adds a
single layer of hatching in the shadows; Clean Lines, which has no shading at all; and
Shapes, the simple shapes it's all built on. The steps go from the head shape and the
features as simple shapes to the lines, one feature at a time.

On eight test faces, when a feature stood out from the average, the caricature pushed it
the right way 26 times out of 29. It uses far less ink than Portrait mode's cross-hatch
on the same photo.

**Left as is, for now.** Glasses aren't drawn, though the eyes behind them are. Beards
are only outlined where they show beside the jaw. Side profiles come out weaker than
face-on photos, and a hat is drawn as if it were hair.

---

## Round 18 — Play Console wouldn't send 1.5.0 for review

*Shipped in: 1.5.0, version code 8 (not yet uploaded)*

> "Can you address this issue that was raised while uploading to Play Console: required
> hardware feature declarations are restricting your app's availability —
> android.hardware.screen.portrait affects Phone, Tablet, Desktop, and Android XR users."

**What changed.** The app still opens upright as before. Because it's locked upright,
though, Android was treating an upright screen as something a device must have, so Play
would have hidden the app from devices that don't report one (some tablets, Chromebooks
and headsets) and refused to send the update for review. The app now says an upright
screen is preferred but not required. The build number went up by one, because Play
won't accept the same build number twice.

**Process failure, owned.** The upright lock had always carried this requirement. Nothing
in the build or the release checklist looked at what the finished app asks of a device,
so the first warning was the store's.

---

## Round 17 — portrait circle smaller than the face; eye guides too big when the eye isn't found; the build failing

*Shipped in: 1.5.0 (not yet uploaded)*

> "In portrait mode, the guiding circle for some of these faces is smaller than the face
> itself. Or the guiding lines for the eyes, if the eye isn't detected by the app, end up
> being bigger than the eye."

**What changed — portrait circle.** The circle around the face is now drawn from the
outline of the face itself (forehead, cheeks, jaw and chin) rather than from a rough box
round the face. On 15 faces in the tester's close-ups, where the chin and the widest
points of the face could be marked by hand, the circle now runs through the chin with
the face inside it on 10, against 2 before. Portrait mode also finds faces it used to
miss on close-ups: on the tester's photos, an extreme close-up and a face in heavy
sunglasses. On one photo it used to take the mouth and chin for the whole face, and it
now gets the whole face. Side profiles are unchanged. The outline can't be read reliably
from the side, so those keep the old circle, and on one strict profile Portrait mode
still finds no face.

**What changed — eye guides when the eye isn't found.** When the photo has a face but the
app can't read the eye itself (side profiles mostly), it now uses the size of the face to
set a sensible size for the eye, and looks for the eye near where the face says it should
be. On ten hand-marked eyes, tested with the automatic reading switched off, the circle
now comes out typically within about an eighth of the real size. It ranges from half the
size (where the app took the pupil for the whole iris) to a third too big. Before, the
same boxes gave circles up to four times too big. On a close-up of one eye with no face
in the photo there's nothing to take the size from, so that still works as before.

> "Tried building the 1.5 version and got this error."

**What changed — the build.** The build was failing while unpacking Android's toolkit,
which it downloads fresh. The download had arrived damaged, and the build only noticed
much later. The build now downloads it with retries and checks it before using it. It
also stopped throwing away its saved copy of the toolkit every time the version number
or the app's settings changed.

**Process failure, owned.** That fresh download only happened because the previous
round changed the app's build settings, which threw away the saved copy and forced a
full re-download on the next build. The download had always been fragile. The change
exposed it, and the first anyone knew was a failed build on the tester's side.

---

## Round 16 — eye guides too big, nose circles and bridge line off

*Shipped in: 1.5.0 (not yet uploaded)*

> "Those sections where you draw a box, like Nose and Eyes, don't work very well —
> especially the guiding lines, which are usually a bit off. Look at this example: the
> guiding lines for the eye are way bigger than the eye itself. Is there a cost-efficient
> way to detect these automatically, with good precision, instead of making the user draw
> a box?"

> "The guiding lines for the nose could use some improvement too: the circles don't always
> land on the edges of the nose curvature, and the purple line doesn't always follow the
> line of the nose."

**What changed — eyes.** On a photo with a face in it, Eyes mode now finds the eye itself
and the box starts round it, the same way Nose mode does. It reads the eye from the whole
face, so the size of the eye comes from the face, not from the box you drew. That was the
fault: the old reading judged the eye's size from the box, so a loose box gave a huge
eye. On ten eyes marked by hand, the iris circle now comes out within about a fifth of
its real size every time, typically within a twentieth, however big the box. Before, with
a loose box, six of those ten were drawn between about three and four times too big. The
lid outline comes from the same reading. Where the circle sits is less exact than its
size: always within about half the iris's width of the middle, closer on most.

Close-ups of a single eye, with no face in the photo, work as before. We tried the new
method on those too and it did worse than the old one (right on 7 of 19 close-ups,
against 10), so it isn't used there. You still draw the box on a close-up. The app is also
careful not to "find" a face in an eye close-up: on five of the nineteen test close-ups
the face finder thought it saw one, and none of them gets through now.

**What changed — nose.** The wing circles and the line down the nose are now placed from
a detailed map of the face rather than worked out by proportion. The line follows the
ridge of the nose from between the eyes to the tip, curving where the nose does, instead
of being one straight stroke. Face-on, the outer edges of the wings now typically land
within a tenth of the nose's width of where they really are, against about an eighth
before, and the worst case is noticeably better. On three-quarter views the far wing is
never drawn inside the tip. Where the nose is found at all is unchanged (13 of the 16 test
photos). On the three photos it already got wrong, the new wings are a little worse.

Both use two small extra pieces from Google's free face-tracking toolkit. They run on the
phone like everything else, and nothing leaves the device. The toolkit's licence allows
use in a paid app, and its credit and licence text now ship inside the app.

**Process failure, owned.** The eye tests checked the app against readings the app had
made itself, all on close-ups, and none of them drew a box round an eye in a face photo
the way a person does. So the size fault the tester found could never show up in a test.
There are now hand-marked eyes in face photos, read through the same box-drawing steps a
person uses. Separately, the first estimate that the new method would also help on
close-ups was wrong; once it was measured properly it made close-ups worse, and it was
left out there. And the first build of this change would have left the two new pieces out
of the app itself (the packaging list didn't include their file type). That was caught
before release.

---

## Round 15 — crash when switching modes

*Shipped in: 1.5.0 (not yet uploaded)*

> "The app crashes when I draw a box in Nose mode and then swap to other modes."

**What changed.** The crash is fixed. When you switched modes with a photo loaded, the app
kept the faces or figures it had already found and handed them to the next mode, instead
of looking again. Portrait mode's faces were being passed to Posture mode, which tried to
treat a face as a whole body and crashed. It also went wrong the other way, more quietly:
Portrait mode offered whole figures from Posture to tap as if they were faces. Each mode
now does its own looking, once per photo.

Nose mode wasn't the cause. Drawing a box there just meant coming from Portrait to Posture
by way of Nose, and the same crash happened going straight from Portrait to Posture.

**Process failure, owned.** The problem had been there since Posture mode got its own way
of finding people, through several releases. No test ever loaded a photo and then switched
between modes, which is exactly what a person trying the app does. There are now tests
for the switches that crashed, and one that tours every mode and back on the same photo.

---

## Round 14 — the nose wasn't being found

*Shipped in: 1.5.0 (not yet uploaded)*

> "Here are some test photos. The app is doing an awful job detecting the nose in the
> first place!"

**What changed.** The tester was right, and it was worse than awful: on the 16 photos sent,
the app found the nose on one. Nose mode had been built assuming you would draw a box
tightly round the nose, but it starts with a box over most of the photo, and on a close-up
of a face it was mistaking the mouth or a beard for the nose. Even with a box drawn round
each nose it only managed five. It now finds the face first and works out where the nose
is from that, which also works on close-ups where only part of the face is in the photo.
It found the nose on 13 of the 16.

When you load a photo the box now starts on the nose instead of covering most of the
picture, and the message underneath says it found the nose. If it picked the wrong spot,
drag a new box. It gives the same result however tightly or loosely you draw that box.

It also tells which way the nose is pointing. Side-on and three-quarter noses get a
construction drawn the way drawing books do a side view — a triangle from the top of the
nose to the tip and back to the wing, one wing behind the tip, the nostril under it —
instead of the face-on version, which looked wrong on a turned head.

**Still wrong on three of the sixteen.** Two faces turned only slightly to one side: the
nose is found, but the tip is placed on the edge of the nose rather than its middle. On
one of those the eyes are cut off by the top of the photo and the app gets the direction of
the turn backwards. On the third it thinks it has found a face that isn't there, and the
drawing lands beside the nose. In all three the box still lands on the nose, so dragging
it a little fixes the framing, though not yet the misread tip.

**Process failure, owned.** The first version was tested only on noses cut out of face
photos and framed by hand, the easy case. Nobody had tried the box the app actually
starts with, and the tests passed because they never asked the question the tester asked.

---

## Round 13 — a mode just for noses

*Shipped in: 1.5.0 (not yet uploaded)*

> "For the next version I want a nose mode. Very similar to the eyes tab, with similar
> steps and guidelines, and as detailed as the eyes section."

**What changed.** A Nose mode was added. You drag a box round the nose, from between the
eyes down to the top lip. Like Eyes, it has a construction style and a long step-by-step
guide — thirteen steps for the realistic style. It starts with the nose's length, width
and tilt; then builds it as a wedge of flat planes (the bridge, the two sides and the
underside, which most beginners forget); then a ball for the tip and one for each wing,
with the nostrils tucked under the wings; then plans where the light and shadows go. The
outline step deliberately shows only the nostrils and the creases round the wings,
because the sides of a nose have no outline — they're drawn with shading. The shading
then goes through the same hatch-and-blend route as the other modes, followed by steps
for the bridge and sides and for the nostrils and the shadow under the nose. The guide
lines show where the tip, wings, root and base of the nose sit, with the numbers kept in
the margins as in Eyes.

**Where it falls short, as tested on 25 noses cut from the face test photos.** The app
reads the nose well on about 14. On 5 it can't see the nostrils at all (a finger over the
nose, a wink, very soft lighting) and shows an average nose in the middle, which is
roughly right on most. On about 5 it gets it wrong: a nose seen from the side, one behind
glasses with a septum ring that it mistakes for a nostril, a broad nose where it picked a
crease in the cheek, and two turned heads. The line down the bridge is always drawn
straight, which is slightly off when the head is turned. Which side the light comes from
is a guess from the photo, and the instructions say to check it.

---

## Round 12 — the jump to realistic, what "Value" means, and the slider on the steps page

*Shipped in: —*

> "Going from the hatch style to realistic is still a big leap. Hatching feels easy to
> draw, but realistic suddenly feels much harder and there isn't a smooth path between
> the two. The 'soft' step before didn't make much sense. Maybe add a step that guides me
> on how to add the different kinds of shading and shadow to get from one to the other?"

**What changed.** The realistic style's steps now go through hatching on the way, in every
mode. After the flat value shapes you hatch the same tones in strokes (the part that feels
easy), then blend the hatching smooth with a blending stump, then do a "lift the lights,
deepen the shadows" step before the finish. On that step the picture marks the brightest
spots in blue (keep them as white paper or lift them out with an eraser) and the darkest
in red (press to full dark). The instructions name the different kinds of light and
shadow — highlight, the lit side, core shadow, reflected light, cast shadow and the thin
dark "contact" shadow where two surfaces meet — and say how each one is drawn. The old
"soft" step is gone; the blended hatching replaces it, and it keeps the lines of the
drawing instead of looking like a blurry photo.

> "What does the Value style even mean? How am I supposed to use the value step?"

**What changed.** "Value" just means how light or dark something is, regardless of
colour. The Value style now says so in its tips, and explains that it's the plan every
shaded drawing is built on: it shows only the big light and dark shapes so you can get
them right before any detail. The value step in the drawing steps now has a key printed
underneath — each grey used in the picture, with the pencil to draw it — so you can fill
each shape by matching it to the key.

> "I want the detail slider available after I press 'Generate drawing steps', so I can
> play with the detail while I'm in the steps. Does that make the app too heavy?"

**What changed.** The steps page has the detail slider now. When you let go of it, the
steps are rebuilt at the new detail in the background and you stay on the step you were
looking at. It isn't too heavy: rebuilding takes under a second on a computer, and it only
happens when you let go, never while you're dragging. On a phone it will be slower, likely
a second or two, and that hasn't been timed yet. Moving it several times quickly only
rebuilds once more, at the last setting.

---

## Round 11 — eye guides crowded, and the circle in the wrong place

*Shipped in: —*

> "I tested the app on a photo and the guiding lines seem a bit too crowded and off,
> especially the circle. What is the circle representing?"

**What changed.** The circle is the outline of the iris — the coloured part of the eye —
and on that photo it was drawn about two-thirds too small and off to one side. The photo
is lit from one side, so the edge of the iris on the shadowed side was faint, and the app
settled on a circle that ran from the bright edge of the iris to the edge of the pupil
instead. It now checks that the circle is centred on the pupil, as an iris always is,
and if not, looks again around the pupil. On the tester's photo the circle now matches
the iris. Across all 38 eye images it was checked against, this changed six results,
all for the better, and left every other one exactly as it was.

The guides were also cleared off the eye. The numbers used to sit right next to the parts
they measured, on top of the drawing, with two full-length lines crossing at the pupil
and the rule-of-thirds grid running through everything. Now the eye only has small
markers on it — the iris circle, a cross on the pupil, dots at the corners, short ticks
at the top and bottom of the lids — and all the numbers sit along the top and left edges
of the picture, each lined up with what it measures.

**Left as is, deliberately.** The rule-of-thirds grid no longer appears in Eyes mode. It
helps with placing a subject in a picture, which doesn't apply to a close-up of one eye.

**Still not right.** On the same photo the app places the corners of the eye too far in,
so it reports the eye as 1.8 irises wide when it is closer to 2.3. The eyelid shapes are
an estimate, and this is the known weakness of that estimate.

---

## Round 10 — steps going backwards, and a style nobody could explain

*Shipped in: 1.4.0 (not yet uploaded)*

> "In contour mode with the detail turned down, step 7 has less in it than step 6, which
> looks wrong. Step 6 doesn't follow the detail I set on the slider at all."

**What changed.** The steps that build up the outline were quietly refusing to go below a
certain amount of detail, while the finished drawing obeyed the slider — so at a low
setting the last step looked like half the drawing had been rubbed out. The outline steps
now use exactly the detail you set. This was not only in Eyes mode: Portrait, Object and
Hands did the same thing and are fixed too.

> "I don't understand what the 'Soft' style really does. It doesn't feel implemented
> correctly and it isn't intuitive."

**What changed.** It was removed as a style. It was meant to show the eye fully shaded
before any sharp detail goes in, but on its own it just looked like the photo out of
focus. That idea only makes sense as a step on the way to the realistic drawing, so that
is where it lives now, and those steps were reworked so each one is visibly closer to the
finished drawing than the last. Eyes mode has five styles, like the others.

> "How accurate and reliable are the pencil grades, pressure and steps written under each
> style?"

**Not changed yet — answered.** The advice follows standard drawing-class practice and was
written from general knowledge. It has not been checked against named sources, reviewed by
a drawing teacher, or tried with learners, and it is the same text for every photo. See
"Still open".

---

## Round 9 — a mode just for eyes

*Shipped in: 1.4.0 (not yet uploaded)*

> "I want a mode specifically for eyes. There are so many guides out there for drawing eyes
> realistically, and I want this to be a lot more detailed going from the outline to the
> realistic version."

**What changed.** An Eyes mode was added. You drag a box round one eye, or load a close-up
and leave the box alone. It has the longest step-by-step guide in the app: twelve stages
where a portrait has nine. It starts with how wide, tall and tilted the eye is, then the
eyeball with the lids wrapped over it, then the iris and pupil, then a planning step for
where the highlight and the lid's shadow will go. After the outline it splits the shading
into small steps instead of one jump: flat tones, the tones blended together, the iris on
its own, the lids and corners, and the lashes last.

**Where it falls short, as tested on 18 close-up photos.** The app has to find the coloured
part of the eye before it can build anything round it. It gets that right on 12 of the 18,
puts it in the right place at the wrong size on 3, and gets it wrong on 3. The eyelid
shapes in the construction steps are an educated estimate fitted to each photo rather than
a tracing, so they are eye-shaped and in the right place but not exact. The shaded steps
do not depend on any of this and come out right regardless.

**Left as is, deliberately.** The app does not try to find the eyes in a photo of a whole
face for you. That was the first plan, and the test photos ended it: nearly all were
close-ups with no face in them, and the face finder "found" a face inside more than half of
those anyway.

---

## Round 8 — figures cut off by the crop; no measurements on the guide lines

*Shipped in: 1.3.0 (not yet uploaded)*

> "The box round a person in posture mode sometimes cuts into the pose — it slices off
> part of the body itself. Making the box about 10% bigger should fix most cases."

**What changed.** The diagnosis was right; the fix went a step further than the
suggestion. The box was being drawn around where the app thinks the person's joints are,
and hair, loose clothing and raised elbows stick out well past that — on four of six test
photos something was sliced off. Making the box 10% bigger was tried first and still
clipped two of the six; it took 20% bigger to clear them all, and that leaves every figure
small in the frame just to cover the worst case. Instead the box is now built around the
person's actual outline, with a little breathing room on top. Nothing is cut on any of the
six, and the figures come out slightly *larger* than a flat bigger box would have left
them. Where the photo itself cuts someone off, that obviously stays cut.

> "In every mode, the horizontal and vertical guide lines should say how far down or
> across the picture they are — a number between 0 and 1."

**What changed.** Every straight guide line now carries its position: 0 is the top or left
edge, 1 is the bottom or right, so "eyes 0.43" means the eye line is 43% of the way down
the page. That covers the eye, nose, mouth and chin lines and the centre line in portraits,
the centre cross in object mode, the shoulder line, hip line and vertical balance line in
posture mode, and the rule-of-thirds grid in all four modes. Slanted lines — the eye line
on a tilted head, say — are measured at their middle.

**Left as is, deliberately.** Hands mode only gains the numbers on the grid. Its own guides
are a circle, a curve and finger joints rather than straight lines, so there is no single
"how far down" to give them.

---

## Round 7 — shading strokes don't match between modes

*Shipped in: 1.2.0 (not yet uploaded)*

> "The shading in posture mode doesn't look like the shading anywhere else. The lines are
> longer and further apart, so it reads as a different style instead of the same app. I'd
> rather it was consistent across the board — either bring the others up to it or bring it
> down to them."

**What changed.** The posture shading was drawing strokes roughly four times as thick and
three times as far apart as every other mode. All four modes now use the same stroke
weight, the same spacing and the same number of layers; only the *direction* of the
strokes differs, because in posture mode they curve around the body. Tightening them also
exposed two drawing faults that the coarse strokes had been hiding — ring patterns at the
hips and the top of the head, and solid dark patches just past the hands and feet. Both
are gone.

---

## Round 6 — posture mode

*Shipped in: —*

> "Can it do whole poses, not just heads and hands? Posture is the thing I'd use most."

**What changed.** A posture mode was added. It starts abstract on purpose — a single
sweeping line for the pose, then a simplified figure with blocks for the ribcage and hips
— before going anywhere near a finished drawing, which is the order a life-drawing class
teaches. It also measures the figure in head-heights as you go, and shows the shoulder and
hip tilts, which is the difference between a stiff figure and one that looks alive.

> "Drawing a box round a person is fiddly on a phone. I'd rather just tap the person I
> want."

**What changed.** The app finds the people in the photo and you tap one. No dragging.

> "When there are two people in the shot and they belong together, I want to pick both,
> and I want the app to treat them as one drawing — including the space between them."

**What changed.** You can tap more than one person. The app then works on a region that
spans everyone you picked plus the gap between them, so a pair who are interacting come
out as one composition rather than two separate drawings.

> "Going from the outline, or the flat grey version, straight to the realistic one is too
> big a jump. There's nothing showing me how I'm supposed to get from one to the other."

**What changed.** A shading stage was added between the flat tones and the finish. Instead
of the shading simply appearing, you now see it built from strokes that curve around the
arms, legs and body, with the darker areas made by crossing more layers of strokes rather
than pressing harder. The step-by-step instructions gained a matching step.

> "The hands and faces on the figures are just blobs."

**Left as is, deliberately.** At whole-body size a hand is a few dozen pixels across, and
detailing it there teaches the wrong habit. The step text now says so explicitly and
points you at the dedicated hands and portrait modes.

---

## Round 5 — portrait guide lines

*Shipped in: —*

> "On some photos the nose and mouth guide lines end up down on the neck."

**What changed.** When the app can't read the face clearly it falls back to standard
proportions, and those were taken from a textbook diagram of a skull — which sits higher
than a real photographed face. The fallback positions were re-measured against 26 real
portraits and corrected.

---

## Round 4 — object mode picks the wrong thing

*Shipped in: —*

> "If there's more than one thing in the photo it tries to draw all of it at once, and I
> have no way of telling it which object I actually meant."

**What changed.** You now drag a box around the object you want before it starts. On a set
of 25 still-life photos the automatic guess was unusable on about half of them. The box
starts out covering most of the photo, so a picture that already worked still works
without touching anything.

---

## Round 3 — hands mode quality on real photos

*Shipped in: —*

> "The guide circle on the contour style is way off the mark."

**What changed.** The guides are now built from the hand's actual joints rather than
estimated from its outline, so they sit on the hand and bend with it.

> "The construction style misses fingers. If part of a finger is slightly hidden it won't
> show any markers for that finger at all — it just ignores it."

**What changed.** This was the big one. The app used to work the hand's structure out from
its silhouette alone, which can't separate fingers held together and can't find a curled
finger at all, because there's no fingertip sticking out to find. It now uses proper hand
tracking that gives the wrist, the knuckles and all three joints of every finger, hidden
or not. Across 20 test photos it reads 19 — including a fist head-on, fingers wrapped
round a mug, a pinch, and a hand holding a pen. The one it can't read falls back to the
old method rather than guessing, because confidently wrong joints on the page are worse
for a learner than approximate ones.

> "The whole palm section of the construction looks off, and at a weird angle."

**What changed.** Same root cause, same fix — the palm block is now drawn from the real
knuckle and wrist positions.

> "The hatching shades the hand and the surface underneath it at the same time. It doesn't
> separate the two."

**What changed.** Shading is now confined to the hand, so a hand photographed on a table
comes back with the hand shaded and the table left as blank paper.

> "On the main page, why do the sample photos on the style buttons look so weird?"

**What changed.** They were generated from a drawn stand-in rather than a photograph, so
they looked nothing like what each style does to a real picture. They were regenerated
from a real hand photo.

---

## Round 2 — app won't start

*Shipped in: —*

> "The app doesn't run on my PC. It opens a blank white screen."

**What changed.** The new scrollable mode bar was wiping out a piece of drawing setup that
the rest of the screen depended on, so everything after it rendered invisibly. Fixed, and
a check was added that fails if it ever happens again.

**Worth recording for the write-up:** this was reported by the tester, not caught in
testing, and it should have been. Blank screenshots had come out of an automated run
beforehand and were written off as a quirk of running without a display. Comparing against
v1.0.0 under identical conditions settled it — the old build filled 73% of the screen, the
new one 1.5%. The automated check that existed at the time was actually asserting the
broken behaviour was correct, and had to be deleted.

---

## Round 1 — hands mode and the mode bar

*Shipped in: —*

> "I want more than faces and objects. Hands are the thing I give up on."

**What changed.** A hands mode was added, with its own styles, guides and step-by-step
sequence. The app was also reorganised underneath so that adding further subjects later
(legs, for instance) doesn't mean rebuilding any screens.

> "The row of mode buttons is all joined together as one bar. I'd rather they were
> separate buttons I can swipe left and right through by dragging — and I don't want a
> scrollbar taking up space."

**What changed.** Separate buttons, drag to scroll in either direction, no scrollbar. The
edges fade to show there's more off-screen.

---

## Still open

Known and not yet addressed. Worth listing in the write-up as acknowledged rather than
missed.

- **Portrait mode's circle on side profiles** is still scaled from the rough box, and on
  one strict profile in the tester's photos no face is found at all. The face's outline
  can't be read reliably from the side. Of the 15 measurable close-up faces, 5 still don't
  fit well, mostly heads tilted or turned well to one side.
- **Cartoon mode doesn't draw glasses**, outlines beards only beside the jaw, is weak on
  side profiles, and draws a hat as hair. A bald head is told from short light hair by
  how smooth it is, which was set on just two bald test photos.
- **Eye guides on side profiles** now take their size from the face, but how well that
  works on a profile couldn't be measured: in the tester's two profiles the iris is
  hidden by lids and lashes.
- **Eyes mode on close-ups of a single eye** (no face in the photo) still uses the old
  reading, which gets about half of the 19 test close-ups right by a strict measure. A
  bright reflection covering half the pupil, a black-and-white photo with the white of the
  eye in shadow, and an eye turned far to one side each throw off the construction steps,
  and on some it places the corners too far in. The new face-based reading can't help
  there: there's no face to take the eye's size from.
- **Eyes mode on face photos was tested on only ten eyes**, in eight photos, and places
  the iris less exactly than it sizes it (up to about half the iris's width off-centre).
- **Eyes mode doesn't draw the tear duct.** On photos with a face it now knows which
  corner is the inner one, but nothing draws it yet; on close-ups it can't tell, so the
  instructions describe it instead.
- **The nose wing correction was tuned on the same six face-on photos it was tested on.**
  More face-on photos would show whether it holds.
- **No visible credits screen.** The licence text for the face-tracking pieces (and the
  other open-source parts) ships inside the app, but nothing in the app shows it. An
  "About" or "Open-source licences" screen would be the tidy way to show it.
- **One hand photo can't be read at all** — a hand mostly out of frame gripping a phone.
  It falls back to the rougher method rather than failing, but the result is poor.
- **Dark backgrounds confuse posture mode's outline.** On one test photo of a figure
  against a black background, a patch of background above the raised arm gets shaded as if
  it were part of the person. One photo in six, and only where the background is close to
  black.
- **Never timed on a real phone.** Everything so far has been measured on a desktop.
