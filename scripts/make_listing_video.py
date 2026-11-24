"""The Play listing's walkthrough video, built from the real screens capture_listing.py took.

    python scripts/make_listing_video.py CAPTURE_DIR OUT.mp4 [--frames DIR]

1920x1080, 30 fps. A guided tour: a caption on the left says what you're doing and why,
the phone on the right shows the app doing it, and an amber ring marks every tap. Each
scene is encoded to its own file (any crossfade into it is inside that file) and the files
are joined without re-encoding. --frames writes a few full-size stills instead, to check
the layout before a full render.
"""
import json
import math
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, FPS = 1920, 1080, 30
BG = (246, 245, 242)
INK = (23, 23, 26)
MUTED = (100, 98, 96)
AMBER = (240, 163, 33)
SERIF_BI = "/usr/share/fonts/truetype/crosextra/Caladea-BoldItalic.ttf"
SERIF = "/usr/share/fonts/truetype/crosextra/Caladea-Regular.ttf"
SANS = "/usr/share/fonts/truetype/google-fonts/ofl/montserrat/Montserrat[wght].ttf"
BRAND = Path(__file__).resolve().parent.parent / "sketch_assistant" / "assets" / "brand"

SCREEN_H = 940                       # the phone's screen, in video pixels
BEZEL, RADIUS = 14, 56
PHONE_CX = 1390
CHAPTERS = ["Photo", "Style", "Guide", "Steps", "Eyes", "Nose", "Hands", "Posture", "Cartoon", "Objects"]
ORDER = {"home": 0, "guide": 1, "steps": 2, "settings": 1, "text": 2}


def font(path, size, weight=None):
    f = ImageFont.truetype(path, size)
    if weight is not None:
        try:
            f.set_variation_by_axes([weight])
        except Exception:
            pass
    return f


F_LABEL, F_HEAD, F_BODY = font(SANS, 26, 700), font(SERIF_BI, 76), font(SANS, 34, 450)
F_CHAP = font(SANS, 18, 600)

# Each scene: chapter index, label, headline, body, and its shots. A shot is
# (capture name, hold seconds) plus optional {"tap": False} to suppress the tap ring.
SCENES = [
    (0, "STEP 1", "Add a photo", "Take one, or choose one from your gallery. The app finds the face for you.",
     [("00_home_empty", 1.6), ("10_portrait_found", 1.6, {"tap_from": "00_home_empty"}), ("11_portrait_line_art", 1.6)]),
    (1, "STEP 2", "Pick a style", "Clean line art, construction lines, values, cross-hatching or full realism.",
     [("11_portrait_line_art", 0.6, {"tap": False}), ("12_portrait_technical", 1.0), ("12_portrait_value_study", 1.0),
      ("12_portrait_crosshatch", 1.0), ("12_portrait_photoreal", 1.0), ("13_portrait_technical_again", 1.2)]),
    (2, "STEP 3", "Open the drawing guide", "Proportion lines you can measure on paper, and a slider for more or less detail.",
     [("14_guide_technical", 2.0), ("15_guide_detail_15", 1.2), ("15_guide_detail_90", 1.2), ("15_guide_detail_50", 1.4)]),
    (3, "STEP 4", "Draw it step by step", "Every step says which pencil to pick up, the technique, and what to put on the paper.",
     [("17_portrait_step01", 1.5)] + [(f"17_portrait_step{i:02d}", 1.05) for i in range(2, 8)] + [("17_portrait_step08", 1.8)]),
    (4, "EYES", "Draw realistic eyes", "A mode of its own: from the first line to the lashes, one step at a time.",
     [("20_eyes_box", 1.6, {"tap_self": True}), ("21_eyes_guide", 1.3)] + [(f"22_eyes_step{i:02d}", 0.85) for i in range(1, 8)]),
    (5, "NOSE", "A nose that looks solid", "Found and framed for you, built from simple planes, then shaded.",
     [("30_nose_box", 1.4, {"tap_self": True}), ("31_nose_guide", 1.2)] +
     [(f"32_nose_step{i:02d}", 0.85) for i in (1, 2, 3, 5, 6, 7)]),
    (6, "HANDS", "Hands, made simple", "The palm, the knuckles and every joint, worked out from your photo.",
     [("41_hands_construct", 1.4, {"tap_self": True}), ("41_hands_contour", 1.0), ("42_hands_guide", 1.3, {"from_tile": "construct"})] +
     [(f"43_hands_step{i:02d}", 0.9) for i in range(1, 6)]),
    (7, "POSTURE", "Figure drawing, life-class style", "Tap one person or several. Line of action, the mannequin, then the outline.",
     [("50_posture_gesture", 1.3, {"tap_self": True}), ("50_posture_gesture_both", 1.2), ("51_posture_body_mannequin", 1.2),
      ("52_posture_guide", 1.2)] + [(f"53_posture_step{i:02d}", 0.85) for i in range(1, 7)]),
    (8, "CARTOON", "Cartoon any portrait", "Clean lines and expressive eyes. Slide further and it becomes a caricature.",
     [("60_cartoon_found", 1.3, {"tap_self": True}), ("61_cartoon_lines", 1.3), ("62_cartoon_hatch", 1.1),
      ("63_cartoon_exaggerate_00", 1.2, {"tap": False}), ("63_cartoon_exaggerate_35", 1.1), ("63_cartoon_exaggerate_80", 1.4)] +
     [(f"64_cartoon_step{i:02d}", 0.85) for i in (1, 2, 4, 5, 7, 8)]),
    (9, "OBJECTS", "Still life, and how to shade it", "Drag a box round an object. Then learn how matte, glossy, glass, fabric and wood take the light.",
     [("70_object_box", 1.4, {"tap_self": True}), ("71_object_contour", 1.2), ("72_object_guide", 1.3, {"tap": False}),
      ("73_object_materials", 2.6, {"tap": False})]),
]
FADE, SLIDE, TAP_LEAD, INTRO, OUTRO = 0.28, 0.38, 0.55, 3.6, 4.6


def ease(t):
    return 0.5 - 0.5 * math.cos(math.pi * max(0.0, min(1.0, t)))


def rounded_mask(size, r):
    m = Image.new("L", size, 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, size[0] - 1, size[1] - 1), r, fill=255)
    return m


class Stage:
    """Everything that doesn't change from frame to frame: the phone frame and its shadow."""

    def __init__(self, caps, meta):
        self.caps, self.meta = caps, meta
        cw, ch = meta["size"]
        self.k = SCREEN_H / ch
        self.sw, self.sh = round(cw * self.k), SCREEN_H
        self.fw, self.fh = self.sw + 2 * BEZEL, self.sh + 2 * BEZEL
        self.fx, self.fy = PHONE_CX - self.fw // 2, (H - self.fh) // 2 - 18
        self.sx, self.sy = self.fx + BEZEL, self.fy + BEZEL
        self.mask = rounded_mask((self.sw, self.sh), RADIUS - BEZEL)
        base = Image.new("RGB", (W, H), BG)
        sh = Image.new("L", (W, H), 0)
        ImageDraw.Draw(sh).rounded_rectangle((self.fx, self.fy + 20, self.fx + self.fw, self.fy + self.fh + 20), RADIUS, fill=80)
        base.paste((0, 0, 0), (0, 0), sh.filter(ImageFilter.GaussianBlur(30)))
        ImageDraw.Draw(base).rounded_rectangle((self.fx, self.fy, self.fx + self.fw, self.fy + self.fh), RADIUS, fill=INK)
        self.base = base
        self._cache = {}

    def screen(self, name):
        if name not in self._cache:
            self._cache[name] = Image.open(self.caps / f"{name}.png").convert("RGB").resize((self.sw, self.sh), Image.LANCZOS)
        return self._cache[name]

    def tap_xy(self, name):
        t = self.meta["shots"].get(name, {}).get("tap")
        return None if t is None else (self.sx + t[0] * self.k, self.sy + t[1] * self.k)


def caption_layer(scene_idx):
    """The left-hand text and the chapter bar for one scene, on a transparent layer."""
    chap, label, head, body = SCENES[scene_idx][:4]
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    x, y = 150, 300
    d.rounded_rectangle((x, y, x + 70, y + 9), 4, fill=AMBER)
    d.text((x, y + 34), label, font=F_LABEL, fill=AMBER)
    y += 84
    for line in wrap(d, head, F_HEAD, 820):
        d.text((x, y), line, font=F_HEAD, fill=INK)
        y += 88
    y += 18
    for line in wrap(d, body, F_BODY, 760):
        d.text((x, y), line, font=F_BODY, fill=MUTED)
        y += 50
    chapter_bar(d, chap)
    return im


def chapter_bar(d, current):
    """The tour's chapters along the bottom, the current one filled in; two rows if needed."""
    x0, x1, y = 150, 1080, H - 130
    x = x0
    for i, name in enumerate(CHAPTERS):
        w = d.textlength(name, font=F_CHAP) + 26
        if x + w > x1:                           # keep clear of the phone
            x, y = x0, y + 52
        on = i == current
        d.rounded_rectangle((x, y, x + w, y + 40), 20, fill=INK if on else (255, 255, 255),
                            outline=None if on else (225, 223, 219))
        d.text((x + 13, y + 9), name, font=F_CHAP, fill=(255, 255, 255) if on else (MUTED if i > current else INK))
        x += w + 7


def wrap(d, text, f, width):
    out, line = [], ""
    for word in text.split():
        trial = (line + " " + word).strip()
        if d.textlength(trial, font=f) <= width:
            line = trial
        else:
            out.append(line)
            line = word
    return out + [line]


def draw_tap(frame, xy, t):
    """An amber ring at xy, `t` seconds after the finger lands (t from -0.25 to ~0.6)."""
    if xy is None or t < -0.25 or t > 0.65:
        return
    over = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(over)
    x, y = xy
    if t < 0:                                     # the finger arriving
        a = 1 + t / 0.25
        r = 30
        d.ellipse((x - r, y - r, x + r, y + r), fill=AMBER + (int(110 * a),), outline=AMBER + (int(230 * a),), width=4)
    else:
        p = t / 0.65
        r = 30 + 46 * ease(p)
        a = 1 - p
        d.ellipse((x - r, y - r, x + r, y + r), outline=AMBER + (int(230 * a),), width=5)
        r2 = 30 * (1 - 0.4 * p)
        d.ellipse((x - r2, y - r2, x + r2, y + r2), fill=AMBER + (int(120 * a),))
    frame.paste(over, (0, 0), over)


def phone_frame(stage, a, b=None, mix=0.0, kind="fade", direction=1):
    """The stage with screen `a`, or partway from `a` to `b`."""
    frame = stage.base.copy()
    if b is None or mix <= 0:
        frame.paste(stage.screen(a), (stage.sx, stage.sy), stage.mask)
        return frame
    sa, sb = stage.screen(a), stage.screen(b)
    if kind == "fade":
        frame.paste(Image.blend(sa, sb, ease(mix)), (stage.sx, stage.sy), stage.mask)
    else:                                         # slide, as the app's pages do
        off = int(stage.sw * ease(mix)) * direction
        strip = Image.new("RGB", (stage.sw, stage.sh), BG)
        strip.paste(sa, (-off, 0))
        strip.paste(sb, (stage.sw - off if direction > 0 else -stage.sw - off, 0))
        frame.paste(strip, (stage.sx, stage.sy), stage.mask)
    return frame


def scene_frames(stage, idx, prev_last):
    """Yield the frames of scene `idx`. `prev_last` (a finished frame) is faded out first."""
    shots = SCENES[idx][4]
    cap = caption_layer(idx)
    timeline = []                                 # (start, name, hold, opts)
    t = 0.0
    for i, s in enumerate(shots):
        name, hold = s[0], s[1]
        opts = s[2] if len(s) > 2 else {}
        trans = 0.0 if i == 0 else (FADE if stage.meta["shots"][name]["screen"] == stage.meta["shots"][shots[i - 1][0]]["screen"] else SLIDE)
        timeline.append((t, name, trans, hold, opts))
        t += trans + hold
    total = t
    lead_in = FADE * 1.6 if prev_last is not None else 0
    n = int(round((total + lead_in) * FPS))
    for f in range(n):
        now = f / FPS - lead_in
        # which shot, and how far through its transition
        k = max(i for i, e in enumerate(timeline) if e[0] <= max(now, 0))
        start, name, trans, hold, opts = timeline[k]
        prog = (now - start) / trans if trans else 1.0
        if prog < 1 and k > 0:
            prev = timeline[k - 1][1]
            sp, sn = stage.meta["shots"][prev]["screen"], stage.meta["shots"][name]["screen"]
            frame = phone_frame(stage, prev, name, prog, "fade" if sp == sn else "slide",
                                1 if ORDER.get(sn, 0) >= ORDER.get(sp, 0) else -1)
        else:
            frame = phone_frame(stage, name)
        frame.paste(cap, (0, 0), cap)
        # taps: a shot's tap lands on the screen before it, just before the change
        for j, (st, nm, tr, hd, op) in enumerate(timeline):
            if op.get("tap", True) is False or j == 0 and not op.get("tap_self"):
                continue
            if op.get("tap_self"):
                draw_tap(frame, stage.tap_xy(nm), now - (st + 0.35))
            elif j > 0:
                draw_tap(frame, stage.tap_xy(op.get("tap_from", nm)), now - (st - 0.05))
        if now < 0 and prev_last is not None:     # crossfade in from the last scene
            frame = Image.blend(prev_last, frame, ease(1 + now / lead_in))
        yield frame


def title_card(sub_lines, small=None):
    im = Image.new("RGB", (W, H), (255, 255, 255))
    art = Image.open(BRAND / "feature_graphic.png").convert("RGB").crop((110, 40, 440, 460))
    art = art.resize((int(art.width * 1.9), int(art.height * 1.9)), Image.LANCZOS)
    im.paste(art, (170, (H - art.height) // 2))
    d = ImageDraw.Draw(im)
    x, y = 960, 390
    d.text((x, y), "Sketch Assistant", font=font(SERIF_BI, 110), fill=INK)
    y += 150
    for line in sub_lines:
        d.text((x + 6, y), line, font=font(SERIF, 48), fill=(70, 70, 74))
        y += 62
    d.rectangle((x + 6, y + 22, x + 220, y + 34), fill=AMBER)
    if small:
        y += 80
        for line in small:
            d.text((x + 6, y), line, font=font(SANS, 30, 500), fill=MUTED)
            y += 44
    return im


def card_frames(card, seconds, fade_from=None, fade_out=False):
    n = int(round(seconds * FPS))
    white = Image.new("RGB", (W, H), (255, 255, 255))
    for f in range(n):
        t = f / FPS
        frame = card
        if fade_from is not None and t < 0.5:
            frame = Image.blend(fade_from, card, ease(t / 0.5))
        elif fade_from is None and t < 0.5:
            frame = Image.blend(white, card, ease(t / 0.5))
        if fade_out and t > seconds - 0.6:
            frame = Image.blend(frame, white, ease((t - (seconds - 0.6)) / 0.6))
        yield frame


def encode(frames, out):
    tmp = out.with_name(out.stem + ".part.mp4")
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                          "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast",
                          "-crf", "18", "-pix_fmt", "yuv420p", "-r", str(FPS), str(tmp)], stdin=subprocess.PIPE)
    last = None
    for fr in frames:
        p.stdin.write(fr.tobytes())
        last = fr
    p.stdin.close()
    if p.wait() != 0:
        raise SystemExit(f"ffmpeg failed on {out.name}")
    tmp.rename(out)
    return last


def main():
    caps, out = Path(sys.argv[1]), Path(sys.argv[2])
    meta = json.loads((caps / "shots.json").read_text())
    stage = Stage(caps, meta)
    intro = title_card(["Learn to draw from any photo,", "step by step"])
    outro = title_card(["Learn to draw from any photo,", "step by step"],
                       ["Works offline. Your photos stay on your phone.", "Get it on Google Play"])
    if "--frames" in sys.argv:
        d = Path(sys.argv[sys.argv.index("--frames") + 1])
        d.mkdir(parents=True, exist_ok=True)
        intro.save(d / "intro.png"); outro.save(d / "outro.png")
        for idx, picks in ((0, (46, 52, 100)), (3, (30, 200)), (9, (25, 200))):
            for f, fr in enumerate(scene_frames(stage, idx, None)):   # one frame in memory at a time
                if f in picks:
                    fr.save(d / f"scene{idx}_{f}.png")
        return
    work = Path(tempfile.mkdtemp(prefix="sa_video_"))
    parts = []
    last = encode(card_frames(intro, INTRO), work / "00.mp4"); parts.append(work / "00.mp4")
    for idx in range(len(SCENES)):
        p = work / f"{idx + 1:02d}.mp4"
        last = encode(scene_frames(stage, idx, last), p)
        parts.append(p)
        print("scene", idx + 1, "of", len(SCENES), flush=True)
    p = work / "99.mp4"
    encode(card_frames(outro, OUTRO, fade_from=last, fade_out=True), p); parts.append(p)
    lst = work / "list.txt"
    lst.write_text("".join(f"file '{q}'\n" for q in parts))
    tmp = out.with_name(out.stem + ".part.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst),
                    "-c", "copy", "-movflags", "+faststart", str(tmp)], check=True)
    tmp.rename(out)
    print("wrote", out)


if __name__ == "__main__":
    main()
