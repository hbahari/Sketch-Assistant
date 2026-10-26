"""Generate the labelled material example illustrations (assets/materials/*.png).  python scripts/make_material_examples.py"""
from pathlib import Path
import cv2
import numpy as np

W, H = 480, 320
OUT = Path(__file__).resolve().parent.parent / "sketch_assistant" / "assets" / "materials"
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
L = np.array([-0.55, 0.55, 0.63], np.float32); L /= np.linalg.norm(L)  # light: upper left, towards viewer
rng = np.random.default_rng(3)
smooth = lambda t: t * t * (3 - 2 * t)


def paper():
    return 246 - 14 * (yy / H) - 6 * rng.random((H, W)).astype(np.float32)


def geom(cx, cy, R):
    x, y = (xx - cx) / R, -(yy - cy) / R
    r2 = x * x + y * y
    return x, y, np.sqrt(np.clip(1 - r2, 0, 1)), r2 <= 1, np.sqrt(r2)


def cast_shadow(img, cx, cy, R, strength=0.6, power=0.7):
    d = ((xx - (cx + 1.0 * R)) / (1.7 * R)) ** 2 + ((yy - (cy + 0.97 * R)) / (0.36 * R)) ** 2
    a = np.clip(1 - d, 0, 1) ** power * (1 - 0.55 * np.clip((xx - cx) / (2.6 * R), 0, 1))
    return img * (1 - strength * a)


def finish(img, name, labels):
    out = cv2.cvtColor(np.clip(img, 0, 255).astype(np.uint8), cv2.COLOR_GRAY2BGR)
    for text, pt, tx, ty in labels:  # label, point on the object, text position
        cv2.line(out, (int(pt[0]), int(pt[1])), (int(tx - 4), int(ty - 4)), (70, 70, 70), 1, cv2.LINE_AA)
        cv2.circle(out, (int(pt[0]), int(pt[1])), 3, (60, 60, 200), -1, cv2.LINE_AA)
        cv2.putText(out, text, (int(tx), int(ty)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (50, 50, 50), 1, cv2.LINE_AA)
    cv2.imwrite(str(OUT / f"{name}.png"), out)


def matte():
    cx, cy, R = 150, 150, 95
    x, y, z, m, r = geom(cx, cy, R)
    ndl = x * L[0] + y * L[1] + z * L[2]
    I = 0.10 + 0.86 * np.clip(ndl, 0, 1) ** 0.9
    I += 0.13 * np.clip((r - 0.72) / 0.28, 0, 1) * (ndl < 0.2)  # reflected light on the shadow side
    img = cast_shadow(paper(), cx, cy, R, 0.62)
    img[m] = 255 * I[m]
    P = lambda a, b: (cx + a * R, cy - b * R)
    finish(img, "matte", [("highlight", P(-0.5, 0.5), 300, 45), ("mid-tone", P(0.0, 0.1), 300, 90),
                          ("core shadow", P(0.5, -0.35), 300, 135), ("reflected light", P(0.82, -0.5), 300, 180),
                          ("cast shadow", (cx + 1.5 * R, cy + 0.98 * R), 300, 290)])


def glossy():
    cx, cy, R = 150, 150, 95
    x, y, z, m, r = geom(cx, cy, R)
    Rx, Ry, Rz = 2 * z * x, 2 * z * y, 2 * z * z - 1
    el = Ry * np.cos(0.35) + Rz * np.sin(0.35)  # reflected elevation (tilted so the horizon curves)
    t = smooth(np.clip((el + 0.03) / 0.08, 0, 1))  # hard horizon between dark ground and bright sky
    I = (0.18 + 0.12 * np.clip(-el, 0, 1)) * (1 - t) + (0.93 - 0.30 * np.clip(el, 0, 1)) * t
    I[(el > 0.5) & (el < 0.68) & (Rx > -0.55) & (Rx < -0.1)] = 1.0  # window reflection
    I *= 1 - 0.40 * r ** 6
    I = np.where((Rx * L[0] + Ry * L[1] + Rz * L[2]) > 0.975, 1.0, I)  # sharp specular
    img = cast_shadow(paper(), cx, cy, R, 0.75, 0.45)
    img[m] = 255 * I[m]
    P = lambda a, b: (cx + a * R, cy - b * R)
    finish(img, "glossy", [("sharp highlight", P(-0.52, 0.5), 300, 45), ("bright sky reflection", P(0.1, 0.62), 300, 90),
                           ("hard horizon line", P(0.45, 0.02), 300, 135), ("dark ground reflection", P(0.1, -0.55), 300, 180),
                           ("crisp cast shadow", (cx + 1.5 * R, cy + 0.98 * R), 300, 290)])


def glass():
    cx, cy, R = 150, 150, 95
    x, y, z, m, r = geom(cx, cy, R)
    ndl = x * L[0] + y * L[1] + z * L[2]
    I = 0.90 - 0.62 * r ** 4 - 0.18 * np.clip(-ndl, 0, 1)  # dark edge, slightly darker on the shadow side
    I += 0.55 * np.exp(-(((x - 0.30) ** 2 + (y + 0.34) ** 2) / (2 * 0.20 ** 2)))  # caustic: bright spot opposite the light
    I = np.where(((x + 0.42) ** 2 / 0.05 + (y - 0.48) ** 2 / 0.012) < 1, 1.0, I)  # window highlight
    img = paper()
    sh = cast_shadow(img, cx, cy, R, 0.40, 0.8)
    sh += 70 * np.exp(-(((xx - (cx + 1.05 * R)) / (0.55 * R)) ** 2 + ((yy - (cy + 0.97 * R)) / (0.15 * R)) ** 2))  # light spot inside the shadow
    img = np.clip(sh, 0, 246)
    img[m] = 255 * np.clip(I, 0, 1)[m]
    P = lambda a, b: (cx + a * R, cy - b * R)
    finish(img, "glass", [("window highlight", P(-0.45, 0.48), 300, 45), ("dark, thick edge", P(0.9, 0.3), 300, 90),
                          ("bright caustic spot", P(0.3, -0.34), 300, 135), ("see-through", P(-0.1, -0.1), 300, 180), ("light spot in shadow", (cx + 1.05 * R, cy + 0.97 * R), 300, 290)])


def fabric():
    ph = lambda X, Y: 2 * np.pi * (X / W * 3.3 + 0.10 * np.sin(Y / H * 5 + X / 70))
    p = ph(xx, yy)
    amp = 0.55 + 0.45 * yy / H
    I = 0.62 + amp * 0.32 * np.cos(p - 0.6) - 0.14 * np.clip(-np.cos(p) - 0.45, 0, 1) - 0.12 * np.exp(-yy / 40)
    bottom = 268 + 10 * np.sin(ph(xx, 268))
    m = (xx > 36) & (xx < 320) & (yy > 16) & (yy < bottom)
    img = paper(); img[m] = 255 * np.clip(I, 0, 1)[m]
    xs = np.arange(50, 310)
    ridge = xs[np.argmax(I[100, 50:310])]; valley = xs[np.argmin(I[200, 50:310])]
    finish(img, "fabric", [("pinch point", (110, 24), 335, 40), ("ridge (light)", (ridge, 100), 335, 110),
                           ("valley (dark)", (valley, 200), 335, 200), ("soft edges", (250, 266), 335, 290)])


def wood():
    kx, ky = 230, 150
    d2 = ((xx - kx) / 50) ** 2 + ((yy - ky) / 18) ** 2
    noise = cv2.GaussianBlur(rng.standard_normal((H, W)).astype(np.float32), (0, 0), 30) * 90
    f = yy + 12 * np.sin(xx / 85 + 0.8) + noise * 0.25 + 40 * np.exp(-d2 / 2) * np.sign(yy - ky + 0.01)
    g = 0.55 * np.sin(2 * np.pi * f / 11) + 0.30 * np.sin(2 * np.pi * f / 4.6 + 1.0) + 0.15 * np.sin(2 * np.pi * f / 23)
    I = 0.72 - 0.30 * np.clip(g, 0, 1) ** 1.5 + 0.012 * rng.standard_normal((H, W)).astype(np.float32)
    I -= 0.28 * np.exp(-d2 * 3.5)
    img = paper(); m = (yy > 22) & (yy < 296) & (xx > 20) & (xx < 330)
    img[m] = 255 * np.clip(I, 0, 1)[m]
    cv2.rectangle(img, (20, 22), (330, 296), 60, 1)
    finish(img, "wood", [("grain direction", (90, 80), 345, 60), ("grain bends", (kx - 55, ky - 4), 345, 130),
                         ("knot (dark)", (kx, ky), 345, 200)])


for fn in (matte, glossy, glass, fabric, wood):
    fn()
print([p.name for p in OUT.iterdir()])
