"""
Defines the game map and track system that both balloons and towers interact with.
"""

import pygame
import csv


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
        self.valid_tower_positions = (
            set()
        )  # Positions where towers can be placed

    def add_waypoint(self, x, y):
        """Add a waypoint to the balloon path"""
        self.waypoints.append((x, y))

    def is_valid_tower_position(self, x, y):
        """Check if a position is valid for tower placement"""
        return (x, y) in self.valid_tower_positions

    def draw(self, screen):
        """Draw the track and path on screen"""
        pass  # Implementation details here


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
