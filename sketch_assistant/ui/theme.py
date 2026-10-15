"""Colours and sizes shared by all screens (light, teal-accented)."""
from kivy.metrics import dp

BG = (0.95, 0.98, 0.97, 1)
SURFACE = (1, 1, 1, 1)
SURFACE_HI = (0.86, 0.94, 0.93, 1)
ACCENT = (0.06, 0.62, 0.56, 1)       # teal
ACCENT_DARK = (0.04, 0.42, 0.38, 1)
TEXT = (0.07, 0.17, 0.17, 1)
MUTED = (0.42, 0.52, 0.51, 1)
WHITE = (1, 1, 1, 1)


def radius():
    return dp(16)
