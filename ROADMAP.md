# Roadmap

Agreed 25 Nov 2026. In order. Each item ships in its own version unless noted.

Phone status: tested by the owner and other testers on real phones, and it works well.
Generating guides takes a moment, which is expected and accepted.

## Done

- **First-launch walkthrough** (v1.9.0, version code 12). A six-step tour over the main
  page that lights up each control in turn: subject bar, photo, styles, guide and
  Settings. It shows once, on the first launch, and again from Settings → "Show the tour
  again". This closes tester report item 3.

## Next

1. **Pro unlock**, as soon as production access is granted. One-time purchase. Contour is
   free in every mode, and every other style shows a watermarked preview on the user's own
   photo with its steps locked. Full plan: `MONETIZATION_PLAN.md`.
2. **Translate the store listing.** Start with Spanish, Portuguese (Brazil), Hindi and
   Indonesian, the big "learn to draw" markets. This is listing text only (title, short and
   full description, screenshot captions), not the app. It can go out at any time, since
   it needs no build.
3. **Trace mode.** Show the sketch full-screen at full brightness with touches locked, so a
   sheet of paper can lie on the phone and the drawing be traced. Keep screen on already
   exists. A camera-overlay ("AR") version is a much bigger job and isn't planned.
4. **Printable worksheets.** A PDF of the steps sheet, sized for A4 or US Letter, with
   the grid, ready to print.
5. **Beginner course.** Short exercises before photos: lines, basic shapes, a shading
   scale, then a first eye. It reuses the existing drawing and step machinery; the work
   is mostly writing the lessons.
6. **Check my drawing.** Photograph the finished drawing; the app finds the face in it and
   compares it with the reference ("the eyes sit 8% too high, the jaw is too narrow").
   This is the headline feature for a 2.0. First, check whether the face finder works on
   pencil drawings at all, before promising anything.

## Probably not

Accounts, cloud sync and social sharing (they go against "nothing leaves your phone"),
subscriptions (a one-time unlock was chosen) and more cartoon polish ahead of the items
above.

## Watching

The app sends no analytics, so Play Console is the only source of data: installs, the
search terms that bring them (Acquisition reports), crashes and freezes (Android vitals),
and ratings. Check these after each release.
