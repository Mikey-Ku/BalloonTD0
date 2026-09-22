"""Measure what BalloonIndex actually buys over a full-map scan.

Targeting and projectile collision both ask "which balloons are near this
point". The naive answer walks every live balloon and distance-checks it; the
grid walks only the cells the radius reaches. Both paths still run the same
precise distance check, so the saving is in how many of those checks happen.

The peak wave releases 54 balloons, and splits push the live count above that,
so 50 through 400 covers the real operating range. Run it with:

    .venv/bin/python tools/bench_index.py
"""

import os
import random
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

from btd.config import MAP_H, MAP_W  # noqa: E402
from btd.game import BalloonIndex  # noqa: E402

QUERIES = 2000
RADII = (95, 140)          # dart monkey, and a longer-ranged tower
POPULATIONS = (50, 150, 400, 800)


class FakeBalloon:
    """Only the three fields BalloonIndex and a distance check touch."""

    __slots__ = ("x", "y", "alive")

    def __init__(self, x, y):
        self.x, self.y, self.alive = x, y, True


def main(seed: int = 7) -> None:
    random.seed(seed)
    print(f"map {MAP_W}x{MAP_H}, grid CELL={BalloonIndex.CELL}, {QUERIES} queries per row\n")
    print(f"{'balloons':>9}{'radius':>7}{'naive us':>10}{'grid us':>9}{'checks':>14}{'speedup':>9}")
    for n in POPULATIONS:
        balloons = [FakeBalloon(random.uniform(0, MAP_W), random.uniform(0, MAP_H))
                    for _ in range(n)]
        index = BalloonIndex()
        index.build(balloons)
        for radius in RADII:
            points = [(random.uniform(0, MAP_W), random.uniform(0, MAP_H))
                      for _ in range(QUERIES)]
            r2 = radius * radius

            start = time.perf_counter()
            for x, y in points:
                [b for b in balloons if b.alive and (b.x - x) ** 2 + (b.y - y) ** 2 <= r2]
            naive = time.perf_counter() - start

            start = time.perf_counter()
            for x, y in points:
                [b for b in index.query(x, y, radius)
                 if (b.x - x) ** 2 + (b.y - y) ** 2 <= r2]
            grid = time.perf_counter() - start

            examined = sum(len(index.query(x, y, radius)) for x, y in points) / len(points)
            print(f"{n:>9}{radius:>7}{naive * 1e6 / QUERIES:>10.1f}"
                  f"{grid * 1e6 / QUERIES:>9.1f}{n:>8.0f} -> {examined:<4.0f}"
                  f"{naive / grid:>8.1f}x")


if __name__ == "__main__":
    main()
