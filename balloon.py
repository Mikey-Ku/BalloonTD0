"""
A file containing the parent class for all Balloons as well as all subclasses.
"""

import pygame


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

    def __init__(  # pylint is tripping , too many args??
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
        self.rect = self.image.get_rect(center=(int(self.x), int(self.y)))
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
        screen.blit(self.image, self.rect)

    def move(self):
        """
        Moves the balloon forward along the path by skipping `speed` waypoints.

        Returns:
            bool: True if the balloon has reached the end of the path.
        """
        self.current_waypoint += int(self.speed)

        if self.current_waypoint >= len(self.waypoints):
            return True

        self.x, self.y = self.waypoints[self.current_waypoint]
        self.rect.center = (int(self.x), int(self.y))  # Update rect position
        return False

    def take_damage(self, amount):
        """
        Downgrade this balloon by `amount` tiers:
          - If idx - amount >= 0: spawn one balloon of that lower tier.
          - Else: pop (no spawn).
        """
        # build a list of just the tier names
        tier_names = [name for name, _ in balloon_tiers]
        try:
            idx = tier_names.index(self.type)
        except ValueError:
            # unknown type → just die
            return []

        # compute target tier
        new_idx = idx - amount

        # if still in range, spawn exactly one of that tier
        if new_idx >= 0:
            _, ctor = balloon_tiers[new_idx]
            child = ctor(self.waypoints)
            child.base_reward = self.base_reward
            # preserve position and progress
            child.x, child.y = self.x, self.y
            child.current_waypoint = self.current_waypoint
            child.rect.center = (
                int(self.x),
                int(self.y),
            )  # Update rect position
            return [child]

        # otherwise it's popped
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
        Initializes a RedBalloon with preset stats.
        """
        super().__init__(
            x=waypoints[0][0],
            y=waypoints[0][1],
            health=2,
            color=(0, 0, 255),
            speed=1.0,
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

    def __init__(self, waypoints):
        super().__init__(
            x=waypoints[0][0],
            y=waypoints[0][1],
            health=3,
            color=(0, 255, 0),
            speed=1.0,
            size=10,
            reward=7,
            damage=3,
            waypoints=waypoints,
        )
        self.type = "green"
        self.load_image("balloon_images/green_balloon.png")


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
            speed=7.0,
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


balloon_tiers = [
    ("red", RedBalloon),
    ("blue", BlueBalloon),
    ("green", GreenBalloon),
    ("yellow", YellowBalloon),
    ("pink", PinkBalloon),
]
