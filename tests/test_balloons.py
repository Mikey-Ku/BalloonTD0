"""
Tests for the balloon damage model and movement.

Several of these pin down bugs that existed in the original implementation, so
they are written to fail loudly if the old behaviour ever returns.
"""

import unittest

from btd import balloons
from btd.balloons import (
    ENERGY, EXPLOSIVE, KINDS, NORMAL, SHARP, Balloon, base_name, modified,
    resolve_hit,
)
from btd.path import Path


def straight_path(length=2000.0):
    """A horizontal path, so distance travelled equals x."""
    return Path([(0.0, 100.0), (length, 100.0)])


class TestSpeeds(unittest.TestCase):
    """Movement speed must be continuous and frame-rate independent."""

    def test_adjacent_tiers_have_distinct_speeds(self):
        """Regression: speeds were truncated with int(), collapsing 1.0/1.4/1.8."""
        path = straight_path()
        travelled = []
        for name in ("red", "blue", "green"):
            balloon = Balloon(KINDS[name])
            for _ in range(60):
                balloon.advance(1 / 60, path)
            travelled.append(round(balloon.distance, 3))

        self.assertEqual(len(set(travelled)), 3, f"speeds collapsed: {travelled}")
        self.assertLess(travelled[0], travelled[1])
        self.assertLess(travelled[1], travelled[2])

    def test_every_kind_moves_at_its_declared_speed(self):
        path = straight_path(20000)
        for name, kind in KINDS.items():
            balloon = Balloon(kind)
            balloon.advance(1.0, path)
            self.assertAlmostEqual(balloon.distance, kind.speed, places=6,
                                   msg=f"{name} moved {balloon.distance}")

    def test_distance_is_independent_of_step_size(self):
        """The same elapsed time must produce the same distance."""
        path = straight_path()

        coarse = Balloon(KINDS["green"])
        for _ in range(10):
            coarse.advance(0.1, path)

        fine = Balloon(KINDS["green"])
        for _ in range(100):
            fine.advance(0.01, path)

        self.assertAlmostEqual(coarse.distance, fine.distance, places=6)

    def test_slow_reduces_speed_then_expires(self):
        path = straight_path()
        balloon = Balloon(KINDS["red"])
        balloon.slow(0.5, 1.0)
        self.assertAlmostEqual(balloon.speed, KINDS["red"].speed * 0.5)

        for _ in range(70):
            balloon.advance(1 / 60, path)
        self.assertAlmostEqual(balloon.speed, KINDS["red"].speed)

    def test_reaching_the_end_is_reported(self):
        path = straight_path(50)
        balloon = Balloon(KINDS["red"])
        self.assertTrue(balloon.advance(10.0, path))


class TestDamage(unittest.TestCase):
    """One coherent hit-point model, with rewards paid once per layer."""

    def drain(self, name, damage=1, damage_type=NORMAL):
        """Pop a balloon and everything inside it one hit at a time."""
        money = pops = 0
        live = [Balloon(KINDS[name])]
        guard = 0
        while live and guard < 100000:
            guard += 1
            target = live[0]
            result = resolve_hit(target, damage, damage_type)
            money += result.money
            pops += result.pops
            if not target.alive:
                live.pop(0)
            live.extend(result.spawned)
        return money, pops

    def test_reward_is_paid_once_per_layer(self):
        """Regression: children inherited base_reward, paying it at every tier."""
        money, pops = self.drain("pink")
        self.assertEqual(pops, 5, "pink should contain exactly 5 layers")
        self.assertEqual(money, 5, "each layer pays its own reward, once")

    def test_total_reward_never_exceeds_contained_balloons(self):
        for name in ("red", "blue", "green", "yellow", "pink", "black",
                     "lead", "rainbow", "ceramic"):
            money, _ = self.drain(name)
            self.assertLessEqual(money, balloons.rbe(name),
                                 f"{name} paid more than it contains")

    def test_excess_damage_is_bounded(self):
        """A huge hit must not multiply through the tree exponentially."""
        ceramic = Balloon(KINDS["ceramic"])
        result = resolve_hit(ceramic, 10_000, NORMAL)
        self.assertLessEqual(result.pops, balloons.rbe("ceramic"))
        self.assertLessEqual(result.money, balloons.rbe("ceramic"))

    def test_partial_damage_leaves_the_balloon_alive(self):
        ceramic = Balloon(KINDS["ceramic"])
        result = resolve_hit(ceramic, 4, NORMAL)
        self.assertTrue(ceramic.alive)
        self.assertEqual(ceramic.hp, 6)
        self.assertEqual(result.pops, 0)
        self.assertEqual(result.money, 0)

    def test_popping_spawns_the_declared_children(self):
        pink = Balloon(KINDS["pink"])
        result = resolve_hit(pink, 1, NORMAL)
        self.assertFalse(pink.alive)
        self.assertEqual([b.kind.name for b in result.spawned], ["yellow"])

    def test_zero_and_negative_damage_do_nothing(self):
        red = Balloon(KINDS["red"])
        for amount in (0, -5):
            result = resolve_hit(red, amount, NORMAL)
            self.assertTrue(red.alive)
            self.assertEqual(result.pops, 0)


class TestImmunity(unittest.TestCase):
    """Damage types are what make tower variety matter."""

    def test_lead_ignores_sharp(self):
        lead = Balloon(KINDS["lead"])
        result = resolve_hit(lead, 99, SHARP)
        self.assertTrue(result.absorbed)
        self.assertTrue(lead.alive)

    def test_lead_is_destroyed_by_explosive(self):
        lead = Balloon(KINDS["lead"])
        result = resolve_hit(lead, 1, EXPLOSIVE)
        self.assertFalse(result.absorbed)
        self.assertFalse(lead.alive)

    def test_black_ignores_explosive_but_not_sharp(self):
        black = Balloon(KINDS["black"])
        self.assertTrue(resolve_hit(black, 99, EXPLOSIVE).absorbed)
        self.assertTrue(black.alive)
        self.assertFalse(resolve_hit(black, 1, SHARP).absorbed)
        self.assertFalse(black.alive)

    def test_energy_hits_everything(self):
        for name in ("lead", "black", "white", "ceramic"):
            balloon = Balloon(KINDS[name])
            self.assertFalse(resolve_hit(balloon, 99, ENERGY).absorbed,
                             f"{name} wrongly resisted energy")


class TestModifiers(unittest.TestCase):
    """Camo, regrow, and fortified are layered onto a base kind."""

    def test_fortified_doubles_hit_points(self):
        self.assertEqual(modified("ceramic", fortified=True).hp,
                         KINDS["ceramic"].hp * 2)

    def test_modifiers_do_not_mutate_the_base_kind(self):
        before = KINDS["ceramic"].hp
        modified("ceramic", fortified=True, camo=True)
        self.assertEqual(KINDS["ceramic"].hp, before)

    def test_children_inherit_modifiers(self):
        parent = Balloon(modified("ceramic", camo=True, fortified=True))
        for child in parent.spawn_children():
            self.assertTrue(child.kind.camo)
            self.assertTrue(child.kind.fortified)

    def test_base_name_strips_every_prefix(self):
        kind = modified("ceramic", camo=True, regen=True, fortified=True)
        self.assertEqual(base_name(kind), "ceramic")

    def test_regen_heals_toward_the_original_tier(self):
        """Regression: children reset their target to their own tier."""
        path = straight_path(500000)
        parent = Balloon(modified("pink", regen=True))
        child = resolve_hit(parent, 1, NORMAL).spawned[0]
        self.assertEqual(child.regen_target, "pink")
        self.assertEqual(base_name(child.kind), "yellow")

        for _ in range(int(3.5 * 60)):
            child.advance(1 / 60, path)
        self.assertEqual(base_name(child.kind), "pink")

    def test_regen_stops_at_the_original_tier(self):
        path = straight_path(500000)
        balloon = Balloon(modified("pink", regen=True))
        for _ in range(int(30 * 60)):
            balloon.advance(1 / 60, path)
        self.assertEqual(base_name(balloon.kind), "pink")


class TestLeakDamage(unittest.TestCase):
    """Leak cost scales with contents but is capped."""

    def test_basic_leak_equals_contained_balloons(self):
        self.assertEqual(Balloon(KINDS["red"]).leak_damage, 1)
        self.assertEqual(Balloon(KINDS["pink"]).leak_damage, 5)

    def test_leak_damage_is_capped(self):
        self.assertEqual(Balloon(KINDS["ceramic"]).leak_damage,
                         balloons.LEAK_CAP)
        self.assertEqual(Balloon(KINDS["zomg"]).leak_damage,
                         balloons.LEAK_CAP_MOAB)

    def test_leak_damage_is_always_positive(self):
        for kind in KINDS.values():
            self.assertGreater(Balloon(kind).leak_damage, 0)


class TestLadder(unittest.TestCase):
    """Structural invariants of the balloon table itself."""

    def test_contained_counts_are_finite_and_increasing(self):
        order = ["red", "blue", "green", "yellow", "pink"]
        values = [balloons.rbe(name) for name in order]
        self.assertEqual(values, sorted(values))

    def test_children_reference_real_kinds(self):
        for kind in KINDS.values():
            for child in kind.children:
                self.assertIn(child, KINDS, f"{kind.name} -> unknown {child}")

    def test_no_kind_contains_itself(self):
        for name in KINDS:
            self.assertLess(balloons.rbe(name), 10 ** 6)


if __name__ == "__main__":
    unittest.main()
