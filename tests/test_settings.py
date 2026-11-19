"""The settings page (gear at the top right of the main page) and what hangs off it.

Run with:  PYTHONPATH=. xvfb-run -a python -m pytest tests/test_settings.py
"""
import configparser
import os
import re
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest

ROOT = Path(__file__).resolve().parent.parent


# --------------------------------------------------------------------------- no Kivy window
def test_the_build_reads_the_version_the_app_shows():
    """buildozer takes the version name from sketch_assistant/__init__.py, the same place the
    settings page and the feedback email read it from -- so the Play listing and the app
    can't disagree. Done the way buildozer's get_version does it (configparser + re.search)."""
    from sketch_assistant import __version__
    cfg = configparser.ConfigParser()
    cfg.read(ROOT / "buildozer.spec")
    assert not cfg.has_option("app", "version"), "a plain `version =` conflicts with version.regex"
    fn = cfg.get("app", "version.filename", vars={"source.dir": str(ROOT)})
    m = re.search(cfg.get("app", "version.regex"), Path(fn).read_text())
    assert m and m.group(1) == __version__


def test_the_privacy_policy_in_the_app_is_the_published_one():
    """The app shows its own copy of the privacy policy (it is offline, so it can't fetch
    the hosted one). Edit PRIVACY_POLICY.md and copy it over the asset; this catches a copy
    that was forgotten."""
    from sketch_assistant.ui.settings import PRIVACY_FILE
    assert PRIVACY_FILE.read_text(encoding="utf-8") == (ROOT / "PRIVACY_POLICY.md").read_text(encoding="utf-8")


def test_feedback_email_is_addressed_and_carries_the_details():
    """The link the email app receives decodes back to the right address, subject and body:
    newlines and the '&' in a phone make or a mode name must not cut the body short."""
    from sketch_assistant import __version__
    from sketch_assistant.platform_utils import mailto_uri
    from sketch_assistant.ui.settings import FEEDBACK_EMAIL, feedback_message
    subject, body = feedback_message("Hands & arms")
    assert __version__ in subject and f"App: Sketch Assistant {__version__}" in body
    assert "Device:" in body and "Mode: Hands & arms" in body
    assert body.startswith("\n"), "room to write comes first, the details after"
    parts = urlsplit(mailto_uri(FEEDBACK_EMAIL, subject, body))
    assert parts.scheme == "mailto" and parts.path == "golemapps1@gmail.com"
    q = parse_qs(parts.query, keep_blank_values=True)
    assert q["subject"] == [subject] and q["body"] == [body]


def test_text_pages_join_wrapped_lines_and_find_headings():
    from sketch_assistant.ui.textpage import paragraphs
    text = "Title here\n=====\n\n# Policy\n\n## Photos\nline one\nline two\n\n------\n\n* a bullet\n  continued"
    assert paragraphs(text) == [("h1", "Title here"), ("h1", "Policy"), ("h2", "Photos"),
                                ("p", "line one line two"), ("p", "* a bullet continued")]


def test_text_pages_avoid_characters_the_app_font_lacks():
    """Kivy's bundled Roboto has no "\u2192"; the privacy policy uses it ("Add a photo \u2192 Take
    photo") and it drew as an empty box. Checked against the font itself, so the test fails
    for any character in either text the font can't draw, not just the arrow."""
    TTFont = pytest.importorskip("fontTools.ttLib").TTFont
    import kivy
    from sketch_assistant.ui.settings import LICENSES_FILE, PRIVACY_FILE
    from sketch_assistant.ui.textpage import paragraphs, to_markup
    font = Path(kivy.__file__).parent / "data" / "fonts" / "Roboto-Regular.ttf"
    cmap = TTFont(str(font)).getBestCmap()
    for f in (PRIVACY_FILE, LICENSES_FILE):
        shown = "".join(to_markup(t) for _, t in paragraphs(f.read_text(encoding="utf-8")))
        missing = {c for c in shown if ord(c) not in cmap and not c.isspace()}
        assert not missing, f"{f.name}: {missing}"


# --------------------------------------------------------------------------- with a window
kivy = pytest.importorskip("kivy")
os.environ.setdefault("KIVY_NO_ARGS", "1")
os.environ.setdefault("KIVY_NO_CONSOLELOG", "1")
from kivy.config import Config  # noqa: E402

Config.set("graphics", "width", "420")
Config.set("graphics", "height", "800")
from kivy.base import EventLoop  # noqa: E402
from kivy.clock import Clock  # noqa: E402


@pytest.fixture(scope="module")
def app():
    EventLoop.ensure_window()
    from sketch_assistant.app import SketchApp
    a = SketchApp()
    sm = a.build()
    EventLoop.window.add_widget(sm)
    sm.transition.duration = 0
    yield a, sm
    EventLoop.window.remove_widget(sm)


def _tick(n=4):
    for _ in range(n):
        Clock.tick()


def _tap(widget):
    widget.dispatch("on_press")
    widget.dispatch("on_release")
    _tick()


def test_the_gear_opens_settings_and_back_returns(app):
    """The gear sits in the logo bar (not a subject tab); tapping it opens Settings, and
    Android's back button comes back to the main page rather than quitting."""
    a, sm = app
    home = sm.get_screen("home")
    from kivy.metrics import dp
    gear = home.logo_bar.gear
    assert gear is not None and gear.parent.parent is home.logo_bar
    assert "settings" not in home.mode_bar.btns
    assert min(gear.size) >= dp(48) - 0.5, "Android's minimum touch target"
    _tap(gear)
    assert sm.current == "settings"
    assert a._back_key(sm, 27) is True
    _tick()
    assert sm.current == "home"


def test_restore_explains_there_is_nothing_to_restore_yet(app):
    a, sm = app
    page = sm.get_screen("settings")
    _tap(page.rows["restore"])
    title, text = page.last_notice
    assert title == "Restore purchase" and "nothing to restore" in text
    page._popup.dismiss(); _tick()


def test_feedback_without_an_email_app_gives_the_address(app, monkeypatch):
    """No email app (or none that answers mailto:) must not be a dead button: the address
    is shown, and copied when the clipboard works."""
    from sketch_assistant.ui import settings
    a, sm = app
    page = sm.get_screen("settings")
    sent = {}
    monkeypatch.setattr(settings, "send_email", lambda to, s, b: sent.update(to=to, s=s, b=b) or False)
    monkeypatch.setattr(settings, "copy_text", lambda t: sent.update(copied=t) or True)
    _tap(page.rows["feedback"])
    assert sent["to"] == "golemapps1@gmail.com" and sent["copied"] == "golemapps1@gmail.com"
    from sketch_assistant.core.modes import mode_of
    assert f"Mode: {mode_of(a.mode).label}" in sent["b"]
    assert "golemapps1@gmail.com" in page.last_notice[1]
    page._popup.dismiss(); _tick()


@pytest.mark.parametrize("row,title,needle", [("licences", "Licences", "Apache License"),
                                              ("privacy", "Privacy policy", "Send feedback")])
def test_licences_and_privacy_open_as_readable_pages(app, row, title, needle):
    """Both texts open in the app, and no single block of text is taller than a phone GPU
    can hold as one texture (2048 px is the floor Android guarantees). One Label for the
    whole licence -- the obvious way to write it -- is over 10,000 px here and fails."""
    a, sm = app
    _tap(sm.get_screen("settings").rows[row])
    page = sm.get_screen("text")
    assert sm.current == "text" and page.bar.title.text == title
    _tick(6)
    labels = page.col.children
    assert any(needle in lb.text for lb in labels)
    tallest = max(lb.texture_size[1] for lb in labels)
    assert tallest < 2048, f"a {tallest:.0f} px block"
    assert a._back_key(sm, 27) is True
    _tick()
    assert sm.current == "settings"
