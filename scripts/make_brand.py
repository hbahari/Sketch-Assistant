"""Build the app logo + icon from the source portrait.   python scripts/make_brand.py

Source artwork: sketch_assistant/assets/brand/source/portrait.png  (replace that file and re-run to swap the art).
Outputs to sketch_assistant/assets/brand/: icon.png (512), mark.png (256), logo.png (mark + wordmark), presplash.png
"""
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

BRAND = Path(__file__).resolve().parent.parent / "sketch_assistant" / "assets" / "brand"
SRC = BRAND / "source" / "portrait.png"
TILE, INK, AMBER = (255, 255, 255), (18, 18, 20), (240, 164, 32)
MARGIN = 0.07          # white space around the artwork, as a fraction of its longest side
# The pencil barrel, in source pixels: everything enclosed within PENCIL_NEAR of this axis is tinted amber.
PENCIL_AXIS = ((950, 630), (720, 1045))
PENCIL_NEAR, PENCIL_MAX_AREA = 35, 4000


def _near_axis(cx, cy):
    (ax, ay), (bx, by) = PENCIL_AXIS
    vx, vy = bx - ax, by - ay
    t = np.clip(((cx - ax) * vx + (cy - ay) * vy) / (vx * vx + vy * vy), 0, 1)
    return np.hypot(cx - (ax + t * vx), cy - (ay + t * vy))


def load_art():
    """Source -> crisp black-on-white RGB, with the pencil barrel tinted amber."""
    import cv2
    g = np.asarray(Image.open(SRC).convert("L"), dtype=np.float32)
    g = np.clip((g - 40) / (243 - 40), 0, 1) * 255                      # normalise: clean white, solid black
    g = g.astype(np.uint8)
    rgb = np.dstack([g] * 3)
    # enclosed white regions lying along the pencil axis = the barrel (the open background and the
    # big hair shapes are excluded by the area limit, so this survives small edits to the artwork)
    n, lab, stats, cent = cv2.connectedComponentsWithStats((g >= 150).astype(np.uint8), 4)
    sel = np.zeros(g.shape, bool)
    for i in range(1, n):
        if i == lab[0, 0] or stats[i, cv2.CC_STAT_AREA] > PENCIL_MAX_AREA:
            continue
        if _near_axis(*cent[i]) < PENCIL_NEAR:
            sel |= lab == i
    rgb[sel] = (np.array(AMBER) * (g[sel, None] / 255.0)).astype(np.uint8)   # keep the shading inside the barrel
    return Image.fromarray(rgb)


def square(img):
    """Trim to the artwork, add an even margin, pad out to a square."""
    a = np.asarray(img.convert("L"))
    ys, xs = np.where(a < 200)
    box = (xs.min(), ys.min(), xs.max() + 1, ys.max() + 1)
    art = img.crop(box)
    side = int(max(art.size) * (1 + 2 * MARGIN))
    out = Image.new("RGB", (side, side), TILE)
    out.paste(art, ((side - art.width) // 2, (side - art.height) // 2))
    return out


ART = square(load_art())


def mark(size=512, thicken=0):
    """Rounded tile with the artwork. `thicken` widens the lines so they survive small sizes."""
    big = size * 4
    art = ART.resize((big, big), Image.LANCZOS)
    if thicken:
        art = art.filter(ImageFilter.MinFilter(thicken))
    img = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    m = Image.new("L", (big, big), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, big - 1, big - 1), radius=int(big * .23), fill=255)
    img.paste(art.convert("RGBA"), (0, 0), m)
    return img.resize((size, size), Image.LANCZOS)


def wordmark(height):
    font = ImageFont.truetype("/usr/share/fonts/truetype/crosextra/Caladea-BoldItalic.ttf", int(height * .56) * 4)
    text = "Sketch Assistant"
    w = int(font.getlength(text)) + 40
    im = Image.new("RGBA", (w, height * 4), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((8, int(height * 4 * .17)), text, font=font, fill=INK + (255,))
    return im.resize((w // 4, height), Image.LANCZOS)


BRAND.mkdir(parents=True, exist_ok=True)
mark(512).save(BRAND / "icon.png")
mark(256, thicken=3).save(BRAND / "mark.png")
wm = wordmark(96)
logo = Image.new("RGBA", (96 + 14 + wm.width, 96), (0, 0, 0, 0))
logo.alpha_composite(mark(96, thicken=5), (0, 0))
logo.alpha_composite(wm, (96 + 14, 0))
logo.save(BRAND / "logo.png")
# Android adaptive icon: 432x432, art kept inside the inner 66% safe zone
fg = Image.new("RGBA", (432, 432), (0, 0, 0, 0))
art = ART.resize((284, 284), Image.LANCZOS).convert("RGBA")
art.putalpha(Image.fromarray(255 - np.asarray(ART.resize((284, 284), Image.LANCZOS).convert("L"))))
fg.alpha_composite(art, (74, 74))
fg.save(BRAND / "icon_fg.png")
Image.new("RGB", (432, 432), TILE).save(BRAND / "icon_bg.png")

# Play Store feature graphic (1024x500, required for the store listing)
fx = Image.new("RGB", (1024, 500), TILE)
fd = ImageDraw.Draw(fx)
fx.paste(ART.resize((430, 430), Image.LANCZOS), (40, 35))
_f = lambda sz, bold=True: ImageFont.truetype(
    "/usr/share/fonts/truetype/crosextra/Caladea-%s.ttf" % ("BoldItalic" if bold else "Regular"), sz)
fd.text((510, 178), "Sketch Assistant", font=_f(62), fill=INK)
fd.text((514, 260), "Turn any photo into a drawing guide", font=_f(30, False), fill=(70, 70, 74))
fd.rectangle((514, 322, 514 + 150, 322 + 7), fill=AMBER)
fx.save(BRAND / "feature_graphic.png")

ps = Image.new("RGB", (1024, 1024), TILE)
ps.paste(ART.resize((620, 620), Image.LANCZOS), (202, 202))
ps.save(BRAND / "presplash.png")
print("wrote", sorted(p.name for p in BRAND.iterdir() if p.is_file()))
