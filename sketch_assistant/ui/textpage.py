"""A page of reading text: the privacy policy and the licences, shown inside the app.

The text is cut into one Label per paragraph. A single Label holding all of it is one GPU
texture, and the licences run to well over 10,000 pixels tall on a phone -- past the
largest texture many phones can make, which shows as a blank page rather than an error.
"""
import re

from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView
from kivy.utils import escape_markup

from . import theme
from .widgets import Card, TitleBar

_RULE = re.compile(r"^[-=_*\s]+$")


def paragraphs(text):
    """Split plain text or simple Markdown into (kind, text) blocks: kind is "h1", "h2" or "p".

    Hard line breaks inside a paragraph are joined: the files are wrapped at about 90
    columns for editing, and kept as they are they wrap a second time on a phone and read
    ragged. Lines that are only rules (----, ====) are dropped; a ==== under a line makes
    that line a heading, as in the licences file.
    """
    out = []
    for block in re.split(r"\n\s*\n", text.replace("\r\n", "\n")):
        lines = [ln.strip() for ln in block.strip().split("\n") if ln.strip()]
        if not lines:
            continue
        if len(lines) >= 2 and _RULE.match(lines[-1]) and set(lines[-1]) <= {"=", "-"}:
            out.append(("h1", " ".join(lines[:-1])))
            continue
        lines = [ln for ln in lines if not _RULE.match(ln)]
        if not lines:
            continue
        if lines[0].startswith("# "):
            out.append(("h1", lines[0][2:].strip()))
            lines = lines[1:]
        elif lines[0].startswith("## "):
            out.append(("h2", lines[0][3:].strip()))
            lines = lines[1:]
        if lines:
            out.append(("p", " ".join(lines)))
    return out


def to_markup(s):
    """Escape Kivy markup in `s`, then turn Markdown **bold** into [b]bold[/b].

    "→" becomes ">" (Kivy's bundled Roboto has no arrow, so it drew as an empty box) and a
    leading "* " becomes a bullet.
    """
    s = s.replace("\u2192", ">")
    if s.startswith("* "):
        s = "\u2022 " + s[2:]
    return re.sub(r"\*\*(.+?)\*\*", r"[b]\1[/b]", escape_markup(s))


class TextScreen(Screen):
    """Title bar, then the text in a scrolling card. `show(title, text)` fills it."""

    def __init__(self, on_back, **kw):
        super().__init__(**kw)
        self.on_back = on_back
        root = BoxLayout(orientation="vertical", spacing=dp(10))
        self.bar = TitleBar("", self.go_back)
        root.add_widget(self.bar)
        self.col = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(10),
                             padding=(dp(16), dp(14)))
        self.col.bind(minimum_height=self.col.setter("height"))
        card = Card(orientation="vertical", size_hint_y=None, padding=0)
        card.bind(minimum_height=card.setter("height"))
        card.add_widget(self.col)
        holder = BoxLayout(orientation="vertical", size_hint_y=None, padding=(dp(14), 0, dp(14), dp(14)))
        holder.bind(minimum_height=holder.setter("height"))
        holder.add_widget(card)
        self.scroll = ScrollView()
        self.scroll.add_widget(holder)
        root.add_widget(self.scroll)
        self.add_widget(root)

    def show(self, title, text):
        self.bar.title.text = title
        self.col.clear_widgets()
        for kind, s in paragraphs(text):
            size = {"h1": 18, "h2": 15}.get(kind, 13)
            lb = Label(text=to_markup(s), markup=True, bold=kind != "p", font_size=sp(size),
                       color=theme.TEXT, size_hint_y=None,
                       halign="left", valign="top")
            lb.bind(width=lambda w, v: setattr(w, "text_size", (v, None)),
                    texture_size=lambda w, v: setattr(w, "height", v[1]))
            self.col.add_widget(lb)
        self.scroll.scroll_y = 1

    def go_back(self):
        self.on_back()
