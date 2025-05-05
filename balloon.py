"""
A file containing the parent class for all Balloons as well as all subclasses.
"""

import random
import math
import pygame

_IMAGE_CACHE = {}


def load_cached(path, size):
    key = (path, size)
    if key not in _IMAGE_CACHE:
        surf = pygame.image.load(path).convert_alpha()
        surf = pygame.transform.scale(surf, size)
        _IMAGE_CACHE[key] = surf
    return _IMAGE_CACHE[key].copy()


class Balloon(pygame.sprite.Sprite):
    """
    Base class for enemy balloons.

    Attributes:
        x (float): X-coordinate of the balloon's position.
        y (float): Y-coordinate of the balloon's position.
        health (int): Current health of the balloon.
        color (tuple): RGB color representation.
        speed (float): Movement speed of the balloon.
        size (int): Visual radius of the balloon.
        reward (int): Money awarded to the player when popped.
        damage (int): Player health reduction if balloon reaches the end.
        waypoints (list): List of (x, y) tuples representing the path.
        current_waypoint (int): Index of the next waypoint to move toward.
        type (str): String representing the balloon type.
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
            x (float): Initial x position.
            y (float): Initial y position.
            health (int): Starting health of the balloon.
            color (tuple): RGB color tuple.
            speed (float): Balloon speed in pixels per frame.
            size (int): Radius of the balloon's visual representation.
            reward (int): Currency given to the player upon popping.
            damage (int): Damage dealt to the player if balloon reaches the end.
            waypoints (list): List of coordinates the balloon moves through.
        """
        super().__init__()
        self.x = x
        self.y = y
        self.health = health
        self.color = color
        self.speed = speed
        self.size = size
        self.reward = reward
        # remember the “true” reward for this balloon (and its descendants)
        self.base_reward = reward
        self.damage = damage
        self.waypoints = waypoints
        self.current_waypoint = 0
        self.type = "base"

        # Sprite properties
        self.image = pygame.Surface(
            (self.size * 2, self.size * 2), pygame.SRCALPHA
        )
        pygame.draw.circle(
            self.image, self.color, (self.size, self.size), self.size
        )  # draw a circle on the image
        self.offset = (0, 0)
        self.rect = self.image.get_rect(
            center=(int(self.x + self.offset[0]), int(self.y + self.offset[1]))
        )

        self.image_path = None  # Path to the balloon image (if any)

    def load_image(self, image_path):
        """Load and scale the balloon image"""
        self.image = pygame.image.load(image_path).convert_alpha()
        self.image = pygame.transform.scale(
            self.image, (self.size * 5, self.size * 5)
        )
        self.rect = self.image.get_rect(center=(int(self.x), int(self.y)))
        self.image_path = image_path  # Store the image path

    def draw(self, screen):
        """
        Draws the balloon on the screen.

        Args:
            screen (pygame.Surface?): The surface to draw the balloon on.
        """
        # always draw at path position + permanent offset
        ox, oy = self.offset
        self.rect.center = (int(self.x + ox), int(self.y + oy))
        screen.blit(self.image, self.rect)

    def move(self):
        """
        Moves the balloon forward along the path by skipping `speed` waypoints.

        Returns:
            bool: True if the balloon has reached the end of the path.
        """
        # if this balloon was just spawned from a MOAB, hold its position
        skip = getattr(self, "skip_frames", 0)
        if skip > 0:
            self.skip_frames = skip - 1
            return False

        self.current_waypoint += int(self.speed)

        if self.current_waypoint >= len(self.waypoints):
            return True

        self.x, self.y = self.waypoints[self.current_waypoint]
        self.rect.center = (int(self.x), int(self.y))  # Update rect position
        return False

    def take_damage(self, amount):
        """
        Downgrade by `amount` tiers, popping if you go below tier 0.
        """
        tier_names = [name for name, _ in balloon_tiers]
        idx = tier_names.index(self.type)

        new_idx = idx - amount
        if new_idx >= 0:
            _, ctor = balloon_tiers[new_idx]
            child = ctor(self.waypoints)
            child.base_reward = self.base_reward
            # preserve position, progress, offset, freeze
            child.x, child.y = self.x, self.y
            child.current_waypoint = self.current_waypoint
            child.offset = getattr(self, "offset", (0, 0))
            child.skip_frames = getattr(self, "skip_frames", 0)
            return [child]

        # new_idx < 0 → popped with no spawn
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
        Initializes a BlueBalloon preset stats.
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
    """

    def __init__(self, waypoints):
        super().__init__(
            x=waypoints[0][0],
            y=waypoints[0][1],
            health=50,  # must absorb 50hp before popping
            color=(128, 128, 128),  # grey
            speed=1.0,  # match other balloons so it actually moves
            size=20,  # visually large
            reward=400,  # reward if it reaches the end
            damage=100,  # lives lost if it reaches the end
            waypoints=waypoints,
        )
        self.type = "moab"
        # if you have a custom MOAB sprite, uncomment:
        self.load_image("balloon_images/moab.png")

    def take_damage(self, amount):
        # subtract damage
        self.health -= amount
        if self.health > 0:
            return [self]

        # spawn 40 greens in a tight cluster (radius=20px),
        # but make sure no two share the same int(x,y) offset
        children = []
        used_pixels = set()
        num_kids = 40
        spread_radius = 20

        while len(children) < num_kids:
            # random point in circle
            theta = random.uniform(0, 2 * math.pi)
            r = random.uniform(0, spread_radius)
            dx = math.cos(theta) * r
            dy = math.sin(theta) * r

            # round to int pixels to test overlap
            pix = (int(dx), int(dy))
            if pix in used_pixels:
                continue
            used_pixels.add(pix)

            g = GreenBalloon(self.waypoints)
            # start exactly at the MOAB’s path position
            g.x, g.y = self.x, self.y
            g.current_waypoint = self.current_waypoint

            # permanent draw‐time offset
            g.offset = (dx, dy)
            # hold for a few frames so you actually see the scatter
            g.skip_frames = 12

            children.append(g)

        return children


balloon_tiers = [
    ("red", RedBalloon),
    ("blue", BlueBalloon),
    ("green", GreenBalloon),
    ("yellow", YellowBalloon),
    ("pink", PinkBalloon),
    ("moab", MoabBalloon),
]
