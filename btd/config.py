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

#: Wider than it needs to be for the controls, on purpose: at 320 the tower
#: rack forced 13px labels and 34px icons, which were hard to read at a
#: glance while a round was running.
SIDEBAR_W = 360
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

# Warm wood-and-leaf palette, chosen to sit with the bright cartoon map art
# rather than against it. The previous dark slate scheme read as a dashboard
# bolted onto a children's game.
#
# Panels are carved wood, content sits on cream, and the accents are pulled
# straight out of the map: leaf green, sun yellow, berry red.

INK = (62, 41, 26)          # dark brown, primary text on cream
INK_SOFT = (122, 94, 70)    # secondary text on cream
PAPER = (252, 245, 226)     # cream panel fill
PAPER_DIM = (232, 218, 190) # cream, pressed or inactive

WOOD_DARK = (74, 48, 30)    # sidebar backdrop
WOOD = (112, 74, 44)        # panel frames
WOOD_LIGHT = (150, 102, 62) # raised edges and hover

# Cabinet woodwork. The sidebar is built as a shelf unit -- a beveled outer
# frame with recessed cubbies -- so these are the tones a bevel needs: a lit
# top edge, a mid face, a shaded bottom edge, and a dark recess behind.
WOOD_HILITE = (192, 136, 74)
WOOD_FACE = (146, 94, 46)
WOOD_SHADE = (92, 57, 27)
WOOD_RECESS = (50, 31, 16)

# Glossy round controls, as on the fast-forward and settings buttons.
BUTTON_BLUE = (62, 154, 228)
BUTTON_BLUE_DARK = (26, 88, 152)
BUTTON_RED = (226, 78, 66)
BUTTON_RED_DARK = (146, 38, 32)
BUTTON_GREEN = (110, 194, 74)
BUTTON_GREEN_DARK = (56, 122, 44)

# Outlined display text, the chunky style used for money and lives.
TEXT_OUTLINE = (48, 28, 14)
TEXT_GOLD = (255, 212, 74)
TEXT_WHITE = (255, 252, 242)

LEAF = (104, 182, 72)       # primary accent
LEAF_DARK = (62, 132, 58)
LEAF_LIGHT = (156, 214, 108)

SUN = (255, 196, 54)        # money
BERRY = (226, 76, 72)       # lives, danger
SKY = (104, 186, 226)       # secondary accent

# Semantic aliases used across the UI.
PANEL = PAPER
PANEL_LIGHT = (255, 252, 240)
PANEL_EDGE = WOOD
ACCENT = LEAF
ACCENT_DIM = LEAF_DARK
MONEY = (206, 142, 22)      # readable on cream, unlike pure SUN
LIVES = (198, 54, 52)
GOOD = LEAF_DARK
BAD = (196, 56, 52)
MUTED = INK_SOFT

RANGE_OK = (110, 230, 150)
RANGE_BAD = (245, 100, 100)

# --- Balloons ------------------------------------------------------------

#: Every non-MOAB balloon is drawn at this radius, so a stack of mixed types
#: reads as one consistent set rather than as art from several sources.
BALLOON_RADIUS = 18

#: When False, balloons are always drawn procedurally, which guarantees a
#: uniform silhouette and size across the whole ladder. Flip to True once a
#: complete, consistently sized balloon set exists in ``balloon_images/``.
#: See ASSETS.md.
USE_BALLOON_ART = False

# --- Audio ---------------------------------------------------------------

DEFAULT_MUSIC_VOLUME = 0.35
DEFAULT_SFX_VOLUME = 0.6
