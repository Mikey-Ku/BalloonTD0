"""
Module for defining tower behavior in the Balloon Tower Defense game.

This module provides the base `Tower` class and its subclasses (`SniperTower`,
`DartTower`, `SuperTower`, `TacTower`). Towers can load images, target and
attack balloons, and support upgrading and selling.
"""

import math
import pygame
from balloon import MoabBalloon

TOWER_IMAGES = {}


class Tower(pygame.sprite.Sprite):
    """
    Represents a tower on the map. Towers are placed on the map and automatically
    attack enemy balloons within their range.

    Attributes:
        x (float): X-coordinate of the tower on the map.
        y (float): Y-coordinate of the tower on the map.
        radius (float): Radius of how large the tower is.
        level (int): Current upgrade level of the tower.
        range (float): Radius within which the tower can attack balloons.
        cost (int): Purchase or upgrade cost of the tower.
        damage (int): Amount of damage dealt per attack.
        attack_speed (float): Number of attacks per second.
        cooldown (float): Time until the tower can attack again.
        last_attack (float): Time of the last attack.
        upgrade_cost (int): Cost to upgrade the tower.
        image (Surface): The tower's sprite image
        rect (Rect): The tower's position and size rectangle
    """

    def __init__(self):
        """
        Initialize base tower attributes and sprite setup.
        """
        super().__init__()
        self.x = 0
        self.y = 0
        self.level = 1
        self.range = 0
        self.cost = 0
        self.damage = 0
        self.attack_speed = 0
        self.cooldown = 0
        self.last_attack = 0
        self.upgrade_cost = 100
        self.angle = 0

        # Sprite properties
        self.image = None
        self.rect = None
        self.radius = 15  # Default tower size
        self.original_image = None  # Store original image for rotation
        self.image_path = None  # Store image path for cache
        self.current_attack_speed = self.attack_speed
        self.current_cooldown = self.cooldown

    def load_image(self, image_path):
        """
        Load and cache the tower's image from disk, scaling to the tower radius.

        Args:
            image_path (str): Path to the image file.
        """
        self.image_path = image_path  # Store for rotation
        try:
            if image_path in TOWER_IMAGES:
                self.original_image = TOWER_IMAGES[image_path]
            else:
                self.original_image = pygame.image.load(
                    image_path
                ).convert_alpha()
                self.original_image = pygame.transform.scale(
                    self.original_image, (self.radius * 4, self.radius * 4)
                )
                TOWER_IMAGES[image_path] = self.original_image

            self.image = self.original_image.copy()
            self.rect = self.image.get_rect(center=(int(self.x), int(self.y)))

        except pygame.error as e:  # pylint: disable=no-member
            print(f"Error loading tower image '{image_path}': {e}")
            # Create a default circular surface if image loading fails
            self.original_image = pygame.Surface(
                (self.radius * 2, self.radius * 2),
                pygame.SRCALPHA,  # pylint: disable=no-member
            )
            pygame.draw.circle(
                self.original_image,
                (100, 100, 100),
                (self.radius, self.radius),
                self.radius,
            )
            self.image = self.original_image.copy()
            self.rect = self.image.get_rect(center=(int(self.x), int(self.y)))

    def update_angle(self, balloons):
        """
        Rotate the tower to face the nearest valid balloon.

        Args:
            balloons (list[Balloon]): List of active balloons to target.
        """
        target = self.find_target(balloons)
        if target:
            dx = target.x - self.x
            dy = target.y - self.y
            self.angle = (math.degrees(math.atan2(-dy, dx)) + 90) % 360

    def update(self, speed_multiplier=1):
        """
        Update sprite position and rotation; adjust cooldowns by multiplier.

        Args:
            speed_multiplier (float): Factor to speed up or slow down firing rates.
        """
        if self.rect:
            self.rect.centerx = int(self.x)
            self.rect.centery = int(self.y)
        if self.original_image:
            rotated_image = pygame.transform.rotate(
                self.original_image, self.angle
            )
            self.image = rotated_image
            self.rect = self.image.get_rect(center=(int(self.x), int(self.y)))
        # Update attack speed based on multiplier
        self.current_attack_speed = self.attack_speed * speed_multiplier
        self.current_cooldown = self.cooldown / speed_multiplier

    def update_position(self, x, y):
        """
        Move the tower to a new coordinate and update its sprite rect.

        Args:
            x (float): New x-coordinate.
            y (float): New y-coordinate.
        """
        self.x = x
        self.y = y
        self.rect.center = (int(x), int(y))

    def in_range(self, target):
        """
        Determine if a given point is within the tower's attack radius.

        Args:
            target (tuple[float, float]): (x, y) coordinates of the target point.

        Returns:
            bool: True if within range, False otherwise.
        """
        x_distance = target[0] - self.x
        y_distance = target[1] - self.y
        if (x_distance**2 + y_distance**2) ** 0.5 <= self.range:
            return True
        return False

    def find_target(self, balloons):
        """
        Select the balloon furthest along its path within range.

        Args:
            balloons (list[Balloon]): Active balloons.

        Returns:
            Balloon or None: Chosen target or None if no valid targets.
        """
        targets_in_range = [
            balloon
            for balloon in balloons
            if self.in_range((balloon.x, balloon.y))
        ]
        if not targets_in_range:
            return None

        # pick the balloon that is furthest along (highest current_waypoint)
        return max(targets_in_range, key=lambda b: b.current_waypoint)

    def attack(self, balloons, current_time):
        """
        Execute an attack if cooldown allows; return popped rewards.

        Args:
            balloons (list[Balloon]): Active balloon instances.
            current_time (float): Current game time in milliseconds.

        Returns:
            list[tuple[Balloon, int]]: List of (balloon, reward) for popped balloons.
        """
        rewards = []
        if not balloons:
            return rewards

        if current_time - self.last_attack < (self.current_cooldown * 1000):
            return rewards

        interval_ms = 1000 / self.current_attack_speed
        popped = []

        if current_time - self.last_attack >= interval_ms:
            target = self.find_target(balloons)
            if target:
                dx = target.x - self.x
                dy = target.y - self.y
                self.angle = math.degrees(math.atan2(-dy, dx))

                # Save reward BEFORE damaging
                original_reward = target.base_reward
                spawned = target.take_damage(self.damage)

                # remove the old balloon…
                balloons.remove(target)

                if spawned:
                    # …and spawn its children
                    balloons.extend(spawned)
                    # but if this was a MOAB that just died, still give its reward
                    if isinstance(target, MoabBalloon) and target.health <= 0:
                        popped.append((target, original_reward))
                else:
                    # popped outright (no children) — give reward as before
                    popped.append((target, original_reward))

                self.last_attack = current_time
        return popped

    def upgrade(self):
        """
        Increase tower stats and level, applying upgrade cost multiplier.
        """
        print(
            f"[Upgrade] {self.__class__.__name__}: damage {self.damage} →"
            f" {self.damage+1}"
        )

        self.level += 1
        self.damage += 1
        self.range *= 1.1
        self.attack_speed *= 1.1
        self.cost = self.cost * 1.5
        self.upgrade_cost = self.upgrade_cost * 1.5

    def sell(self):
        """
        Calculate sell value as a fraction of the tower's upgrade cost.

        Returns:
            float: Amount refunded to the player.
        """
        return self.upgrade_cost * 0.7


class SniperTower(Tower):
    """
    A subclass of Tower representing a sniper tower.
    """

    def __init__(self):
        """
        Initializes a SniperTower with preset stats.
        """
        super().__init__()
        self.level = 1
        self.range = 100000
        self.cost = 200
        self.damage = 2
        self.attack_speed = 0.5
        self.cooldown = 1.0
        self.radius = 15
        self.load_image("monkey_images/sniper_monkey.png")
        # Initialize rect position after x,y are set
        if self.rect:
            self.rect.centerx = int(self.x)
            self.rect.centery = int(self.y)


class DartTower(Tower):
    """
    A subclass of Tower representing a dart tower.
    """

    def __init__(self):
        """
        Initializes a DartTower with preset stats.
        """
        super().__init__()
        self.level = 1
        self.range = 100
        self.cost = 100
        self.damage = 1
        self.attack_speed = 1
        self.cooldown = 1.0
        self.radius = 15
        self.load_image("monkey_images/dart_monkey.png")
        # Initialize rect position after x,y are set
        if self.rect:
            self.rect.centerx = int(self.x)
            self.rect.centery = int(self.y)


class SuperTower(Tower):
    """
    Initializes a SuperTower with preset stats.
    """

    def __init__(self):
        """
        Initializes a SuperTower with preset stats.
        """
        super().__init__()
        self.level = 1
        self.range = 150
        self.cost = 2000
        self.damage = 1
        self.attack_speed = 2.5
        self.cooldown = 0.2
        self.radius = 15
        self.load_image("monkey_images/super_monkey.png")
        if self.rect:
            self.rect.centerx = int(self.x)
            self.rect.centery = int(self.y)


class TacTower(Tower):
    """
    Initializes a TacTower with preset stats.
    """

    def __init__(self):
        """
        Initializes a TacTower with preset stats.
        """
        super().__init__()
        self.level = 1
        self.range = 50
        self.cost = 300
        self.damage = 1
        self.attack_speed = 1.5
        self.cooldown = 0.8
        self.radius = 15
        self.load_image("monkey_images/tac_tower.png")
        if self.rect:
            self.rect.centerx = int(self.x)
            self.rect.centery = int(self.y)
