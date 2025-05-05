"""
A file that holds all test cases for our game.

This test suite covers:
- Initial game state
- Speed toggling behavior
- Balloon round preparation and queue population
"""

import pytest
import pygame
import time

from user_interface import TowerPurchasingUI, TowerMenu, GameUI
from main import Game
from towers import Tower, SniperTower, DartTower, SuperTower, TacTower


@pytest.fixture
def game():
    return Game()


@pytest.fixture
def test_initial_state(game):
    """
    Test that the game's initial state is correctly set.

    Asserts:
        - `game.money == 200`: player starts with 200 money
        - `game.lives == 100`: player starts with 100 lives
        - `game.current_round == 1`: round count starts at 1
        - `not game.round_started`: no round is active initially
    """
    assert game.money == 200
    assert game.lives == 100
    assert game.current_round == 1
    assert not game.round_started


def test_toggle_speed(game):
    """
    Test that toggling game speed alternates between 1x and 2x.

    Asserts:
        - `game.speed_multiplier == 1`: initial speed is 1x
        - After toggle, `game.speed_multiplier == 2`: toggles to 2x
        - After second toggle, `game.speed_multiplier == 1`: toggles back to 1x
    """
    assert game.speed_multiplier == 1
    game.toggle_speed()
    assert game.speed_multiplier == 2
    game.toggle_speed()
    assert game.speed_multiplier == 1


def test_prepare_round_fills_queue(game):
    """
    Test that preparing a round fills the balloon queue with enemies.

    Asserts:
        - `hasattr(game, "balloons_queue")`: game has the queue attribute
        - `isinstance(game.balloons_queue, list)`: queue is a list
        - `len(game.balloons_queue) > 0`: queue is not empty after round prep
    """
    game.current_round = 1
    game.prepare_round()
    assert hasattr(game, "balloons_queue")
    assert isinstance(game.balloons_queue, list)
    assert len(game.balloons_queue) > 0
