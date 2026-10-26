"""Camera, gallery and file saving for desktop and Android.

On Android everything goes through content:// URIs and the system picker, so the app needs
no storage or camera permission at all:

* the gallery uses ACTION_GET_CONTENT and the chosen URI is streamed into the app's cache;
* the camera writes into a MediaStore entry we create, which we then stream back;
* Save PNG inserts into MediaStore (Pictures/SketchAssistant) so the file shows in the gallery.

plyer is only used on desktop: its Android code resolves content URIs to filesystem paths,
which scoped storage (Android 10+) no longer allows.
"""
import os
import shutil
import tempfile
from pathlib import Path

ALBUM = "SketchAssistant"
RESULT_OK = -1
_REQUEST = 0x5A01
_pending = {"callback": None, "uri": None}


# --------------------------------------------------------------------------- Android plumbing
def _activity():
    """The running Android Activity, or None when not on Android."""
    try:
        from jnius import autoclass
        return autoclass("org.kivy.android.PythonActivity").mActivity
    except Exception:
        return None


def _read_uri(uri, suffix=".jpg"):
    """Copy a content:// URI into a private cache file and return its path.

    Uses a POSIX file descriptor so the bytes never cross the Java/Python boundary.
    """
    act = _activity()
    pfd = act.getContentResolver().openFileDescriptor(uri, "r")
    path = os.path.join(act.getCacheDir().getAbsolutePath(), "picked" + suffix)
    with os.fdopen(pfd.detachFd(), "rb") as src, open(path, "wb") as dst:
        shutil.copyfileobj(src, dst)
    return path


def _on_activity_result(request, result, intent):
    cb, uri = _pending["callback"], _pending["uri"]
    if request != _REQUEST or cb is None:
        return
    _pending.update(callback=None, uri=None)
    if result != RESULT_OK:
        return                                   # user cancelled
    target = uri or (intent.getData() if intent is not None else None)
    if target is None:
        return
    try:
        cb(_read_uri(target))
    except Exception:
        pass                                     # a failed read just leaves the current photo in place


def _start(intent, callback, uri=None):
    from android import activity as android_activity
    _pending.update(callback=callback, uri=uri)
    android_activity.unbind(on_activity_result=_on_activity_result)
    android_activity.bind(on_activity_result=_on_activity_result)
    _activity().startActivityForResult(intent, _REQUEST)


# --------------------------------------------------------------------------- photo input
def pick_from_gallery(callback):
    """Open the system picker and hand `callback` a readable image path."""
    if _activity() is None:
        from plyer import filechooser
        filechooser.open_file(filters=[("Images", "*.jpg", "*.jpeg", "*.png")],
                              on_selection=lambda sel: sel and callback(sel[0]))
        return
    from jnius import autoclass
    Intent = autoclass("android.content.Intent")
    intent = Intent(Intent.ACTION_GET_CONTENT)
    intent.setType("image/*")
    intent.addCategory(Intent.CATEGORY_OPENABLE)
    _start(intent, callback)


def take_photo(callback):
    """Launch the system camera app. Falls back to the gallery if it is unavailable."""
    act = _activity()
    if act is None:
        try:
            from plyer import camera
            path = str(Path(tempfile.gettempdir()) / "sketch_assistant_capture.jpg")
            camera.take_picture(filename=path, on_complete=callback)
        except Exception:                        # no camera backend on this desktop
            pick_from_gallery(callback)
        return
    try:
        from jnius import autoclass, cast
        Intent = autoclass("android.content.Intent")
        MediaStore = autoclass("android.provider.MediaStore")
        ContentValues = autoclass("android.content.ContentValues")
        Images = autoclass("android.provider.MediaStore$Images$Media")
        values = ContentValues()
        values.put("mime_type", "image/jpeg")
        uri = act.getContentResolver().insert(Images.EXTERNAL_CONTENT_URI, values)
        if uri is None:
            raise RuntimeError("could not create a MediaStore entry for the capture")
        intent = Intent(MediaStore.ACTION_IMAGE_CAPTURE)
        intent.putExtra(MediaStore.EXTRA_OUTPUT, cast("android.os.Parcelable", uri))
        intent.addFlags(Intent.FLAG_GRANT_WRITE_URI_PERMISSION)
        _start(intent, callback, uri)
    except Exception:
        pick_from_gallery(callback)


# --------------------------------------------------------------------------- saving
def _save_android(data, name):
    """Insert a PNG into the gallery under Pictures/SketchAssistant; returns its path or None."""
    act = _activity()
    if act is None:
        return None
    try:
        from jnius import autoclass
        ContentValues = autoclass("android.content.ContentValues")
        Images = autoclass("android.provider.MediaStore$Images$Media")
        values = ContentValues()
        values.put("_display_name", name)
        values.put("mime_type", "image/png")
        values.put("relative_path", f"Pictures/{ALBUM}")      # Android 10+
        resolver = act.getContentResolver()
        uri = resolver.insert(Images.EXTERNAL_CONTENT_URI, values)
        if uri is None:
            return None
        pfd = resolver.openFileDescriptor(uri, "w")
        with os.fdopen(pfd.detachFd(), "wb") as f:
            f.write(data)
        return Path("Pictures") / ALBUM / name
    except Exception:
        return None                                           # older Android: fall through to a file


def export_dir():
    """Where Save PNG writes when MediaStore is not available."""
    base = Path.home() / "Pictures" / ALBUM
    try:
        base.mkdir(parents=True, exist_ok=True)
        return base
    except OSError:                                           # read-only or sandboxed: app storage
        from kivy.app import App
        base = Path(App.get_running_app().user_data_dir)
        base.mkdir(parents=True, exist_ok=True)
        return base


def save_png(img_bgr, name):
    """Write a PNG and return where it landed; raises on failure."""
    import cv2
    ok, buf = cv2.imencode(".png", img_bgr)
    if not ok:
        raise IOError("PNG encoding failed")
    data = buf.tobytes()
    saved = _save_android(data, name)
    if saved is not None:
        return saved
    path = export_dir() / name
    path.write_bytes(data)                                    # unicode-safe on Windows
    return path


def reveal(path):
    """Open the folder containing `path` in the system file browser (desktop only)."""
    import subprocess
    import sys
    if _activity() is not None:
        return
    folder = str(Path(path).parent)
    try:
        if sys.platform.startswith("win"):
            os.startfile(folder)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", folder])
        else:
            subprocess.Popen(["xdg-open", folder])
    except Exception:
        pass
