"""The silhouette fallback, checked against synthetic hands whose anatomy we know.

This exercises `_from_silhouette`, which is what runs when the ONNX landmark models are
not installed. It draws hands itself -- a palm polygon plus tapering fingers at known
positions -- and asks the fallback to find them back.

Passing here is necessary but a long way from sufficient, and it is worth saying why: an
earlier version of this file was the *only* test of the hand pipeline, it passed every
case, and the code still lost whole fingers on real photographs. Synthetic hands have
splayed fingers and clean edges; real ones are held together, curl, and sit on textured
backgrounds. `tests/test_handpose.py` covers the real path on a real photo.
"""
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from sketch_assistant.core import hands  # noqa: E402
from sketch_assistant.core.hands import _from_silhouette  # noqa: E402

SIZE = 520


def draw_hand(spread=1.0, angle=0.0, folded=(), scale=1.0, flip=False):
    """An open hand: palm quad, four fingers off the knuckle arc, thumb off the side."""
    img = np.full((SIZE, SIZE, 3), 240, np.uint8)
    cx, cy = SIZE / 2, SIZE * 0.62
    pr = SIZE * 0.14 * scale
    layers = []

    # palm: slightly fan-shaped, wider at the knuckles than at the wrist
    palm = np.array([[-1.05, 0.55], [1.05, 0.55], [1.25, -0.75], [-1.25, -0.75]]) * pr
    layers.append((palm, int(pr * 0.5)))

    # four fingers, rooted on the knuckle arc, lengths as in a real hand
    for i, (dx, length, lean) in enumerate([(-0.92, 1.70, -0.20), (-0.31, 1.95, -0.06),
                                            (0.31, 1.85, 0.07), (0.92, 1.45, 0.22)]):
        if i in folded:
            length *= 0.42
        base = np.array([dx * pr * 1.15, -0.70 * pr])
        tip = base + np.array([lean * spread * pr * 1.5, -length * pr])
        layers.append((np.array([base, tip]), int(pr * 0.30)))

    # thumb: off the side of the palm, shorter and at a wide angle
    layers.append((np.array([[-1.0 * pr, 0.30 * pr], [-2.0 * pr * spread, -0.55 * pr]]), int(pr * 0.36)))
    # the forearm runs off the bottom of the frame, as it does in any photo of a hand --
    # which is what lets the wrist be found from the silhouette's contact with the border
    layers.append((np.array([[-0.62 * pr, 0.55 * pr], [-0.62 * pr, 4.0 * pr],
                             [0.62 * pr, 4.0 * pr], [0.62 * pr, 0.55 * pr]]), int(pr * 0.4)))

    rot = np.deg2rad(angle)
    R = np.array([[np.cos(rot), -np.sin(rot)], [np.sin(rot), np.cos(rot)]])
    for pts, th in layers:
        p = pts @ R.T + (cx, cy)
        if flip:
            p[:, 0] = SIZE - p[:, 0]
        p = p.astype(np.int32)
        if len(p) > 2:
            cv2.fillPoly(img, [p], (60, 60, 60))
        cv2.polylines(img, [p], False, (60, 60, 60), th * 2, cv2.LINE_AA)
        for q in p:
            cv2.circle(img, tuple(q), th, (60, 60, 60), -1, cv2.LINE_AA)
    return img


def _contour(img):
    """Exact silhouette of the drawing, so the test checks hands.py and not GrabCut."""
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    cs, _ = cv2.findContours((g < 150).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    return max(cs, key=cv2.contourArea)


def _dist_along_wrist_axis(p, h):
    """How far `p` lies toward the wrist, as a fraction of the palm-to-wrist distance.
    Every digit sits on the finger side of the palm; the forearm does not."""
    u = np.array(h.wrist, float) - np.array(h.palm, float)
    n = float(np.linalg.norm(u)) or 1.0
    return float(np.dot(np.array(p, float) - np.array(h.palm, float), u / n)) / n


def check(name, img, want_min_tips=4):
    h = _from_silhouette(img, _contour(img))
    assert h is not None, f"{name}: no hand found"
    mask = np.zeros(img.shape[:2], np.uint8)
    cv2.drawContours(mask, [_contour(img)], -1, 255, -1)
    px, py = int(h.palm[0]), int(h.palm[1])
    assert mask[py, px] == 255, f"{name}: palm centre fell outside the hand"
    assert want_min_tips <= len(h.tips) <= 5, f"{name}: found {len(h.tips)} tips"
    # every finger axis must point away from the palm and have real length
    for base, tip in h.fingers:
        assert hands._dist(base, tip) > h.palm_r * 0.2, f"{name}: zero-length finger axis"
        assert hands._dist(tip, h.palm) > hands._dist(base, h.palm) * 0.95, \
            f"{name}: finger axis points back into the palm"
    assert hands._dist(h.wrist, h.palm) > h.palm_r * 0.5, f"{name}: wrist sits on the palm"
    assert len(h.knuckles) == len(h.tips), f"{name}: knuckle arc has {len(h.knuckles)} points"

    # no "finger" may be the forearm: the two corners where the arm crosses the frame
    # reach as far from the palm as a thumb does, and are the easiest thing to mistake
    for t in h.tips:
        assert _dist_along_wrist_axis(t, h) < 0.85, f"{name}: a tip lies past the wrist"

    # the palm must sit between the wrist and the fingers, not down the arm -- a forearm
    # as wide as the palm can otherwise win the largest-inscribed-circle contest
    fc = np.mean(np.array(h.tips), axis=0)
    assert hands._dist(h.palm, fc) < hands._dist(h.wrist, fc), f"{name}: palm is behind the wrist"

    # knuckles must spread around the palm, not collapse onto one point: when they
    # collapse the finger axes fan from a single spot and the drawing is useless
    bases = [b for b, _ in h.fingers]
    spread = max(hands._dist(a, b) for a in bases for b in bases)
    # 0.5 rather than something tighter: with the fingers held together the bases really
    # are close, and the failure this guards against is total collapse onto one point
    assert spread > h.palm_r * 0.5, f"{name}: finger bases collapsed (spread {spread:.0f})"
    for b in bases:                      # each base sits on the palm's edge, not inside it
        assert 0.5 < hands._dist(b, h.palm) / h.palm_r < 2.0, f"{name}: base off the palm edge"

    print(f"  ok  {name:<34} tips={len(h.tips)} valleys={len(h.valleys)} palm_r={h.palm_r:.0f}")
    return h


def main():
    print("silhouette fallback: hand structure from the outline alone")
    cases = [
        # expected tip counts are lower than five for some poses on purpose: this is the
        # degraded path, and an outline genuinely does not separate fingers held together
        ("open hand", dict(), 5),
        ("fingers together", dict(spread=0.35), 4),
        ("fingers spread wide", dict(spread=1.6), 4),
        ("rotated 25 deg", dict(angle=25), 5),
        ("rotated -30 deg", dict(angle=-30), 5),
        ("mirrored (left hand)", dict(flip=True), 5),
        ("small in frame", dict(scale=0.62), 4),
        ("large in frame", dict(scale=1.25), 5),
        ("one finger folded", dict(folded=(1,)), 4),
        ("two fingers folded", dict(folded=(1, 2)), 3),
        # the thumb runs off the side of the frame as well as the arm off the bottom, so
        # two separate stretches of silhouette touch the border and the wider one wins
        ("thumb clipped by the frame", dict(spread=2.1), 4),
    ]
    for name, kw, want in cases:
        check(name, draw_hand(**kw), want)

    print("\nshapes that are not hands must be rejected")
    for name, img in (
        ("plain circle", cv2.circle(np.full((SIZE, SIZE, 3), 240, np.uint8),
                                    (SIZE // 2, SIZE // 2), SIZE // 4, (60, 60, 60), -1)),
        ("plain square", cv2.rectangle(np.full((SIZE, SIZE, 3), 240, np.uint8),
                                       (120, 120), (400, 400), (60, 60, 60), -1)),
        ("empty frame", np.full((SIZE, SIZE, 3), 240, np.uint8)),
    ):
        try:
            c = _contour(img)
        except ValueError:
            print(f"  ok  {name:<34} no silhouette at all")
            continue
        h = _from_silhouette(img, c)
        assert h is None, f"{name}: wrongly reported a hand"
        print(f"  ok  {name:<34} rejected")
    print("\nall hand-structure checks passed")


def test_silhouette_fallback():
    """Entry point so this runs under pytest in CI as well as standalone."""
    main()


if __name__ == "__main__":
    main()
