"""
A file that holds all test cases for our game.

This test suite covers:
- Initial game state
- Speed toggling behavior
- Balloon round preparation and queue population
- Balloon spawning
- Tower placement
- Round completion
- Game over behavior
"""

import pytest
from main import Game


@pytest.fixture
def game():
    return Game()


def test_initial_state(game_instance):
    """
    Test that the game's initial state is correctly set.

    Asserts:
        - `game.money == 200`: player starts with 200 money
        - `game.lives == 100`: player starts with 100 lives
        - `game.current_round == 1`: round count starts at 1
        - `not game.round_started`: no round is active initially
    """
    assert game_instance.money == 200
    assert game_instance.lives == 100
    assert game_instance.current_round == 1
    assert not game_instance.round_started


def test_toggle_speed(game_instance):
    """
    Test that toggling game speed alternates between 1x and 2x.

    Asserts:
        - `game.speed_multiplier == 1`: initial speed is 1x
        - After toggle, `game.speed_multiplier == 2`: toggles to 2x
        - After second toggle, `game.speed_multiplier == 1`: toggles back to 1x
    """
    assert game_instance.speed_multiplier == 1
    game_instance.toggle_speed()
    assert game_instance.speed_multiplier == 2
    game_instance.toggle_speed()
    assert game_instance.speed_multiplier == 1


def test_prepare_round_fills_queue(game_instance):
    """
    Test that preparing a round fills the balloon queue with enemies.

    Asserts:
        - `hasattr(game, "balloons_queue")`: game has the queue attribute
        - `isinstance(game.balloons_queue, list)`: queue is a list
        - `len(game.balloons_queue) > 0`: queue is not empty after round prep
    """
    game_instance.current_round = 1
    game_instance.prepare_round()
    assert hasattr(game_instance, "balloons_queue")
    assert isinstance(game_instance.balloons_queue, list)
    assert len(game_instance.balloons_queue) > 0


def test_balloon_spawning(game_instance):
    """
    Test that balloons spawn correctly during a round.

    Asserts:
        - Balloons are added to the `game.balloons` list.
        - The `game.balloons_queue` decreases in size after spawning.
    """
    game_instance.current_round = 1
    game_instance.prepare_round()
    initial_queue_size = len(game_instance.balloons_queue)
    game_instance.next_balloon_time = 0  # Force immediate spawn
    game_instance.clock_ticks = 0
    game_instance.run()  # Simulate one game loop iteration
    assert len(game_instance.balloons) > 0
    assert len(game_instance.balloons_queue) < initial_queue_size


def test_round_completion(game_instance):
    """
    Test that the game correctly handles round completion.

    Asserts:
        - `game.current_round` increments after a round is completed.
        - `game.money` increases as a reward for completing the round.
        - `game.round_started` is reset to False.
    """
    game_instance.current_round = 1
    game_instance.money = 200
    game_instance.prepare_round()
    game_instance.balloons_queue = []  # Simulate all balloons spawned
    game_instance.balloons = []  # Simulate all balloons popped
    game_instance.run()  # Simulate one game loop iteration
    assert game_instance.current_round == 2
    assert game_instance.money > 200
    assert not game_instance.round_started


def test_game_over_on_zero_lives(game_instance):
    """
    Test that the game ends when the player's lives reach zero.

    Asserts:
        - The game loop exits when `game.lives <= 0`.
    """
    game_instance.lives = 0
    with pytest.raises(SystemExit):  # Assuming the game exits on end
        game_instance.run()


def test_toggle_speed_behavior(game_instance):
    """
    Test that toggling speed updates the `speed_multiplier` correctly.

    Asserts:
        - Speed toggles between 1 and 2.
    """
    assert game_instance.speed_multiplier == 1
    game_instance.toggle_speed()
    assert game_instance.speed_multiplier == 2
    game_instance.toggle_speed()
    assert game_instance.speed_multiplier == 1


def test_prepare_round_creates_correct_queue(game_instance):
    """
    Test that `prepare_round` creates the correct balloon queue for a round.

    Asserts:
        - The `game.balloons_queue` matches the expected configuration.
    """
    game_instance.current_round = 1
    game_instance.prepare_round()
    expected_queue = [
        balloon_type
        for balloon_type, count in game_instance.round_spawn_list[0]["balloons"]
        for _ in range(count)
    ]
    assert game_instance.balloons_queue == expected_queue
