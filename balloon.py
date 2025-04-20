"""
A file containing the parent class for all Balloons as well as all subclasses.
"""

import pygame


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
    """

    waypoints = []  # the path that all balloons take

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
        Moves the balloon toward its next waypoint along the path.

        This method updates the balloon's position based on its speed and current waypoint.
        Once a waypoint is reached, it progresses to the next one.

        **** Will implement more once we reach a consensus on how waypoints work

        Returns:
            bool: True if the balloon has reached the final
            waypoint (end of path). False, if otherwise.
        """
        pass

    def take_damage(self, amount):
        """
        Reduces the balloon's health by a specified amount.

        Args:
            amount (int): The amount of damage to apply.

        Returns:
            bool: True if the balloon's health drops to 0 or
            below (popped). False, if not.
        """
        self.health -= amount
        return self.health <= 0


class RedBalloon(Balloon):
    """
    A subclass of Balloon representing a standard red balloon.

    Attributes:
        type (str): The type identifier for the balloon ("red").
    """

    def __init__(self):
        """
        Initializes a RedBalloon with preset stats.
        """
        super().__init__(
            x=Balloon.waypoints[0][0],
            y=Balloon.waypoints[0][1],
            health=1,
            color=(255, 0, 0),  # rgb red
            speed=1.0,
            size=10,
            reward=5,
            damage=1,
            waypoints=Balloon.waypoints,
        )
        self.type = "red"


class BlueBalloon(Balloon):
    """
    A subclass of Balloon representing a standard red balloon.

    Attributes:
        type (str): The type identifier for the balloon ("red").
    """

    def __init__(self):
        """
        Initializes a RedBalloon with preset stats.
        """
        super().__init__(
            x=Balloon.waypoints[0][0],
            y=Balloon.waypoints[0][1],
            health=1,
            color=(0, 0, 255),  # rgb blue
            speed=1.0,
            size=10,
            reward=5,
            damage=1,
            waypoints=Balloon.waypoints,
        )
        self.type = "red"
