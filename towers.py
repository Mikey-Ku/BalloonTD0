class Tower:
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
    """

    def __init__(self):
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
        """Attack balloons if cooldown has passed"""
        if (
            current_time - self.last_attack >= self.cooldown * 1000
        ):  # Convert to milliseconds
            target = self.find_target(balloons)
            if target:
                target.take_damage(self.damage)
                self.last_attack = current_time

    def upgrade(self):
        """
        Upgrade tower attributes at a cost.
        """
        self.level += 1
        self.damage *= 1.5
        self.range *= 1.1
        self.attack_speed *= 1.2
        self.cost = self.cost * 1.5

    def sell(self):
        """
        Return partial cost for selling the tower.
        """
        return self.cost * 0.7


class SniperTower(Tower):
    """
    A subclass of Tower representing a sniper tower.
    """

    def __init__(self):
        """
        Initializes a SniperTower with preset stats.
        """
        super().__init__()
        self.x = 0
        self.y = 0
        self.level = 1
        self.range = 100000
        self.cost = 200
        self.damage = 20
        self.attack_speed = 1.0
        self.cooldown = 1.0


class DartTower(Tower):
    """
    A subclass of Tower representing a dart tower.
    """

    def __init__(self):
        """
        Initializes a DartTower with preset stats.
        """
        super().__init__()
        self.x = 0
        self.y = 0
        self.level = 1
        self.range = 100
        self.cost = 100
        self.damage = 5
        self.attack_speed = 1.0
        self.cooldown = 1.0
