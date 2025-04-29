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

    def __init__(self, width=1920, height=1080):
        """
        Initialize the track with game dimensions and waypoints
        """
        self.width = width
        self.height = height
        self.waypoints = []
        self.towers = []
        self.tower_locations = []
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
        for tower in self.tower_locations:

            wx, wy = tower
            #  print(wx)
            distance = math.sqrt((x - wx) ** 2 + (y - wy) ** 2)
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

    def add_tower(self, tower):
        """Add a tower to the map if position is valid"""
        x, y = tower.position
        if self.is_valid_tower_position(x, y):
            self.towers.append(tower)
            self.tower_locations.append((x, y))
            print(self.tower_locations)
            return True
        return False

    def remove_tower(self, tower):
        """Remove a tower from the map"""
        if tower in self.towers:
            self.towers.remove(tower)
            return True
        return False

    def draw(self, screen):
        # Draw the path as a thick line between waypoints
        """"""
        if len(self.waypoints) >= 2:
            pygame.draw.lines(
                screen, (0, 0, 0), False, self.waypoints, 4
            )  # black path line

        # Optional: draw circles for turns or debugging
        for x, y in self.waypoints:
            pygame.draw.circle(screen, (0, 255, 0), (int(x), int(y)), 3)


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
