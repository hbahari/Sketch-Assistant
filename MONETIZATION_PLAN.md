# Monetization plan (Pro unlock)

Status: **planned, not built.** Agreed 18 Nov 2026. Build after production access
is granted. The payments profile is set up; we're waiting on Google's test deposit.

## Background

- The app was published as **free**. Google Play does not let a free app become
  paid, so we monetize with an **in-app purchase** inside the existing listing.
- No grandfathering is needed. The ~15 closed testers will get Pro features for free
  until the unlock ships, and the developer is fine with that.

## The split

Revised 19 Nov 2026. **Free:** one style per mode, the contour, with its full
step-by-step guide. Everything else is Pro. Tiles are listed in the order the app shows them.

| Mode     | Tiles (free in **bold**)                                              |
|----------|-----------------------------------------------------------------------|
| Portrait | **Line Art**, Technical, Value Study, Cross-Hatch, Photorealism       |
| Eyes     | Construction, **Contour**, Value Study, Cross-Hatch, Photorealism     |
| Nose     | Construction, **Contour**, Value Study, Cross-Hatch, Photorealism     |
| Hands    | Construction, **Contour**, Value Study, Cross-Hatch, Photorealism     |
| Posture  | Gesture, Mannequin, **Contour**, Value Study, Cross-Contour, Photorealism |
| Cartoon  | **Clean Lines**, Light Hatching                                       |
| Object   | Basic Shapes, **Contour**, Value Study, Cross-Hatch, Photorealism     |

How to pitch it: free shows you *what* to draw; Pro teaches you how to *build and
shade* it.

The free set is recorded in code as `styles.FREE`. A test checks that each mode has
exactly one free style and that it's the line style.

## Style order: the drawing flow

The tiles follow the order a drawing is built in: construction or gesture first, then
contour, then tone. This was set on 19 Nov 2026, after "free styles first" was tried and
taken back. Each mode opens on its first tile, so Eyes, Nose, Hands, Object and Posture
open on a style that will be Pro.

When Pro is built: for a user without Pro, open each mode on its **free style** (not the
first tile), and show the Pro tiles in place with the lock badge. Tapping a locked
construction tile showing the user's own photo, watermarked, is the strongest advert for
Pro the app has.

## Open question: is trace mode free or Pro?

Trace mode was added in v1.10.0. It isn't decided yet whether it stays free or goes
behind Pro. One option: tracing a free style (the contour) stays free, and tracing a Pro
style needs Pro, since the style itself is locked anyway. That needs no rule of its own.

## Pricing model

- **One-time "Pro unlock"** (a non-consumable in-app product), not a subscription.
  - The app is offline, with no servers and no recurring content, so a monthly fee
    tends to draw 1-star reviews.
  - It's the simplest Play Billing flow: no renewals, grace periods or account holds.
  - It works offline, because Play caches the purchase on the device. Restore
    purchases with `queryPurchasesAsync`.
- Suggested price: **USD 4.99–7.99**, priced locally per country in Play Console.
- A subscription can be added alongside the unlock later. Don't remove the unlock.

## Locked-style UX

- Don't just grey out Pro styles. Let the user **render a Pro style on their own
  photo as a preview**, with a small "Pro" watermark.
- Lock the **step-by-step guide** (and saving/exporting without the watermark)
  behind the purchase.
- Show a lock badge on Pro style pills. Tapping one renders the preview and an
  unlock button.
- **Restore purchase** already has a button on the Settings page (the gear, added in
  v1.7.0). It calls `purchases.restore()`, which for now says there's nothing to
  restore. The billing code replaces that function, and the page needs no change.

## Implementation notes (for when we build it)

- Use Google Play Billing Library from Kivy via **pyjnius**, adding the
  `com.android.billingclient:billing` gradle dependency in `buildozer.spec`.
- Product ID: e.g. `pro_unlock`. Create it under **Monetize → Products → In-app
  products**. That page unlocks only after a build containing the Billing library
  is uploaded, and an internal or closed track is enough for this.
- Acknowledge purchases within 3 days, or Play refunds them automatically.
- Billing code lives in `sketch_assistant/purchases.py`. Lock the styles that
  aren't in `styles.FREE`.
- Keep a local "is Pro" flag, refreshed from Play on each launch. The app must
  never need the internet to draw.
- Test with license testers in Play Console, using test cards so no real charges
  happen.
- Desktop and dev builds: treat as Pro, or use an env var to toggle.
- Update PLAY_LISTING.md ("Contains in-app purchases"), PRIVACY_POLICY.md (Play
  handles payment; the app still sends nothing itself), README and
  TESTER_COMMENTS.md.
