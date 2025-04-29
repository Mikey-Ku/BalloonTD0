import os
import pygame

# Add image cache at module level
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

        # Sprite properties
        self.image = None
        self.rect = None
        self.radius = 15  # Default tower size

    def load_image(self, image_path):
        """Load and scale the tower image"""
        try:
            if image_path in TOWER_IMAGES:
                self.image = TOWER_IMAGES[image_path]
            else:
                self.image = pygame.image.load(image_path).convert_alpha()
                self.image = pygame.transform.scale(
                    self.image, (self.radius * 4, self.radius * 4)
                )
                TOWER_IMAGES[image_path] = self.image

            self.rect = self.image.get_rect(center=(int(self.x), int(self.y)))

        except pygame.error as e:
            print(f"Error loading tower image '{image_path}': {e}")
            # Create a default circular surface if image loading fails
            self.image = pygame.Surface(
                (self.radius * 2, self.radius * 2), pygame.SRCALPHA
            )
            pygame.draw.circle(
                self.image,
                (100, 100, 100),
                (self.radius, self.radius),
                self.radius,
            )
            self.rect = self.image.get_rect(center=(int(self.x), int(self.y)))

    def update(self):
        """Update method required by pygame.sprite.Sprite"""
        if self.rect:
            self.rect.centerx = int(self.x)
            self.rect.centery = int(self.y)

    def update_position(self, x, y):
        """Update tower position and rectangle"""
        self.x = x
        self.y = y
        self.rect.center = (int(x), int(y))

    def in_range(self, target):
        """
        checks if a balloon is in range of the tower

        Args:
            target (list): contains the x and y coords of a ballon
        Returns:
            boolean: represents whether the balloon is in range or not
        """
        x_distance = target[0] - self.x
        y_distance = target[1] - self.y
        if (x_distance**2 + y_distance**2) ** 0.5 <= self.range:
            return True
        return False

    def find_target(self, balloons):
        """Find the first balloon in range"""
        for balloon in balloons:
            if self.in_range((balloon.x, balloon.y)):
                return balloon
        return None

    def attack(self, balloons, current_time):
        interval_ms = 1000 / self.attack_speed
        if current_time - self.last_attack >= interval_ms:
            target = self.find_target(balloons)
            if target:
                balloons.remove(target)  # kill the old one
                spawned = target.take_damage(self.damage)
                balloons.extend(spawned)  # maybe one new lower‐tier
                self.last_attack = current_time

        return None

    def upgrade(self):
        """
        Upgrade tower attributes at a cost.
        """
        print(
            f"[Upgrade] {self.__class__.__name__}: damage {self.damage} →"
            f" {self.damage+1}"
        )

        self.level += 1
        self.damage += 1
        self.range *= 1.1
        self.attack_speed *= 1.2
        self.cost = self.cost * 1.5  # this is messed up it sells for too much
        self.upgrade_cost = self.upgrade_cost * 1.5

    def sell(self):
        """
        Return partial cost for selling the tower.
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
        self.attack_speed = 1.0
        self.cooldown = 1.0
        self.radius = 15
        # Load the image
        self.load_image("sniper_monkey.png")
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
        self.attack_speed = 1.0
        self.cooldown = 1.0
        self.radius = 15
        # Load the image
        self.load_image("dart_monkey.png")
        # Initialize rect position after x,y are set
        if self.rect:
            self.rect.centerx = int(self.x)
            self.rect.centery = int(self.y)
