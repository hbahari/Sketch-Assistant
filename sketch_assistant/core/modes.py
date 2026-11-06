"""What a subject mode is, and the list of them.

Before this existed, "which subject am I drawing" was answered in eight different places
by `if mode == "object"` and `if style_key.startswith("obj_")`. Adding Hands that way
would have meant finding all eight again, and Legs after it a ninth and tenth. So a mode
is now one object that carries everything that varies with the subject:

    styles        the renderers offered for it
    detect        how to find the subject in the photo (None = use the whole frame)
    guide         which construction lines to draw over the sketch
    stages        how to break the drawing into steps
    materials     whether the surface-material guide is relevant

To add a subject, append one `Mode` here and the text entries it needs in `data/`. No UI
or pipeline file has to change.
"""
from dataclasses import dataclass
from typing import Callable, Optional

from . import guides as _guides
from . import steps as _steps
from .faces import detect_faces


def _detect_people(img):
    """Figures, as tappable boxes. Imported lazily so the pose models are only loaded
    when Posture mode is actually used."""
    from .bodies import detect
    return detect(img)
from .styles import BODY_STYLES, HAND_STYLES, OBJECT_STYLES, STYLES


@dataclass(frozen=True)
class Mode:
    key: str
    label: str                       # what the mode button says
    styles: dict                     # style key -> Style
    guide: Callable                  # (overlay, w, h, th, ctx) -> list of text labels
    stages: Callable                 # (ctx) -> list of Stage
    detect: Optional[Callable] = None        # img -> list of Face-like boxes to tap
    materials: bool = False          # show the material guide on the drawing-guide page
    pick_box: bool = False           # the user draws the region instead of tapping a found one
    multi: bool = False              # several detections can be chosen at once
    hint: str = ""                   # status line once a photo is loaded
    found_fmt: str = ""              # status line after a successful detection ({n} boxes)
    none_fmt: str = ""               # ...and after an unsuccessful one

    @property
    def default_style(self):
        return next(iter(self.styles))


MODES = {m.key: m for m in (
    Mode(
        key="portrait",
        label="Portrait",
        styles=STYLES,
        detect=detect_faces,
        guide=_guides.face_guides,
        stages=_steps.portrait_stages,
        hint="Pick a sketch style",
        found_fmt="{n} face(s) found - tap a box",
        none_fmt="No faces found - use New photo to try another",
    ),
    Mode(
        key="object",
        label="Object",
        styles=OBJECT_STYLES,
        guide=_guides.frame_guides,
        stages=_steps.object_stages,
        materials=True,
        pick_box=True,
        hint="Drag a box round one object, then pick a style",
    ),
    Mode(
        key="hands",
        label="Hands",
        styles=HAND_STYLES,
        guide=_guides.hand_guides,
        stages=_steps.hand_stages,
        hint="Pick a style (one hand, plain background)",
    ),
    Mode(
        key="body",
        label="Posture",
        styles=BODY_STYLES,
        detect=_detect_people,
        guide=_guides.body_guides,
        stages=_steps.body_stages,
        multi=True,
        hint="Pick a style",
        found_fmt="{n} figure(s) found - tap one, or several",
        none_fmt="No figure found - use New photo to try another",
    ),
)}

DEFAULT = "portrait"


def mode_of(key):
    return MODES.get(key, MODES[DEFAULT])


def styles_for(key):
    return mode_of(key).styles


def mode_of_style(style_key):
    """Which mode offers this style. Used where only the style key is to hand."""
    for m in MODES.values():
        if style_key in m.styles:
            return m
    return MODES[DEFAULT]


def build_stages(mode, source_img, style_key, detail, lm=(), crop_shape=None, box=None, progress=None):
    """Build the drawing sequence for `mode`. Returns a list of steps.Stage.

    This is the one place that turns a mode into a stage ladder; the UI calls it without
    knowing which subject it is dealing with.
    """
    job = _steps.Job(source_img, style_key, detail, tuple(lm), crop_shape, box, progress, mode)
    return mode_of(mode).stages(job)
