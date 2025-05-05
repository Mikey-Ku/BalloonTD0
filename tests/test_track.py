import pytest
from track import Track, load_waypoints_from_csv


@pytest.fixture
def example_track():
    """
    Fixture to provide a sample Track instance.
    """
    return Track(width=800, height=600)


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


def test_load_waypoints_from_csv(sample_csv):
    """
    Test that waypoints are correctly loaded from a CSV file.

    Asserts:
        - The returned list matches the waypoints in the CSV file.
    """
    waypoints = load_waypoints_from_csv(sample_csv)
    assert waypoints == [(100.0, 100.0), (200.0, 200.0), (300.0, 300.0)]


def test_is_valid_tower_position_no_waypoints(sample_track):
    """
    Test tower placement validation when there are no waypoints.

    Asserts:
        - Towers can be placed anywhere within the track boundaries.
    """
    assert sample_track.is_valid_tower_position(100, 100) is True
    assert sample_track.is_valid_tower_position(0, 0) is False
    assert sample_track.is_valid_tower_position(800, 600) is False


def test_is_valid_tower_position_with_waypoints(sample_track):
    """
    Test tower placement validation when waypoints are present.

    Asserts:
        - Towers cannot be placed near waypoints.
    """
    sample_track.waypoints = [(100, 100), (200, 200)]
    assert sample_track.is_valid_tower_position(100, 100) is False
    assert sample_track.is_valid_tower_position(110, 110) is False
    assert sample_track.is_valid_tower_position(300, 300) is True


def test_update_valid_positions(sample_track):
    """
    Test that valid tower positions are correctly updated.

    Asserts:
        - Valid positions are correctly calculated based on waypoints and boundaries.
    """
    sample_track.waypoints = [(100, 100), (200, 200)]
    sample_track.update_valid_positions()
    assert (50, 50) not in sample_track.valid_tower_positions
    assert (300, 300) in sample_track.valid_tower_positions
    assert (100, 100) not in sample_track.valid_tower_positions
