"""
Module for managing the track and waypoints in the Balloon Tower Defense game.

This module defines the `Track` class and functions for loading waypoints
from a CSV file.
"""

import math
import csv


class Track:
    """Represents the track on which balloons move."""

    def __init__(self, width=800, height=600):
        """
        Initializes the track with game dimensions and waypoints.

        Args:
            width (int): The width of the game map.
            height (int): The height of the game map.
        """
        self.width = width
        self.height = height
        self.waypoints = []
        self.towers = []
        self.valid_tower_positions = set()
        self.tower_invalid_radius = 15

    def is_valid_tower_position(self, x, y):
        """
        Checks if a position is valid for tower placement.

        Args:
            x (float): The x-coordinate of the position.
            y (float): The y-coordinate of the position.

        Returns:
            bool: True if the position is valid for tower placement, False otherwise.
        """
        for waypoint in self.waypoints:
            w_x, w_y = waypoint
            distance = math.sqrt((x - w_x) ** 2 + (y - w_y) ** 2)
            if distance < self.tower_invalid_radius:
                return False
        for tower in self.towers:
            distance = math.sqrt((x - tower.x) ** 2 + (y - tower.y) ** 2)
            if distance < 30:
                return False
        if x < 0 or x > self.width or y < 0 or y > self.height:
            return False
        return True

    def update_valid_positions(self):
        """
        Updates the set of valid tower positions.
        """
        self.valid_tower_positions = set()

        grid_size = 20
        for x in range(50, self.width - 50, grid_size):
            for y in range(50, self.height - 50, grid_size):
                if self.is_valid_tower_position(x, y):
                    self.valid_tower_positions.add((x, y))


def load_waypoints_from_csv(filename):
    """
    Loads waypoints from a CSV file.

    Args:
        filename (str): The path to the CSV file containing waypoints.

    Returns:
        list: A list of waypoints, where each waypoint is a tuple (x, y).
    """
    waypoints = []
    with open(filename, newline="", encoding="utf-8") as csvfile:
        reader = csv.reader(csvfile)
        next(reader)
        for row in reader:
            if len(row) >= 2:
                x = float(row[0])
                y = float(row[1])
                waypoints.append((x, y))
    return waypoints
