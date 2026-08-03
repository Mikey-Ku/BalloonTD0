"""
Export map art references for drawing custom backgrounds.

Run from the project root::

    python tools/export_maps.py

For every map this writes three PNGs into ``tools/map_export/``:

``<key>_render.png``
    The background the game currently draws procedurally. Useful as a
    starting point, or just to see what you are replacing.

``<key>_guide.png``
    A tracing guide: the track centre line, the walkable width, and the
    entry/exit markers on a transparent-ish backdrop. Draw your artwork with
    this as a reference layer so the painted track lines up with where
    balloons actually walk.

``<key>_buildable.png``
    Green where towers may be placed, red where they may not. Handy for
    checking that a hand-drawn track does not leave the player with too
    little room to build.

Finished art goes to ``background_images/<key>.png`` at exactly the size
printed by this script, and the game picks it up automatically.
"""

from __future__ import annotations

import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pygame  # noqa: E402  (must follow the SDL env setup)

from btd import maps  # noqa: E402
from btd.config import MAP_H, MAP_W  # noqa: E402

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "map_export")


def guide_surface(map_def: maps.MapDef, path) -> pygame.Surface:
    """Draw a tracing guide showing the track and its clearance."""
    surf = pygame.Surface((MAP_W, MAP_H))
    surf.fill((26, 28, 34))

    clearance = maps.track_clearance(map_def)
    steps = max(2, int(path.length / 4))
    points = [path.position_at(path.length * i / steps) for i in range(steps + 1)]

    # Buildable clearance boundary, then the walkable width, then the line.
    pygame.draw.lines(surf, (58, 46, 46), False, points, int(clearance * 2))
    pygame.draw.lines(surf, (120, 104, 78), False, points,
                      max(4, map_def.track_width))
    pygame.draw.lines(surf, (255, 220, 120), False, points, 2)

    # Direction ticks every 200px so the flow is unambiguous.
    for i in range(0, int(path.length), 200):
        p_x, p_y = path.position_at(i)
        pygame.draw.circle(surf, (255, 255, 255), (int(p_x), int(p_y)), 3)

    start = path.position_at(0)
    end = path.position_at(path.length)
    pygame.draw.circle(surf, (86, 216, 120), (int(start[0]), int(start[1])), 16, 3)
    pygame.draw.circle(surf, (232, 82, 82), (int(end[0]), int(end[1])), 16, 3)

    font = pygame.font.Font(None, 26)
    surf.blit(font.render("ENTRY", True, (86, 216, 120)),
              (start[0] + 20, start[1] - 8))
    surf.blit(font.render("EXIT", True, (232, 82, 82)), (end[0] + 20, end[1] - 8))
    return surf


def buildable_surface(map_def: maps.MapDef, path, background) -> pygame.Surface:
    """Shade the map by whether a tower may be placed at each point."""
    surf = background.copy()
    clearance = maps.track_clearance(map_def)
    for y in range(6, MAP_H, 10):
        for x in range(6, MAP_W, 10):
            ok = path.distance_to(x, y, clearance) >= clearance
            pygame.draw.circle(surf, (70, 230, 110) if ok else (235, 70, 70),
                               (x, y), 2)
    return surf


def main() -> None:
    """Export every registered map."""
    pygame.init()
    pygame.display.set_mode((64, 64))
    os.makedirs(OUT_DIR, exist_ok=True)

    print(f"Map size: {MAP_W} x {MAP_H} (all art must match exactly)\n")

    for key in maps.MAP_ORDER:
        map_def = maps.MAPS[key]
        path = maps.build_path(map_def)
        background = maps.build_background(map_def, path)

        for suffix, surface in (
            ("render", background),
            ("guide", guide_surface(map_def, path)),
            ("buildable", buildable_surface(map_def, path, background)),
        ):
            out = os.path.join(OUT_DIR, f"{key}_{suffix}.png")
            pygame.image.save(surface, out)

        slots = maps.art_candidates(key) + [map_def.background]
        has_art = any(maps.assets.exists(c) for c in slots if c)
        status = "custom art" if has_art else "procedural placeholder"
        print(f"  {map_def.name:16s} {key:12s} {status}"
              f"   track {path.length:7.0f}px")

    print(f"\nWrote {len(maps.MAP_ORDER) * 3} files to {OUT_DIR}")
    print("Drop finished art at background_images/<key>.png to override.")
    pygame.quit()


if __name__ == "__main__":
    main()
