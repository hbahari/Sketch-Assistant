"""The printable worksheet (PDF): layout, the PDF itself, and the Save choice on the Steps page.

Run with:  PYTHONPATH=. xvfb-run -a python -m pytest tests/test_worksheet.py
"""
import io
import os
import re
import time
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from sketch_assistant.core import worksheet as ws

FIX = Path(__file__).resolve().parent / "fixtures"


def fake_text(log=None):
    """A stand-in for Kivy's text drawing: a block sized by the text, recording what was asked."""
    def render(markup, px, width, color=(0, 0, 0)):
        if log is not None:
            log.append(markup)
        lines = max(1, len(markup) * px // (2 * max(1, int(width)))) + markup.count("\n")
        out = np.zeros((lines * int(px * 1.3), int(width), 4), np.uint8)
        out[:, :, 3] = 0
        return out
    return render


def fake_stages(n=7, shape=(800, 659)):
    rng = np.random.default_rng(0)
    return [SimpleNamespace(title=f"Stage {i + 1}", key=f"k{i}",
                            image=rng.integers(0, 255, shape + (3,), dtype=np.uint8)) for i in range(n)]


# --------------------------------------------------------------------------- no window needed
def test_paper_follows_the_region():
    assert ws.paper_for_country("CA") == "letter" and ws.paper_for_country("us") == "letter"
    assert ws.paper_for_country("GB") == "a4" and ws.paper_for_country("DE") == "a4"
    assert ws.paper_for_country("") == "a4", "unknown region: the world's default"


def test_grid_cells_are_square_and_cover_the_drawing():
    cols, rows = ws.grid_shape(659, 800)
    assert cols == 4 and rows * (659 / cols) >= 800 > (rows - 1) * (659 / cols)


def test_every_step_and_its_instructions_are_on_the_pages():
    """Each 'Step i of n' heading appears exactly once, with its own instructions, and the
    pages run reference, steps, practice, trace. Seen to fail when the last step was
    dropped by an off-by-one in the packing loop."""
    log = []
    stages = fake_stages(7)
    texts = [f"instructions for {s.title}" for s in stages]
    pages = ws.build_pages(stages[0].image, stages, texts, "Portrait - Line Art", "letter", fake_text(log))
    heads = [m for m in log if re.search(r"Step \d+ of 7", m)]
    assert [re.search(r"Step (\d+) of 7", h).group(1) for h in heads] == [str(i) for i in range(1, 8)]
    for t in texts:
        assert log.count(t) == 1
    W, H = ws.page_size("letter")
    assert all(p.shape == (H, W, 3) for p in pages)
    assert any("Grid method reference" in m for m in log)
    assert any("Practice grid" in m for m in log) and any("Trace or check" in m for m in log)
    assert len(pages) >= 4


def test_guide_lines_are_on_the_grid_pages():
    """The subject's guide lines go on the photo and the drawing (page 1) and on the practice
    and trace pages, drawn fresh at each size; never on the step pages. Checked with guide
    'lines' of a colour nothing else on the page uses."""
    calls = []

    def guides_at(w, h):
        calls.append((w, h))
        g = np.full((h, w, 3), 255, np.uint8)
        g[h // 2 - 3:h // 2 + 3, :] = (0, 0, 255)                     # pure red, BGR
        return g
    stages = fake_stages(4)
    plain = ws.build_pages(stages[0].image, stages, [""] * 4, "t", "letter", fake_text())
    pages = ws.build_pages(stages[0].image, stages, [""] * 4, "t", "letter", fake_text(), guides_at)
    assert len(calls) == 4, f"{len(calls)} guide drawings: photo, drawing, practice and trace"
    changed = [int((np.abs(a.astype(int) - b.astype(int)).max(axis=2) > 40).sum()) for a, b in zip(plain, pages)]
    assert changed[0] > 0 and changed[-2] > 0 and changed[-1] > 0, changed
    assert all(c == 0 for c in changed[1:-2]), f"guides on a step page: {changed}"
    assert max(c[0] for c in calls) > 1000, "the practice page's guides weren't drawn at its size"


def test_the_grid_is_grey_so_the_blue_guides_stand_out():
    assert len(set(ws.GRID)) == 1, "grid colour isn't a neutral grey"


def test_the_practice_squares_match_the_size_printed_on_page_one():
    """Page 1 tells you how big to rule your squares; the practice page must really be that
    size when printed at 100%."""
    cols, rows = ws.grid_shape(659, 800)
    cell = ws.practice_cell_inches("letter", cols, rows)
    W, H = ws.page_size("letter")
    m = ws._px(ws.MARGIN)
    field = ws.practice_field("letter", cols, rows, None, W - 2 * m, H - 2 * m - ws._px(1.15))
    pad = ws._px(0.22)
    grid_w = field.shape[1] - pad
    assert abs(grid_w / cols / ws.DPI - cell) < 0.01
    assert field.shape[0] <= H - 2 * m and field.shape[1] <= W - 2 * m


@pytest.mark.parametrize("paper,size_pt", [("letter", (612, 792)), ("a4", (595.4, 841.7))])
def test_the_pdf_is_valid_and_exactly_paper_sized(paper, size_pt):
    """A real PDF reader opens it, the page count matches, every page is exactly the paper
    (so it prints 1:1), and every cross-reference points at its object. Seen to fail with
    the cross-reference offsets one byte out."""
    pypdf = pytest.importorskip("pypdf")
    pages = [np.full((ws.page_size(paper)[1], ws.page_size(paper)[0], 3), v, np.uint8) for v in (255, 200, 120)]
    data = ws.pdf_bytes(pages, paper)
    assert data.startswith(b"%PDF-1.4") and data.rstrip().endswith(b"%%EOF")
    xref = int(re.search(rb"startxref\n(\d+)", data).group(1))
    rows = data[xref:].split(b"\n")[3:]
    for i, row in enumerate(r for r in rows if r.endswith(b" n ")):
        off = int(row[:10])
        assert data[off:].startswith(b"%d 0 obj" % (i + 1)), f"xref entry {i + 1} is wrong"
    reader = pypdf.PdfReader(io.BytesIO(data), strict=True)
    assert len(reader.pages) == 3
    for pg in reader.pages:
        w, h = float(pg.mediabox.width), float(pg.mediabox.height)
        assert abs(w - size_pt[0]) < 1 and abs(h - size_pt[1]) < 1


# --------------------------------------------------------------------------- with a window
pytest.importorskip("kivy")
os.environ.setdefault("KIVY_NO_ARGS", "1")
os.environ.setdefault("KIVY_NO_CONSOLELOG", "1")
from kivy.config import Config  # noqa: E402

Config.set("graphics", "width", "420")
Config.set("graphics", "height", "800")
from kivy.base import EventLoop  # noqa: E402
from kivy.clock import Clock  # noqa: E402


def _tick(n=6, wait=0.0):
    end = time.time() + wait
    while True:
        for _ in range(n):
            Clock.tick()
            EventLoop.idle()
        if time.time() >= end:
            break
        time.sleep(0.03)


def test_printed_text_reads_top_to_bottom():
    """The first line of a block must be at its top. The first worksheet printed every line
    upside down (Kivy's pixel rows were flipped the wrong way)."""
    EventLoop.ensure_window()
    from sketch_assistant.ui.print_text import render_text
    rgba = render_text("[b]WWWWWWWW[/b]\n\n\n\n\n\n\n.", 40, 600)
    ink = rgba[:, :, 3].sum(axis=1)
    q = len(ink) // 4
    assert ink[:q].sum() > 5 * ink[-q:].sum(), "the heavy first line isn't at the top"


def test_printed_text_honours_bold_markup():
    """[b]...[/b] must make bold text, not print the tags. Seen to fail with Kivy's plain
    text label, which prints '[b]' literally."""
    EventLoop.ensure_window()
    from sketch_assistant.ui.print_text import render_text

    def ink_width(markup):
        cols = np.where(render_text(markup, 40, 1200)[:, :, 3].max(axis=0) > 0)[0]
        return cols[-1] - cols[0]
    plain, tagged = ink_width("Hello"), ink_width("[b]Hello[/b]")
    assert tagged < plain * 1.4, f"tags printed: {tagged}px vs {plain}px"


@pytest.fixture(scope="module")
def app(tmp_path_factory):
    from kivy.core.window import Window
    from sketch_assistant import prefs
    from sketch_assistant.app import SketchApp
    from sketch_assistant.core.modes import build_stages
    prefs.use_file(tmp_path_factory.mktemp("prefs") / "prefs.json")
    prefs.set("tour_done", True)
    EventLoop.ensure_window()
    a = SketchApp()
    sm = a.build()
    a.root = sm
    Window.add_widget(sm)
    sm.transition.duration = 0
    _tick()
    home = sm.get_screen("home")
    home._load(str(FIX / "portraits_close" / "close_12.jpg"))
    _tick()
    home.on_face(0, home.regions["portrait"][0])
    a.stages = build_stages(a.mode, a.source_img, a.style_key, a.get_detail(a.style_key),
                            a.landmarks, a.crop_shape, a.crop_box)
    sm.current = "steps"
    _tick()
    yield a, sm
    Window.remove_widget(sm)


def test_save_offers_the_worksheet_and_saves_a_pdf(app, monkeypatch):
    pypdf = pytest.importorskip("pypdf")
    from sketch_assistant import prefs
    from sketch_assistant.ui import steps as steps_mod
    a, sm = app
    st = sm.get_screen("steps")
    saved, opened = {}, []
    monkeypatch.setattr(steps_mod, "save_document", lambda data, name: saved.update(data=data, name=name) or ("Downloads/SketchAssistant/" + name, "HANDLE"))
    monkeypatch.setattr(steps_mod, "open_document", lambda h: opened.append(h) or True)
    prefs.set("paper", "a4")
    st.save_btn.dispatch("on_release")
    _tick()
    assert st.paper_btns["a4"].active and not st.paper_btns["letter"].active
    st.pdf_btn.dispatch("on_release")
    _tick(wait=0.3)
    assert saved["name"] == f"worksheet_portrait_{a.style_key}.pdf" and opened == ["HANDLE"]
    reader = pypdf.PdfReader(io.BytesIO(saved["data"]))
    assert len(reader.pages) >= 4
    assert abs(float(reader.pages[0].mediabox.height) - 841.7) < 1, "not the A4 that was chosen"
    assert "Downloads" in st.caption.text


def test_paper_choice_is_remembered_and_defaults_by_region(app, monkeypatch):
    from sketch_assistant import prefs
    from sketch_assistant.ui import steps as steps_mod
    a, sm = app
    st = sm.get_screen("steps")
    prefs.set("paper", None)
    monkeypatch.setattr(steps_mod, "local_country", lambda: "CA")
    assert st.paper() == "letter"
    monkeypatch.setattr(steps_mod, "local_country", lambda: "FR")
    assert st.paper() == "a4"
    st.set_paper("letter")
    assert prefs.get("paper") == "letter" and st.paper() == "letter"
