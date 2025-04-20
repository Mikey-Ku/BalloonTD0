"""
Defines the game map and track system that both balloons and towers
interact with.
"""

import math
import csv
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
        self.valid_tower_positions = set()
        self.tower_invalid_radius = 15

    def load_waypoints_from_csv(self, csv_file_path):
        """Load waypoints from a CSV file"""
        self.waypoints = []
        with open(csv_file_path, "r") as csv_file:
            csv_reader = csv.reader(csv_file)
            for row in csv_reader:
                if len(row) >= 2:
                    try:
                        x = int(row[0])
                        y = int(row[1])
                        self.waypoints.append((x, y))
                    except ValueError:
                        print(
                            f"Warning: Could not convert {row} to coordinates"
                        )

            self.update_valid_positions()

    def is_valid_tower_position(self, x, y):
        """Check if a position is valid for tower placement"""
        for waypoint in self.waypoints:
            wx, wy = waypoint
            distance = math.sqrt((x - wx) ** 2 + (y - wy) ** 2)
            if distance < self.tower_invalid_radius:
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

    def add_tower(self, tower):
        """Add a tower to the map if position is valid"""
        x, y = tower.position
        if self.is_valid_tower_position(x, y):
            self.towers.append(tower)
            return True
        return False

    def remove_tower(self, tower):
        """Remove a tower from the map"""
        if tower in self.towers:
            self.towers.remove(tower)
            return True
        return False
