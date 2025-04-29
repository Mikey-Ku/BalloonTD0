"""
rounds.py

Defines the sequence of rounds (waves) for the Balloon TD game.
"""

rounds_config = [
    {"balloons": [("red", 20)],  "spawn_delay": 500},
    {"balloons": [("red", 10), ("blue", 10)], "spawn_delay": 500},
    {"balloons": [("blue", 20)], "spawn_delay": 300},
    {"balloons": [("green", 10)], "spawn_delay": 300},
    {"balloons": [("yellow", 10)], "spawn_delay": 300},
    {"balloons": [("pink", 15)], "spawn_delay": 200},
]
