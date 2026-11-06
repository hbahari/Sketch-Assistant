"""Regenerate the style-button thumbnails.

    python scripts/make_examples.py portrait.jpg object.jpg [hand.jpg] [body.jpg]

Every style in every mode gets one 360x360 tile. The hand reference is optional: without
it a shaded synthetic hand stands in, so the tiles are never blank. Replace it with a real
photo of a hand on a plain background whenever one is to hand -- the tiles are the first
thing anyone sees of a style.

The committed Posture tiles were made from `tests/fixtures/bodies/kneeling.jpg` cropped to
`union_box(detect(...), margin=0.08)`. Recorded because the reference photos for the other
modes do not live in the repo, so a single stale tile is otherwise impossible to redo
without reframing the whole set.
"""
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from sketch_assistant.core.faces import crop_face, detect_faces, load_image  # noqa: E402
from sketch_assistant.core.modes import MODES  # noqa: E402
from sketch_assistant.core.styles import render  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "sketch_assistant" / "assets" / "examples"


def synthetic_hand(size=560):
    """A lit, shaded hand, for when no photo is supplied.

    Flat silhouettes are useless as thumbnails -- Value Study and Photorealism would both
    come out as a black blob -- so the mass is shaded with a directional gradient plus a
    soft falloff from the outline, which reads as rounded fingers.
    """
    mask = np.zeros((size, size), np.uint8)
    cx, cy, pr = size / 2, size * 0.60, size * 0.145
    parts = [(np.array([[-1.05, .55], [1.05, .55], [1.25, -.75], [-1.25, -.75]]) * pr, pr * .5)]
    for dx, ln, lean in ((-.92, 1.70, -.20), (-.31, 1.95, -.06), (.31, 1.85, .07), (.92, 1.45, .22)):
        base = np.array([dx * pr * 1.15, -.70 * pr])
        parts.append((np.array([base, base + [lean * pr * 1.5, -ln * pr]]), pr * .30))
    parts.append((np.array([[-1.0 * pr, .30 * pr], [-2.0 * pr, -.55 * pr]]), pr * .36))
    # the forearm leaves the frame, as it does in a real photo
    parts.append((np.array([[-.62 * pr, .55 * pr], [-.62 * pr, 4.0 * pr],
                            [.62 * pr, 4.0 * pr], [.62 * pr, .55 * pr]]), pr * .4))
    for pts, th in parts:
        p = (pts + (cx, cy)).astype(np.int32)
        if len(p) > 2:
            cv2.fillPoly(mask, [p], 255)
        cv2.polylines(mask, [p], False, 255, int(th * 2), cv2.LINE_AA)
        for q in p:
            cv2.circle(mask, tuple(q), int(th), 255, -1, cv2.LINE_AA)

    # round the form: bright where the light falls, darker toward the outline and the palm
    dt = cv2.distanceTransform(mask, cv2.DIST_L2, 5)
    dt = cv2.normalize(dt, None, 0, 1, cv2.NORM_MINMAX)
    ys, xs = np.mgrid[0:size, 0:size].astype(np.float32) / size
    light = 1.0 - 0.45 * (xs * 0.7 + ys * 0.3)              # light from the upper left
    tone = np.clip(118 + 150 * light * (0.35 + 0.65 * np.sqrt(dt)), 0, 255)
    bg = np.clip(232 - 26 * ys, 0, 255)                      # a plain, slightly graded wall
    g = np.where(mask > 0, tone, bg).astype(np.float32)
    g = cv2.GaussianBlur(g, (0, 0), 1.2)
    g += np.random.default_rng(0).normal(0, 2.0, g.shape)
    return cv2.cvtColor(np.clip(g, 0, 255).astype(np.uint8), cv2.COLOR_GRAY2BGR)


def tile(src, key, fit=False):
    """Render one style and save a 360x360 thumbnail.

    `fit` letterboxes instead of cropping to a centre square. A standing figure is far
    taller than it is wide, so a centre crop of one shows a midriff and nothing else --
    the tile has to show the whole pose to mean anything.
    """
    sk = render(key, src)
    h, w = sk.shape[:2]
    if fit:
        scale = 360 / max(h, w)
        small = cv2.resize(sk, (max(1, int(w * scale)), max(1, int(h * scale))),
                           interpolation=cv2.INTER_AREA)
        sq = np.full((360, 360, 3), 255, np.uint8)
        y0, x0 = (360 - small.shape[0]) // 2, (360 - small.shape[1]) // 2
        sq[y0:y0 + small.shape[0], x0:x0 + small.shape[1]] = small
    else:
        s = min(h, w)
        crop = sk[(h - s) // 2:(h + s) // 2, (w - s) // 2:(w + s) // 2]
        sq = cv2.resize(crop, (360, 360), interpolation=cv2.INTER_AREA)
    cv2.imwrite(str(OUT / f"{key}.png"), sq)


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    full = load_image(sys.argv[1])
    faces = detect_faces(full)
    if not faces:
        sys.exit(f"No face found in {sys.argv[1]} -- the portrait tiles need one.")
    sources = {
        "portrait": crop_face(full, faces[0]),
        "object": load_image(sys.argv[2]),
        "hands": load_image(sys.argv[3]) if len(sys.argv) > 3 else synthetic_hand(),
        "body": load_image(sys.argv[4]) if len(sys.argv) > 4 else None,
    }
    if len(sys.argv) <= 3:
        print("note: no hand photo given, using the synthetic stand-in for the Hands tiles")
    if len(sys.argv) <= 4:
        print("note: no figure photo given, so the Posture tiles were skipped")
    for mode, m in MODES.items():
        src = sources.get(mode)
        if src is None:
            print(f"warning: no reference image for mode '{mode}', its tiles were skipped")
            continue
        for key in m.styles:
            tile(src, key, fit=(mode == "body"))
            print(f"  {key}")
    print("wrote", len(list(OUT.glob('*.png'))), "thumbnails to", OUT)


if __name__ == "__main__":
    main()
