"""
module that defines the player class
"""


class Player:
    """
    player class
    """

    def __init__(self, name, age):
        """
        constructor for player class
        """
        self.name = name
        self.age = age
        self.score = 0

    def __str__(self):
        """
        string representation of player
        """
        return f"{self.name} ({self.age})"
