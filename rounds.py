"""
rounds.py

Defines the sequence of rounds (waves) for the Balloon TD game.
"""

rounds_config = [
    # --- Rounds 1–5: intro waves (spawn_delay=500ms) ---
    {"balloons": [("red", 10)], "spawn_delay": 500},
    {"balloons": [("red", 15)], "spawn_delay": 500},
    {"balloons": [("red", 20)], "spawn_delay": 500},
    {"balloons": [("blue", 10)], "spawn_delay": 500},
    {"balloons": [("blue", 15)], "spawn_delay": 500},
    # --- Rounds 6–9: intermediate (spawn_delay=400ms) ---
    {"balloons": [("green", 10)], "spawn_delay": 400},
    {"balloons": [("green", 15)], "spawn_delay": 400},
    {"balloons": [("yellow", 10)], "spawn_delay": 400},
    {"balloons": [("pink", 10)], "spawn_delay": 400},
    # --- Round 10: 1 MOAB (boss wave, faster) ---
    {"balloons": [("moab", 1)], "spawn_delay": 100},
    # --- Rounds 11–15: big single-color (spawn_delay=300ms) ---
    {"balloons": [("red", 25)], "spawn_delay": 300},
    {"balloons": [("blue", 20)], "spawn_delay": 300},
    {"balloons": [("green", 20)], "spawn_delay": 300},
    {"balloons": [("yellow", 15)], "spawn_delay": 300},
    {"balloons": [("pink", 20)], "spawn_delay": 300},
    # --- Rounds 16–19: mixed waves (spawn_delay=200ms) ---
    {"balloons": [("red", 10), ("blue", 10)], "spawn_delay": 200},
    {"balloons": [("blue", 10), ("green", 10)], "spawn_delay": 200},
    {"balloons": [("green", 10), ("yellow", 10)], "spawn_delay": 200},
    {"balloons": [("yellow", 10), ("pink", 10)], "spawn_delay": 200},
    # --- Round 20: 3 MOABs (final boss) ---
    {"balloons": [("moab", 3)], "spawn_delay": 100},
]
