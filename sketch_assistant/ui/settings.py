"""Settings page, opened from the gear at the top right of the main page.

Kept to the few things people actually come looking for: a way to reach the developer, a
way to rate the app, restoring a purchase (a placeholder until Pro exists), and the privacy
policy and licences. It is a page of its own rather than a subject tab, so the tabs stay
about drawing.
"""
from pathlib import Path

from kivy.graphics import Color, Ellipse, Line, RoundedRectangle
from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView

from .. import __version__, prefs, purchases
from ..platform_utils import copy_text, device_summary, keep_screen_on, open_store_page, send_email
from . import theme
from .widgets import RoundButton, TitleBar

FEEDBACK_EMAIL = "golemapps1@gmail.com"
ASSETS = Path(__file__).resolve().parent.parent / "assets"
PRIVACY_FILE = ASSETS / "privacy_policy.txt"      # a copy of PRIVACY_POLICY.md (a test keeps them equal)
LICENSES_FILE = ASSETS / "LICENSES.txt"


def feedback_message(mode_label=None):
    """Subject and body for the feedback email: room to write first, the details after.

    The details are in plain sight in the user's own email app, so they can read exactly
    what is sent and delete any of it before pressing send.
    """
    subject = f"Sketch Assistant {__version__} feedback"
    details = [f"App: Sketch Assistant {__version__}", device_summary()]
    if mode_label:
        details.append(f"Mode: {mode_label}")
    body = ("\n\n\n"
            "---\n"
            "Write above this line. The details below help with fixing problems; "
            "delete them if you'd rather not send them.\n" + "\n".join(details))
    return subject, body


class Row(RoundButton):
    """A full-width settings row: bold title, a muted line under it, a chevron at the right."""

    def __init__(self, title, subtitle, **kw):
        text = f"[b]{title}[/b]\n[size=12sp][color=73706e]{subtitle}[/color][/size]"
        super().__init__(text=text, markup=True, font_size=sp(15), halign="left", valign="middle",
                         padding=(dp(18), 0, dp(40), 0), size_hint_y=None, height=dp(66),
                         radii=[dp(18)] * 4, **kw)

    def _draw(self, *_):
        super()._draw()
        x, y, w, h = self.x, self.y, self.width, self.height
        cx, cy = x + w - dp(22), y + h / 2
        with self.canvas.after:
            Color(*theme.MUTED)
            Line(points=[cx - dp(4), cy + dp(7), cx + dp(3), cy, cx - dp(4), cy - dp(7)],
                 width=dp(1.6), cap="round", joint="round")


class ToggleRow(Row):
    """A settings row with an on/off switch at the right instead of a chevron. Tapping
    anywhere on the row flips it."""

    def __init__(self, title, subtitle, value, on_change, **kw):
        self.value, self.on_change = bool(value), on_change
        super().__init__(title, subtitle, **kw)
        self.padding = (dp(18), 0, dp(78), 0)

    def on_release(self):
        self.value = not self.value
        self._draw()
        self.on_change(self.value)

    def _draw(self, *_):
        RoundButton._draw(self)
        if not hasattr(self, "value"):
            return
        w, h = dp(46), dp(26)
        # from x/width/y/height, not right/center_y: those aliases update after the pos and
        # size events that call this, so the first laid-out draw put the switch at the left
        x, y = self.x + self.width - dp(18) - w, self.y + (self.height - h) / 2
        knob = h - dp(6)
        with self.canvas.after:
            Color(*(theme.AMBER if self.value else theme.SURFACE_HI))
            RoundedRectangle(pos=(x, y), size=(w, h), radius=[h / 2])
            Color(*theme.WHITE)
            kx = x + w - dp(3) - knob if self.value else x + dp(3)
            Ellipse(pos=(kx, y + dp(3)), size=(knob, knob))
            if not self.value:
                Color(*theme.MUTED[:3], 0.35)
                Line(ellipse=(kx, y + dp(3), knob, knob), width=dp(1))


def _section(text):
    lb = Label(text=text.upper(), bold=True, font_size=sp(11), color=theme.MUTED, size_hint_y=None,
               height=dp(30), halign="left", valign="bottom", padding=(dp(6), dp(4)))
    lb.bind(size=lambda w, v: setattr(w, "text_size", v))
    return lb


class SettingsScreen(Screen):
    def __init__(self, app, on_back, show_text, **kw):
        """`show_text(title, text)` opens the reading page; `on_back()` leaves this one."""
        super().__init__(**kw)
        self.app_ref, self.on_back, self.show_text = app, on_back, show_text
        root = BoxLayout(orientation="vertical", spacing=dp(6))
        root.add_widget(TitleBar("Settings", self.go_back))
        col = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(10),
                        padding=(dp(14), 0, dp(14), dp(18)))
        col.bind(minimum_height=col.setter("height"))

        self.rows = {
            "screen_on": ToggleRow("Keep screen on", "While the app is open, so it won't dim as you draw",
                                   prefs.get("keep_screen_on"), self.set_screen_on),
            "feedback": Row("Send feedback", "Report a problem or suggest an idea",
                            on_release=lambda *_: self.send_feedback()),
            "rate": Row("Rate Sketch Assistant", "Leave a review on Google Play",
                        on_release=lambda *_: self.rate()),
            "restore": Row("Restore purchase", "Bought Pro before? Get it back on this phone",
                           on_release=lambda *_: self.restore()),
            "privacy": Row("Privacy policy", "Your photos never leave your phone",
                           on_release=lambda *_: self.show_text("Privacy policy", _read(PRIVACY_FILE))),
            "licences": Row("Licences", "Open-source software in the app",
                            on_release=lambda *_: self.show_text("Licences", _read(LICENSES_FILE))),
        }
        col.add_widget(_section("While drawing"))
        col.add_widget(self.rows["screen_on"])
        col.add_widget(_section("Help us improve"))
        col.add_widget(self.rows["feedback"]); col.add_widget(self.rows["rate"])
        col.add_widget(_section("Purchases"))
        col.add_widget(self.rows["restore"])
        col.add_widget(_section("About"))
        col.add_widget(self.rows["privacy"]); col.add_widget(self.rows["licences"])
        self.version = Label(text=f"Sketch Assistant {__version__}", color=theme.MUTED, font_size=sp(12),
                             size_hint_y=None, height=dp(40))
        col.add_widget(self.version)
        scroll = ScrollView(); scroll.add_widget(col)
        root.add_widget(scroll)
        self.add_widget(root)

    # actions
    def set_screen_on(self, on):
        prefs.set("keep_screen_on", on)
        keep_screen_on(on)

    def send_feedback(self):
        from ..core.modes import mode_of
        try:
            label = mode_of(self.app_ref.mode).label
        except Exception:
            label = None
        subject, body = feedback_message(label)
        if not send_email(FEEDBACK_EMAIL, subject, body):
            copied = copy_text(FEEDBACK_EMAIL)
            self.notice("No email app found",
                        f"You can write to {FEEDBACK_EMAIL}" + (" - the address is copied, ready to paste." if copied else "."))

    def rate(self):
        if not open_store_page():
            self.notice("Couldn't open Google Play", "Search for Sketch Assistant in the Play Store app.")

    def restore(self):
        purchases.restore(lambda msg: self.notice("Restore purchase", msg))

    def notice(self, title, text):
        """A small message box with an OK button. Kept as `self.last_notice` for tests."""
        self.last_notice = (title, text)
        box = BoxLayout(orientation="vertical", spacing=dp(12), padding=dp(14))
        lb = Label(text=text, color=theme.TEXT, font_size=sp(14), halign="left", valign="top")
        lb.bind(size=lambda w, v: setattr(w, "text_size", v))
        box.add_widget(lb)
        pop = Popup(title=title, content=box, size_hint=(0.86, None), height=dp(250), separator_height=0,
                    background="", background_color=theme.BG, title_color=theme.TEXT, title_size=sp(16))
        box.add_widget(RoundButton(text="OK", bold=True, active=True, size_hint_y=None, height=dp(46),
                                   radii=[dp(23)] * 4, on_release=lambda *_: pop.dismiss()))
        pop.open()
        self._popup = pop

    def go_back(self):
        self.on_back()


def _read(path):
    try:
        return Path(path).read_text(encoding="utf-8")
    except OSError:
        return "This text is missing from the app. It is also on the app's Google Play page."
