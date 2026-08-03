"""
Track geometry: arc-length parameterised paths with a spatial index.

The original implementation stored a balloon's progress as an integer index
into a waypoint list and advanced it by ``int(speed)`` every frame. That had
two consequences: speeds below 2.0 all truncated to the same integer (so red,
blue, and green balloons moved identically), and travel rate was tied to the
frame rate.

Here a path is parameterised by *distance travelled in pixels*. A balloon
stores a float distance and advances by ``speed * dt``, so any speed is
representable and movement is frame-rate independent.

The class also owns tower-placement queries. Testing a candidate position used
to scan all ~2,500 waypoints every frame; a uniform grid over the path samples
reduces that to a handful of comparisons.
"""

from __future__ import annotations

import csv
import math

Point = tuple[float, float]


def catmull_rom(control: list[Point], samples_per_span: int = 24) -> list[Point]:
    """Smooth a sparse list of control points into a curve.

    Uses a centripetal-ish Catmull-Rom spline, which passes through every
    control point and does not overshoot the way a uniform spline can. Lets a
    map be authored as a dozen points instead of thousands.

    Args:
        control: Control points, in order.
        samples_per_span: Samples emitted between each pair of control points.

    Returns:
        The sampled curve.
    """
    if len(control) < 3:
        return list(control)

    # Duplicate the endpoints so the first and last spans are well defined.
    pts = [control[0]] + list(control) + [control[-1]]
    out: list[Point] = []

    for i in range(len(pts) - 3):
        p_0, p_1, p_2, p_3 = pts[i], pts[i + 1], pts[i + 2], pts[i + 3]
        for step in range(samples_per_span):
            t = step / samples_per_span
            t_2 = t * t
            t_3 = t_2 * t
            x = 0.5 * (
                2 * p_1[0]
                + (-p_0[0] + p_2[0]) * t
                + (2 * p_0[0] - 5 * p_1[0] + 4 * p_2[0] - p_3[0]) * t_2
                + (-p_0[0] + 3 * p_1[0] - 3 * p_2[0] + p_3[0]) * t_3
            )
            y = 0.5 * (
                2 * p_1[1]
                + (-p_0[1] + p_2[1]) * t
                + (2 * p_0[1] - 5 * p_1[1] + 4 * p_2[1] - p_3[1]) * t_2
                + (-p_0[1] + 3 * p_1[1] - 3 * p_2[1] + p_3[1]) * t_3
            )
            out.append((x, y))

    out.append(control[-1])
    return out


class Path:
    """An arc-length parameterised track.

    Attributes:
        points: The polyline vertices, in order.
        cumulative: ``cumulative[i]`` is the distance along the path to
            ``points[i]``. Strictly non-decreasing.
        length: Total path length in pixels.
    """

    #: Side length of a spatial-index cell, in pixels.
    CELL = 32

    def __init__(self, points: list[Point]):
        """Build a path from an ordered polyline.

        Args:
            points: At least two distinct ``(x, y)`` vertices.

        Raises:
            ValueError: If fewer than two distinct points are supplied.
        """
        cleaned: list[Point] = []
        for pt in points:
            if not cleaned or _dist(cleaned[-1], pt) > 1e-9:
                cleaned.append((float(pt[0]), float(pt[1])))
        if len(cleaned) < 2:
            raise ValueError("a path needs at least two distinct points")

        self.points = cleaned
        self.cumulative = [0.0]
        for i in range(1, len(cleaned)):
            self.cumulative.append(
                self.cumulative[-1] + _dist(cleaned[i - 1], cleaned[i])
            )
        self.length = self.cumulative[-1]

        self._grid: dict[tuple[int, int], list[Point]] = {}
        self._build_index()

    # -- geometry ---------------------------------------------------------

    def _build_index(self) -> None:
        """Bucket densely resampled path points into a uniform grid."""
        step = 4.0
        n = max(2, int(self.length / step) + 1)
        for i in range(n):
            pos = self.position_at(self.length * i / (n - 1))
            cell = (int(pos[0]) // self.CELL, int(pos[1]) // self.CELL)
            self._grid.setdefault(cell, []).append(pos)

    def position_at(self, distance: float) -> Point:
        """Return the point that is ``distance`` pixels along the path.

        Distances outside ``[0, length]`` clamp to the endpoints.
        """
        if distance <= 0:
            return self.points[0]
        if distance >= self.length:
            return self.points[-1]

        idx = _bisect(self.cumulative, distance)
        prev_d = self.cumulative[idx - 1]
        span = self.cumulative[idx] - prev_d
        t = 0.0 if span <= 0 else (distance - prev_d) / span

        (x_0, y_0), (x_1, y_1) = self.points[idx - 1], self.points[idx]
        return (x_0 + (x_1 - x_0) * t, y_0 + (y_1 - y_0) * t)

    def heading_at(self, distance: float) -> float:
        """Return the path's direction at ``distance``, in degrees.

        Measured counter-clockwise from screen-right, matching the convention
        used for sprite rotation elsewhere.
        """
        ahead = self.position_at(min(self.length, distance + 4.0))
        behind = self.position_at(max(0.0, distance - 4.0))
        return math.degrees(math.atan2(-(ahead[1] - behind[1]), ahead[0] - behind[0]))

    def distance_to(self, x: float, y: float, cutoff: float) -> float:
        """Approximate distance from ``(x, y)`` to the nearest path point.

        Only searches grid cells within ``cutoff``, so the return value is
        only meaningful when it is below ``cutoff``.

        Args:
            x: Query x coordinate.
            y: Query y coordinate.
            cutoff: Search radius in pixels.

        Returns:
            The nearest distance found, or ``cutoff`` if nothing is nearer.
        """
        reach = int(cutoff // self.CELL) + 1
        c_x, c_y = int(x) // self.CELL, int(y) // self.CELL
        best = cutoff

        for g_y in range(c_y - reach, c_y + reach + 1):
            for g_x in range(c_x - reach, c_x + reach + 1):
                for p_x, p_y in self._grid.get((g_x, g_y), ()):
                    d = math.hypot(p_x - x, p_y - y)
                    if d < best:
                        best = d
        return best


def _dist(a: Point, b: Point) -> float:
    """Euclidean distance between two points."""
    return math.hypot(b[0] - a[0], b[1] - a[1])


def _bisect(values: list[float], target: float) -> int:
    """Index of the first entry in ``values`` strictly greater than ``target``.

    Clamped to ``[1, len(values) - 1]`` so it is always safe to index both
    ``idx`` and ``idx - 1``.
    """
    lo, hi = 1, len(values) - 1
    while lo < hi:
        mid = (lo + hi) // 2
        if values[mid] <= target:
            lo = mid + 1
        else:
            hi = mid
    return lo


def load_waypoints_csv(filename: str, scale: float = 1.0) -> list[Point]:
    """Read ``x,y`` waypoints from a CSV file with a header row.

    Args:
        filename: Path to the CSV file.
        scale: Uniform factor applied to every coordinate.

    Returns:
        The waypoints in file order.
    """
    points: list[Point] = []
    with open(filename, newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        next(reader, None)  # header
        for row in reader:
            if len(row) >= 2:
                try:
                    points.append((float(row[0]) * scale, float(row[1]) * scale))
                except ValueError:
                    continue
    return points
