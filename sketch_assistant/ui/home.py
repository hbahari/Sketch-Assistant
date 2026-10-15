"""Main page: header, mode bar, photo + preview side by side, 5 style tiles, guide button."""
from pathlib import Path
from kivy.clock import Clock
from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import Screen

from ..core.faces import crop_face, detect_faces, load_image
from ..core.styles import STYLES, render
from ..platform_utils import pick_from_gallery, take_photo
from . import theme
from .widgets import Card, FaceSelector, Header, RoundButton, UploadCard, to_texture

EXAMPLES = Path(__file__).resolve().parent.parent / "assets" / "examples"


class HomeScreen(Screen):
    def __init__(self, app, **kw):
        super().__init__(**kw)
        self.app_ref, r = app, theme.radius()
        self.photo_loaded = False
        root = BoxLayout(orientation="vertical", spacing=dp(12))
        root.add_widget(Header("Sketch Assistant", "Turn any photo into a drawing guide"))
        body = BoxLayout(orientation="vertical", spacing=dp(10), padding=(dp(14), 0, dp(14), dp(14)))

        bar = BoxLayout(size_hint_y=None, height=dp(46), spacing=0)  # attached segmented control
        bar.add_widget(RoundButton(text="Portrait", radii=[r, 0, 0, r], active=True, bold=True))
        bar.add_widget(RoundButton(text="Object (soon)", radii=[0, r, r, 0], disabled=True))
        body.add_widget(bar)

        # photo (left) and sketch preview (right), side by side
        row = BoxLayout(spacing=dp(10))
        self.box = BoxLayout()  # upload card <-> photo card
        self.upload_btn = UploadCard(
            text="[b]Add a photo[/b]\n[size=12sp]Take one or upload from gallery[/size]", markup=True,
            font_size=sp(16), radii=[dp(24)] * 4, on_release=lambda *_: self.choose_source())
        self.selector = FaceSelector(on_select=self.on_face)
        self.photo_card = Card(padding=dp(6)); self.photo_card.add_widget(self.selector)
        self.box.add_widget(self.upload_btn)
        self.preview = Image(fit_mode="contain")
        self.placeholder = Label(text="Your sketch\nwill appear here", color=theme.MUTED, halign="center", font_size=sp(13))
        self.preview_card = Card(padding=dp(6)); self.preview_card.add_widget(self.placeholder)
        row.add_widget(self.box); row.add_widget(self.preview_card)
        body.add_widget(row)

        self.status = Label(text="Add a photo to begin", size_hint_y=None, height=dp(24), color=theme.MUTED, font_size=sp(13))
        self.status.bind(on_touch_down=lambda w, t: self.photo_loaded and w.collide_point(*t.pos) and self.choose_source())
        body.add_widget(self.status)

        # 5 compact style tiles that together span the width of the two boxes
        style_row = BoxLayout(size_hint_y=None, height=dp(100), spacing=dp(8))
        self.style_btns = {}
        for key, st in STYLES.items():
            b = RoundButton(text=st.short, source=str(EXAMPLES / f"{key}.png"), disabled=True, bold=True,
                            font_size=sp(11), valign="bottom", padding=(0, dp(7)),
                            on_release=lambda _b, k=key: self.on_style(k))
            self.style_btns[key] = b
            style_row.add_widget(b)
        body.add_widget(style_row)

        self.guide_btn = RoundButton(text="Enlarge & drawing guide", bold=True, size_hint_y=None, height=dp(54),
                                     disabled=True, active=True, radii=[dp(27)] * 4,
                                     on_release=lambda *_: self.manager.switch_to_guide())
        body.add_widget(self.guide_btn)
        root.add_widget(body)
        self.add_widget(root)

    def _set_preview(self, sketch):
        self.preview_card.clear_widgets()
        if sketch is None:
            self.preview_card.add_widget(self.placeholder)
        else:
            self.preview.texture = to_texture(sketch)
            self.preview_card.add_widget(self.preview)

    # photo input
    def choose_source(self):
        content = BoxLayout(orientation="vertical", spacing=dp(10), padding=dp(12))
        pop = Popup(title="Add photo", content=content, size_hint=(0.85, 0.35), separator_height=0,
                    background="", background_color=theme.BG, title_color=theme.TEXT)
        content.add_widget(RoundButton(text="Take photo", on_release=lambda *_: (pop.dismiss(), take_photo(self.load))))
        content.add_widget(RoundButton(text="Choose from gallery", on_release=lambda *_: (pop.dismiss(), pick_from_gallery(self.load))))
        pop.open()

    def load(self, path):
        Clock.schedule_once(lambda dt: self._load(path))  # callbacks may come from other threads

    def _load(self, path):
        try:
            img = load_image(path)
        except ValueError as e:
            self.status.text = str(e)
            return
        faces = detect_faces(img)
        self.app_ref.photo, self.app_ref.sketch, self.photo_loaded = img, None, True
        self.box.clear_widgets(); self.box.add_widget(self.photo_card)
        self.selector.set_photo(img, faces)
        self.status.text = f"{len(faces)} face(s) found - tap a box" if faces else "No faces found - tap here for another photo"
        for b in self.style_btns.values():
            b.disabled, b.active = True, False
        self.guide_btn.disabled = True
        self._set_preview(None)

    # face + style
    def on_face(self, idx, face):
        self.app_ref.face_img = crop_face(self.app_ref.photo, face)
        for b in self.style_btns.values():
            b.disabled = False
        self.status.text = "Pick a sketch style (tap here to change photo)"
        self.on_style("line_art")

    def on_style(self, key):
        self.apply(key, render(key, self.app_ref.face_img))

    def apply(self, key, sketch):
        """Show `sketch` as the current result (also used when returning from the guide page)."""
        a = self.app_ref
        a.style_key, a.sketch = key, sketch
        for k, b in self.style_btns.items():
            b.active = k == key
        self._set_preview(sketch)
        self.guide_btn.disabled = False
