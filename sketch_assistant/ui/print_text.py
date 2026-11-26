"""Draw text for printed pages with Kivy's own text renderer: the same font and markup as the
screen, so a worksheet's step instructions read exactly as they do in the app.

Must run on the main (Kivy) thread: text is rendered to a GPU texture and read back.
"""
import numpy as np


def render_text(markup, px, width, color=(40, 40, 44)):
    """markup (Kivy markup), px font size in pixels, width to wrap at, BGR colour ->
    RGBA uint8 array, ink in RGB and coverage in alpha, top row first."""
    from kivy.core.text.markup import MarkupLabel        # the plain core Label ignores [b] etc.
    b, g, r = color
    lb = MarkupLabel(text=markup, markup=True, font_size=px, text_size=(int(width), None),
                   color=(r / 255, g / 255, b / 255, 1), halign="left", valign="top")
    lb.refresh()
    tex = lb.texture
    if tex is None:
        return np.zeros((1, int(width), 4), np.uint8)
    arr = np.frombuffer(tex.pixels, np.uint8).reshape(tex.height, tex.width, 4)
    return np.ascontiguousarray(arr[::-1]) if FLIP else arr


# Whether Kivy's texture pixels come bottom row first. Measured, not assumed: they don't
# (the first worksheet printed every line upside down with this True). test_worksheet
# checks the first line of a block lands at its top.
FLIP = False
