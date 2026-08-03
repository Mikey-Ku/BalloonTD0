"""
Balloon definitions and the damage model.

The original code had two damage systems that contradicted each other: every
balloon carried a ``health`` field that was never decremented, while
``take_damage`` separately walked a flat tier list by index. It also copied
``base_reward`` onto every child, so a single pink balloon paid its full
reward once per tier as it was chewed down.

This module replaces both with one rule:

    A balloon has ``hp`` hit points. Damage removes hit points. When they
    reach zero the balloon pops, pays its own reward exactly once, and is
    replaced by its children. Damage left over after a pop cascades into
    those children, which is what makes a single high-damage shot tear
    through a stack.

Balloon *kinds* are immutable data. A :class:`Balloon` is a live instance with
a position along the path.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, replace

import pygame

from . import assets

# Damage types. Certain balloons are immune to certain types, which is what
# makes tower variety matter rather than everything being a damage stat.
SHARP = "sharp"
EXPLOSIVE = "explosive"
ENERGY = "energy"
NORMAL = "normal"

#: Pixels per second travelled by the slowest balloon. Every other speed is a
#: multiple of this, so the whole game's pacing is one number.
BASE_SPEED = 64.0

#: Lives lost when a balloon leaks is its RBE (total balloons it contains),
#: capped so that one unlucky leak cannot silently end a run outright.
LEAK_CAP = 25
LEAK_CAP_MOAB = 100


@dataclass(frozen=True)
class BalloonKind:
    """Immutable stats for one balloon type.

    Attributes:
        name: Unique identifier, also used in wave definitions.
        hp: Hits absorbed at this layer before popping.
        speed_mult: Speed as a multiple of :data:`BASE_SPEED`.
        children: Names of the balloons this one releases when popped.
        reward: Money paid when this layer pops.
        radius: Collision and draw radius in pixels.
        color: Fill colour used when no sprite is available.
        image: Optional sprite path relative to the project root.
        immune: Damage types this balloon ignores entirely.
        camo: Only towers with camo detection can target it.
        regen: Heals back toward its original kind over time.
        fortified: Applied as a modifier; doubles ``hp``.
        moab: Treated as MOAB-class for targeting and rendering.
    """

    name: str
    hp: int
    speed_mult: float
    children: tuple[str, ...]
    reward: int
    radius: int
    color: tuple[int, int, int]
    image: str | None = None
    immune: frozenset[str] = field(default_factory=frozenset)
    camo: bool = False
    regen: bool = False
    fortified: bool = False
    moab: bool = False

    @property
    def speed(self) -> float:
        """Travel speed in pixels per second."""
        return BASE_SPEED * self.speed_mult


def _k(name, hp, speed, children, reward, radius, color, **kw) -> BalloonKind:
    """Shorthand constructor for the table below."""
    return BalloonKind(
        name=name,
        hp=hp,
        speed_mult=speed,
        children=tuple(children),
        reward=reward,
        radius=radius,
        color=color,
        **kw,
    )


IMG = "balloon_images/"

#: The balloon ladder, ordered weakest to strongest.
KINDS: dict[str, BalloonKind] = {
    k.name: k
    for k in [
        _k("red", 1, 1.00, (), 1, 15, (222, 48, 48), image=IMG + "red_balloon.png"),
        _k("blue", 1, 1.40, ("red",), 1, 16, (56, 108, 232), image=IMG + "blue_balloon.png"),
        _k("green", 1, 1.80, ("blue",), 1, 17, (56, 186, 86), image=IMG + "green_balloon.png"),
        _k("yellow", 1, 3.20, ("green",), 1, 17, (240, 214, 62), image=IMG + "yellow_balloon.png"),
        _k("pink", 1, 3.50, ("yellow",), 1, 18, (244, 130, 190), image=IMG + "pink_balloon.png"),
        _k("black", 1, 1.80, ("pink", "pink"), 1, 16, (36, 36, 40), immune=frozenset({EXPLOSIVE})),
        _k("white", 1, 2.00, ("pink", "pink"), 1, 16, (238, 240, 246)),
        _k("lead", 1, 1.00, ("black", "black"), 1, 17, (110, 116, 130), immune=frozenset({SHARP})),
        _k("zebra", 1, 1.80, ("black", "white"), 1, 17, (140, 140, 148)),
        _k("rainbow", 1, 2.20, ("zebra", "zebra"), 1, 19, (250, 150, 60)),
        _k("ceramic", 10, 2.50, ("rainbow", "rainbow"), 3, 21, (176, 116, 70)),
        _k("moab", 200, 1.00, ("ceramic",) * 4, 60, 42, (110, 120, 200),
           image=IMG + "moab.png", moab=True),
        # Bloons gives BFBs and ZOMGs 0.25x and 0.18x speed, but this track is
        # long enough that those values put a single ZOMG on screen for over
        # four minutes. Raised so a boss round stays tense rather than tedious.
        _k("bfb", 700, 0.45, ("moab",) * 4, 180, 58, (196, 62, 62), moab=True),
        _k("zomg", 4000, 0.35, ("bfb",) * 4, 700, 74, (110, 190, 70), moab=True),
    ]
}

#: Ladder order, used to decide what a regen balloon heals back into.
LADDER = [
    "red", "blue", "green", "yellow", "pink",
    "black", "white", "lead", "zebra", "rainbow", "ceramic",
]


def modified(name: str, camo: bool = False, regen: bool = False,
             fortified: bool = False) -> BalloonKind:
    """Return a kind with modifier flags applied.

    Modifiers propagate to children in real Bloons, and they do here too --
    see :func:`Balloon.spawn_children`.

    Args:
        name: Base kind name.
        camo: Make it targetable only by camo-detecting towers.
        regen: Make it heal back toward its base kind over time.
        fortified: Double its hit points.

    Returns:
        A new :class:`BalloonKind`; the base entry in :data:`KINDS` is
        untouched.
    """
    base = KINDS[name]
    if not (camo or regen or fortified):
        return base

    tag = base.name
    if fortified:
        tag = "fortified-" + tag
    if camo:
        tag = "camo-" + tag
    if regen:
        tag = "regen-" + tag

    return replace(
        base,
        name=tag,
        hp=base.hp * 2 if fortified else base.hp,
        camo=camo or base.camo,
        regen=regen or base.regen,
        fortified=fortified or base.fortified,
    )


def base_name(kind: BalloonKind) -> str:
    """Strip modifier prefixes to recover the underlying ladder name."""
    name = kind.name
    for prefix in ("regen-", "camo-", "fortified-"):
        while name.startswith(prefix):
            name = name[len(prefix):]
    return name


def rbe(name: str, _seen: int = 0) -> int:
    """Total number of balloons contained in a balloon, including itself.

    This is the standard "red bloon equivalent" measure. It is used for leak
    damage so that the cost of letting something through is proportional to
    what it actually contains, rather than a hand-tuned number per type.
    """
    if _seen > 12:  # depth guard; the real ladder is 6 deep
        return 1
    kind = KINDS[name]
    return kind.hp + sum(rbe(c, _seen + 1) for c in kind.children)


_RBE_CACHE = {name: rbe(name) for name in KINDS}


# --- sprites -------------------------------------------------------------

_SPRITES: dict[tuple[str, bool], pygame.Surface] = {}


def _draw_balloon(size: int, color: tuple[int, int, int], moab: bool) -> pygame.Surface:
    """Render a balloon shape procedurally.

    Used for the balloon types the original project had no art for (black,
    white, lead, zebra, rainbow, ceramic, BFB, ZOMG) so the whole ladder looks
    like it belongs to one set.
    """
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    if moab:
        body = pygame.Rect(1, size * 0.22, size - 2, size * 0.56)
        pygame.draw.ellipse(surf, color, body)
        pygame.draw.ellipse(surf, _shade(color, 0.55), body, max(2, size // 22))
        fin = [
            (size * 0.06, size * 0.5),
            (size * 0.0, size * 0.28),
            (size * 0.0, size * 0.72),
        ]
        pygame.draw.polygon(surf, _shade(color, 0.7), fin)
        pygame.draw.ellipse(
            surf, _shade(color, 1.35),
            pygame.Rect(size * 0.24, size * 0.31, size * 0.34, size * 0.13),
        )
    else:
        body = pygame.Rect(size * 0.10, 0, size * 0.80, size * 0.86)
        pygame.draw.ellipse(surf, color, body)
        pygame.draw.ellipse(surf, _shade(color, 0.6), body, max(1, size // 16))
        knot = [
            (size * 0.5, size * 0.80),
            (size * 0.40, size * 0.99),
            (size * 0.60, size * 0.99),
        ]
        pygame.draw.polygon(surf, _shade(color, 0.72), knot)
        pygame.draw.ellipse(
            surf, _shade(color, 1.5),
            pygame.Rect(size * 0.26, size * 0.14, size * 0.20, size * 0.28),
        )
    return surf


def _shade(color: tuple[int, int, int], factor: float) -> tuple[int, int, int]:
    """Multiply a colour's brightness, clamped to valid channel values."""
    return tuple(max(0, min(255, int(c * factor))) for c in color)


def art_candidates(name: str) -> list[str]:
    """Filenames checked for a balloon's artwork, in priority order.

    ``balloon_images/<name>.png`` is the slot to drop new art into;
    ``<name>_balloon.png`` is also accepted because that is how the original
    project named the six sprites it shipped with.
    """
    return [f"{IMG}{name}.png", f"{IMG}{name}_balloon.png"]


def sprite_for(kind: BalloonKind) -> pygame.Surface:
    """Return the cached sprite for a balloon kind.

    Uses real artwork when a file exists for this balloon (see
    :func:`art_candidates`) and falls back to a drawn shape otherwise, so the
    eight balloon types the project has no art for still render in a matching
    style.

    Camo balloons get a green wash so they read as different at a glance,
    which matters because most towers cannot target them.
    """
    key = (kind.name, kind.fortified)
    cached = _SPRITES.get(key)
    if cached is not None:
        return cached

    size = kind.radius * 2
    base = base_name(kind)
    surf = assets.optional(art_candidates(base) + [kind.image], (size, size))
    surf = surf.copy() if surf is not None else _draw_balloon(size, kind.color, kind.moab)

    if kind.camo:
        wash = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
        wash.fill((118, 196, 128, 255))
        surf.blit(wash, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    if kind.fortified:
        pygame.draw.ellipse(surf, (215, 200, 140), surf.get_rect(), max(2, size // 12))

    _SPRITES[key] = surf
    return surf


# --- live balloons -------------------------------------------------------

class Balloon:
    """A balloon travelling along the track.

    Attributes:
        kind: Immutable stats for this balloon.
        hp: Remaining hit points at the current layer.
        distance: Distance travelled along the path, in pixels.
        offset: Small perpendicular jitter so stacks do not overlap exactly.
        x, y: Cached world position, refreshed by :meth:`advance`.
        slow_timer: Seconds of remaining slow effect.
        slow_factor: Multiplier applied to speed while slowed.
        alive: Cleared once the balloon has popped or leaked.
    """

    __slots__ = (
        "kind", "hp", "distance", "offset", "x", "y", "slow_timer",
        "slow_factor", "alive", "regen_timer", "regen_target", "speed_scale",
    )

    #: Seconds between regen ticks.
    REGEN_PERIOD = 3.0

    def __init__(self, kind: BalloonKind, distance: float = 0.0,
                 offset: float = 0.0, hp_scale: float = 1.0,
                 speed_scale: float = 1.0):
        self.kind = kind
        # Difficulty scaling deliberately skips single-hit balloons. Rounding
        # 1 hp by a 1.5x multiplier would double every red balloon in one
        # step, so basic-balloon difficulty is expressed through counts and
        # speed instead (see ``count_scale`` in the difficulty table).
        self.hp = kind.hp if kind.hp <= 1 else max(2, int(round(kind.hp * hp_scale)))
        self.distance = distance
        self.offset = offset
        self.x = 0.0
        self.y = 0.0
        self.slow_timer = 0.0
        self.slow_factor = 1.0
        self.alive = True
        self.regen_timer = 0.0
        self.regen_target = base_name(kind)
        self.speed_scale = speed_scale

    @property
    def speed(self) -> float:
        """Current travel speed in pixels per second, including slows."""
        return self.kind.speed * self.slow_factor * self.speed_scale

    @property
    def leak_damage(self) -> int:
        """Lives lost if this balloon reaches the end of the track.

        Proportional to how many balloons it contains, but capped: an
        uncapped ceramic leak would cost 104 lives and end most runs on the
        spot, which reads as unfair rather than punishing.
        """
        contained = _RBE_CACHE.get(base_name(self.kind), 1)
        return min(LEAK_CAP_MOAB if self.kind.moab else LEAK_CAP, contained)

    def advance(self, dt: float, path) -> bool:
        """Move along the path and refresh the cached position.

        Args:
            dt: Elapsed simulation time in seconds.
            path: The :class:`~btd.path.Path` being followed.

        Returns:
            ``True`` if the balloon reached the end of the track this tick.
        """
        if self.slow_timer > 0.0:
            self.slow_timer -= dt
            if self.slow_timer <= 0.0:
                self.slow_factor = 1.0

        if self.kind.regen:
            self.regen_timer += dt
            if self.regen_timer >= self.REGEN_PERIOD:
                self.regen_timer = 0.0
                self._regenerate()

        self.distance += self.speed * dt
        if self.distance >= path.length:
            self.x, self.y = path.position_at(path.length)
            return True

        p_x, p_y = path.position_at(self.distance)
        self.x, self.y = p_x, p_y + self.offset
        return False

    def _regenerate(self) -> None:
        """Heal one step back up the ladder toward the original kind."""
        current = base_name(self.kind)
        if current == self.regen_target:
            return
        try:
            idx = LADDER.index(current)
            target_idx = LADDER.index(self.regen_target)
        except ValueError:
            return
        if idx >= target_idx:
            return

        healed = LADDER[idx + 1]
        self.kind = modified(
            healed,
            camo=self.kind.camo,
            regen=True,
            fortified=self.kind.fortified,
        )
        self.hp = self.kind.hp

    def slow(self, factor: float, duration: float) -> None:
        """Apply a slow, keeping whichever effect is stronger."""
        if factor < self.slow_factor or self.slow_timer <= 0.0:
            self.slow_factor = min(self.slow_factor, factor)
        self.slow_timer = max(self.slow_timer, duration)

    def immune_to(self, damage_type: str) -> bool:
        """Whether this balloon ignores a damage type outright."""
        return damage_type in self.kind.immune

    def spawn_children(self, hp_scale: float = 1.0,
                       speed_scale: float = 1.0) -> list["Balloon"]:
        """Create the balloons released when this one pops.

        Children inherit camo, regen, and fortified from their parent, spread
        out slightly so a burst is readable on screen, and are nudged forward
        by a few pixels each so they do not perfectly overlap.
        """
        out: list[Balloon] = []
        n = len(self.kind.children)
        for i, child_name in enumerate(self.kind.children):
            kind = modified(
                child_name,
                camo=self.kind.camo,
                regen=self.kind.regen,
                fortified=self.kind.fortified,
            )
            spread = 0.0 if n == 1 else (i / (n - 1) - 0.5)
            child = Balloon(
                kind,
                distance=max(0.0, self.distance - abs(spread) * 14.0),
                offset=self.offset + spread * 16.0,
                hp_scale=hp_scale,
                speed_scale=speed_scale,
            )
            child.x, child.y = self.x, self.y
            # Regen heals back toward whatever the balloon was when it first
            # entered the track, not merely toward its own current tier.
            child.regen_target = self.regen_target
            out.append(child)
        return out


@dataclass
class HitResult:
    """Outcome of applying damage to one or more balloons.

    Attributes:
        money: Total reward earned.
        pops: Number of layers destroyed, used for score and effects.
        spawned: New balloons created by cascading pops.
        absorbed: True if the target was immune and nothing happened.
    """

    money: int = 0
    pops: int = 0
    spawned: list[Balloon] = field(default_factory=list)
    absorbed: bool = False


def resolve_hit(balloon: Balloon, damage: int, damage_type: str,
                hp_scale: float = 1.0, speed_scale: float = 1.0) -> HitResult:
    """Apply damage to a balloon, cascading leftover damage into children.

    This is the single entry point for all damage in the game. Rewards are
    paid once per layer actually destroyed, which is what keeps the economy
    stable -- the old code paid the parent's full reward at every tier.

    Args:
        balloon: The balloon being hit. Mutated in place; ``alive`` is cleared
            if it pops.
        damage: Hit points to remove.
        damage_type: One of :data:`SHARP`, :data:`EXPLOSIVE`, :data:`ENERGY`,
            :data:`NORMAL`.
        hp_scale: Difficulty multiplier applied to any spawned children.
        speed_scale: Difficulty multiplier applied to any spawned children.

    Returns:
        A :class:`HitResult` describing money earned and balloons created.
    """
    result = HitResult()
    if not balloon.alive or damage <= 0:
        return result
    if balloon.immune_to(damage_type):
        result.absorbed = True
        return result

    # Excess damage punches straight through into a single child rather than
    # into every child. Splitting it across all children would compound: a
    # ceramic releases two rainbows, each releasing two zebras, so full
    # leftover damage per child grows exponentially with depth. Carrying it
    # into one child keeps total damage dealt bounded by ``damage`` while
    # still letting a big shot tear through a stack.
    target: Balloon | None = balloon
    remaining = damage

    while target is not None and remaining > 0:
        if not target.alive or target.immune_to(damage_type):
            break

        if remaining < target.hp:
            target.hp -= remaining
            break

        remaining -= target.hp
        target.hp = 0
        target.alive = False
        result.money += target.kind.reward
        result.pops += 1

        children = target.spawn_children(hp_scale, speed_scale)
        result.spawned.extend(children)
        target = children[0] if children else None

    # Children consumed by the cascade should not be handed back as live.
    result.spawned = [b for b in result.spawned if b.alive]
    return result


def in_radius(balloon: Balloon, x: float, y: float, radius: float) -> bool:
    """Whether a balloon's body overlaps a circle."""
    return math.hypot(balloon.x - x, balloon.y - y) <= radius + balloon.kind.radius
