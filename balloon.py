"""
A file containing the parent class for all Balloons as well as all subclasses.
"""

import pygame

BALLOON_TIERS = [
    ("red", lambda waypoints: RedBalloon(waypoints)),
    ("blue", lambda waypoints: BlueBalloon(waypoints)),
    ("green", lambda waypoints: GreenBalloon(waypoints)),
    ("yellow", lambda waypoints: YellowBalloon(waypoints)),
]


class Balloon:
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
        self.x = x
        self.y = y
        self.health = health
        self.color = color
        self.speed = speed
        self.size = size
        self.reward = reward
        self.damage = damage
        self.waypoints = waypoints
        self.current_waypoint = 0
        self.type = "base"

    def draw(self, screen):
        """
        Draws the balloon on the screen as a circle.

        Args:
            screen (pygame.Surface?): The surface to draw the balloon on.
        """
        pygame.draw.circle(
            screen, self.color, (int(self.x), int(self.y)), self.size
        )

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
        return False

    def take_damage(self, amount):
        self.health -= amount
        if self.health > 0:
            return []

        index = next(
            (
                i
                for i, (name, _) in enumerate(BALLOON_TIERS)
                if name == self.type
            ),
            None,
        )
        if index is None:
            return []

        balloons_to_spawn = []
        remaining_damage = -self.health

        while index > 0 and remaining_damage > 0:
            index -= 1
            spawn_name, spawn_func = BALLOON_TIERS[index]
            new_balloon = spawn_func(self.waypoints)
            new_balloon.x, new_balloon.y = self.x, self.y
            new_balloon.current_waypoint = self.current_waypoint
            balloons_to_spawn.append(new_balloon)
            remaining_damage -= new_balloon.health

        return balloons_to_spawn


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
            health=4,
            color=(255, 192, 203),
            speed=12.0,
            size=10,
            reward=20,
            damage=10,
            waypoints=waypoints,
        )
        self.type = "pink"
