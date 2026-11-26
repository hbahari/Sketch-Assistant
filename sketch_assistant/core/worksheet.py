"""Printable worksheet: a PDF lesson for paper, built from the photo and the drawing steps.

Pages, in order:
  1. Reference: the photo and the finished drawing side by side under one grid, for the grid
     method (copy one square at a time), with the size to rule the squares on paper. The
     subject's own guide lines (eye, nose, mouth and chin lines; the oval) are drawn on
     both as well, as on the practice and trace pages.
  2. Steps: each step's picture beside its written instructions (pencil, technique, what to
     do), packed as many to a page as fit.
  3. Practice: the same grid, empty, as large as the page allows -- draw straight onto it.
  4. Trace: the finished drawing at that same size, printed faint, to trace or to check
     your drawing against.

Pages are drawn as pictures at 200 dpi and written into a PDF here, with no PDF or
imaging library: the app ships neither on Android, and a PDF of picture pages is a short,
fixed format. Text is drawn by whatever `render_text` the caller passes (the app uses
Kivy's, so the words and the font match the screen); this module never imports Kivy.
"""
import math

import cv2
import numpy as np

DPI = 200
PAPER = {                      # (width, height) in inches
    "letter": (8.5, 11.0),
    "a4": (8.27, 11.69),
}
LETTER_COUNTRIES = {"US", "CA", "MX", "PH", "CL", "CO", "VE", "GT", "CR", "PA", "DO", "PR", "SV"}
MARGIN = 0.55                  # inches
INK = (40, 40, 44)             # BGR
MUTED = (110, 108, 106)
GRID = (168, 168, 168)         # light grey: the blue is kept for the guide lines on top
COLS = 4                       # grid columns across the drawing


def paper_for_country(code):
    """US Letter where that's the local paper, A4 everywhere else."""
    return "letter" if (code or "").upper() in LETTER_COUNTRIES else "a4"


def page_size(paper):
    w, h = PAPER[paper]
    return round(w * DPI), round(h * DPI)


def _px(inches):
    return round(inches * DPI)


# --------------------------------------------------------------------------- drawing
def _paste_text(page, rgba, x, y):
    """Composite a rendered text block (RGBA, ink in RGB, coverage in A) onto a BGR page."""
    h, w = rgba.shape[:2]
    H, W = page.shape[:2]
    h, w = min(h, H - y), min(w, W - x)
    if h <= 0 or w <= 0:
        return 0
    a = rgba[:h, :w, 3:4].astype(np.float32) / 255.0
    ink = rgba[:h, :w, 2::-1].astype(np.float32)               # RGBA -> BGR
    region = page[y:y + h, x:x + w].astype(np.float32)
    page[y:y + h, x:x + w] = (region * (1 - a) + ink * a).astype(np.uint8)
    return h


def _fit(img, box_w, box_h):
    h, w = img.shape[:2]
    s = min(box_w / w, box_h / h)
    return cv2.resize(img, (max(1, round(w * s)), max(1, round(h * s))), interpolation=cv2.INTER_AREA)


def _bgr(img):
    return cv2.cvtColor(img, cv2.COLOR_GRAY2BGR) if img.ndim == 2 else img


def grid_shape(w, h, cols=COLS):
    """(cols, rows) of square cells covering a w x h picture."""
    return cols, max(1, math.ceil(h / (w / cols) - 1e-6))


def _overlay_guides(im, lines):
    """Lay guide lines (drawn on white) over a picture: their coloured pixels replace the
    picture's, so they read on a dark photo as well as on white paper."""
    if lines.shape[1] < 1000:
        # small pictures (the reference page): the guides come out a pixel wide, too thin to
        # read over a pencil drawing, so they're thickened by one pixel
        lines = cv2.erode(lines, np.ones((2, 2), np.uint8))
    g = lines.astype(np.int16)
    ink = np.clip((255 - g.min(axis=2)) / 255.0 * 2.2, 0, 1)[..., None]   # strength of the line
    return (im * (1 - ink) + g * ink).astype(np.uint8)


def _gridded(img, cols, rows, size_w, label=True, faint=False, guides_at=None, shape=None):
    """The picture at width size_w on a white field exactly cols x rows squares, with the guide
    lines (guides_at(w, h) -> lines on white) and the grid drawn over it, and the columns
    lettered / rows numbered along the outside edge. `shape` is the drawing's (h, w), for
    where the guides go when there's no picture (the empty practice grid)."""
    cell = size_w / cols
    field_h = round(cell * rows)
    field = np.full((field_h, round(size_w), 3), 255, np.uint8)
    src_h, src_w = img.shape[:2] if img is not None else (shape or (None, None))
    if img is not None:
        im = _bgr(cv2.resize(img, (round(size_w), round(img.shape[0] * size_w / img.shape[1])),
                             interpolation=cv2.INTER_AREA))
        if faint:
            im = (255 - (255 - im.astype(np.float32)) * 0.28).astype(np.uint8)
        field[:min(field_h, im.shape[0])] = im[:field_h]
    if guides_at is not None and src_w:
        gw, gh = round(size_w), min(field_h, round(src_h * size_w / src_w))
        field[:gh] = _overlay_guides(field[:gh], guides_at(gw, gh))
    thick = max(1, _px(0.008))
    for c in range(cols + 1):
        x = min(field.shape[1] - 1, round(c * cell))
        cv2.line(field, (x, 0), (x, field_h - 1), GRID, thick, cv2.LINE_AA)
    for r in range(rows + 1):
        y = min(field_h - 1, round(r * cell))
        cv2.line(field, (0, y), (field.shape[1] - 1, y), GRID, thick, cv2.LINE_AA)
    if not label:
        return field
    pad = _px(0.22)
    out = np.full((field_h + pad, field.shape[1] + pad, 3), 255, np.uint8)
    out[pad:, pad:] = field
    scale = DPI / 200 * 0.62
    for c in range(cols):
        t = chr(ord("A") + c)
        (tw, th), _ = cv2.getTextSize(t, cv2.FONT_HERSHEY_SIMPLEX, scale, 2)
        cx = pad + round((c + 0.5) * cell)
        cv2.putText(out, t, (cx - tw // 2, pad - _px(0.06)), cv2.FONT_HERSHEY_SIMPLEX, scale, MUTED, 2, cv2.LINE_AA)
    for r in range(rows):
        t = str(r + 1)
        (tw, th), _ = cv2.getTextSize(t, cv2.FONT_HERSHEY_SIMPLEX, scale, 2)
        cy = pad + round((r + 0.5) * cell)
        cv2.putText(out, t, (pad - tw - _px(0.06), cy + th // 2), cv2.FONT_HERSHEY_SIMPLEX, scale, MUTED, 2, cv2.LINE_AA)
    return out


class _Page:
    """A blank page with the running header; `y` is where the next thing goes."""

    def __init__(self, paper, render_text, header):
        self.W, self.H = page_size(paper)
        self.img = np.full((self.H, self.W, 3), 255, np.uint8)
        self.m = _px(MARGIN)
        self.text = render_text
        self.width = self.W - 2 * self.m
        t = render_text(header, _px(0.12), self.width, color=MUTED)
        _paste_text(self.img, t, self.m, self.m)
        rule_y = self.m + t.shape[0] + _px(0.06)
        cv2.line(self.img, (self.m, rule_y), (self.W - self.m, rule_y), (215, 215, 215), max(1, _px(0.006)))
        self.y = rule_y + _px(0.18)
        self.bottom = self.H - self.m

    def write(self, markup, size_in, width=None, x=None, color=INK, gap=0.10):
        t = self.text(markup, _px(size_in), width or self.width, color=color)
        _paste_text(self.img, t, self.m if x is None else x, self.y)
        self.y += t.shape[0] + _px(gap)
        return t.shape[0]

    def place(self, pic, x=None):
        x = (self.W - pic.shape[1]) // 2 if x is None else x
        self.img[self.y:self.y + pic.shape[0], x:x + pic.shape[1]] = pic
        self.y += pic.shape[0]


# --------------------------------------------------------------------------- pages
def build_pages(photo, stages, step_texts, title, paper, render_text, guides_at=None):
    """The worksheet's pages as BGR images.

    photo: the photo the steps were drawn from (the crop). stages: objects with .title and
    .image, the last one being the finished drawing. step_texts: Kivy-style markup for each
    stage ("" for none). render_text(markup, px, width, color=BGR) -> RGBA array.
    guides_at(w, h): the subject's guide lines drawn on white at that size, or None for none;
    drawn at each size asked for, so they stay sharp on the large practice page.
    """
    final = _bgr(stages[-1].image)
    cols, rows = grid_shape(final.shape[1], final.shape[0])
    header = f"Sketch Assistant  -  {title}"
    pages = []

    # 1. reference
    p = _Page(paper, render_text, header)
    p.write("[b]Grid method reference[/b]", 0.26, gap=0.06)
    p.write("Rule the same grid lightly on your paper with an H pencil. Then copy one square at a "
            "time: look at a square here, and draw only what's inside it in the same square on "
            "your paper. Square by square, the proportions take care of themselves."
            + (" The blue lines are the guides: sketch them in first, lightly, to place the features."
               if guides_at is not None else ""), 0.125, color=MUTED, gap=0.22)
    gap = _px(0.3)
    each_w = (p.width - gap - _px(0.22) * 2) / 2
    avail_h = p.bottom - p.y - _px(1.25)
    each_w = min(each_w, (avail_h - _px(0.22)) / rows * cols)
    a = _gridded(photo, cols, rows, each_w, guides_at=guides_at)
    b = _gridded(final, cols, rows, each_w, guides_at=guides_at)
    x0 = (p.W - (a.shape[1] + gap + b.shape[1])) // 2
    top = p.y
    p.img[top:top + a.shape[0], x0:x0 + a.shape[1]] = a
    p.img[top:top + b.shape[0], x0 + a.shape[1] + gap:x0 + a.shape[1] + gap + b.shape[1]] = b
    p.y = top + max(a.shape[0], b.shape[0]) + _px(0.08)
    lab_w = a.shape[1]
    p.write("Photo", 0.12, width=lab_w, x=x0 + _px(0.22), color=MUTED, gap=0)
    p.y -= render_text("Photo", _px(0.12), lab_w, color=MUTED).shape[0]
    p.write("Drawing", 0.12, width=lab_w, x=x0 + a.shape[1] + gap + _px(0.22), color=MUTED, gap=0.22)
    cell_in = practice_cell_inches(paper, cols, rows)
    p.write(f"[b]On your paper:[/b] {cols} squares across and {rows} down, each "
            f"{cell_in * 2.54:.1f} cm ({cell_in:.2f} in) \u2013 the size of the practice page at the end. "
            f"Any size works as long as the squares are square.", 0.125, gap=0.3)
    tips = [
        "Measure the squares with a ruler and rule the lines lightly with an H pencil, so they "
        "erase cleanly once the drawing is done.",
        "Letter the columns and number the rows on your paper the same way as here, so you "
        "always know which square you're in.",
        "Work one square at a time, from the top left. Look at where each line enters and leaves "
        "the square, and copy just that.",
        "Draw lines lightly at first. Shading comes last, once every square has its outlines.",
        "Stuck on a square? Turn the photo and your paper upside down: you'll see plain shapes "
        "instead of an eye or a hand, and copy them more accurately.",
    ]
    if p.bottom - p.y > _px(2.2):
        p.write("[b]Tips for the grid method[/b]", 0.16, gap=0.08)
        for t in tips:
            if p.bottom - p.y < _px(0.6):
                break
            p.write(f"\u2022  {t}", 0.12, gap=0.07)
    pages.append(p.img)

    # 2. steps, as many to a page as fit
    n = len(stages)
    pic_w = round(p.width * 0.40)
    text_x_off = pic_w + _px(0.25)
    text_w = p.width - text_x_off
    p = _Page(paper, render_text, header)
    p.write("[b]Step by step[/b]", 0.26, gap=0.15)
    for i, (st, txt) in enumerate(zip(stages, step_texts)):
        pic = _fit(_bgr(st.image), pic_w, _px(2.75))           # three steps to a page
        head = render_text(f"[b]Step {i + 1} of {n}  -  {st.title}[/b]", _px(0.15), text_w, color=INK)
        body = render_text(txt, _px(0.115), text_w, color=INK) if txt else None
        text_h = head.shape[0] + (_px(0.08) + body.shape[0] if body is not None else 0)
        block_h = max(pic.shape[0], text_h)
        if p.y + block_h > p.bottom:
            pages.append(p.img)
            p = _Page(paper, render_text, header)
        y = p.y
        p.img[y:y + pic.shape[0], p.m:p.m + pic.shape[1]] = pic
        cv2.rectangle(p.img, (p.m, y), (p.m + pic.shape[1] - 1, y + pic.shape[0] - 1), (220, 220, 220), 1)
        _paste_text(p.img, head, p.m + text_x_off, y)
        if body is not None:
            _paste_text(p.img, body, p.m + text_x_off, y + head.shape[0] + _px(0.08))
        p.y = y + block_h + _px(0.26)
        if i < n - 1 and p.y < p.bottom:
            cv2.line(p.img, (p.m, p.y - _px(0.15)), (p.W - p.m, p.y - _px(0.15)), (232, 232, 232), 1)
    pages.append(p.img)

    # 3. practice grid and 4. faint trace, the same size
    for kind in ("practice", "trace"):
        p = _Page(paper, render_text, header)
        if kind == "practice":
            p.write("[b]Practice grid[/b]", 0.26, gap=0.04)
            p.write("Draw straight onto this page, one square at a time, using the reference page.",
                    0.125, color=MUTED, gap=0.15)
        else:
            p.write("[b]Trace or check[/b]", 0.26, gap=0.04)
            p.write("The finished drawing at the same size, printed faint. Trace it, or hold it against "
                    "your drawing to the light to see where it differs.", 0.125, color=MUTED, gap=0.15)
        pic = practice_field(paper, cols, rows, final if kind == "trace" else None,
                             p.width, p.bottom - p.y, guides_at=guides_at, shape=final.shape[:2])
        p.place(pic)
        pages.append(p.img)
    return pages


def _practice_width(paper, cols, rows, avail_w=None, avail_h=None):
    W, H = page_size(paper)
    m = _px(MARGIN)
    pad = _px(0.22)
    avail_w = (W - 2 * m) if avail_w is None else avail_w
    avail_h = (H - 2 * m - _px(1.15)) if avail_h is None else avail_h
    return min(avail_w - pad, (avail_h - pad) / rows * cols)


def practice_cell_inches(paper, cols, rows):
    return _practice_width(paper, cols, rows) / cols / DPI


def practice_field(paper, cols, rows, img, avail_w, avail_h, guides_at=None, shape=None):
    return _gridded(img, cols, rows, _practice_width(paper, cols, rows, avail_w, avail_h),
                    faint=img is not None, guides_at=guides_at, shape=shape)


# --------------------------------------------------------------------------- PDF
def pdf_bytes(pages, paper, quality=85):
    """A PDF with one full-page JPEG per page. Sized exactly to the paper, so it prints 1:1."""
    w_pt, h_pt = (v * 72 for v in PAPER[paper])
    objs = []                                      # object bodies, numbered from 1

    def add(body):
        objs.append(body)
        return len(objs)

    catalog = add(None)
    pages_obj = add(None)
    kids = []
    for img in pages:
        ok, jpg = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, quality])
        if not ok:
            raise IOError("JPEG encoding failed")
        jpg = jpg.tobytes()
        h, w = img.shape[:2]
        im = add(b"<< /Type /XObject /Subtype /Image /Width %d /Height %d /ColorSpace /DeviceRGB "
                 b"/BitsPerComponent 8 /Filter /DCTDecode /Length %d >>\nstream\n" % (w, h, len(jpg))
                 + jpg + b"\nendstream")
        draw = b"q %.2f 0 0 %.2f 0 0 cm /Im0 Do Q" % (w_pt, h_pt)
        content = add(b"<< /Length %d >>\nstream\n" % len(draw) + draw + b"\nendstream")
        kids.append(add(b"<< /Type /Page /Parent %d 0 R /MediaBox [0 0 %.2f %.2f] "
                        b"/Resources << /XObject << /Im0 %d 0 R >> >> /Contents %d 0 R >>"
                        % (pages_obj, w_pt, h_pt, im, content)))
    objs[catalog - 1] = b"<< /Type /Catalog /Pages %d 0 R >>" % pages_obj
    objs[pages_obj - 1] = (b"<< /Type /Pages /Kids [" + b" ".join(b"%d 0 R" % k for k in kids)
                           + b"] /Count %d >>" % len(kids))
    out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = []
    for i, body in enumerate(objs, 1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % i + body + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1)
    for off in offsets:
        out += b"%010d 00000 n \n" % off
    out += (b"trailer\n<< /Size %d /Root %d 0 R /Info << /Producer (Sketch Assistant) >> >>\n"
            b"startxref\n%d\n%%%%EOF\n" % (len(objs) + 1, catalog, xref))
    return bytes(out)
