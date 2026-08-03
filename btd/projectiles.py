"""
Projectiles.

The original game had no projectiles at all -- towers applied damage directly
to whatever they targeted, so there was nothing on screen between a tower and
a popping balloon. Giving shots real travel time also makes tower placement
matter, because a slow projectile can miss a fast balloon.

Two flavours exist:

* :class:`Projectile` -- a physical shot that travels, can pierce several
  balloons, and optionally explodes on contact.
* Hitscan effects, which towers resolve immediately and register as a
  :class:`Beam` purely so the player can see the shot.
"""

from __future__ import annotations

import math

from .balloons import Balloon, HitResult, in_radius, resolve_hit


class Projectile:
    """A travelling shot.

    Attributes:
        x, y: World position.
        v_x, v_y: Velocity in pixels per second.
        damage: Hit points removed per balloon struck.
        damage_type: One of the damage type constants in :mod:`btd.balloons`.
        pierce: Number of separate balloons this shot can still hit.
        life: Seconds remaining before it expires.
        radius: Collision radius.
        splash: Explosion radius on contact; 0 for a direct-hit shot.
        moab_bonus: Extra damage applied only to MOAB-class balloons.
        alive: Cleared once spent.
        hit: Balloons already struck, so pierce does not re-hit the same one.
    """

    __slots__ = (
        "x", "y", "v_x", "v_y", "damage", "damage_type", "pierce", "life",
        "radius", "splash", "moab_bonus", "alive", "hit", "colour", "trail",
    )

    def __init__(self, x, y, v_x, v_y, damage, damage_type, pierce=1,
                 life=2.0, radius=4, splash=0.0, moab_bonus=0,
                 colour=(250, 246, 230), trail=False):
        self.x = x
        self.y = y
        self.v_x = v_x
        self.v_y = v_y
        self.damage = damage
        self.damage_type = damage_type
        self.pierce = pierce
        self.life = life
        self.radius = radius
        self.splash = splash
        self.moab_bonus = moab_bonus
        self.alive = True
        self.hit: set[int] = set()
        self.colour = colour
        self.trail = trail

    @property
    def angle(self) -> float:
        """Heading in degrees, counter-clockwise from screen-right."""
        return math.degrees(math.atan2(-self.v_y, self.v_x))

    def advance(self, dt: float, bounds: tuple[int, int]) -> None:
        """Move the projectile and expire it if it leaves the map or times out."""
        self.x += self.v_x * dt
        self.y += self.v_y * dt
        self.life -= dt
        if self.life <= 0:
            self.alive = False
            return
        margin = 40
        if not (-margin <= self.x <= bounds[0] + margin
                and -margin <= self.y <= bounds[1] + margin):
            self.alive = False

    def damage_against(self, balloon: Balloon) -> int:
        """Damage this shot deals to a specific balloon."""
        return self.damage + (self.moab_bonus if balloon.kind.moab else 0)


def collide(projectile: Projectile, balloons: list[Balloon],
            hp_scale: float = 1.0, speed_scale: float = 1.0) -> HitResult:
    """Resolve a projectile against the balloon list for one tick.

    Handles both direct hits and, for explosive shots, the splash that follows.

    Args:
        projectile: The shot being tested. Mutated: ``pierce`` is spent and
            ``alive`` may be cleared.
        balloons: Live balloons. Not mutated; new balloons come back in the
            result so the caller controls list ownership.
        hp_scale: Difficulty multiplier passed to spawned children.
        speed_scale: Difficulty multiplier passed to spawned children.

    Returns:
        Combined :class:`~btd.balloons.HitResult` for everything struck.
    """
    total = HitResult()
    if not projectile.alive:
        return total

    for balloon in balloons:
        if projectile.pierce <= 0 or not projectile.alive:
            break
        if not balloon.alive or id(balloon) in projectile.hit:
            continue
        if not in_radius(balloon, projectile.x, projectile.y, projectile.radius):
            continue

        projectile.hit.add(id(balloon))

        if projectile.splash > 0:
            _explode(projectile, balloons, total, hp_scale, speed_scale)
            projectile.alive = False
            break

        result = resolve_hit(
            balloon, projectile.damage_against(balloon),
            projectile.damage_type, hp_scale, speed_scale,
        )
        _merge(total, result)
        # An immune balloon stops the shot rather than being passed through,
        # which is what makes lead and black balloons feel like real walls.
        projectile.pierce -= 1

    if projectile.pierce <= 0:
        projectile.alive = False
    return total


def _explode(projectile: Projectile, balloons: list[Balloon], total: HitResult,
             hp_scale: float, speed_scale: float) -> None:
    """Apply an explosive shot's splash to everything in its radius."""
    for other in balloons:
        if not other.alive:
            continue
        if in_radius(other, projectile.x, projectile.y, projectile.splash):
            _merge(total, resolve_hit(
                other, projectile.damage_against(other),
                projectile.damage_type, hp_scale, speed_scale,
            ))


def _merge(into: HitResult, other: HitResult) -> None:
    """Accumulate one hit result into another."""
    into.money += other.money
    into.pops += other.pops
    into.spawned.extend(other.spawned)


class Beam:
    """A short-lived line drawn for a hitscan shot.

    Purely cosmetic; the damage was already applied when the beam was created.
    """

    __slots__ = ("x1", "y1", "x2", "y2", "life", "max_life", "colour", "width")

    def __init__(self, x1, y1, x2, y2, colour=(255, 240, 190), width=2, life=0.12):
        self.x1, self.y1 = x1, y1
        self.x2, self.y2 = x2, y2
        self.life = life
        self.max_life = life
        self.colour = colour
        self.width = width

    @property
    def alive(self) -> bool:
        """Whether the beam still has time left to draw."""
        return self.life > 0

    def advance(self, dt: float) -> None:
        """Age the beam."""
        self.life -= dt
