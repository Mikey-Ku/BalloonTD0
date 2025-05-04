"""
Defines the game map and track system that both balloons and towers
interact with.
"""

import math
import csv
import pygame


class Track:
    """
    A class to represent the game map and balloon path
    """

    def __init__(self, width=800, height=600):
        """
        Initialize the track with game dimensions and waypoints
        """
        self.width = width
        self.height = height
        self.waypoints = []
        self.towers = []
        self.valid_tower_positions = set()
        self.tower_invalid_radius = 15

    def is_valid_tower_position(self, x, y):
        """Check if a position is valid for tower placement"""
        for waypoint in self.waypoints:
            wx, wy = waypoint
            distance = math.sqrt((x - wx) ** 2 + (y - wy) ** 2)
            if distance < self.tower_invalid_radius:
                return False
        for tower in self.towers:
            distance = math.sqrt((x - tower.x) ** 2 + (y - tower.y) ** 2)
            if distance < 30:
                return False
        return True

    def update_valid_positions(self):
        """Update the set of valid tower positions"""
        self.valid_tower_positions = set()

        grid_size = 20
        for x in range(50, self.width - 50, grid_size):
            for y in range(50, self.height - 50, grid_size):
                if self.is_valid_tower_position(x, y):
                    self.valid_tower_positions.add((x, y))

    def draw(self, screen):
        """Draw the track and path on screen"""
        # Draw path between waypoints
        if len(self.waypoints) > 1:
            pygame.draw.lines(
                screen, (100, 100, 100), False, self.waypoints, 20
            )

        # Draw waypoints
        for point in self.waypoints:
            pygame.draw.circle(
                screen, (50, 50, 50), (int(point[0]), int(point[1])), 5
            )


def load_waypoints_from_csv(filename):
    """
    Loads waypoints from a CSV file and returns a list of (x, y) tuples.
    """
    waypoints = []
    with open(filename, newline="") as csvfile:
        reader = csv.reader(csvfile)
        next(reader)  # skip header
        for row in reader:
            if len(row) >= 2:
                x = float(row[0])
                y = float(row[1])
                waypoints.append((x, y))
    return waypoints
