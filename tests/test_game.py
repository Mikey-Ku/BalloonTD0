"""Integration tests for a run: waves, economy, placement, and determinism."""

import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from btd import maps
from btd.config import DIFFICULTIES, MAP_H, MAP_W, TICK
from btd.game import LOST, RUNNING, WON, BalloonIndex, Run
from btd.balloons import KINDS as BALLOON_KINDS
from btd.balloons import Balloon
from btd.save import SaveData
from btd.waves import build_schedule, wave_for


def setUpModule():
    pygame.init()
    pygame.display.set_mode((64, 64))


def tearDownModule():
    pygame.quit()


def free_spot(run, key="dart", skip=0):
    """Find a legal placement position, skipping the first ``skip`` hits."""
    seen = 0
    for y in range(30, MAP_H - 30, 11):
        for x in range(30, MAP_W - 30, 11):
            if run.can_place(key, x, y):
                if seen == skip:
                    return x, y
                seen += 1
    raise AssertionError("no legal placement found")


class TestWaves(unittest.TestCase):
    """Round definitions and spawn scheduling."""

    def test_every_round_up_to_120_is_defined_and_non_empty(self):
        for number in range(1, 121):
            wave = wave_for(number)
            self.assertTrue(wave.groups, f"round {number} is empty")
            self.assertGreater(wave.rbe, 0, f"round {number} contains nothing")

    def test_schedule_is_time_ordered(self):
        schedule = build_schedule(wave_for(25))
        times = [entry[0] for entry in schedule]
        self.assertEqual(times, sorted(times))

    def test_schedule_length_matches_the_round(self):
        wave = wave_for(12)
        expected = sum(group.count for group in wave.groups)
        self.assertEqual(len(build_schedule(wave)), expected)

    def test_count_scale_changes_the_number_of_balloons(self):
        wave = wave_for(12)
        base = len(build_schedule(wave, 1.0))
        more = len(build_schedule(wave, 2.0))
        self.assertGreater(more, base)

    def test_difficulty_ramps_overall(self):
        """Later rounds must contain more than earlier ones, boss spikes aside."""
        for early, late in ((1, 10), (10, 20), (20, 30), (30, 40), (40, 55)):
            self.assertLess(wave_for(early).rbe, wave_for(late).rbe,
                            f"round {late} is not harder than {early}")

    def test_no_round_has_an_absurd_duration(self):
        for number in range(1, 81):
            self.assertLess(wave_for(number).duration, 180,
                            f"round {number} takes too long to release")

    def test_describe_is_readable(self):
        self.assertIn("red", wave_for(1).describe())


class TestPlacement(unittest.TestCase):
    """Tower placement rules."""

    def setUp(self):
        self.run = Run("meadow", "normal")
        self.run.money = 100000

    def test_cannot_build_on_the_track(self):
        for fraction in (0.1, 0.35, 0.6, 0.9):
            p_x, p_y = self.run.path.position_at(self.run.path.length * fraction)
            self.assertFalse(self.run.can_place("dart", p_x, p_y),
                             f"track point {fraction} was buildable")

    def test_cannot_build_off_the_map(self):
        for point in ((-50, 100), (MAP_W + 50, 100), (100, -50), (100, MAP_H + 50)):
            self.assertFalse(self.run.can_place("dart", *point))

    def test_cannot_stack_towers(self):
        x, y = free_spot(self.run)
        self.assertIsNotNone(self.run.place_tower("dart", x, y))
        self.assertFalse(self.run.can_place("dart", x, y))
        self.assertFalse(self.run.can_place("dart", x + 8, y + 8))

    def test_placement_deducts_money(self):
        before = self.run.money
        x, y = free_spot(self.run)
        self.run.place_tower("dart", x, y)
        self.assertEqual(self.run.money, before - self.run.tower_cost("dart"))

    def test_cannot_afford_means_no_tower(self):
        self.run.money = 0
        x, y = free_spot(self.run)
        self.assertIsNone(self.run.place_tower("dart", x, y))
        self.assertEqual(self.run.towers, [])

    def test_selling_refunds_and_removes(self):
        x, y = free_spot(self.run)
        tower = self.run.place_tower("dart", x, y)
        before = self.run.money
        self.run.sell_tower(tower)
        self.assertNotIn(tower, self.run.towers)
        self.assertEqual(self.run.money, before + tower.sell_value)

    def test_selling_twice_is_harmless(self):
        x, y = free_spot(self.run)
        tower = self.run.place_tower("dart", x, y)
        self.run.sell_tower(tower)
        money = self.run.money
        self.run.sell_tower(tower)
        self.assertEqual(self.run.money, money)

    def test_upgrade_requires_funds(self):
        x, y = free_spot(self.run)
        tower = self.run.place_tower("dart", x, y)
        self.run.money = 0
        self.assertFalse(self.run.upgrade_tower(tower, 0))
        self.assertEqual(tower.tiers, [0, 0])

    def test_tower_at_finds_a_placed_tower(self):
        x, y = free_spot(self.run)
        tower = self.run.place_tower("dart", x, y)
        self.assertIs(self.run.tower_at(x + 3, y + 3), tower)
        self.assertIsNone(self.run.tower_at(x + 300, y + 300))


class TestRunFlow(unittest.TestCase):
    """Round lifecycle, economy, and end conditions."""

    def setUp(self):
        self.run = Run("meadow", "normal")

    def test_starting_resources_match_the_difficulty(self):
        rules = DIFFICULTIES["normal"]
        self.assertEqual(self.run.money, rules["money"])
        self.assertEqual(self.run.lives, rules["lives"])
        self.assertEqual(self.run.max_rounds, rules["rounds"])

    def test_starting_a_round_queues_balloons(self):
        self.assertTrue(self.run.start_round())
        self.assertTrue(self.run.round_active)
        self.assertTrue(self.run.schedule)

    def test_cannot_start_a_round_twice(self):
        self.run.start_round()
        self.assertFalse(self.run.start_round())

    def test_leaks_cost_lives_and_end_the_round(self):
        before = self.run.lives
        self.run.start_round()
        for _ in range(int(200 / TICK)):
            self.run._step(TICK)
            if not self.run.round_active:
                break
        self.assertLess(self.run.lives, before, "undefended round cost nothing")

    def test_clearing_a_round_advances_and_pays_a_bonus(self):
        self.run.money = 1000000
        for i in range(6):
            spot = free_spot(self.run, skip=i * 3)
            self.run.place_tower("super", *spot)
        money_before = self.run.money

        self.run.start_round()
        for _ in range(int(200 / TICK)):
            self.run._step(TICK)
            if not self.run.round_active:
                break

        self.assertFalse(self.run.round_active)
        self.assertEqual(self.run.round_number, 2)
        self.assertGreater(self.run.money, money_before)
        self.assertEqual(self.run.lives, DIFFICULTIES["normal"]["lives"])

    def test_running_out_of_lives_loses(self):
        self.run.lives = 1
        self.run.start_round()
        for _ in range(int(300 / TICK)):
            self.run._step(TICK)
            if self.run.outcome != RUNNING:
                break
        self.assertEqual(self.run.outcome, LOST)

    def test_clearing_the_final_round_wins(self):
        self.run.max_rounds = 1
        self.run.money = 1000000
        for i in range(6):
            self.run.place_tower("super", *free_spot(self.run, skip=i * 3))
        self.run.start_round()
        for _ in range(int(200 / TICK)):
            self.run._step(TICK)
            if self.run.outcome != RUNNING:
                break
        self.assertEqual(self.run.outcome, WON)

    def test_speed_cycles_and_stays_in_range(self):
        seen = set()
        for _ in range(6):
            seen.add(self.run.speed)
            self.run.toggle_speed()
        self.assertEqual(seen, {1, 2, 3})

    def test_pausing_freezes_the_simulation(self):
        self.run.start_round()
        self.run.advance(0.5)
        distance = sum(b.distance for b in self.run.balloons)
        self.run.paused = True
        for _ in range(20):
            self.run.advance(0.1)
        self.assertEqual(sum(b.distance for b in self.run.balloons), distance)


class TestDeterminism(unittest.TestCase):
    """A fixed timestep must give identical results for identical input."""

    def build(self):
        run = Run("meadow", "normal")
        run.money = 100000
        for i in range(4):
            run.place_tower("dart", *free_spot(run, skip=i * 5))
        run.start_round()
        return run

    def signature(self, run):
        return (round(run.money, 4), run.lives, run.total_pops,
                len(run.balloons), round(sum(b.distance for b in run.balloons), 3))

    def test_same_steps_give_the_same_state(self):
        first, second = self.build(), self.build()
        for _ in range(600):
            first._step(TICK)
            second._step(TICK)
        self.assertEqual(self.signature(first), self.signature(second))

    def test_frame_pacing_does_not_change_the_outcome(self):
        """Ten 0.1s frames must equal a hundred 0.01s frames."""
        coarse, fine = self.build(), self.build()
        for _ in range(20):
            coarse.advance(0.1)
        for _ in range(200):
            fine.advance(0.01)
        self.assertEqual(self.signature(coarse), self.signature(fine))

    def test_fast_forward_matches_real_time(self):
        """Three seconds at 1x must equal one second at 3x."""
        slow, fast = self.build(), self.build()
        fast.speed = 3
        for _ in range(180):
            slow.advance(TICK)
        for _ in range(60):
            fast.advance(TICK)
        self.assertEqual(self.signature(slow), self.signature(fast))


class TestBalloonIndex(unittest.TestCase):
    """The spatial index must return a superset of what is in range."""

    def test_query_finds_nearby_balloons(self):
        index = BalloonIndex()
        balloons = []
        for i in range(50):
            balloon = Balloon(BALLOON_KINDS["red"])
            balloon.x, balloon.y = i * 18, 300
            balloons.append(balloon)
        index.build(balloons)

        found = index.query(200, 300, 60)
        expected = [b for b in balloons if abs(b.x - 200) <= 60]
        for balloon in expected:
            self.assertIn(balloon, found)

    def test_large_radius_returns_everything(self):
        index = BalloonIndex()
        balloons = []
        for i in range(20):
            balloon = Balloon(BALLOON_KINDS["red"])
            balloon.x, balloon.y = i * 40, i * 30
            balloons.append(balloon)
        index.build(balloons)
        self.assertEqual(len(index.query(0, 0, 99999)), 20)

    def test_dead_balloons_are_excluded_from_full_scans(self):
        index = BalloonIndex()
        balloon = Balloon(BALLOON_KINDS["red"])
        balloon.alive = False
        index.build([balloon])
        self.assertEqual(index.query(0, 0, 99999), [])


class TestMaps(unittest.TestCase):
    """Every registered map must load and be playable."""

    def test_all_maps_build(self):
        for key in maps.MAP_ORDER:
            run = Run(key, "normal")
            self.assertGreater(run.path.length, 500, key)
            self.assertEqual(run.background.get_size(), (MAP_W, MAP_H), key)

    def test_all_maps_have_room_to_build(self):
        for key in maps.MAP_ORDER:
            run = Run(key, "normal")
            buildable = sum(
                1
                for y in range(30, MAP_H - 30, 20)
                for x in range(30, MAP_W - 30, 20)
                if run.can_place("dart", x, y)
            )
            total = len(range(30, MAP_H - 30, 20)) * len(range(30, MAP_W - 30, 20))
            self.assertGreater(buildable / total, 0.4,
                               f"{key} has too little buildable space")

    def test_map_order_matches_the_registry(self):
        self.assertEqual(set(maps.MAP_ORDER), set(maps.MAPS))


class TestSave(unittest.TestCase):
    """Save data must survive a bad file and a read-only location."""

    def test_records_and_reports_a_new_best(self):
        save = SaveData()
        save.writable = False  # keep the test off the real filesystem
        save.data["best"] = {}
        self.assertTrue(save.record_run("meadow", "normal", 12, 100, False))
        self.assertEqual(save.best_round("meadow", "normal"), 12)
        self.assertFalse(save.record_run("meadow", "normal", 5, 10, False))
        self.assertEqual(save.best_round("meadow", "normal"), 12)

    def test_unknown_map_has_no_best(self):
        save = SaveData()
        save.writable = False
        self.assertEqual(save.best_round("nope", "normal"), 0)

    def test_flush_on_a_read_only_path_does_not_raise(self):
        save = SaveData()
        save.path = "/proc/definitely-not-writable/save.json"
        save.flush()  # must not raise
        self.assertFalse(save.writable)


if __name__ == "__main__":
    unittest.main()
