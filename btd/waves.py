"""
Round definitions and spawn scheduling.

The original game shipped 20 rounds as a flat list of ``(type, count)`` pairs
with a single spawn delay per round, and simply ended when the list ran out.

Rounds 1-40 here are authored so that each new balloon type arrives with room
to react to it, and everything past 40 is generated procedurally so a run can
continue indefinitely. Spawn groups carry their own spacing and start delay,
so a round can open with a trickle of ceramics while a stream of regrow greens
runs underneath it.
"""

from __future__ import annotations

from dataclasses import dataclass

from .balloons import KINDS, modified, rbe


@dataclass(frozen=True)
class Group:
    """One stream of identical balloons within a round.

    Attributes:
        kind: Base balloon name, e.g. ``"ceramic"``.
        count: How many to release.
        spacing: Seconds between consecutive releases.
        delay: Seconds after the round starts before the first release.
        camo: Spawn them as camo.
        regen: Spawn them as regrow.
        fortified: Spawn them fortified.
    """

    kind: str
    count: int
    spacing: float = 0.45
    delay: float = 0.0
    camo: bool = False
    regen: bool = False
    fortified: bool = False

    @property
    def rbe(self) -> int:
        """Total balloons contained in this group."""
        return rbe(self.kind) * self.count * (2 if self.fortified else 1)


@dataclass(frozen=True)
class Wave:
    """A complete round.

    Attributes:
        number: 1-based round number.
        groups: Spawn streams that make up the round.
    """

    number: int
    groups: tuple[Group, ...]

    @property
    def rbe(self) -> int:
        """Total balloons contained in the round."""
        return sum(g.rbe for g in self.groups)

    @property
    def duration(self) -> float:
        """Seconds from round start until the last balloon is released."""
        return max(
            (g.delay + g.spacing * max(0, g.count - 1) for g in self.groups),
            default=0.0,
        )

    def describe(self) -> str:
        """Short human-readable summary, shown in the HUD before a round."""
        parts = []
        for g in self.groups:
            tag = ""
            if g.fortified:
                tag += "F"
            if g.camo:
                tag += "C"
            if g.regen:
                tag += "R"
            parts.append(f"{g.count}x {g.kind}{'-' + tag if tag else ''}")
        return ", ".join(parts)


def _g(kind, count, spacing=0.45, delay=0.0, flags="") -> Group:
    """Shorthand group constructor. ``flags`` may contain ``c``, ``r``, ``f``."""
    return Group(
        kind=kind,
        count=count,
        spacing=spacing,
        delay=delay,
        camo="c" in flags,
        regen="r" in flags,
        fortified="f" in flags,
    )


# Authored rounds 1-40. Each entry is the tuple of groups for that round.
# The shape of the curve: a new balloon type is introduced in small numbers
# one round before it appears in bulk, so the player gets a warning shot.
_AUTHORED: list[tuple[Group, ...]] = [
    # 1-5: reds and the first blues.
    (_g("red", 20, 0.60),),
    (_g("red", 32, 0.50),),
    (_g("red", 24, 0.50), _g("blue", 6, 0.70, 3.0)),
    (_g("red", 20, 0.45), _g("blue", 14, 0.55, 2.0)),
    (_g("blue", 28, 0.45),),
    # 6-10: greens arrive.
    (_g("red", 18, 0.35), _g("blue", 16, 0.45, 1.0), _g("green", 4, 1.10, 5.0)),
    (_g("blue", 22, 0.40), _g("green", 10, 0.70, 2.0)),
    (_g("green", 22, 0.45),),
    (_g("green", 26, 0.40), _g("blue", 20, 0.40, 1.5)),
    (_g("green", 34, 0.34), _g("red", 20, 0.40, 2.0)),
    # 11-15: yellows and pinks.
    (_g("yellow", 10, 0.80), _g("green", 20, 0.40, 1.0)),
    (_g("yellow", 24, 0.45),),
    (_g("yellow", 26, 0.40), _g("pink", 6, 1.00, 4.0)),
    (_g("pink", 16, 0.55), _g("yellow", 18, 0.40, 1.5)),
    (_g("pink", 32, 0.38),),
    # 16-20: black, white, zebra, and the first lead. These types contain far
    # more balloons than pink does, so the counts drop sharply to keep the
    # round-over-round difficulty curve smooth.
    (_g("black", 8, 0.55), _g("white", 8, 0.55, 1.0)),
    (_g("black", 12, 0.45), _g("pink", 20, 0.38, 1.5)),
    (_g("white", 14, 0.45), _g("zebra", 4, 1.00, 3.0)),
    (_g("zebra", 8, 0.60), _g("black", 12, 0.42, 2.0)),
    (_g("lead", 8, 0.70), _g("white", 16, 0.40, 1.5)),
    # 21-25: camo and regrow arrive, then the first MOAB.
    (_g("green", 24, 0.38, 0.0, "c"), _g("zebra", 8, 0.70, 2.0)),
    (_g("lead", 10, 0.60), _g("yellow", 20, 0.35, 1.5, "r")),
    (_g("zebra", 14, 0.50), _g("white", 12, 0.42, 1.0, "c")),
    (_g("rainbow", 6, 0.90), _g("black", 20, 0.40, 2.0)),
    (_g("moab", 1, 1.0), _g("green", 24, 0.38, 2.5)),
    # 26-30: rainbows in bulk, a second MOAB, the first ceramics.
    (_g("rainbow", 12, 0.60), _g("lead", 12, 0.55, 2.0)),
    (_g("moab", 1, 1.0), _g("rainbow", 10, 0.60, 3.0)),
    (_g("rainbow", 16, 0.50, 0.0, "r"), _g("zebra", 16, 0.40, 1.5)),
    (_g("ceramic", 4, 1.20), _g("rainbow", 14, 0.50, 2.0)),
    (_g("ceramic", 8, 0.85), _g("lead", 16, 0.45, 2.0, "c")),
    # 31-35: ceramics in numbers, then the first BFB.
    (_g("ceramic", 12, 0.65), _g("rainbow", 16, 0.42, 1.5)),
    (_g("moab", 2, 3.0), _g("ceramic", 8, 0.80, 3.0)),
    (_g("ceramic", 12, 0.60, 0.0, "c"), _g("rainbow", 18, 0.38, 2.0)),
    (_g("ceramic", 16, 0.55), _g("lead", 20, 0.40, 1.5, "r")),
    (_g("bfb", 1, 1.0), _g("ceramic", 10, 0.70, 4.0)),
    # 36-40: fortified everything, closing on two BFBs.
    (_g("moab", 3, 2.4), _g("ceramic", 14, 0.55, 2.0, "c")),
    (_g("ceramic", 16, 0.50, 0.0, "f"), _g("rainbow", 20, 0.34, 1.5, "c")),
    (_g("moab", 4, 2.0, 0.0, "f"), _g("ceramic", 14, 0.55, 3.0)),
    (_g("ceramic", 20, 0.45, 0.0, "cr"), _g("lead", 20, 0.40, 2.0, "f")),
    (_g("bfb", 2, 4.0), _g("moab", 3, 2.4, 4.0), _g("ceramic", 16, 0.50, 2.0, "c")),
]


def _procedural(number: int) -> tuple[Group, ...]:
    """Generate a round beyond the authored set.

    Scales counts and modifier frequency with the round number, and puts a
    named boss on every tenth round so the pacing stays legible.

    Args:
        number: 1-based round number, expected to be above 40.

    Returns:
        The round's spawn groups.
    """
    over = number - 40
    # Compounding growth. A fixed set of fully upgraded towers has a ceiling
    # -- the cross-path rule caps any one tower -- so endless rounds have to
    # grow geometrically or the late game becomes a formality.
    scale = 1.11 ** over

    groups: list[Group] = []

    # Boss cadence: ZOMGs every tenth round from 50, BFBs on the other fives.
    if number % 10 == 0 and number >= 50:
        groups.append(_g("zomg", max(1, int(1 + over / 14)), 5.0, 0.0,
                         "f" if number > 60 else ""))
    if number % 5 == 0:
        groups.append(_g("bfb", max(1, int(1 + over / 7)), 3.0, 2.0,
                         "f" if number > 55 else ""))

    groups.append(_g("moab", max(2, int(3 * scale ** 0.62)),
                     max(0.6, 2.4 - over * 0.045), 2.0,
                     "f" if number > 48 else ""))

    groups.append(_g("ceramic", max(12, int(16 * scale ** 0.58)),
                     max(0.10, 0.50 - over * 0.010), 1.5,
                     "cr" if number % 3 == 0 else "c"))

    groups.append(_g("rainbow", max(16, int(20 * scale ** 0.45)),
                     max(0.08, 0.34 - over * 0.007), 3.0,
                     "r" if number % 2 == 0 else ""))

    return tuple(groups)


def wave_for(number: int) -> Wave:
    """Return the round definition for a 1-based round number."""
    if 1 <= number <= len(_AUTHORED):
        return Wave(number, _AUTHORED[number - 1])
    return Wave(number, _procedural(number))


def build_schedule(wave: Wave, count_scale: float = 1.0) -> list[tuple[float, object]]:
    """Flatten a round into a time-ordered spawn schedule.

    Args:
        wave: The round to schedule.
        count_scale: Difficulty multiplier on group sizes. Spacing shrinks by
            the same factor so a harder round is denser rather than merely
            longer.

    Returns:
        ``(time_seconds, BalloonKind)`` pairs sorted by time. The game pops
        entries off the front as the round clock advances.
    """
    schedule: list[tuple[float, object]] = []
    for group in wave.groups:
        if group.kind not in KINDS:
            continue
        kind = modified(
            group.kind,
            camo=group.camo,
            regen=group.regen,
            fortified=group.fortified,
        )
        count = max(1, int(round(group.count * count_scale)))
        spacing = group.spacing / max(0.2, count_scale)
        for i in range(count):
            schedule.append((group.delay + i * spacing, kind))

    schedule.sort(key=lambda entry: entry[0])
    return schedule


def round_bonus(number: int, base: int, per_round: int) -> int:
    """Money awarded for completing a round."""
    return base + per_round * number
