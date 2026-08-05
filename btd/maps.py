"""
Map definitions and background rendering.

The original project had exactly one map: a 2,500-row CSV of waypoints paired
with a background image that already had the track painted on it. That is kept
as-is, but adding a second map that way would mean hand-producing another
2,500-row CSV.

So maps here are authored as a list of control points instead. A Catmull-Rom
spline turns them into a smooth path. Every shipped map pairs those points
with hand-drawn artwork, and ``tools/trace_map.py`` derives the points *from*
that artwork so the two cannot drift apart.

A map may also omit artwork entirely, in which case the background is painted
from the path itself. No shipped map does that today, but it is the on-ramp
for a new one: drop in control points, play it immediately, and replace the
generated background with art later.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

import pygame

from . import assets
from .config import MAP_H, MAP_SCALE, MAP_W
from .path import Path, catmull_rom, load_waypoints_csv


@dataclass(frozen=True)
class MapDef:
    """A playable map.

    Attributes:
        key: Unique identifier, used in save data.
        name: Display name.
        difficulty: Descriptive label shown on the map picker.
        csv: Waypoint CSV to load, or ``None`` to use ``control``.
        background: Background image to use, or ``None`` to render one.
        control: Control points for the spline, in map coordinates.
        grass: Base ground colour for rendered backgrounds.
        track: Track colour for rendered backgrounds.
        track_width: Track width in pixels.
        clearance: How far a tower must stay from the path centre line. Set
            it for art-backed maps, where the painted track width has nothing
            to do with ``track_width``; ``None`` derives a sensible default.
    """

    key: str
    name: str
    difficulty: str
    csv: str | None = None
    background: str | None = None
    control: tuple[tuple[float, float], ...] = ()
    grass: tuple[int, int, int] = (104, 152, 84)
    track: tuple[int, int, int] = (176, 152, 116)
    track_width: int = 46
    decor: tuple[int, int, int] = field(default=(76, 118, 62))
    clearance: float | None = None


MAPS: dict[str, MapDef] = {}


def _add(m: MapDef) -> MapDef:
    """Register a map definition."""
    MAPS[m.key] = m
    return m


_add(MapDef(
    key="meadow",
    name="Monkey Meadow",
    difficulty="Intermediate",
    csv="equidistant_points.csv",
    background="background_images/Background.webp",
))

# Traced from artwork with tools/trace_map.py -- the control points below are
# the measured centre line of the painted track, not hand-placed guesses.
_add(MapDef(
    key="sprint",
    name="Sprint Track",
    difficulty="Beginner",
    background="background_images/sprint.png",
    clearance=30.0,
    # Three laps of the oval, one per lane, working outward from lane 1 --
    # which is what the "1 2 3" markings painted at the start line count.
    # Balloons enter on the inside lane and leave on the outside, so the
    # track is long and every tower placed on it gets three passes.
    control=(
        (958, 554), (844, 554), (730, 554), (616, 554), (503, 554),
        (389, 554), (277, 537), (193, 463), (165, 355), (202, 249),
        (292, 182), (405, 171), (519, 171), (632, 173), (733, 223),
        (789, 320), (780, 432), (711, 520), (604, 554), (492, 570),
        (380, 594), (268, 587), (176, 523), (122, 424), (120, 311),
        (169, 209), (259, 141), (370, 121), (484, 121), (598, 121),
        (708, 146), (795, 217), (840, 321), (833, 433), (775, 530),
        (680, 591), (568, 606), (455, 623), (343, 642), (232, 625),
        (141, 557), (83, 460), (66, 349), (94, 239), (161, 148),
        (258, 90), (370, 72), (484, 72), (597, 73), (709, 93),
        (804, 154), (868, 247), (892, 358), (872, 469), (810, 564),
        (717, 629), (616, 652), (730, 652), (844, 652), (958, 652),
    ),
))

_add(MapDef(
    key="park",
    name="Park Path",
    difficulty="Advanced",
    background="background_images/park.png",
    clearance=34.0,
    control=(
        (800, 4), (798, 35), (800, 66), (800, 97), (803, 127),
        (784, 152), (759, 170), (729, 177), (698, 175), (670, 162),
        (647, 141), (622, 123), (596, 107), (567, 97), (537, 86),
        (507, 78), (477, 73), (446, 74), (415, 76), (385, 82),
        (355, 90), (326, 102), (299, 117), (274, 135), (250, 154),
        (229, 177), (212, 203), (206, 232), (181, 251), (170, 280),
        (162, 310), (156, 341), (156, 372), (158, 403), (164, 433),
        (166, 463), (178, 490), (188, 519), (204, 544), (227, 566),
        (243, 591), (265, 613), (292, 628), (318, 646), (346, 660),
        (375, 670), (405, 664), (434, 676), (465, 676), (476, 674),
        (507, 674), (537, 668), (567, 661), (594, 646), (619, 629),
        (645, 611), (667, 589), (680, 562), (674, 532), (652, 511),
        (623, 500), (595, 513), (571, 532), (545, 549), (517, 563),
        (488, 572), (457, 574), (425, 574), (395, 568), (366, 556),
        (340, 540), (314, 524), (298, 499), (285, 472), (269, 446),
        (258, 417), (256, 386), (258, 355), (263, 324), (270, 294),
        (289, 269), (308, 245), (330, 223), (357, 208), (384, 194),
        (414, 187), (445, 182), (475, 186), (498, 206), (506, 236),
        (488, 260), (462, 276), (432, 281), (403, 291), (391, 319),
        (367, 336), (352, 362), (360, 392), (370, 421), (381, 449),
        (405, 467), (434, 476), (465, 478), (496, 473), (521, 455),
        (543, 433), (561, 407), (586, 389), (616, 386), (647, 386),
        (678, 384), (709, 386), (740, 385), (771, 386), (802, 384),
        (833, 384), (865, 384), (896, 386), (927, 386), (958, 386),
    ),
))


#: Shown in this order in the picker: easiest first. Sprint's three laps give
#: towers three passes at everything, so it is by far the gentlest.
MAP_ORDER = ("sprint", "meadow", "park")


def build_path(map_def: MapDef) -> Path:
    """Construct the :class:`~btd.path.Path` for a map.

    CSV-backed maps are scaled from the original 800x600 design space;
    control-point maps are already authored in final map coordinates.
    """
    if map_def.csv:
        points = load_waypoints_csv(assets.path(map_def.csv), MAP_SCALE)
        return Path(points)
    return Path(catmull_rom(list(map_def.control), samples_per_span=28))



def art_candidates(key: str) -> list[str]:
    """Filenames checked for a map's background art, in priority order.

    ``background_images/<key>.png`` is the slot to drop new art into. It must
    be exactly ``MAP_W x MAP_H`` and have the track painted where the spline
    actually runs -- use ``tools/export_maps.py`` to export the rendered
    version as a tracing guide.
    """
    return [f"background_images/{key}.png", f"background_images/{key}.webp"]


def build_background(map_def: MapDef, path: Path) -> pygame.Surface:
    """Produce the map's background surface.

    Prefers hand-drawn artwork when a file exists for this map, and otherwise
    paints grass, the track, and scenery derived from the path itself.
    """
    art = assets.optional(art_candidates(map_def.key) + [map_def.background],
                          (MAP_W, MAP_H))
    if art is not None:
        return art
    return _render_background(map_def, path)


def _render_background(map_def: MapDef, path: Path) -> pygame.Surface:
    """Paint a background for a control-point map.

    Layered back to front: grass, grass texture, a soft drop shadow under the
    track, the track itself, then scenery. Scenery goes last so bushes can
    overhang the track edge the way they do in the hand-drawn map, but it is
    still kept clear of the walkable line.
    """
    surf = pygame.Surface((MAP_W, MAP_H))
    surf.fill(map_def.grass)

    # Seeded on the map key, so a map looks identical every run.
    rng = random.Random(sum(ord(c) * (i + 3) for i, c in enumerate(map_def.key)))

    _grass_texture(surf, map_def, rng)

    clear = map_def.track_width * 0.5

    # Drop shadow, then the darker verge, then the walking surface.
    _stroke_path(surf, path, map_def.track_width + 14,
                 _darken(map_def.grass, 0.80))
    _stroke_path(surf, path, map_def.track_width + 6, _darken(map_def.track, 0.70))
    _stroke_path(surf, path, map_def.track_width, map_def.track)
    _dirt_speckle(surf, path, map_def, rng)

    for _ in range(150):
        b_x = rng.randrange(-10, MAP_W + 10)
        b_y = rng.randrange(-10, MAP_H + 10)
        if path.distance_to(b_x, b_y, clear + 30) < clear + 16:
            continue
        _bush(surf, b_x, b_y, rng.randint(9, 21), map_def.decor, rng)

    _draw_markers(surf, path)
    return surf


def _grass_texture(surf: pygame.Surface, map_def: MapDef,
                   rng: random.Random) -> None:
    """Scatter faint tufts so the ground is not a flat colour field."""
    light = _darken(map_def.grass, 1.10)
    dark = _darken(map_def.grass, 0.92)
    for _ in range(1400):
        x = rng.randrange(0, MAP_W)
        y = rng.randrange(0, MAP_H)
        colour = light if rng.random() < 0.5 else dark
        pygame.draw.line(surf, colour, (x, y), (x, y - rng.randint(2, 4)))


def _dirt_speckle(surf: pygame.Surface, path: Path, map_def: MapDef,
                  rng: random.Random) -> None:
    """Add grit along the track so it does not read as a flat ribbon."""
    light = _darken(map_def.track, 1.07)
    dark = _darken(map_def.track, 0.90)
    steps = int(path.length / 7)
    half = map_def.track_width * 0.5 - 4
    for i in range(steps):
        p_x, p_y = path.position_at(path.length * i / max(1, steps))
        for _ in range(2):
            o_x = p_x + rng.uniform(-half, half)
            o_y = p_y + rng.uniform(-half, half)
            if math.hypot(o_x - p_x, o_y - p_y) > half:
                continue
            colour = light if rng.random() < 0.5 else dark
            pygame.draw.circle(surf, colour, (int(o_x), int(o_y)),
                               rng.randint(1, 2))


def _bush(surf: pygame.Surface, x: int, y: int, size: int,
          base: tuple[int, int, int], rng: random.Random) -> None:
    """Draw a two-tone bush: a shaded base with a lit canopy on top."""
    shade = rng.randint(-10, 10)
    body = tuple(max(0, min(255, c + shade)) for c in base)
    pygame.draw.circle(surf, _darken(body, 0.72), (x, y + size // 4), size)
    pygame.draw.circle(surf, body, (x, y), int(size * 0.86))
    pygame.draw.circle(surf, _darken(body, 1.22),
                       (x - size // 4, y - size // 4), max(2, size // 3))


def _stroke_path(surf: pygame.Surface, path: Path, width: int,
                 colour: tuple[int, int, int]) -> None:
    """Draw the path as a thick line with rounded joins."""
    step = 6.0
    count = max(2, int(path.length / step))
    points = [path.position_at(path.length * i / count) for i in range(count + 1)]
    pygame.draw.lines(surf, colour, False, points, width)
    # Round off the joins; pygame's polyline leaves mitred corners.
    for i in range(0, len(points), 3):
        pygame.draw.circle(surf, colour, (int(points[i][0]), int(points[i][1])),
                           width // 2)


def _draw_markers(surf: pygame.Surface, path: Path) -> None:
    """Mark where balloons enter and where they escape."""
    start = path.position_at(0)
    end = path.position_at(path.length)
    pygame.draw.circle(surf, (86, 196, 120), (int(start[0]), int(start[1])), 15)
    pygame.draw.circle(surf, (20, 40, 26), (int(start[0]), int(start[1])), 15, 3)
    pygame.draw.circle(surf, (216, 80, 80), (int(end[0]), int(end[1])), 15)
    pygame.draw.circle(surf, (48, 16, 16), (int(end[0]), int(end[1])), 15, 3)


def _darken(colour: tuple[int, int, int], factor: float) -> tuple[int, int, int]:
    """Scale a colour's brightness."""
    return tuple(max(0, min(255, int(c * factor))) for c in colour)


def track_clearance(map_def: MapDef) -> float:
    """Minimum distance a tower must keep from the track centre line.

    Art-backed maps declare this explicitly, because how wide their track is
    painted is unrelated to ``track_width`` -- the Sprint Track's running
    surface is roughly four times wider than the Meadow's footpath.
    """
    if map_def.clearance is not None:
        return map_def.clearance
    if map_def.background:
        return 26.0
    return map_def.track_width * 0.5 + 8.0


def blurred(surface: pygame.Surface, passes: int = 3) -> pygame.Surface:
    """Cheap box blur, used behind menus.

    Downscales and upscales repeatedly, which is far faster than a real
    convolution and is indistinguishable behind a dark overlay.
    """
    out = surface
    for _ in range(passes):
        small = pygame.transform.smoothscale(
            out, (max(1, out.get_width() // 4), max(1, out.get_height() // 4))
        )
        out = pygame.transform.smoothscale(small, surface.get_size())
    return out


def spawn_angle(path: Path) -> float:
    """Direction balloons travel at the start of the track, in degrees."""
    return math.degrees(
        math.atan2(
            -(path.position_at(10)[1] - path.position_at(0)[1]),
            path.position_at(10)[0] - path.position_at(0)[0],
        )
    )
