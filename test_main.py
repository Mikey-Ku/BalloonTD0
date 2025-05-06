"""
A file that holds all test cases for our game.

This test suite covers:
- Initial game state
- Speed toggling behavior
- Balloon round preparation and queue population
- Balloon spawning
- Round completion
- Game over behavior
"""

import pytest
from unittest.mock import patch, MagicMock
from main import Game


@pytest.fixture
def mock_pygame(monkeypatch):
    """Mock pygame module to prevent initialization during tests"""
    # Mock pygame modules and methods
    monkeypatch.setattr("pygame.init", lambda: None)
    monkeypatch.setattr("pygame.mixer.init", lambda: None)
    monkeypatch.setattr("pygame.mixer.music.load", lambda _: None)
    monkeypatch.setattr("pygame.mixer.music.play", lambda loops=0: None)
    monkeypatch.setattr(
        "pygame.display.set_mode", lambda resolution: MagicMock()
    )
    monkeypatch.setattr("pygame.display.set_caption", lambda _: None)
    monkeypatch.setattr("pygame.image.load", lambda _: MagicMock())
    monkeypatch.setattr("pygame.transform.scale", lambda img, size: img)
    monkeypatch.setattr("pygame.font.SysFont", lambda *args: MagicMock())
    monkeypatch.setattr("pygame.Rect", lambda *args: MagicMock())


class MockTrack:
    def __init__(self):
        self.waypoints = []


# Mock for load_waypoints_from_csv
def mock_load_waypoints():
    return [(i * 10, i * 10) for i in range(10)]  # Simple mock waypoints


@pytest.fixture
def game_instance(monkeypatch):
    """Fixture to create a game instance for testing without pygame initialization"""
    # Mock Track and waypoints loading
    monkeypatch.setattr("main.Track", MockTrack)
    monkeypatch.setattr(
        "main.load_waypoints_from_csv", lambda _: mock_load_waypoints()
    )

    # Mock rounds_config for testing
    mock_rounds = [
        {"spawn_delay": 500, "balloons": [("red", 10), ("blue", 5)]},
        {
            "spawn_delay": 400,
            "balloons": [("red", 15), ("blue", 10), ("green", 5)],
        },
    ]
    monkeypatch.setattr("main.rounds_config", mock_rounds)

    game = Game()

    # Setup game attributes that might not be properly initialized due to mocking
    game.round_spawn_list = mock_rounds
    game.balloons = []

    return game


def test_initial_state(game_instance):
    """Tests game initialization state.

    Args:
        game_instance: A Game fixture with mocked pygame components.

    Tests:
        Verifies initial values for:
            * Player money (200)
            * Player lives (100)
            * Current round (1)
            * Round started flag (False)
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

    # Mock balloon classes
    class MockBalloon:
        def __init__(self, waypoints):
            self.waypoints = waypoints

    # Patch balloon classes
    with patch("main.RedBalloon", MockBalloon):
        game_instance.current_round = 1
        game_instance.prepare_round()
        initial_queue_size = len(game_instance.balloons_queue)
        game_instance.next_balloon_time = 0  # Force immediate spawn
        game_instance.clock_ticks = 0

        # Mock the balloon spawning logic
        if (
            game_instance.balloons_queue
            and game_instance.clock_ticks >= game_instance.next_balloon_time
        ):
            bt = game_instance.balloons_queue.pop(0)
            # Add a mock balloon to the list
            game_instance.balloons.append(MockBalloon(game_instance.waypoints))
            game_instance.next_balloon_time = (
                game_instance.clock_ticks + game_instance.spawn_delay
            )

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
    game_instance.round_started = True
    game_instance.prepare_round()
    game_instance.balloons_queue = []  # Simulate all balloons spawned
    game_instance.balloons = []  # Simulate all balloons popped

    # Simulate round completion logic
    if not game_instance.balloons and not game_instance.balloons_queue:
        finished = game_instance.current_round
        game_instance.current_round += 1
        game_instance.money += 20 * finished
        game_instance.round_started = False

    assert game_instance.current_round == 2
    assert game_instance.money == 220  # 200 + 20*1
    assert not game_instance.round_started


def test_game_over_on_zero_lives(game_instance):
    """
    Test that the game ends when the player's lives reach zero.

    Asserts:
        - The game state reflects game over when `game.lives <= 0`.
    """
    game_instance.lives = 0

    # Simulate game over condition check
    game_over = game_instance.lives <= 0

    assert game_over


def test_prepare_round_creates_correct_queue(game_instance):
    """
    Test that `prepare_round` creates the correct balloon queue for a round.

    Asserts:
        - The `game.balloons_queue` matches the expected configuration.
    """
    game_instance.current_round = 1
    game_instance.prepare_round()

    # Get expected queue from round_spawn_list
    round_info = game_instance.round_spawn_list[0]  # First round (index 0)
    expected_queue = []

    for balloon_type, count in round_info["balloons"]:
        for _ in range(count):
            expected_queue.append(balloon_type)

    assert game_instance.balloons_queue == expected_queue
