"""
Persistent settings and high scores.

Writes a single JSON file. Every filesystem operation is guarded, because the
browser build runs on a virtual filesystem that may not be writable -- in that
case the game keeps the data in memory for the session and simply does not
persist it, rather than failing to start.
"""

from __future__ import annotations

import json
import os

from .config import DEFAULT_MUSIC_VOLUME, DEFAULT_SFX_VOLUME

FILENAME = "balloon_td_save.json"

_DEFAULTS: dict = {
    "music_volume": DEFAULT_MUSIC_VOLUME,
    "sfx_volume": DEFAULT_SFX_VOLUME,
    "show_ranges": True,
    "best": {},          # "map:difficulty" -> best round reached
    "wins": 0,
    "total_pops": 0,
}


def _save_dir() -> str:
    """Return a writable directory for save data.

    Prefers the platform's user-data location and falls back to the working
    directory, which is what the browser build ends up using.
    """
    home = os.path.expanduser("~")
    candidates = [
        os.path.join(home, "Library", "Application Support", "BalloonTD"),
        os.path.join(os.environ.get("APPDATA", ""), "BalloonTD"),
        os.path.join(home, ".local", "share", "BalloonTD"),
    ]
    for candidate in candidates:
        parent = os.path.dirname(candidate)
        if parent and os.path.isdir(parent):
            return candidate
    return os.path.join(os.getcwd(), ".btd")


class SaveData:
    """In-memory settings and records, backed by a JSON file when possible.

    Attributes:
        data: The live dictionary of settings and records.
        writable: False if the last write attempt failed.
    """

    def __init__(self):
        self.data = dict(_DEFAULTS)
        self.data["best"] = {}
        self.writable = True
        self.path = os.path.join(_save_dir(), FILENAME)
        self.load()

    def load(self) -> None:
        """Read the save file, keeping defaults for anything missing."""
        try:
            with open(self.path, encoding="utf-8") as handle:
                stored = json.load(handle)
        except (OSError, ValueError):
            return
        if not isinstance(stored, dict):
            return
        for key, value in stored.items():
            if key in _DEFAULTS and isinstance(value, type(_DEFAULTS[key])):
                self.data[key] = value

    def flush(self) -> None:
        """Write the save file, silently giving up if the location is read-only."""
        if not self.writable:
            return
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            with open(self.path, "w", encoding="utf-8") as handle:
                json.dump(self.data, handle, indent=2)
        except OSError:
            self.writable = False

    # -- typed accessors --------------------------------------------------

    def get(self, key: str):
        """Read a setting."""
        return self.data.get(key, _DEFAULTS.get(key))

    def set(self, key: str, value) -> None:
        """Write a setting and persist immediately."""
        self.data[key] = value
        self.flush()

    def best_round(self, map_key: str, difficulty: str) -> int:
        """Highest round reached on a map and difficulty."""
        return int(self.data["best"].get(f"{map_key}:{difficulty}", 0))

    def record_run(self, map_key: str, difficulty: str, round_reached: int,
                   pops: int, won: bool) -> bool:
        """Record the outcome of a finished run.

        Args:
            map_key: Map identifier.
            difficulty: Difficulty identifier.
            round_reached: Highest round the player survived.
            pops: Balloon layers destroyed during the run.
            won: Whether the final round was cleared.

        Returns:
            True if this run set a new best for that map and difficulty.
        """
        key = f"{map_key}:{difficulty}"
        previous = int(self.data["best"].get(key, 0))
        improved = round_reached > previous
        if improved:
            self.data["best"][key] = round_reached
        self.data["total_pops"] = int(self.data.get("total_pops", 0)) + pops
        if won:
            self.data["wins"] = int(self.data.get("wins", 0)) + 1
        self.flush()
        return improved
