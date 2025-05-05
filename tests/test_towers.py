"""
Test file for towers.py
Validates core behavior of the Tower class, including targeting, attack logic, upgrades, and selling.
"""

import time
import pytest
from towers import Tower


class TestBalloon:
    """
    A minimal mock balloon object for testing towers.
    Mimics position, health, reward, and waypoint progress.
    """

    def __init__(self, x, y, health=1, base_reward=5, current_waypoint=0):
        self.x = x
        self.y = y
        self.health = health
        self.base_reward = base_reward
        self.current_waypoint = current_waypoint

    def take_damage(self, damage):
        self.health -= damage
        return [] if self.health <= 0 else None


@pytest.fixture
def basic_tower():
    """
    Create and return a basic Tower instance with known parameters.

    Returns:
        A Tower object with:
        - x, y = 100
        - range = 50
        - damage = 1
        - attack_speed = 1
        - cooldown = 1
    """
    t = Tower()
    t.x = 100
    t.y = 100
    t.range = 50
    t.damage = 1
    t.attack_speed = 1
    t.cooldown = 1
    t.last_attack = 0
    t.update()
    return t


def test_in_range(basic_tower):
    """
    Test whether a point is within the tower's range.

    Asserts:
        - (110, 110) is within range → True
        - (200, 200) is outside range → False
    """
    assert basic_tower.in_range((110, 110)) is True
    assert basic_tower.in_range((200, 200)) is False


def test_find_target_prefers_farthest_waypoint(basic_tower):
    """
    Verify that the tower selects the target with the farthest progress along the path.

    Asserts:
        - Among three balloons, the one with the highest current_waypoint (in range) is selected
        - Balloon b1 (waypoint=2) is selected over b2 (waypoint=1)
        - Balloon b3 is out of range and ignored
    """
    b1 = TestBalloon(105, 105, current_waypoint=2)
    b2 = TestBalloon(120, 120, current_waypoint=1)
    b3 = TestBalloon(200, 200, current_waypoint=3)
    target = basic_tower.find_target([b1, b2, b3])
    assert target == b1


def test_attack_respects_cooldown(basic_tower):
    """
    Test that the tower respects cooldown between attacks.

    Asserts:
        - First attack happens and returns reward [(target, 5)]
        - Second attack occurs too soon → returns empty list []
    """
    balloon = TestBalloon(100, 100)
    basic_tower.range = 1000
    now = time.time() * 1000

    balloons = [balloon]
    rewards = basic_tower.attack(balloons, now + 2000)
    assert len(rewards) == 1
    assert rewards[0][1] == 5

    balloons = [TestBalloon(100, 100)]
    rewards = basic_tower.attack(balloons, now + 2001)
    assert rewards == []


def test_upgrade_increases_stats(basic_tower):
    """
    Ensure tower upgrades increase damage and range.

    Asserts:
        - Damage increases by 1
        - Range increases (greater than previous)
    """
    old_damage = basic_tower.damage
    old_range = basic_tower.range
    basic_tower.upgrade()
    assert basic_tower.damage == old_damage + 1
    assert basic_tower.range > old_range


def test_sell_returns_correct_value(basic_tower):
    """
    Verify that the tower returns 70% of its upgrade cost when sold.

    Asserts:
        - Return value equals upgrade_cost * 0.7
    """
    expected_value = basic_tower.upgrade_cost * 0.7
    assert basic_tower.sell() == expected_value
