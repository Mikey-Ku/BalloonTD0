"""
Trace a walkable path out of a hand-drawn map background.

Adding a map from artwork means telling the game where balloons actually walk.
Doing that by eye is fiddly and drifts off the painted track. This finds the
real centre line instead:

1. Classify track pixels by colour.
2. Distance-transform the mask, so every track pixel knows how far it is from
   the edge of the track.
3. Run Dijkstra between rough guide points with a cost that strongly prefers
   staying far from the edges, which pulls the route onto the centre line.
4. Simplify the result into a handful of control points to paste into
   ``btd/maps.py``.

Guide points only need to be roughly right and roughly on the track; their job
is to say which way round an ambiguous loop or spiral to go, not to be
accurate. Everything else is measured from the art.

    python tools/trace_map.py sprint
    python tools/trace_map.py park --overlay
"""

from __future__ import annotations

import argparse
import heapq
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

OUT_DIR = os.path.join(ROOT, "tools", "map_export")

#: Dijkstra runs at half resolution; the corridor is far wider than 2 px and
#: this makes the search roughly four times cheaper.
SCALE = 2


def track_mask(image: np.ndarray, kind: str) -> np.ndarray:
    """Classify track pixels.

    Args:
        image: ``(H, W, 3)`` RGB array.
        kind: ``"maroon"`` for the running track, ``"stone"`` for cobbles.

    Returns:
        Boolean mask of walkable pixels.
    """
    red, green, blue = image[:, :, 0], image[:, :, 1], image[:, :, 2]

    if kind == "maroon":
        # The dirt patch in the top-right corner is also reddish, but it is
        # much yellower. Excluding it by green channel keeps the whole track,
        # where cutting the corner off by coordinates clipped real track.
        mask = ((red > green + 30) & (red > blue + 25) & (red > 70)
                & (red < 190) & (green < 118))
        # White lane markings sit inside the running surface.
        mask |= (red > 200) & (green > 195) & (blue > 190)
    else:
        span = image.max(axis=2) - image.min(axis=2)
        mask = (span < 44) & (image.min(axis=2) > 112)
        # The river reads as pale grey-blue; require blue not to dominate so
        # open water is excluded.
        mask &= blue < red + 20

    # Bridges and anti-aliased edges leave small holes that would otherwise
    # cut the corridor in half. Close them -- but only a little, because a
    # large close would weld neighbouring arms of a spiral together and let
    # the search cut corners it should not.
    return close_gaps(mask, 4)


def close_gaps(mask: np.ndarray, amount: int) -> np.ndarray:
    """Morphological close: dilate then erode, bridging gaps up to ``2*amount``."""
    def grow(src: np.ndarray) -> np.ndarray:
        out = src.copy()
        out[1:, :] |= src[:-1, :]
        out[:-1, :] |= src[1:, :]
        out[:, 1:] |= src[:, :-1]
        out[:, :-1] |= src[:, 1:]
        return out

    work = mask
    for _ in range(amount):
        work = grow(work)
    for _ in range(amount):
        work = ~grow(~work)
    return work


def paint_bridges(mask: np.ndarray, bridges, width: int) -> np.ndarray:
    """Force line segments into the mask.

    Foreground scenery -- a bush, a tree canopy, a rock -- is painted *over*
    the path in the artwork, so colour classification sees a hole there and
    the corridor comes apart. A bridge says "the path really does continue
    through here"; it is the one thing the tool cannot infer from the image.
    """
    if not bridges:
        return mask
    canvas = Image.new("1", (mask.shape[1], mask.shape[0]), 0)
    draw = ImageDraw.Draw(canvas)
    for (x_1, y_1), (x_2, y_2) in bridges:
        draw.line([(x_1, y_1), (x_2, y_2)], fill=1, width=width)
    return mask | np.asarray(canvas, dtype=bool)


def edge_distance(mask: np.ndarray, limit: int = 70) -> np.ndarray:
    """Distance from each track pixel to the nearest off-track pixel.

    A simple breadth-first dilation. Exact enough for weighting a search, and
    avoids a scipy dependency.
    """
    dist = np.zeros(mask.shape, dtype=np.float32)
    known = ~mask
    remaining = mask.copy()

    for step in range(1, limit + 1):
        if not remaining.any():
            break
        grown = np.zeros_like(known)
        grown[1:, :] |= known[:-1, :]
        grown[:-1, :] |= known[1:, :]
        grown[:, 1:] |= known[:, :-1]
        grown[:, :-1] |= known[:, 1:]
        newly = grown & remaining
        dist[newly] = step
        known |= newly
        remaining &= ~newly

    return dist


def snap(mask: np.ndarray, point: tuple[int, int]) -> tuple[int, int]:
    """Move a guide point onto the nearest track pixel."""
    x, y = point
    height, width = mask.shape
    x = max(0, min(width - 1, x))
    y = max(0, min(height - 1, y))
    if mask[y, x]:
        return x, y

    for radius in range(1, 90):
        for d_y in range(-radius, radius + 1):
            for d_x in range(-radius, radius + 1):
                if max(abs(d_x), abs(d_y)) != radius:
                    continue
                n_x, n_y = x + d_x, y + d_y
                if 0 <= n_x < width and 0 <= n_y < height and mask[n_y, n_x]:
                    return n_x, n_y
    raise SystemExit(f"guide point {point} is nowhere near the track")


def dijkstra(mask: np.ndarray, weight: np.ndarray,
             start: tuple[int, int], goal: tuple[int, int]) -> list[tuple[int, int]]:
    """Cheapest route between two track pixels under ``weight``."""
    height, width = mask.shape
    best = np.full(mask.shape, np.inf, dtype=np.float32)
    prev = np.full((height, width, 2), -1, dtype=np.int32)

    s_x, s_y = start
    g_x, g_y = goal
    best[s_y, s_x] = 0.0
    queue = [(0.0, s_x, s_y)]

    steps = [(-1, 0, 1.0), (1, 0, 1.0), (0, -1, 1.0), (0, 1, 1.0),
             (-1, -1, 1.414), (1, -1, 1.414), (-1, 1, 1.414), (1, 1, 1.414)]

    while queue:
        cost, x, y = heapq.heappop(queue)
        if cost > best[y, x]:
            continue
        if x == g_x and y == g_y:
            break
        for d_x, d_y, length in steps:
            n_x, n_y = x + d_x, y + d_y
            if not (0 <= n_x < width and 0 <= n_y < height) or not mask[n_y, n_x]:
                continue
            step_cost = cost + length * weight[n_y, n_x]
            if step_cost < best[n_y, n_x]:
                best[n_y, n_x] = step_cost
                prev[n_y, n_x] = (x, y)
                heapq.heappush(queue, (step_cost, n_x, n_y))

    if not np.isfinite(best[g_y, g_x]):
        raise SystemExit(f"no route from {start} to {goal} within the track")

    route = []
    x, y = g_x, g_y
    while (x, y) != (s_x, s_y):
        route.append((x, y))
        x, y = prev[y, x]
    route.append((s_x, s_y))
    route.reverse()
    return route


def resample_loop(loop: list[tuple[float, float]],
                  count: int) -> list[tuple[float, float]]:
    """Resample a closed polyline to evenly spaced points."""
    closed = list(loop) + [loop[0]]
    cumulative = [0.0]
    for a, b in zip(closed, closed[1:]):
        cumulative.append(cumulative[-1] + math.dist(a, b))
    total = cumulative[-1]

    out = []
    for i in range(count):
        target = total * i / count
        idx = min(max(np.searchsorted(cumulative, target), 1), len(closed) - 1)
        span = cumulative[idx] - cumulative[idx - 1]
        t = 0.0 if span <= 0 else (target - cumulative[idx - 1]) / span
        a, b = closed[idx - 1], closed[idx]
        out.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
    return out


def smooth_loop(loop: list[tuple[float, float]],
                passes: int) -> list[tuple[float, float]]:
    """Moving-average smoothing that wraps around a closed loop."""
    pts = list(loop)
    count = len(pts)
    for _ in range(passes):
        pts = [(
            (pts[i - 1][0] + pts[i][0] * 2 + pts[(i + 1) % count][0]) / 4,
            (pts[i - 1][1] + pts[i][1] * 2 + pts[(i + 1) % count][1]) / 4,
        ) for i in range(count)]
    return pts


def offset_loop(loop: list[tuple[float, float]], amount: float,
                centre: tuple[float, float], window: int = 6
                ) -> list[tuple[float, float]]:
    """Shift a closed polyline sideways by ``amount``.

    Tangents are measured across a window of several points rather than
    between immediate neighbours. A Dijkstra route is a staircase of single
    pixel steps, so a one-step tangent flips direction constantly and the
    offset ring ties itself in knots.

    Positive values move away from ``centre``, negative toward it, so callers
    can talk about outer and inner lanes without tracking loop winding.
    """
    out = []
    count = len(loop)
    for i, (x, y) in enumerate(loop):
        p_x, p_y = loop[(i - window) % count]
        n_x, n_y = loop[(i + window) % count]
        t_x, t_y = n_x - p_x, n_y - p_y
        length = math.hypot(t_x, t_y) or 1.0
        o_x, o_y = -t_y / length, t_x / length
        if (x - centre[0]) * o_x + (y - centre[1]) * o_y < 0:
            o_x, o_y = -o_x, -o_y
        out.append((x + o_x * amount, y + o_y * amount))
    return out


def build_laps(loop: list[tuple[float, float]], lanes: list[float],
               blend: float = 0.22) -> list[tuple[float, float]]:
    """Walk a closed loop once per lane, changing lane on the home straight.

    Args:
        loop: Closed centre line, evenly spaced, in the direction of travel.
        lanes: Sideways offset per lap, outward-positive.
        blend: Fraction of a lap spent easing into the next lane.

    Returns:
        A single open path covering ``len(lanes)`` laps.
    """
    centre = (sum(x for x, _ in loop) / len(loop),
              sum(y for _, y in loop) / len(loop))
    rings = [offset_loop(loop, amount, centre) for amount in lanes]

    out: list[tuple[float, float]] = []
    steps = len(loop)
    for lap, ring in enumerate(rings):
        previous = rings[lap - 1] if lap > 0 else None
        for i in range(steps):
            # Ease in from the previous lane over the opening stretch of the
            # lap. Blending at the *start* rather than the end puts every lane
            # change just after the start line, on the home straight -- both
            # where a runner would change, and the only part of the oval
            # straight enough for the shift not to read as a wobble.
            if previous is None or i >= steps * blend:
                out.append(ring[i])
                continue
            t = i / (steps * blend)
            t = t * t * (3 - 2 * t)  # smoothstep
            a, b = previous[i], ring[i]
            out.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
    if rings:
        out.append(rings[-1][0])
    return out


def simplify(points: list[tuple[float, float]], count: int) -> list[tuple[int, int]]:
    """Resample a dense route down to ``count`` evenly spaced control points."""
    if len(points) <= count:
        return [(int(x), int(y)) for x, y in points]

    cumulative = [0.0]
    for a, b in zip(points, points[1:]):
        cumulative.append(cumulative[-1] + math.dist(a, b))
    total = cumulative[-1]

    out = []
    for i in range(count):
        target = total * i / (count - 1)
        idx = np.searchsorted(cumulative, target)
        idx = min(max(idx, 1), len(points) - 1)
        span = cumulative[idx] - cumulative[idx - 1]
        t = 0.0 if span <= 0 else (target - cumulative[idx - 1]) / span
        a, b = points[idx - 1], points[idx]
        out.append((int(round(a[0] + (b[0] - a[0]) * t)),
                    int(round(a[1] + (b[1] - a[1]) * t))))
    return out


def smooth(points: list[tuple[int, int]], passes: int = 6) -> list[tuple[float, float]]:
    """Moving-average smoothing, endpoints pinned."""
    pts = [(float(x), float(y)) for x, y in points]
    for _ in range(passes):
        out = [pts[0]]
        for i in range(1, len(pts) - 1):
            out.append((
                (pts[i - 1][0] + pts[i][0] * 2 + pts[i + 1][0]) / 4,
                (pts[i - 1][1] + pts[i][1] * 2 + pts[i + 1][1]) / 4,
            ))
        out.append(pts[-1])
        pts = out
    return pts


# Guide points per map, in final 960x720 coordinates. Only rough accuracy is
# needed: they exist to disambiguate which way round a loop the path goes.
GUIDES = {
    "sprint": {
        "kind": "maroon",
        # The oval only, traced as a closed loop. The lane spurs at the
        # bottom right are added as entry and exit afterwards.
        "loop": [
            (640, 566), (420, 574), (250, 540), (110, 430), (78, 330),
            (130, 210), (250, 140), (450, 118), (660, 122), (810, 170),
            (890, 270), (884, 400), (820, 500), (640, 566),
        ],
        # Three laps, innermost lane first, working outward -- which is what
        # the "1 2 3" lane numbers painted at the start line are counting.
        "lanes": [-30.0, 0.0, 30.0],
        "entry": (958, 536),
        "exit": (958, 664),
        "controls": 46,
    },
    "park": {
        "kind": "stone",
        # A bush is painted over the path just before it leaves the right
        # edge, which severs the corridor there.
        "bridges": [((790, 384), (959, 386))],
        "width": 46,
        # Only three guides: the spiral's own walls force the route, so the
        # search does not need telling how to get round it.
        "points": [(800, 4), (470, 660), (958, 386)],
        "controls": 30,
    },
}


def trace(key: str, overlay: bool) -> None:
    """Trace one map and print its control points."""
    spec = GUIDES[key]
    image_path = os.path.join(ROOT, "background_images", f"{key}.png")
    image = np.asarray(Image.open(image_path).convert("RGB")).astype(int)

    mask_full = track_mask(image, spec["kind"])
    mask_full = paint_bridges(mask_full, spec.get("bridges"), spec.get("width", 40))
    mask = mask_full[::SCALE, ::SCALE]
    dist = edge_distance(mask)
    span = max(1.0, float(dist.max()))

    # Strong centre preference: cost rises sharply toward the track edges.
    weight = 1.0 + 24.0 * (1.0 - dist / span) ** 3
    weight[~mask] = np.inf

    def run_guides(points):
        out: list[tuple[int, int]] = []
        guides = [snap(mask, (x // SCALE, y // SCALE)) for x, y in points]
        for start, goal in zip(guides, guides[1:]):
            leg = dijkstra(mask, weight, start, goal)
            out.extend(leg if not out else leg[1:])
        return [(x * SCALE, y * SCALE) for x, y in out]

    if "loop" in spec:
        traced = run_guides(spec["loop"])
        loop = smooth_loop(resample_loop(traced, 480), passes=40)
        laps = build_laps(loop, spec["lanes"])
        # Spurs are joined as straight runs. The whole fan at the start line
        # is track, so routing them costs nothing and avoids the knots that
        # Dijkstra ties where a spur meets the ring.
        full = [spec["entry"]] + laps + [spec["exit"]]
    else:
        full = run_guides(spec["points"])
    passes = 4 if "loop" in spec else 10
    controls = simplify(smooth(full, passes=passes), spec["controls"])

    length = sum(math.dist(a, b) for a, b in zip(full, full[1:]))
    print(f"\n{key}: {len(full)} traced px, path length {length:.0f}px, "
          f"track width ~{span * SCALE * 2:.0f}px")
    print("    control=(")
    for i in range(0, len(controls), 4):
        row = ", ".join(f"({x}, {y})" for x, y in controls[i:i + 4])
        print(f"        {row},")
    print("    ),")

    if overlay:
        os.makedirs(OUT_DIR, exist_ok=True)
        pic = Image.open(image_path).convert("RGB")
        draw = ImageDraw.Draw(pic)
        draw.line(full, fill=(255, 40, 220), width=5)
        for i, (x, y) in enumerate(controls):
            draw.ellipse([x - 6, y - 6, x + 6, y + 6], fill=(255, 235, 60),
                         outline=(0, 0, 0), width=2)
            draw.text((x + 9, y - 7), str(i), fill=(0, 0, 0))
        start, end = full[0], full[-1]
        draw.ellipse([start[0] - 14, start[1] - 14, start[0] + 14, start[1] + 14],
                     outline=(60, 255, 90), width=5)
        draw.ellipse([end[0] - 14, end[1] - 14, end[0] + 14, end[1] + 14],
                     outline=(255, 60, 60), width=5)
        out = os.path.join(OUT_DIR, f"{key}_trace.png")
        pic.save(out)
        print(f"    overlay -> {out}")


def main() -> None:
    """Entry point."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("maps", nargs="*", default=list(GUIDES),
                        help="map keys to trace")
    parser.add_argument("--overlay", action="store_true",
                        help="write a PNG showing the traced route on the art")
    args = parser.parse_args()

    for key in args.maps:
        if key not in GUIDES:
            raise SystemExit(f"unknown map {key!r}; known: {', '.join(GUIDES)}")
        trace(key, args.overlay)


if __name__ == "__main__":
    main()
