"""Compose the Play listing screenshots from captures made by capture_listing.py.

    python scripts/make_listing_assets.py PHONE_CAPS TABLET7_CAPS TABLET10_CAPS OUT_DIR

Each screenshot is a real screen from the app, framed in a plain device outline under a
short caption. Google asks for little text on screenshots, so it's one headline and one
line under it. Writes OUT_DIR/phone/*.png (1080x1920), OUT_DIR/tablet7/*.png (1080x1920),
OUT_DIR/tablet10/*.png (1440x2560) and OUT_DIR/feature_graphic.png (1024x500). Play wants
tablet screenshots at exactly 9:16 and at least 1080 px a side; the tablet screens inside
are captured at tablet shapes and fitted into that frame.
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

BG = (246, 245, 242)
INK = (23, 23, 26)
MUTED = (100, 98, 96)
AMBER = (240, 163, 33)
SERIF_BI = "/usr/share/fonts/truetype/crosextra/Caladea-BoldItalic.ttf"     # the logo's face
SANS = "/usr/share/fonts/truetype/google-fonts/ofl/montserrat/Montserrat[wght].ttf"

# (file name, capture, headline, line under it). Order is the listing order.
PHONE = [
    ("01_photo_to_lesson", "90_portrait_home_photoreal", "Turn any photo into\na drawing lesson",
     "From a photo to a pencil study you can learn to draw"),
    ("02_realistic_guides", "90_portrait_guide_photoreal", "Draw realistic\nportraits",
     "Proportion lines over a graphite study, to measure as you go"),
    ("03_shading_steps", "90_portrait_photoreal_step12", "Learn shading\nstep by step",
     "Twelve stages, from the first line to a finished portrait"),
    ("04_cross_hatching", "90_portrait_guide_crosshatch_clean", "Master\ncross-hatching",
     "Tone built from layered strokes, with the pencils to use"),
    ("05_eyes", "91_eyes_guide_eye_realistic_clean", "Draw realistic eyes",
     "Iris fibres, highlights and lashes, one step at a time"),
    ("06_hands", "92_hands_guide_hand_realistic_clean", "Draw realistic hands",
     "Worked out from your photo joint by joint, then shaded"),
    ("07_figure", "93_posture_guide_body_formhatch", "Figure drawing,\nlife-class style",
     "Shading that wraps around the body, measured in heads"),
    ("08_cartoon", "61_cartoon_lines", "Or cartoon\nany portrait",
     "Clean lines, expressive eyes, and a caricature slider"),
]
# Tablets take up to 8 too: the same story, with the nose and the construction steps
TABLET = [PHONE[0], PHONE[1], PHONE[2], PHONE[4],
          ("05_nose", "94_nose_guide_nose_realistic_clean", "Draw a convincing nose",
           "Planes and shadows, built up to a finished study"),
          PHONE[5], PHONE[6], PHONE[7]]


def font(path, size, weight=None):
    f = ImageFont.truetype(path, size)
    if weight is not None:
        try:
            f.set_variation_by_axes([weight])
        except Exception:
            pass
    return f


def rounded(im, r):
    mask = Image.new("L", im.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, im.width - 1, im.height - 1), r, fill=255)
    out = Image.new("RGBA", im.size)
    out.paste(im, (0, 0), mask)
    return out


def compose(cap, W, H, head, sub):
    """Caption on top, the screen in a slim dark device frame below it, on the app's paper."""
    k = W / 1080                                   # sizes below are for a 1080-wide canvas
    canvas = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(canvas)
    hf, sf = font(SERIF_BI, int(84 * k)), font(SANS, int(36 * k), 500)
    lines = head.split("\n")
    # The caption band is the same height whatever the headline, so every device frame in
    # the set sits at the same height and size: a one-line headline is centred in the room
    # for two.
    y = int(110 * k) + (int(49 * k) if len(lines) == 1 else 0)
    d.rounded_rectangle((W / 2 - 50 * k, y, W / 2 + 50 * k, y + 10 * k), 5 * k, fill=AMBER)
    y += int(46 * k)
    for line in lines:
        w = d.textlength(line, font=hf)
        d.text(((W - w) / 2, y), line, font=hf, fill=INK)
        y += int(98 * k)
    y = int(110 * k) + int(46 * k) + 2 * int(98 * k) + int(26 * k)
    w = d.textlength(sub, font=sf)
    if w > W - 120 * k:                            # never let the line run off the edge
        sf = font(SANS, int(36 * k * (W - 120 * k) / w), 500)
        w = d.textlength(sub, font=sf)
    d.text(((W - w) / 2, y), sub, font=sf, fill=MUTED)
    top = y + int(80 * k)

    screen = Image.open(cap).convert("RGB")
    bezel, rad = int(16 * k), int(64 * k)
    avail_h = H - top - int(60 * k)
    sh = avail_h - 2 * bezel
    sw = int(sh * screen.width / screen.height)
    if sw > W * 0.8:
        sw = int(W * 0.8)
        sh = int(sw * screen.height / screen.width)
    screen = screen.resize((sw, sh), Image.LANCZOS)
    fw, fh = sw + 2 * bezel, sh + 2 * bezel
    fx, fy = (W - fw) // 2, top
    shadow = Image.new("L", (W, H), 0)
    ImageDraw.Draw(shadow).rounded_rectangle((fx, fy + 18 * k, fx + fw, fy + fh + 18 * k), rad, fill=70)
    shadow = shadow.filter(ImageFilter.GaussianBlur(28 * k))
    canvas.paste(Image.new("RGB", (W, H), (0, 0, 0)), (0, 0), shadow)
    d = ImageDraw.Draw(canvas)
    d.rounded_rectangle((fx, fy, fx + fw, fy + fh), rad, fill=INK)
    canvas.paste(rounded(screen, rad - bezel), (fx + bezel, fy + bezel), rounded(screen, rad - bezel))
    return canvas


def feature_graphic(src, out):
    """The existing feature graphic's drawing, with a tagline that carries the search words."""
    im = Image.open(src).convert("RGB")
    d = ImageDraw.Draw(im)
    d.rectangle((470, 150, 1024, 360), fill=(255, 255, 255))
    d.text((500, 182), "Sketch Assistant", font=font(SERIF_BI, 57), fill=INK)
    sf = font("/usr/share/fonts/truetype/crosextra/Caladea-Regular.ttf", 28)
    d.text((504, 258), "Learn to draw from any photo,", font=sf, fill=(70, 70, 74))
    d.text((504, 292), "step by step", font=sf, fill=(70, 70, 74))
    d.rectangle((504, 340, 645, 348), fill=AMBER)
    im.save(out)


def main(phone, t7, t10, out):
    out = Path(out)
    for sub, caps, (W, H), items in (("phone", phone, (1080, 1920), PHONE),
                                     ("tablet7", t7, (1080, 1920), TABLET),
                                     ("tablet10", t10, (1440, 2560), TABLET)):
        (out / sub).mkdir(parents=True, exist_ok=True)
        for i, (name, cap, head, line) in enumerate(items, 1):
            img = compose(Path(caps) / f"{cap}.png", W, H, head, line)
            img.save(out / sub / f"{i:02d}_{name.split('_', 1)[1]}.png", optimize=True)
            print(sub, name)
    brand = Path(__file__).resolve().parent.parent / "sketch_assistant" / "assets" / "brand"
    feature_graphic(brand / "feature_graphic.png", out / "feature_graphic.png")


if __name__ == "__main__":
    main(*sys.argv[1:5])
