"""
Global configuration constants for Balloon TD.

Everything that is a tunable number or a shared piece of layout lives here so
that gameplay balance and screen layout can be adjusted in one place.

The original project was authored against an 800x600 window with the UI drawn
on top of the playfield. This version separates the playfield from a dedicated
sidebar, and scales the original map coordinates up by ``MAP_SCALE`` so the
existing waypoint data and background art still line up.
"""

# --- Window layout -------------------------------------------------------

#: Original design resolution the map artwork and waypoint CSV were authored in.
SOURCE_MAP_SIZE = (800, 600)

#: Uniform scale applied to source map coordinates. 800*1.2 = 960, 600*1.2 = 720.
MAP_SCALE = 1.2

MAP_W = int(SOURCE_MAP_SIZE[0] * MAP_SCALE)
MAP_H = int(SOURCE_MAP_SIZE[1] * MAP_SCALE)

SIDEBAR_W = 320
SCREEN_W = MAP_W + SIDEBAR_W
SCREEN_H = MAP_H

FPS = 60

#: Fixed simulation timestep in seconds. The simulation always advances in
#: whole steps of this size so behaviour is identical regardless of the
#: machine's real frame rate.
TICK = 1.0 / 60.0

#: Upper bound on simulation steps per rendered frame. Prevents a spiral of
#: death if the process is suspended (e.g. window dragged, tab backgrounded).
MAX_STEPS_PER_FRAME = 8

# --- Economy -------------------------------------------------------------

STARTING_MONEY = 650
STARTING_LIVES = 150

#: Fraction of total money spent on a tower that is refunded when it is sold.
SELL_REFUND = 0.75

#: Money awarded for finishing round N is BASE + PER_ROUND * N. Popping pays
#: roughly $1 per balloon layer, which alone does not keep pace with tower
#: prices in the early rounds, so the completion bonus carries the early game.
ROUND_BONUS_BASE = 110
ROUND_BONUS_PER_ROUND = 18

# --- Speed ---------------------------------------------------------------

#: Selectable game speeds. The simulation runs more steps per frame rather
#: than raising the frame-rate cap, so physics stays identical at every speed.
SPEED_STEPS = (1, 2, 3)

# --- Difficulty ----------------------------------------------------------

DIFFICULTIES = {
    "easy": {
        "label": "Easy",
        "money": 1200,
        "lives": 200,
        "hp_scale": 0.8,
        "speed_scale": 0.9,
        "cost_scale": 0.9,
        "count_scale": 0.8,
        "rounds": 40,
    },
    "normal": {
        "label": "Normal",
        "money": 850,
        "lives": 150,
        "hp_scale": 1.0,
        "speed_scale": 1.0,
        "cost_scale": 1.0,
        "count_scale": 1.1,
        "rounds": 60,
    },
    "hard": {
        "label": "Hard",
        "money": 700,
        "lives": 100,
        "hp_scale": 1.35,
        "speed_scale": 1.08,
        "cost_scale": 1.08,
        "count_scale": 1.25,
        "rounds": 80,
    },
}

DEFAULT_DIFFICULTY = "normal"

# --- Palette -------------------------------------------------------------

# A single restrained palette keeps the HUD readable over busy map art.
INK = (18, 21, 28)
INK_SOFT = (58, 64, 78)
PAPER = (238, 241, 246)
PANEL = (30, 34, 44)
PANEL_LIGHT = (44, 50, 63)
PANEL_EDGE = (68, 76, 94)

ACCENT = (86, 176, 255)
ACCENT_DIM = (48, 104, 154)
MONEY = (255, 205, 74)
LIVES = (255, 96, 104)
GOOD = (108, 214, 138)
BAD = (240, 92, 92)
MUTED = (140, 149, 168)

RANGE_OK = (110, 230, 150)
RANGE_BAD = (245, 100, 100)

# --- Audio ---------------------------------------------------------------

DEFAULT_MUSIC_VOLUME = 0.35
DEFAULT_SFX_VOLUME = 0.6
