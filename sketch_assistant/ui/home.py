"""Main page: header, the subject bar, photo + preview side by side, style tiles.

Everything that varies by subject comes from core/modes.py, so adding a subject needs no
change here. (The detail slider lives on the guide page.)
"""
from pathlib import Path
from kivy.clock import Clock
from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import Screen

from ..core.faces import crop_info, crop_to_box, load_image
from ..core.modes import MODES, mode_of
from ..core.styles import render
from ..platform_utils import pick_from_gallery, take_photo
from . import theme
from .widgets import (BoxSelector, Card, FaceSelector, LogoBar, ModeBar, RoundButton,
                      UploadCard, to_texture)

EXAMPLES = Path(__file__).resolve().parent.parent / "assets" / "examples"


class HomeScreen(Screen):
    def __init__(self, app, **kw):
        super().__init__(**kw)
        self.app_ref = app
        self.photo_loaded, self.regions, self.tiles = False, None, {}
        root = BoxLayout(orientation="vertical", spacing=dp(6))
        root.add_widget(LogoBar())
        body = BoxLayout(orientation="vertical", spacing=dp(8), padding=(0, 0, 0, dp(14)))

        # the subject bar spans the full width so it can scroll under the page margins
        self.mode_bar = ModeBar([(m.key, m.label) for m in MODES.values()], self.set_mode)
        self.mode_bar.select(app.mode)
        body.add_widget(self.mode_bar)

        inner = BoxLayout(orientation="vertical", spacing=dp(8), padding=(dp(14), 0))
        row = BoxLayout(spacing=dp(10))  # photo (left) and sketch preview (right)
        self.box = BoxLayout()  # upload card <-> photo card
        self.upload_btn = UploadCard(text="[b]Add a photo[/b]\n[size=12sp]Take one or upload from gallery[/size]", markup=True,
                                     font_size=sp(16), radii=[dp(24)] * 4, on_release=lambda *_: self.choose_source())
        self.selector = FaceSelector(on_select=self.on_face)
        self.box_picker = BoxSelector(on_select=self.on_box)
        self.photo_card = Card(padding=dp(6)); self.photo_card.add_widget(self.selector)
        self.box.add_widget(self.upload_btn)
        self.preview = Image(fit_mode="contain")
        self.placeholder = Label(text="Your sketch\nwill appear here", color=theme.MUTED, halign="center", font_size=sp(13))
        self.preview_card = Card(padding=dp(6)); self.preview_card.add_widget(self.placeholder)
        row.add_widget(self.box); row.add_widget(self.preview_card)
        inner.add_widget(row)

        # status line + "New photo" button (appears once a photo is loaded)
        status_row = BoxLayout(size_hint_y=None, height=dp(34), spacing=dp(8))
        self.status = Label(text="Add a photo to begin", color=theme.MUTED, font_size=sp(13), halign="left", valign="middle")
        self.status.bind(size=lambda w, v: setattr(w, "text_size", v))
        self.new_photo_btn = RoundButton(text="+ New photo", bold=True, font_size=sp(12), size_hint=(None, 1), width=dp(112),
                                         radii=[dp(17)] * 4, fill=theme.AMBER, on_release=lambda *_: self.choose_source())
        status_row.add_widget(self.status)
        self.status_row = status_row
        inner.add_widget(status_row)

        self.rows = {k: self._make_row(m.styles) for k, m in MODES.items()}
        self.style_holder = BoxLayout(size_hint_y=None, height=dp(100))
        self.style_holder.add_widget(self.rows[app.mode])
        inner.add_widget(self.style_holder)

        self.guide_btn = RoundButton(text="Enlarge & drawing guide", bold=True, size_hint_y=None, height=dp(54),
                                     disabled=True, active=True, radii=[dp(27)] * 4,
                                     on_release=lambda *_: self.manager.switch_to_guide())
        inner.add_widget(self.guide_btn)
        body.add_widget(inner)
        root.add_widget(body)
        self.add_widget(root)

    def _make_row(self, styles):
        row = BoxLayout(spacing=dp(8))
        for key, st in styles.items():
            b = RoundButton(text=st.short, source=str(EXAMPLES / f"{key}.png"), disabled=True, bold=True,
                            font_size=sp(11), valign="bottom", padding=(0, dp(7)), on_release=lambda _b, k=key: self.on_style(k))
            self.tiles[key] = b
            row.add_widget(b)
        return row

    def _set_preview(self, sketch):
        self.preview_card.clear_widgets()
        if sketch is None:
            self.preview_card.add_widget(self.placeholder)
        else:
            self.preview.texture = to_texture(sketch)
            self.preview_card.add_widget(self.preview)

    def _reset_results(self):
        a = self.app_ref
        a.sketch, a.style_key = None, None
        for b in self.tiles.values():
            b.disabled, b.active = True, False
        self.guide_btn.disabled = True
        self._set_preview(None)

    # modes
    def set_mode(self, key):
        a = self.app_ref
        if key == a.mode:
            return
        a.mode = key
        self.mode_bar.select(key)
        self.style_holder.clear_widgets(); self.style_holder.add_widget(self.rows[key])
        self._reset_results()
        if self.photo_loaded:
            self._prepare_photo()
        else:
            self.status.text = "Add a photo to begin"

    def _prepare_photo(self):
        """Set the photo card up for this mode: a detector's boxes, a drawn box, or neither."""
        a, m = self.app_ref, mode_of(self.app_ref.mode)
        self._show_picker(self.box_picker if m.pick_box else self.selector)
        if m.pick_box:                             # the user draws the region
            self.box_picker.set_photo(a.photo)
            self._enable_styles(m)
            self.status.text = m.hint
            self.on_box(self.box_picker.box)       # render the default box straight away
            return
        if m.detect is None:                       # whole image is used, no detection
            self.selector.set_photo(a.photo, [])
            a.source_img, a.landmarks, a.crop_shape, a.crop_box = a.photo, (), None, None
            self._enable_styles(m)
            self.status.text = m.hint
            self.on_style(m.default_style)
            return
        if self.regions is None:
            self.regions = m.detect(a.photo)
        self.selector.set_photo(a.photo, self.regions)
        n = len(self.regions)
        self.status.text = m.found_fmt.format(n=n) if n else m.none_fmt

    def _show_picker(self, widget):
        """Swap the photo card's contents between the tap-a-box and draw-a-box pickers."""
        if widget.parent is self.photo_card:
            return
        self.photo_card.clear_widgets()
        self.photo_card.add_widget(widget)

    def on_box(self, box):
        """A region was drawn (or defaulted): crop to it and re-render the current style."""
        a = self.app_ref
        a.source_img = crop_to_box(a.photo, box)
        a.landmarks, a.crop_box = (), None
        a.crop_shape = a.source_img.shape[:2]
        self.on_style(a.style_key or mode_of(a.mode).default_style)

    def _enable_styles(self, m):
        for key in m.styles:
            self.tiles[key].disabled = False

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
        self.app_ref.photo, self.regions, self.photo_loaded = img, None, True
        if self.new_photo_btn.parent is None:
            self.status_row.add_widget(self.new_photo_btn)
        self.box.clear_widgets(); self.box.add_widget(self.photo_card)
        self._reset_results()
        self._prepare_photo()

    # detected region + style
    def on_face(self, idx, face):
        """A detected box was tapped: crop to it and offer this mode's styles."""
        a, m = self.app_ref, mode_of(self.app_ref.mode)
        a.source_img, a.landmarks, a.crop_box = crop_info(a.photo, face)
        a.crop_shape = a.source_img.shape[:2]
        self._enable_styles(m)
        self.status.text = m.hint
        self.on_style(m.default_style)

    def on_style(self, key):
        a = self.app_ref
        self.apply(key, render(key, a.source_img, a.get_detail(key)))

    def apply(self, key, sketch):
        """Show `sketch` as the current result (also used when returning from the guide page)."""
        a = self.app_ref
        a.style_key, a.sketch = key, sketch
        for k, b in self.tiles.items():
            b.active = k == key
        self._set_preview(sketch)
        self.guide_btn.disabled = False
