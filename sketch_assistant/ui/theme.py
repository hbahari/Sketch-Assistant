"""Colours and sizes shared by all screens: black ink, white paper, amber accent (matches the app icon)."""
from kivy.metrics import dp

BG = (0.965, 0.960, 0.950, 1)         # soft warm white (page)
SURFACE = (1, 1, 1, 1)                # cards and unselected buttons
SURFACE_HI = (0.925, 0.920, 0.910, 1) # pressed state
ACCENT = (0.09, 0.09, 0.10, 1)        # ink black: primary buttons, selected tabs
ACCENT_2 = (0.22, 0.21, 0.20, 1)      # charcoal: end of the button gradient
ACCENT_DARK = (0.60, 0.40, 0.02, 1)   # dark amber: label on a selected tile
AMBER = (0.94, 0.64, 0.13, 1)         # the pencil in the icon: secondary actions and highlights
TEXT = (0.09, 0.09, 0.10, 1)
MUTED = (0.45, 0.44, 0.43, 1)
WHITE = (1, 1, 1, 1)
ACCENT_HEX = "a66a00"                 # dark amber, for [color=...] markup on white


def radius():
    return dp(16)
