"""The user's settings, kept between launches in a small JSON file in the app's own storage.

Nothing here leaves the phone. A missing or damaged file just means the defaults.
"""
import json
from pathlib import Path

DEFAULTS = {
    "keep_screen_on": False,
    "tour_done": False,          # the first-launch tour has been seen (or skipped)
    "trace_darker": True,        # trace mode deepens the lines so they show through paper
    "paper": None,               # worksheet paper, "letter" or "a4"; None = by the phone's region
}
_path = None


def _file():
    global _path
    if _path is None:
        try:
            from kivy.app import App
            _path = Path(App.get_running_app().user_data_dir) / "prefs.json"
        except Exception:
            _path = Path.home() / ".sketch_assistant_prefs.json"
    return _path


def use_file(path):
    """Point the settings at another file (tests)."""
    global _path
    _path = Path(path)


def get(key):
    try:
        data = json.loads(_file().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = {}
    return data.get(key, DEFAULTS[key])


def set(key, value):        # noqa: A001 - mirrors get()
    f = _file()
    try:
        data = json.loads(f.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = {}
    data[key] = value
    try:
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(data), encoding="utf-8")
    except OSError:
        pass                # the setting still applies for this session
