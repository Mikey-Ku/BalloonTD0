"""
Tests for track.py module.

This module contains unit tests for the Track class and related utilities:
    * Track initialization
    * Waypoint loading
    * Tower placement validation
    * Position update mechanics
"""

import pytest
from track import Track, load_waypoints_from_csv


@pytest.fixture
def sample_track():
    """
    Fixture to provide a sample Track instance.
    """
    track = Track(width=800, height=600)
    # Initialize with empty towers
    track.towers = []
    return track


@pytest.fixture
def sample_waypoints_csv(tmp_path):
    """
    Fixture to create a temporary CSV file with sample waypoints.
    """
    csv_path = tmp_path / "waypoints.csv"
    with open(csv_path, "w", encoding="utf-8") as f:
        f.write("x,y\n")
        f.write("100,100\n")
        f.write("200,200\n")
        f.write("300,300\n")
    return csv_path


def test_load_waypoints_from_csv(sample_waypoints_csv):
    """Tests CSV waypoint loading functionality.

    Args:
        sample_waypoints_csv: A fixture providing a temporary CSV file with test waypoints.

    Tests:
        Verifies that:
            * Waypoints are correctly parsed from CSV
            * Coordinates are converted to proper float tuples
    """
    waypoints = load_waypoints_from_csv(sample_waypoints_csv)
    assert waypoints == [(100.0, 100.0), (200.0, 200.0), (300.0, 300.0)]


def test_is_valid_tower_position_no_waypoints(sample_track):
    """Tests tower placement validation with empty track.

    Args:
        sample_track: A Track fixture with no waypoints.

    Tests:
        Verifies that:
            * Positions within boundaries are valid
            * Positions outside boundaries are invalid
    """
    # Inside boundaries should be valid
    assert sample_track.is_valid_tower_position(100, 100) is True

    # Outside boundaries should be invalid
    assert sample_track.is_valid_tower_position(-10, 100) is False  # Left edge
    assert sample_track.is_valid_tower_position(810, 100) is False  # Right edge
    assert sample_track.is_valid_tower_position(100, -10) is False  # Top edge
    assert (
        sample_track.is_valid_tower_position(100, 610) is False
    )  # Bottom edge


def test_is_valid_tower_position_with_waypoints(sample_track):
    """
    Test tower placement validation when waypoints are present.

    Asserts:
        - Towers cannot be placed near waypoints.
    """
    # Set small tower_invalid_radius to make test more predictable
    sample_track.tower_invalid_radius = 15
    sample_track.waypoints = [(100, 100), (200, 200)]

    # Position exactly at a waypoint
    assert sample_track.is_valid_tower_position(100, 100) is False

    # Position exactly at tower_invalid_radius distance (using Pythagorean theorem)
    # Calculate a point exactly 15 units away
    x = 100 + sample_track.tower_invalid_radius * 0.7071  # cos(45°) ≈ 0.7071
    y = 100 + sample_track.tower_invalid_radius * 0.7071  # sin(45°) ≈ 0.7071
    assert sample_track.is_valid_tower_position(x, y) is False

    # Position just outside tower_invalid_radius
    x = 100 + sample_track.tower_invalid_radius * 1.1
    y = 100 + sample_track.tower_invalid_radius * 1.1
    assert sample_track.is_valid_tower_position(x, y) is True


def test_is_valid_tower_position_with_existing_towers(sample_track):
    """
    Test tower placement validation when other towers exist.

    Asserts:
        - Towers cannot be placed too close to existing towers.
    """

    # Create a mock tower
    class MockTower:
        def __init__(self, x, y):
            self.x = x
            self.y = y

    # Add a tower at position (200, 200)
    mock_tower = MockTower(200, 200)
    sample_track.towers = [mock_tower]

    # Too close to existing tower (less than 30 units away)
    assert sample_track.is_valid_tower_position(210, 210) is False

    # Far enough from existing tower (more than 30 units away)
    assert sample_track.is_valid_tower_position(250, 250) is True


def test_update_valid_positions(sample_track):
    """
    Test that valid tower positions are correctly updated.

    Asserts:
        - Valid positions are correctly calculated based on waypoints.
    """
    # Ensure the track has no waypoints initially
    sample_track.waypoints = []

    # Update valid positions with no waypoints
    sample_track.update_valid_positions()

    # Position (50, 50) should be valid with no waypoints
    assert (50, 50) in sample_track.valid_tower_positions

    # Now add waypoints and update again
    sample_track.waypoints = [(50, 50)]  # Add waypoint at (50, 50)
    sample_track.update_valid_positions()

    # Position (50, 50) should now be invalid due to waypoint
    assert (50, 50) not in sample_track.valid_tower_positions
