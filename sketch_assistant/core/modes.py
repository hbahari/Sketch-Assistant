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
from . import eyes as _eyes
from . import noses as _noses
from . import steps as _steps
from .faces import detect_faces


def _mesh_reason():
    """Caricature can't fall back to anything without the face mesh; say why up front."""
    from .landmarks import unavailable_reason
    reason = unavailable_reason()
    return None if reason is None else "Cartoon can't work here: " + reason


def _detect_people(img):
    """Figures, as tappable boxes. Imported lazily so the pose models are only loaded
    when Posture mode is actually used."""
    from .bodies import detect
    return detect(img)
from .styles import BODY_STYLES, CARICATURE_STYLES, EYE_STYLES, HAND_STYLES, NOSE_STYLES, OBJECT_STYLES, STYLES


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
    locate: Optional[Callable] = None        # photo -> a box to start the box picker on, or None
    on_crop: Optional[Callable] = None       # (photo, crop, origin) -> None, told about every crop
    slider_labels: tuple = ("Less detail", "More detail")   # what the slider's two ends say
    requires: Optional[Callable] = None      # () -> why the mode can't work here, or None
    note: str = ""                   # shown whenever the mode is chosen, before any photo too

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
        # Framed by the user, but the box starts on an eye when the photo has a face: the
        # face sets the eye's scale, which the rules reading a crop on its own get wrong
        # (see core/eyes.py). Close-ups of one eye, with no face, start as before.
        key="eyes",
        label="Eyes",
        styles=EYE_STYLES,
        guide=_guides.eye_guides,
        stages=_steps.eye_stages,
        pick_box=True,
        locate=_eyes.propose_box,
        on_crop=_eyes.note_crop,
        found_fmt="Found an eye - drag a new box if it's not right",
        none_fmt="Drag a box round one eye",
        hint="Drag a box round one eye, then pick a style",
    ),
    Mode(
        # Framed by the user, like Eyes: a nose reference is often a close-up, and a box
        # the user draws is the one framing every renderer can trust.
        key="nose",
        label="Nose",
        styles=NOSE_STYLES,
        guide=_guides.nose_guides,
        stages=_steps.nose_stages,
        pick_box=True,
        hint="Drag a box round the nose, from between the eyes to the lip",
        # The box starts on the nose. Started on 85% of the photo, a close-up of a face
        # handed the analysis the mouth and chin too, and it found the nose on one of
        # sixteen test photos. See core/noses.py.
        locate=_noses.propose_box,
        on_crop=_noses.note_crop,
        found_fmt="Found the nose - drag a new box if it's not right",
        none_fmt="Couldn't find a face - drag a box round the nose",
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
        # Portraits only: the face is found and tapped as in Portrait mode, and the slider
        # sets how far the face's own differences from an average face are pushed.
        key="caricature",
        label="Cartoon",          # shown as Cartoon: a tester found "caricature" promised the wrong thing
        styles=CARICATURE_STYLES,
        detect=detect_faces,
        guide=_guides.caricature_guides,
        stages=_steps.caricature_stages,
        hint="Portraits only - pick a style; the slider sets how far to exaggerate",
        found_fmt="{n} face(s) found - tap a box (Cartoon works on portraits only)",
        none_fmt="No face found - Cartoon works on portraits only",
        note="Cartoon works on portraits only - add a photo of a face",
        slider_labels=("Less exaggerated", "More exaggerated"),
        requires=_mesh_reason,
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
