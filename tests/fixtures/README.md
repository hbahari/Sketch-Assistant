# Test fixtures

Real photographs, downscaled to 520px on the long side (~150 KB in total).

They exist because the hand pipeline cannot be tested on synthetic shapes. An earlier
version worked the hand out from its silhouette, passed every synthetic case, and then
lost whole fingers on real photographs. Synthetic hands have splayed fingers, clean edges
and no background; real ones are held together, curled, wrapped round objects, and sit on
wooden tables.

| File | Why it is here |
|---|---|
| `hand.jpg` | a hand on a wooden table: an ordinary cluttered background |
| `pen_signing.jpg` | writing on a sheet of paper: the hand is partly occluded, and the paper is what a naive segmentation grabs instead of the hand |
| `mug_grip.jpg` | fingers wrapped round a mug: most of them hidden, and a second object touching the hand |
| `mug_handle.jpg` | a pinch grip on a handle, with only the fingertips in contact |
| `fist.jpg` | a fist head-on: no fingers visible in the outline at all |
| `ok_sign.jpg` | thumb and forefinger touching, which closes a loop in the outline |
| `open_palm.jpg` | the easy case, as a control |
| `cupped_dark.jpg` | darker skin, so a lighting or contrast assumption fails loudly |
| `phone_grip.jpg` | holding a phone, the hand running off the edge of the frame |

Each of the middle rows broke an earlier version of this code.
