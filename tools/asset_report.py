"""
Report which artwork is real and which is still a drawn placeholder.

Run from the project root::

    python tools/asset_report.py

Every sprite in the game looks for a file at a predictable path and falls back
to procedural drawing when it is absent, so this is the authoritative list of
what art is still needed and exactly where each file goes.

Pass ``--markdown`` to emit the tables used in ``ASSETS.md``.
"""

from __future__ import annotations

import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pygame  # noqa: E402

from btd import assets, balloons, game, maps  # noqa: E402
from btd.config import MAP_H, MAP_W, USE_BALLOON_ART  # noqa: E402
from btd.towers import KINDS as TOWER_KINDS  # noqa: E402
from btd.towers import TOWER_ORDER  # noqa: E402


def collect() -> list[tuple[str, str, str, str, bool]]:
    """Gather every art slot.

    Returns:
        ``(category, name, target_path, on_screen_size, has_art)`` rows.
    """
    rows = []

    for name, kind in balloons.KINDS.items():
        candidates = balloons.art_candidates(name)
        found = next((c for c in candidates if assets.exists(c)), None)
        size = kind.radius * 2
        # With USE_BALLOON_ART off, a present file is still not being used, so
        # report it as unused rather than as satisfied.
        in_use = found is not None and USE_BALLOON_ART
        rows.append(("Balloon", name, found or candidates[0],
                     f"{size}x{size}", in_use))

    for key in TOWER_ORDER:
        candidates = game.tower_art_candidates(key)
        found = next((c for c in candidates if assets.exists(c)), None)
        if found is None and TOWER_KINDS[key].image \
                and assets.exists(TOWER_KINDS[key].image):
            found = TOWER_KINDS[key].image
        size = game.TOWER_SPRITE_SIZE
        rows.append(("Tower", TOWER_KINDS[key].label, found or candidates[0],
                     f"{size}x{size}", found is not None))

    for key in maps.MAP_ORDER:
        candidates = maps.art_candidates(key)
        found = next((c for c in candidates if assets.exists(c)), None)
        declared = maps.MAPS[key].background
        if found is None and declared and assets.exists(declared):
            found = declared
        rows.append(("Map", maps.MAPS[key].name, found or candidates[0],
                     f"{MAP_W}x{MAP_H}", found is not None))

    return rows


def main() -> None:
    """Print the report."""
    pygame.init()
    pygame.display.set_mode((64, 64))

    rows = collect()
    markdown = "--markdown" in sys.argv

    if markdown:
        current = None
        for category, name, target, size, has_art in rows:
            if category != current:
                current = category
                print(f"\n### {category}s\n")
                print("| Name | File | Size | Status |")
                print("|---|---|---|---|")
            status = "art" if has_art else "**placeholder**"
            print(f"| {name} | `{target}` | {size} | {status} |")
    else:
        width = max(len(r[1]) for r in rows) + 2
        current = None
        for category, name, target, size, has_art in rows:
            if category != current:
                current = category
                print(f"\n{category.upper()}S")
            mark = "ok " if has_art else "TODO"
            print(f"  [{mark}] {name:<{width}} {size:>9}  {target}")

    done = sum(1 for r in rows if r[4])
    print(f"\n{done}/{len(rows)} slots use real artwork; "
          f"{len(rows) - done} are drawn procedurally.")
    if not USE_BALLOON_ART:
        print("\nNote: USE_BALLOON_ART is off in btd/config.py, so every "
              "balloon is\ndrawn procedurally at a uniform size regardless of "
              "any file present.\nTurn it on once a full, consistently sized "
              "set exists.")
    pygame.quit()


if __name__ == "__main__":
    main()
