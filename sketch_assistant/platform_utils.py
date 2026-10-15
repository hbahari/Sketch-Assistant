"""Camera / gallery / storage helpers that work on desktop and mobile (via plyer)."""
import tempfile
from pathlib import Path


def pick_from_gallery(callback):
    from plyer import filechooser
    filechooser.open_file(filters=[("Images", "*.jpg", "*.jpeg", "*.png")],
                          on_selection=lambda sel: sel and callback(sel[0]))


def take_photo(callback):
    from plyer import camera
    path = str(Path(tempfile.gettempdir()) / "sketch_assistant_capture.jpg")
    try:
        camera.take_picture(filename=path, on_complete=lambda p: callback(p))
    except Exception:  # no camera backend (desktop) or camera app unavailable -> use the gallery
        pick_from_gallery(callback)


def export_dir():
    """Where Save PNG writes: Pictures/SketchAssistant on Android (visible in the gallery), else the home folder."""
    try:
        from android.storage import primary_external_storage_path
        base = Path(primary_external_storage_path()) / "Pictures" / "SketchAssistant"
        base.mkdir(parents=True, exist_ok=True)
        return base
    except Exception:
        pass
    try:
        from kivy.app import App
        base = Path(App.get_running_app().user_data_dir)
    except Exception:
        base = Path.home()
    base.mkdir(parents=True, exist_ok=True)
    return base
