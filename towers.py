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
    """

    def init(self):
        self.x = 0
        self.y = 0
        self.level = 1
        self.range = 0
        self.cost = 0
        self.damage = 0
        self.attack_speed = 0
        self.cooldown = 0

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
        """
        Chooses a balloon to attack. By finding the balloons in range
        and finding the one furthest along the track.
        Args:
            balloons (list or dict)
        Returns:
            the class of the balloon to attack
        """
        range_balloons = []
        for balloon in balloons:
            if self.in_range(balloons[balloon]):
                range_balloons.append(balloon)
            for balloon in range_balloons:
                current_balloon = balloons[balloon]
                if current_balloon.current_waypoint > balloon.current_waypoint:
                    current_balloon = balloon
        return current_balloon

    def attack(self, balloons, current_time):
        """
        Attacks a balloon if it's in range and at a rate based on cooldown
        and uses the take damage.

        Args:
            balloons (list or dict)
        Returns:
            Deals damage to a balloon
        """
        if (current_time % self.cooldown) == 0:
            target = self.find_target(balloons)
            target.take_damage(self.damage)

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
