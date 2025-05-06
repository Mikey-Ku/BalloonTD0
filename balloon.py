"""
Module for defining balloon types in the Balloon Tower Defense game.

This module defines classes for different types of balloons, each with
unique properties such as health, speed, and reward.
"""

import random
import math
import pygame

_IMAGE_CACHE = {}


def load_cached(path, size):
    """
    Loads and caches an image, scaling it to the specified size.

    Args:
        path (str): Path to the image file.
        size (tuple): Desired size of the image.

    Returns:
        pygame.Surface: The cached and scaled image surface.
    """
    key = (path, size)
    if key not in _IMAGE_CACHE:
        surf = pygame.image.load(path).convert_alpha()
        surf = pygame.transform.scale(surf, size)
        _IMAGE_CACHE[key] = surf
    return _IMAGE_CACHE[key].copy()


class Balloon(pygame.sprite.Sprite):
    """
    Base class for all enemy balloons.

    Attributes:
        x (float): Current x-coordinate of the balloon.
        y (float): Current y-coordinate of the balloon.
        health (int): Remaining health of the balloon.
        color (tuple[int, int, int]): RGB color of the balloon.
        speed (float): Movement speed (waypoints per frame).
        size (int): Visual radius of the balloon.
        reward (int): Money awarded when the balloon is popped.
        base_reward (int): Original reward value for child inheritance.
        damage (int): Player health reduction if the balloon reaches the end.
        waypoints (list[tuple[float, float]]): Path coordinates.
        current_waypoint (int): Index of the next waypoint to approach.
        type (str): Identifier string for balloon tier.
        skip_frames (int): Frames to skip before the next move.
        image (pygame.Surface): Visual representation of the balloon.
        rect (pygame.Rect): Rect for drawing the balloon.
        offset (tuple[float, float]): Rendering offset from path position.
        image_path (str | None): File path of the loaded image, if any.
    """

    def __init__(
        self,
        x,
        y,
        health,
        color,
        speed,
        size,
        reward,
        damage,
        waypoints,
    ):
        """
        Initializes a Balloon instance.

        Args:
            x (float): Initial x-coordinate.
            y (float): Initial y-coordinate.
            health (int): Starting health.
            color (tuple[int, int, int]): RGB color.
            speed (float): Movement speed (waypoints per frame).
            size (int): Radius for drawing.
            reward (int): Money given when popped.
            damage (int): Damage to player if not popped.
            waypoints (list[tuple[float, float]]): Path to follow.
        """
        super().__init__()
        self.x = x
        self.y = y
        self.health = health
        self.color = color
        self.speed = speed
        self.size = size
        self.reward = reward
        self.base_reward = reward
        self.damage = damage
        self.waypoints = waypoints
        self.current_waypoint = 0
        self.type = "base"
        self.skip_frames = 0

        self.image = pygame.Surface(
            (self.size * 2, self.size * 2), pygame.SRCALPHA
        )
        pygame.draw.circle(
            self.image, self.color, (self.size, self.size), self.size
        )
        self.offset = (0, 0)
        self.rect = self.image.get_rect(
            center=(int(self.x + self.offset[0]), int(self.y + self.offset[1]))
        )

        self.image_path = None

    def load_image(self, image_path):
        """
        Loads and scales the balloon image.

        Args:
            image_path (str): Path to the image file.
        """
        self.image = pygame.image.load(image_path).convert_alpha()
        self.image = pygame.transform.scale(
            self.image, (self.size * 5, self.size * 5)
        )
        self.rect = self.image.get_rect(center=(int(self.x), int(self.y)))
        self.image_path = image_path

    def draw(self, screen):
        """
        Draws the balloon on the screen.

        Args:
            screen (pygame.Surface): The surface to draw the balloon on.
        """
        x_offset, y_offset = self.offset
        self.rect.center = (int(self.x + x_offset), int(self.y + y_offset))
        screen.blit(self.image, self.rect)

    def move(self):
        """
        Moves the balloon forward along the path by skipping `speed` waypoints.

        Returns:
            bool: True if the balloon has reached the end of the path.
        """
        skip = getattr(self, "skip_frames", 0)
        if skip > 0:
            self.skip_frames = skip - 1
            return False

        self.current_waypoint += int(self.speed)

        if self.current_waypoint >= len(self.waypoints):
            return True

        self.x, self.y = self.waypoints[self.current_waypoint]
        self.rect.center = (int(self.x), int(self.y))
        return False

    def take_damage(self, amount):
        """
        Downgrade by `amount` tiers, popping if you go below tier 0.

        Args:
            amount (int): Amount of damage to take.

        Returns:
            list: List of child balloons spawned after taking damage.
        """
        tier_names = [name for name, _ in balloon_tiers]
        idx = tier_names.index(self.type)

        new_idx = idx - amount
        if new_idx >= 0:
            _, ctor = balloon_tiers[new_idx]
            child = ctor(self.waypoints)
            child.base_reward = self.base_reward
            child.x, child.y = self.x, self.y
            child.current_waypoint = self.current_waypoint
            child.offset = getattr(self, "offset", (0, 0))
            child.skip_frames = getattr(self, "skip_frames", 0)
            return [child]

        return []


class RedBalloon(Balloon):
    """
    A subclass of Balloon representing a standard red balloon.

    Attributes:
        type (str): The type identifier for the balloon ("red").
    """

    def __init__(self, waypoints):
        """
        Initializes a RedBalloon with preset stats.

        Args:
            waypoints (list): A list of waypoints the balloon will follow.
        """
        super().__init__(
            x=waypoints[0][0],
            y=waypoints[0][1],
            health=1,
            color=(255, 0, 0),
            speed=1.0,
            size=10,
            reward=3,
            damage=1,
            waypoints=waypoints,
        )
        self.type = "red"
        self.load_image("balloon_images/red_balloon.png")


class BlueBalloon(Balloon):
    """
    A subclass of Balloon representing a standard blue balloon.

    Attributes:
        type (str): The type identifier for the balloon ("blue").
    """

    def __init__(self, waypoints):
        """
        Initializes a BlueBalloon with preset stats.

        Args:
            waypoints (list): A list of waypoints the balloon will follow.
        """
        super().__init__(
            x=waypoints[0][0],
            y=waypoints[0][1],
            health=2,
            color=(0, 0, 255),
            speed=1.4,
            size=10,
            reward=5,
            damage=2,
            waypoints=waypoints,
        )
        self.type = "blue"
        self.load_image("balloon_images/blue_balloon.png")


class GreenBalloon(Balloon):
    """
    A subclass of Balloon representing a standard green balloon.

    Attributes:
        type (str): The type identifier for the balloon ("green").
    """

    BASE_IMAGE = "balloon_images/green_balloon.png"

    def __init__(self, waypoints):
        """
        Initializes a GreenBalloon with preset stats.

        Args:
            waypoints (list): A list of waypoints the balloon will follow.
        """
        super().__init__(
            x=waypoints[0][0],
            y=waypoints[0][1],
            health=3,
            color=(0, 255, 0),
            speed=1.8,
            size=10,
            reward=7,
            damage=3,
            waypoints=waypoints,
        )
        self.type = "green"
        img_size = (self.size * 5, self.size * 5)
        self.image = load_cached(GreenBalloon.BASE_IMAGE, img_size)
        self.rect = self.image.get_rect(center=(int(self.x), int(self.y)))


class YellowBalloon(Balloon):
    """
    A subclass of Balloon representing a standard yellow balloon.

    Attributes:
        type (str): The type identifier for the balloon ("yellow").
    """

    def __init__(self, waypoints):
        """
        Initializes a YellowBalloon with preset stats.

        Args:
            waypoints (list): A list of waypoints the balloon will follow.
        """
        super().__init__(
            x=waypoints[0][0],
            y=waypoints[0][1],
            health=4,
            color=(255, 255, 0),
            speed=7,
            size=10,
            reward=10,
            damage=5,
            waypoints=waypoints,
        )
        self.type = "yellow"
        self.load_image("balloon_images/yellow_balloon.png")


class PinkBalloon(Balloon):
    """
    A subclass of Balloon representing a standard pink balloon.

    Attributes:
        type (str): The type identifier for the balloon ("pink").
    """

    def __init__(self, waypoints):
        """
        Initializes a PinkBalloon with preset stats.

        Args:
            waypoints (list): A list of waypoints the balloon will follow.
        """
        super().__init__(
            x=waypoints[0][0],
            y=waypoints[0][1],
            health=5,
            color=(255, 192, 203),
            speed=12.0,
            size=10,
            reward=15,
            damage=10,
            waypoints=waypoints,
        )
        self.type = "pink"
        self.load_image("balloon_images/pink_balloon.png")


class MoabBalloon(Balloon):
    """
    A multi-hit “MOAB” that takes 50 damage to die,
    then bursts into 40 GreenBalloons scattered around its death spot.

    Attributes:
        type (str): The type identifier for the balloon ("moab").
    """

    def __init__(self, waypoints):
        """
        Initializes a MoabBalloon with preset stats.

        Args:
            waypoints (list): A list of waypoints the balloon will follow.
        """
        super().__init__(
            x=waypoints[0][0],
            y=waypoints[0][1],
            health=50,
            color=(128, 128, 128),
            speed=1.0,
            size=20,
            reward=400,
            damage=100,
            waypoints=waypoints,
        )
        self.type = "moab"
        self.load_image("balloon_images/moab.png")

    def take_damage(self, amount):
        """
        Handles damage taken by the MoabBalloon.

        Args:
            amount (int): Amount of damage to take.

        Returns:
            list: List of child balloons spawned after taking damage.
        """
        self.health -= amount
        if self.health > 0:
            return [self]

        children = []
        used_pixels = set()
        num_kids = 40
        spread_radius = 20

        while len(children) < num_kids:
            theta = random.uniform(0, 2 * math.pi)
            radius = random.uniform(0, spread_radius)
            dx = math.cos(theta) * radius
            dy = math.sin(theta) * radius

            pix = (int(dx), int(dy))
            if pix in used_pixels:
                continue
            used_pixels.add(pix)

            damaged_balloon = GreenBalloon(self.waypoints)
            damaged_balloon.x, damaged_balloon.y = self.x, self.y
            damaged_balloon.current_waypoint = self.current_waypoint
            damaged_balloon.offset = (dx, dy)
            damaged_balloon.skip_frames = 12

            children.append(damaged_balloon)

        return children


balloon_tiers = [
    ("red", RedBalloon),
    ("blue", BlueBalloon),
    ("green", GreenBalloon),
    ("yellow", YellowBalloon),
    ("pink", PinkBalloon),
    ("moab", MoabBalloon),
]
