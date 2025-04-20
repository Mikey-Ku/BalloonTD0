class Tower:
    """
    Represents a tower on the map. Towers are placed on the map and automatically
    attack enemy balloons within their range.

    Attributes:
    x (float): X-coordinate of the tower on the map.
    y (float): Y-coordinate of the tower on the map.
    type (str): The classifies the type of tower.
    level (int): Current upgrade level of the tower.
    range (float): Radius within which the tower can attack balloons.
    cost (int): Purchase or upgrade cost of the tower.
    damage (int): Amount of damage dealt per attack.
    attack_speed (float): Number of attacks per second.
    cooldown (float): Time until the tower can attack again.
    """

    def init(self):

        self.type = ""
        self._x_coord = 0
        self._y_coord = 0
        self._level = 1
        self._range = 0
        self._cost = 0
        self._damage = 0
        self._attack_speed = 0
        self._cooldown = 0

    def find_target(self, balloons):
        """
        Chooses a balloon to attack. By finding the balloons in range
        and finding the one furtherest along the track.

        Args:
            balloons (list or dict)
        Returns:
            the class of the balloon to attack
        """
        current_balloon = []
        for balloon in balloons:

            def in_range(balloon):
                if balloon.current_waypoint > current_balloon:
                    current_balloon = balloon

        return current_balloon

    def in_range(self, target):
        """
        Finds all balloons in range

        Args:
            target (list): contains the x and y coords of a ballon
        Returns:
            boolean: represents whether the balloon is in range or not
        """
        dx = target[0] - self.x
        dy = target[1] - self.y
        if (dx**2 + dy**2) ** 0.5 <= self.range:
            return True
        return False

    def attack(self, balloons, current_time):
        """
        Attacks a balloon if it's in range and at a rate based on cooldown
        and uses the take damage.

        Args:
            balloons (list or dict)
        Returns:
            Deals damage to a balloon
        """

        if (current_time % self._cooldown) == 0:
            target = self.find_target(balloons)
            target.take_damage(self.damage)

    # not neccessary for base implementation

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
