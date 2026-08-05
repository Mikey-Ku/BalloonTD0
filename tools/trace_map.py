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

from btd.path import catmull_rom  # noqa: E402

OUT_DIR = os.path.join(ROOT, "tools", "map_export")

#: Dijkstra runs at half resolution; the corridor is far wider than 2 px and
#: this makes the search roughly four times cheaper.
SCALE = 2


def track_mask(image: np.ndarray, kind: str) -> np.ndarray:
    """Classify track pixels.

    Args:
        image: ``(H, W, 3)`` RGB array.
        kind: ``"lanes"`` for the running track (surface only, so the
            painted lines separate it), or ``"stone"`` for cobbles.

    Returns:
        Boolean mask of walkable pixels.
    """
    red, green, blue = image[:, :, 0], image[:, :, 1], image[:, :, 2]

    if kind == "lanes":
        # Running surface only. The painted lane lines are left OUT, so they
        # separate the mask into three independent corridors that can each be
        # traced on their own. Gap-closing is skipped: the lines are only 3px
        # wide and a close would weld the lanes back together.
        mask = ((red > green + 30) & (red > blue + 25) & (red > 70)
                & (red < 190) & (green < 118))
        return mask

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


def blur(field: np.ndarray, passes: int) -> np.ndarray:
    """Soften a distance field with repeated box averaging.

    The route is steered toward wherever the track is widest, which makes it
    swerve around anything that dents the edge -- and the artwork paints grass
    tufts and leaves across the path, each of which reads as a dent. Softening
    the field first ignores features that small while leaving the corridor's
    real shape intact.

    Blurring the *weight* rather than closing the *mask* matters: a
    morphological close large enough to swallow a tuft also welds neighbouring
    arms of the spiral together, and the search promptly cut a third off the
    route through the join.
    """
    out = field.astype(np.float32)
    for _ in range(passes):
        total = out.copy()
        total[1:, :] += out[:-1, :]
        total[:-1, :] += out[1:, :]
        total[:, 1:] += out[:, :-1]
        total[:, :-1] += out[:, 1:]
        out = total / 5.0
    return out


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


def stadium(c_x: float, c_y: float, half: float, radius: float,
            steps: int = 480) -> list[tuple[float, float]]:
    """Generate a running-track ring: two straights joined by two semicircles.

    Traced-and-offset lanes did not survive this map. Offsetting one centre
    line sideways self-intersected on the curves, where the radius of
    curvature is comparable to the offset, and tracing each lane separately
    needs the corridors to be continuous, which the start-line fan breaks.

    A running track is a stadium curve by construction, so the lanes are
    exactly derivable: same centre, same straight length, one radius each.
    Smooth, concentric, and incapable of crossing itself.

    Args:
        c_x, c_y: Centre of the oval.
        half: Half the length of each straight.
        radius: Distance from the straights to this lane's centre line.
        steps: Points generated around the ring.

    Returns:
        A closed ring, ordered anticlockwise from the right-hand end of the
        bottom straight -- the direction the balloons run.
    """
    straight = 2 * half
    arc = math.pi * radius
    total = 2 * straight + 2 * arc

    ring = []
    for i in range(steps):
        d = total * i / steps
        if d < straight:                       # bottom straight, right to left
            ring.append((c_x + half - d, c_y + radius))
        elif d < straight + arc:               # left cap, bottom to top
            t = (d - straight) / radius
            ring.append((c_x - half - math.sin(t) * radius,
                         c_y + math.cos(t) * radius))
        elif d < 2 * straight + arc:           # top straight, left to right
            ring.append((c_x - half + (d - straight - arc), c_y - radius))
        else:                                  # right cap, top to bottom
            t = (d - 2 * straight - arc) / radius
            ring.append((c_x + half + math.sin(t) * radius,
                         c_y - math.cos(t) * radius))
    return ring


def build_laps(loop: list[tuple[float, float]], lanes: list[list],
               blend: float = 0.16) -> list[tuple[float, float]]:
    """Walk one lap per lane, easing between lanes on the home straight.

    Args:
        loop: Unused; kept so the caller reads symmetrically with the rings.
        lanes: One closed, phase-aligned, equal-length ring per lap.
        blend: Fraction of a lap spent easing into the next lane.

    Returns:
        A single open path covering ``len(lanes)`` laps.
    """
    rings = lanes

    out: list[tuple[float, float]] = []
    steps = len(rings[0])
    for lap, ring in enumerate(rings):
        previous = rings[lap - 1] if lap > 0 else None
        for i in range(steps):
            # The loop's origin is the start/finish line, so easing across
            # during the opening stretch of a lap *is* the change happening as
            # the previous lap completes -- and it puts it on the home
            # straight, past the painted lane numbers. Blending over the
            # closing stretch instead lands it midway round the right-hand
            # curve, where three lanes crossing at once reads as a tangle.
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


def densify(a: tuple[float, float], b: tuple[float, float],
            step: float = 4.0) -> list[tuple[float, float]]:
    """Fill in points along a straight segment.

    Straight runs would otherwise be two endpoints with a void between them,
    which both starves the control-point resampling and makes the fidelity
    check report a huge false drift over the gap.
    """
    count = max(1, int(math.dist(a, b) / step))
    return [(a[0] + (b[0] - a[0]) * i / count,
             a[1] + (b[1] - a[1]) * i / count) for i in range(count + 1)]


def fidelity(controls: list[tuple[int, int]],
             route: list[tuple[float, float]]) -> float:
    """Worst distance from the resulting spline back to the traced route.

    The game rebuilds a Catmull-Rom curve from the control points, so what
    matters is not how well the *points* sit on the track but how well the
    *curve through them* does. Too few points and the spline chords across a
    tight turn, which is exactly what put balloons on the grass in the Park
    Path's spiral.
    """
    curve = catmull_rom([(float(x), float(y)) for x, y in controls],
                        samples_per_span=28)
    step = max(1, len(route) // 900)
    sampled = route[::step]
    worst = 0.0
    for point in curve[::3]:
        worst = max(worst, min(math.dist(point, r) for r in sampled))
    return worst


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
        "kind": "lanes",
        # Measured off the artwork. Scanning columns through the straights
        # puts the track centre line at y=122.5 on top and y=602.5 on the
        # bottom, so the oval centres on y=362.5; scanning rows at that height
        # fixes the horizontal centre and straight length. Each lane sits
        # about 49px from the next, matching the painted bands of 46, 41 and
        # 49px separated by 3px lines.
        "stadium": {"c_x": 479.0, "c_y": 362.5, "half": 123.0},
        # Innermost lane first, working outward -- what the "1 2 3" markings
        # painted at the start line count.
        "lane_radii": [191.5, 241.5, 290.0],
        # Entry and exit sit at exactly the y of the lane they join -- lane 1
        # starts at c_y + 191.5 = 554, lane 3 at c_y + 290 = 652.5 -- so both
        # spurs run dead level. Picking them by eye left a 3 degree tilt, and
        # balloons visibly drifted across the lane markings on the way in.
        # These also land in the painted spur lanes, whose centres at the right
        # edge measure 552 and 648.
        "entry": (958, 554),
        "exit": (958, 652),
        "controls": 90,
        "smoothing": 2,
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
        # The spiral turns tightly enough that control-point spacing decides
        # whether the curve is followed or cut across. At 30 the spline strayed
        # 23px from the traced route -- half the width of a path that is only
        # 76px wide -- so balloons visibly clipped the corners onto the grass.
        "controls": 120,
        "smoothing": 5,
        # Grass and leaves are painted across the stone in places; without
        # this the route weaves around each one.
        "blur": 16,
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
    smoothed = blur(dist, spec.get("blur", 0))

    # Strong centre preference: cost rises sharply toward the track edges.
    weight = 1.0 + 24.0 * (1.0 - smoothed / span) ** 3
    weight[~mask] = np.inf

    def run_guides(points):
        out: list[tuple[int, int]] = []
        guides = [snap(mask, (x // SCALE, y // SCALE)) for x, y in points]
        for start, goal in zip(guides, guides[1:]):
            leg = dijkstra(mask, weight, start, goal)
            out.extend(leg if not out else leg[1:])
        return [(x * SCALE, y * SCALE) for x, y in out]

    if "stadium" in spec:
        rings = [stadium(radius=r, **spec["stadium"])
                 for r in spec["lane_radii"]]
        laps = build_laps(None, rings)
        # Spurs join as straight runs: the whole fan at the start line is
        # track, so routing them costs nothing.
        full = (densify(spec["entry"], laps[0])
                + laps
                + densify(laps[-1], spec["exit"]))
    else:
        full = run_guides(spec["points"])
    controls = simplify(smooth(full, passes=spec.get("smoothing", 6)),
                        spec["controls"])

    length = sum(math.dist(a, b) for a, b in zip(full, full[1:]))
    drift = fidelity(controls, full)
    print(f"\n{key}: {len(full)} traced px, path length {length:.0f}px, "
          f"track width ~{span * SCALE * 2:.0f}px")
    print(f"    {len(controls)} control points, worst drift from the traced "
          f"route {drift:.1f}px")
    if drift > span * SCALE * 0.45:
        print("    WARNING: that is a large share of the track half-width; "
              "raise 'controls'")
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
