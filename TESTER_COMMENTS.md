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

- **One hand photo can't be read at all** — a hand mostly out of frame gripping a phone.
  It falls back to the rougher method rather than failing, but the result is poor.
- **Dark backgrounds confuse posture mode's outline.** On one test photo of a figure
  against a black background, a patch of background above the raised arm gets shaded as if
  it were part of the person. One photo in six, and only where the background is close to
  black.
- **Never timed on a real phone.** Everything so far has been measured on a desktop.
