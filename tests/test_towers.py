"""Tests for tower stats, upgrade paths, and target selection."""

import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from btd.balloons import KINDS as BALLOON_KINDS
from btd.balloons import Balloon, modified
from btd.config import SELL_REFUND
from btd.towers import (
    CLOSE, FARM, FIRST, LAST, STRONG, TARGETING_MODES, Tower,
)
from btd.towers import KINDS as TOWER_KINDS


def setUpModule():
    """Sprite loading needs a display surface, even a dummy one."""
    pygame.init()
    pygame.display.set_mode((64, 64))


def tearDownModule():
    pygame.quit()


def at(name, distance, x=0.0, y=0.0):
    """Build a balloon positioned for targeting tests."""
    balloon = Balloon(BALLOON_KINDS[name], distance=distance)
    balloon.x, balloon.y = x, y
    return balloon


class TestDefinitions(unittest.TestCase):
    """Structural checks on the tower table."""

    def test_every_tower_has_two_paths_of_three_tiers(self):
        for kind in TOWER_KINDS.values():
            self.assertEqual(len(kind.paths), 2, kind.key)
            for path in kind.paths:
                self.assertEqual(len(path), 3, kind.key)

    def test_upgrade_costs_increase_along_a_path(self):
        for kind in TOWER_KINDS.values():
            for path in kind.paths:
                costs = [u.cost for u in path]
                self.assertEqual(costs, sorted(costs), kind.key)

    def test_every_upgrade_has_an_effect(self):
        for kind in TOWER_KINDS.values():
            for path in kind.paths:
                for upgrade in path:
                    self.assertTrue(upgrade.effects,
                                    f"{kind.key}: {upgrade.name} does nothing")
                    self.assertTrue(upgrade.desc.strip())


class TestUpgrades(unittest.TestCase):
    """Stats are rebuilt from base plus purchases, never accumulated."""

    def setUp(self):
        self.tower = Tower(TOWER_KINDS["dart"], 100, 100)

    def test_starts_at_base_stats(self):
        kind = TOWER_KINDS["dart"]
        self.assertEqual(self.tower.damage, kind.damage)
        self.assertEqual(self.tower.range, kind.range)
        self.assertEqual(self.tower.tiers, [0, 0])

    def test_recompute_is_idempotent(self):
        self.tower.apply_upgrade(0)
        self.tower.apply_upgrade(1)
        snapshot = (self.tower.damage, self.tower.range, self.tower.rate,
                    self.tower.pierce)
        for _ in range(5):
            self.tower.recompute()
        self.assertEqual(
            (self.tower.damage, self.tower.range, self.tower.rate,
             self.tower.pierce),
            snapshot,
        )

    def test_upgrades_apply_their_effects(self):
        before = self.tower.pierce
        self.tower.apply_upgrade(0)  # Sharp Shots: +1 pierce
        self.assertEqual(self.tower.pierce, before + 1)

    def test_camo_detection_is_granted_by_upgrade(self):
        self.assertFalse(self.tower.camo)
        for _ in range(3):
            self.tower.apply_upgrade(1)  # path 2 tier 3 grants camo
        self.assertTrue(self.tower.camo)

    def test_cross_path_rule_blocks_maxing_both(self):
        for _ in range(3):
            self.tower.apply_upgrade(0)
        self.assertEqual(self.tower.tiers[0], 3)

        self.assertTrue(self.tower.can_upgrade(1))
        self.tower.apply_upgrade(1)
        self.tower.apply_upgrade(1)
        self.assertEqual(self.tower.tiers[1], 2)

        self.assertFalse(self.tower.can_upgrade(1),
                         "both paths must not reach the final tier")
        self.assertIsNone(self.tower.upgrade_cost(1))

    def test_apply_upgrade_is_a_no_op_when_blocked(self):
        for _ in range(3):
            self.tower.apply_upgrade(0)
        for _ in range(2):
            self.tower.apply_upgrade(1)
        before = list(self.tower.tiers)
        self.tower.apply_upgrade(1)
        self.assertEqual(self.tower.tiers, before)

    def test_maxed_path_reports_no_next_upgrade(self):
        for _ in range(3):
            self.tower.apply_upgrade(0)
        self.assertIsNone(self.tower.next_upgrade(0))
        self.assertIsNone(self.tower.upgrade_cost(0))

    def test_sell_value_tracks_total_spent(self):
        self.assertEqual(self.tower.sell_value,
                         int(TOWER_KINDS["dart"].cost * SELL_REFUND))
        self.tower.apply_upgrade(0)
        self.assertEqual(self.tower.sell_value,
                         int(self.tower.total_spent * SELL_REFUND))

    def test_sell_value_never_exceeds_spend(self):
        for _ in range(3):
            self.tower.apply_upgrade(0)
        self.assertLess(self.tower.sell_value, self.tower.total_spent)

    def test_cost_scale_applies_to_purchase_and_upgrades(self):
        scaled = Tower(TOWER_KINDS["dart"], 0, 0, cost_scale=2.0)
        self.assertEqual(scaled.total_spent, TOWER_KINDS["dart"].cost * 2)
        self.assertEqual(scaled.upgrade_cost(0),
                         TOWER_KINDS["dart"].paths[0][0].cost * 2)

    def test_tier_label(self):
        self.tower.apply_upgrade(0)
        self.tower.apply_upgrade(0)
        self.tower.apply_upgrade(1)
        self.assertEqual(self.tower.tier_label, "2-1")


class TestTargeting(unittest.TestCase):
    """Target selection must honour the chosen priority and camo."""

    def setUp(self):
        self.tower = Tower(TOWER_KINDS["dart"], 0, 0)
        self.tower.range = 500

    def test_first_picks_the_furthest_along(self):
        balloons = [at("red", 10), at("red", 90), at("red", 50)]
        self.tower.targeting = FIRST
        self.assertEqual(self.tower.find_target(balloons).distance, 90)

    def test_last_picks_the_least_far_along(self):
        balloons = [at("red", 10), at("red", 90), at("red", 50)]
        self.tower.targeting = LAST
        self.assertEqual(self.tower.find_target(balloons).distance, 10)

    def test_close_picks_the_nearest_in_space(self):
        balloons = [at("red", 10, x=300), at("red", 90, x=40)]
        self.tower.targeting = CLOSE
        self.assertEqual(self.tower.find_target(balloons).x, 40)

    def test_strong_prefers_moab_class(self):
        balloons = [at("red", 900), at("moab", 10)]
        self.tower.targeting = STRONG
        self.assertTrue(self.tower.find_target(balloons).kind.moab)

    def test_out_of_range_balloons_are_ignored(self):
        self.tower.range = 50
        self.assertIsNone(self.tower.find_target([at("red", 10, x=400)]))

    def test_dead_balloons_are_ignored(self):
        balloon = at("red", 10)
        balloon.alive = False
        self.assertIsNone(self.tower.find_target([balloon]))

    def test_camo_is_invisible_without_detection(self):
        camo = Balloon(modified("green", camo=True))
        camo.x = camo.y = 0
        self.assertFalse(self.tower.camo)
        self.assertIsNone(self.tower.find_target([camo]))

        self.tower.camo = True
        self.assertIsNotNone(self.tower.find_target([camo]))

    def test_empty_list_returns_none(self):
        self.assertIsNone(self.tower.find_target([]))

    def test_cycling_visits_every_mode_and_returns(self):
        start = self.tower.targeting
        seen = {start}
        for _ in range(len(TARGETING_MODES) - 1):
            self.tower.cycle_targeting()
            seen.add(self.tower.targeting)
        self.assertEqual(seen, set(TARGETING_MODES))
        self.tower.cycle_targeting()
        self.assertEqual(self.tower.targeting, start)


class TestFiring(unittest.TestCase):
    """Firing respects cooldown and produces the right shot pattern."""

    def test_cooldown_limits_rate(self):
        tower = Tower(TOWER_KINDS["dart"], 0, 0)
        targets = [at("red", 10, x=50)]

        shots, _ = tower.update(0.001, targets)
        self.assertEqual(len(shots), 1)

        shots, _ = tower.update(0.001, targets)
        self.assertEqual(len(shots), 0, "fired twice inside one cooldown")

        shots, _ = tower.update(1.0 / tower.rate, targets)
        self.assertEqual(len(shots), 1)

    def test_no_target_means_no_shots(self):
        tower = Tower(TOWER_KINDS["dart"], 0, 0)
        shots, effects = tower.update(1.0, [])
        self.assertEqual(shots, [])
        self.assertEqual(effects, [])

    def test_radial_tower_fires_a_ring(self):
        tower = Tower(TOWER_KINDS["tack"], 0, 0)
        shots, _ = tower.update(1.0, [at("red", 10, x=20)])
        self.assertEqual(len(shots), TOWER_KINDS["tack"].shots)

    def test_farm_never_fires(self):
        tower = Tower(TOWER_KINDS["farm"], 0, 0)
        shots, effects = tower.update(10.0, [at("red", 10, x=1)])
        self.assertEqual(shots, [])
        self.assertEqual(effects, [])
        self.assertGreater(tower.income, 0)

    def test_farm_income_grows_with_upgrades(self):
        tower = Tower(TOWER_KINDS["farm"], 0, 0)
        before = tower.income
        tower.apply_upgrade(0)
        self.assertGreater(tower.income, before)

    def test_hitscan_tower_returns_effects_not_projectiles(self):
        tower = Tower(TOWER_KINDS["sniper"], 0, 0)
        shots, effects = tower.update(10.0, [at("red", 10, x=800)])
        self.assertEqual(shots, [])
        self.assertTrue(effects)

    def test_pulse_tower_only_fires_with_balloons_in_range(self):
        tower = Tower(TOWER_KINDS["ice"], 0, 0)
        _, effects = tower.update(10.0, [])
        self.assertEqual(effects, [])
        _, effects = tower.update(10.0, [at("red", 10, x=10)])
        self.assertTrue(effects)

    def test_sniper_reaches_across_the_map(self):
        tower = Tower(TOWER_KINDS["sniper"], 0, 0)
        self.assertTrue(tower.in_range(at("red", 0, x=900, y=700)))

    def test_farm_mode_constant_is_used(self):
        self.assertEqual(TOWER_KINDS["farm"].mode, FARM)


if __name__ == "__main__":
    unittest.main()
