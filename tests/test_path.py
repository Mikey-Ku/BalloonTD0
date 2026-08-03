"""Tests for track geometry and the spatial index."""

import math
import unittest

from btd.path import Path, catmull_rom


class TestPathGeometry(unittest.TestCase):
    """Arc-length parameterisation must be exact and monotonic."""

    def setUp(self):
        self.line = Path([(0, 0), (100, 0), (100, 100)])

    def test_length_is_the_sum_of_segments(self):
        self.assertAlmostEqual(self.line.length, 200.0)

    def test_endpoints(self):
        self.assertEqual(self.line.position_at(0), (0.0, 0.0))
        self.assertEqual(self.line.position_at(self.line.length), (100.0, 100.0))

    def test_interpolates_within_a_segment(self):
        self.assertAlmostEqual(self.line.position_at(50)[0], 50.0)
        self.assertAlmostEqual(self.line.position_at(50)[1], 0.0)

    def test_crosses_a_vertex_correctly(self):
        x, y = self.line.position_at(150)
        self.assertAlmostEqual(x, 100.0)
        self.assertAlmostEqual(y, 50.0)

    def test_distances_outside_the_range_clamp(self):
        self.assertEqual(self.line.position_at(-500), self.line.position_at(0))
        self.assertEqual(self.line.position_at(10 ** 9),
                         self.line.position_at(self.line.length))

    def test_position_is_continuous(self):
        """No sample may jump further than the sampling interval allows."""
        step = self.line.length / 500
        previous = self.line.position_at(0)
        for i in range(1, 501):
            current = self.line.position_at(step * i)
            self.assertLessEqual(math.dist(previous, current), step * 1.01)
            previous = current

    def test_duplicate_points_are_collapsed(self):
        path = Path([(0, 0), (0, 0), (10, 0), (10, 0)])
        self.assertAlmostEqual(path.length, 10.0)

    def test_degenerate_input_is_rejected(self):
        with self.assertRaises(ValueError):
            Path([(5, 5)])
        with self.assertRaises(ValueError):
            Path([(5, 5), (5, 5)])

    def test_heading_points_along_the_path(self):
        self.assertAlmostEqual(self.line.heading_at(50), 0.0, places=4)
        self.assertAlmostEqual(self.line.heading_at(150), -90.0, places=4)


class TestSpatialIndex(unittest.TestCase):
    """distance_to must agree with brute force wherever it reports a hit."""

    def setUp(self):
        self.path = Path(catmull_rom(
            [(40, 40), (300, 120), (500, 400), (200, 560), (700, 640)]
        ))
        step = 2.0
        count = int(self.path.length / step)
        self.samples = [self.path.position_at(step * i) for i in range(count + 1)]

    def brute(self, x, y):
        """Exact nearest distance to the sampled path."""
        return min(math.hypot(p[0] - x, p[1] - y) for p in self.samples)

    def test_matches_brute_force(self):
        cutoff = 60.0
        for y in range(10, 700, 37):
            for x in range(10, 940, 41):
                approx = self.path.distance_to(x, y, cutoff)
                exact = self.brute(x, y)
                if approx < cutoff or exact < cutoff:
                    self.assertLess(abs(min(approx, cutoff) - min(exact, cutoff)),
                                    3.0, f"mismatch at ({x}, {y})")

    def test_points_on_the_path_report_near_zero(self):
        for fraction in (0.0, 0.25, 0.5, 0.75, 1.0):
            p_x, p_y = self.path.position_at(self.path.length * fraction)
            self.assertLess(self.path.distance_to(p_x, p_y, 40), 3.0)

    def test_never_exceeds_the_cutoff(self):
        self.assertLessEqual(self.path.distance_to(-5000, -5000, 25.0), 25.0)


class TestCatmullRom(unittest.TestCase):
    """The spline must pass through its control points."""

    def test_passes_through_endpoints(self):
        control = [(0, 0), (50, 80), (140, 20), (200, 90)]
        curve = catmull_rom(control)
        self.assertEqual(curve[0], control[0])
        self.assertEqual(curve[-1], control[-1])

    def test_short_input_is_returned_unchanged(self):
        self.assertEqual(catmull_rom([(0, 0), (1, 1)]), [(0, 0), (1, 1)])

    def test_produces_a_denser_curve(self):
        control = [(0, 0), (50, 80), (140, 20), (200, 90)]
        self.assertGreater(len(catmull_rom(control)), len(control) * 10)

    def test_stays_near_the_control_hull(self):
        """Centripetal-style splines should not wildly overshoot."""
        control = [(0, 0), (100, 0), (200, 0), (300, 0)]
        for _, y in catmull_rom(control):
            self.assertLess(abs(y), 1e-6)


if __name__ == "__main__":
    unittest.main()
