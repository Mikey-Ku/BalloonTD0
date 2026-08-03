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
from .config import BALLOON_RADIUS, USE_BALLOON_ART

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

#: Shorthand for the shared non-MOAB radius. Every ordinary balloon uses it,
#: so the ladder reads as one set and a stack of mixed types lines up cleanly.
R = BALLOON_RADIUS

#: The balloon ladder, ordered weakest to strongest.
KINDS: dict[str, BalloonKind] = {
    k.name: k
    for k in [
        _k("red", 1, 1.00, (), 1, R, (226, 58, 54)),
        _k("blue", 1, 1.40, ("red",), 1, R, (62, 116, 226)),
        _k("green", 1, 1.80, ("blue",), 1, R, (66, 182, 92)),
        _k("yellow", 1, 3.20, ("green",), 1, R, (244, 210, 66)),
        _k("pink", 1, 3.50, ("yellow",), 1, R, (246, 138, 192)),
        _k("black", 1, 1.80, ("pink", "pink"), 1, R, (54, 52, 58),
           immune=frozenset({EXPLOSIVE})),
        _k("white", 1, 2.00, ("pink", "pink"), 1, R, (240, 242, 248)),
        _k("lead", 1, 1.00, ("black", "black"), 1, R, (126, 132, 146),
           immune=frozenset({SHARP})),
        _k("zebra", 1, 1.80, ("black", "white"), 1, R, (156, 156, 164)),
        _k("rainbow", 1, 2.20, ("zebra", "zebra"), 1, R, (250, 150, 60)),
        _k("ceramic", 10, 2.50, ("rainbow", "rainbow"), 3, R, (182, 124, 76)),
        # MOAB-class stay larger on purpose -- they are meant to read as a
        # different category, not another balloon.
        _k("moab", 200, 1.00, ("ceramic",) * 4, 60, 40, (118, 128, 208), moab=True),
        # Bloons gives BFBs and ZOMGs 0.25x and 0.18x speed, but this track is
        # long enough that those values put a single ZOMG on screen for over
        # four minutes. Raised so a boss round stays tense rather than tedious.
        _k("bfb", 700, 0.45, ("moab",) * 4, 180, 54, (202, 68, 66), moab=True),
        _k("zomg", 4000, 0.35, ("bfb",) * 4, 700, 70, (118, 196, 78), moab=True),
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


#: Ink colour for balloon outlines. A single dark brown across every balloon
#: is what makes the ladder read as one hand-drawn set at a uniform size.
OUTLINE = (52, 34, 22)

#: Extra markings per balloon, so uniformly sized balloons stay tellable
#: apart. Without these, lead / zebra / ceramic are just three grey circles.
PATTERNS = {
    "zebra": "stripes",
    "rainbow": "bands",
    "ceramic": "plates",
    "lead": "sheen",
    "white": "sheen",
}


def _draw_balloon(size: int, color: tuple[int, int, int], moab: bool,
                  pattern: str | None = None,
                  fortified: bool = False) -> pygame.Surface:
    """Render a balloon procedurally in the game's cartoon style.

    Every balloon shares one silhouette, one outline weight, and one size, so
    the ladder looks like a single set. Type is communicated by fill colour
    plus an optional pattern rather than by shape or scale.

    Args:
        size: Sprite width and height in pixels.
        color: Body fill colour.
        moab: Draw the elongated blimp shape instead of a balloon.
        pattern: Optional key from :data:`PATTERNS`.

    Returns:
        A surface with a transparent background.
    """
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    # Capped so a ZOMG is not drawn with a 10px border while a red gets 3.
    # A roughly constant line weight is what holds the set together visually.
    line = max(2, min(4, round(size / 13)))
    gold = (236, 198, 92)

    if moab:
        body = pygame.Rect(line, size * 0.24, size - line * 2, size * 0.52)
        pygame.draw.ellipse(surf, color, body)
        # Nose highlight gives the blimp a direction.
        pygame.draw.ellipse(
            surf, _shade(color, 1.22),
            pygame.Rect(body.x + body.w * 0.10, body.y + body.h * 0.16,
                        body.w * 0.34, body.h * 0.30),
        )
        tail = [
            (line, size * 0.50),
            (line * 0.2, size * 0.30),
            (line * 0.2, size * 0.70),
        ]
        pygame.draw.polygon(surf, _shade(color, 0.72), tail)
        pygame.draw.polygon(surf, OUTLINE, tail, max(1, line - 1))
        pygame.draw.ellipse(surf, OUTLINE, body, line)
        if fortified:
            pygame.draw.ellipse(surf, gold, body.inflate(-line * 3, -line * 3), line)
        return surf

    body = pygame.Rect(size * 0.09, size * 0.02, size * 0.82, size * 0.84)
    pygame.draw.ellipse(surf, color, body)

    if pattern:
        _apply_pattern(surf, body, color, pattern, line)

    # Knot, drawn before the outline so the outline caps it cleanly.
    knot = [
        (size * 0.50, size * 0.78),
        (size * 0.38, size * 0.99),
        (size * 0.62, size * 0.99),
    ]
    pygame.draw.polygon(surf, _shade(color, 0.74), knot)
    pygame.draw.polygon(surf, OUTLINE, knot, max(1, line - 1))

    # Specular highlight, then the heavy outline on top.
    pygame.draw.ellipse(
        surf, _lighten(color, 0.55),
        pygame.Rect(body.x + body.w * 0.18, body.y + body.h * 0.14,
                    body.w * 0.26, body.h * 0.32),
    )
    pygame.draw.ellipse(surf, OUTLINE, body, line)
    if fortified:
        # Gold band inside the outline, following the body rather than a
        # circle bolted around the whole sprite.
        pygame.draw.ellipse(surf, gold, body.inflate(-line * 2, -line * 2), line)
    return surf


def _apply_pattern(surf: pygame.Surface, body: pygame.Rect,
                   color: tuple[int, int, int], pattern: str, line: int) -> None:
    """Draw a balloon's distinguishing markings, clipped to its body."""
    previous = surf.get_clip()
    clip = pygame.Surface(surf.get_size(), pygame.SRCALPHA)

    if pattern == "stripes":
        step = max(3, body.w // 5)
        for i, x in enumerate(range(body.x, body.right, step)):
            if i % 2:
                pygame.draw.rect(clip, (34, 32, 36), (x, body.y, step, body.h))
    elif pattern == "bands":
        colours = [(232, 62, 58), (246, 158, 46), (246, 216, 66),
                   (86, 190, 96), (72, 132, 226), (150, 92, 208)]
        step = body.h / len(colours)
        for i, band in enumerate(colours):
            pygame.draw.rect(clip, band,
                             (body.x, body.y + i * step, body.w, step + 1))
    elif pattern == "plates":
        # Interlocking plates, drawn dark enough to read at 36 px.
        dark = _shade(color, 0.52)
        step = body.h / 3.0
        for i in range(3):
            top = body.y + i * step
            pygame.draw.arc(clip, dark,
                            pygame.Rect(body.x - body.w * 0.1, top,
                                        body.w * 1.2, step * 1.8),
                            3.35, 6.07, max(2, line))
        pygame.draw.line(clip, dark, (body.centerx, body.y),
                         (body.centerx, body.bottom), max(2, line - 1))
    elif pattern == "sheen":
        pygame.draw.ellipse(
            clip, _shade(color, 0.82),
            pygame.Rect(body.x, body.centery, body.w, body.h * 0.5),
        )

    # Mask the pattern to the balloon body so nothing spills past the edge.
    mask = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
    pygame.draw.ellipse(mask, (255, 255, 255, 255), body)
    clip.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    surf.blit(clip, (0, 0))
    surf.set_clip(previous)


def _shade(color: tuple[int, int, int], factor: float) -> tuple[int, int, int]:
    """Multiply a colour's brightness, clamped to valid channel values."""
    return tuple(max(0, min(255, int(c * factor))) for c in color)


def _lighten(color: tuple[int, int, int], amount: float) -> tuple[int, int, int]:
    """Blend a colour toward white by ``amount`` in ``[0, 1]``."""
    return tuple(int(c + (255 - c) * amount) for c in color)


def art_candidates(name: str) -> list[str]:
    """Filenames checked for a balloon's artwork, in priority order.

    ``balloon_images/<name>.png`` is the slot to drop new art into. The
    original project's ``<name>_balloon.png`` files are deliberately not
    checked: they are inconsistent in size and style with each other, which is
    what motivated drawing the whole ladder procedurally instead.
    """
    return [f"{IMG}{name}.png"]


def sprite_for(kind: BalloonKind) -> pygame.Surface:
    """Return the cached sprite for a balloon kind.

    Draws every balloon procedurally by default so the whole ladder shares one
    silhouette, one outline weight, and one size. Set
    :data:`~btd.config.USE_BALLOON_ART` to opt back into file artwork once a
    complete, consistently sized set exists.

    Camo balloons get a green wash so they read as different at a glance,
    which matters because most towers cannot target them.
    """
    key = (kind.name, kind.fortified)
    cached = _SPRITES.get(key)
    if cached is not None:
        return cached

    size = kind.radius * 2
    base = base_name(kind)
    surf = None
    if USE_BALLOON_ART:
        art = assets.optional(art_candidates(base), (size, size))
        surf = art.copy() if art is not None else None
    if surf is None:
        surf = _draw_balloon(size, kind.color, kind.moab, PATTERNS.get(base),
                             fortified=kind.fortified)
        fortified_drawn = True
    else:
        fortified_drawn = False

    if kind.camo:
        wash = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
        wash.fill((132, 202, 140, 255))
        surf.blit(wash, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    if kind.fortified and not fortified_drawn:
        # Only needed for file artwork; the procedural path draws the gold
        # band against the real body shape instead of the sprite bounds.
        pygame.draw.ellipse(surf, (236, 198, 92), surf.get_rect(),
                            max(2, size // 12))

    _SPRITES[key] = surf
    return surf


# --- live balloons -------------------------------------------------------

class Balloon:
    """A balloon travelling along the track.

    Attributes:
        kind: Immutable stats for this balloon.
        hp: Remaining hit points at the current layer.
        distance: Distance travelled along the path, in pixels.
        x, y: Cached world position, refreshed by :meth:`advance`.
        slow_timer: Seconds of remaining slow effect.
        slow_factor: Multiplier applied to speed while slowed.
        alive: Cleared once the balloon has popped or leaked.
    """

    __slots__ = (
        "kind", "hp", "distance", "x", "y", "slow_timer",
        "slow_factor", "alive", "regen_timer", "regen_target", "speed_scale",
    )

    #: Seconds between regen ticks.
    REGEN_PERIOD = 3.0

    def __init__(self, kind: BalloonKind, distance: float = 0.0,
                 hp_scale: float = 1.0, speed_scale: float = 1.0):
        self.kind = kind
        # Difficulty scaling deliberately skips single-hit balloons. Rounding
        # 1 hp by a 1.5x multiplier would double every red balloon in one
        # step, so basic-balloon difficulty is expressed through counts and
        # speed instead (see ``count_scale`` in the difficulty table).
        self.hp = kind.hp if kind.hp <= 1 else max(2, int(round(kind.hp * hp_scale)))
        self.distance = distance
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

        self.x, self.y = path.position_at(self.distance)
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

    #: Gap between children released by one pop, in pixels along the track.
    CHILD_GAP = BALLOON_RADIUS * 1.9

    def spawn_children(self, hp_scale: float = 1.0,
                       speed_scale: float = 1.0) -> list["Balloon"]:
        """Create the balloons released when this one pops.

        Children are staggered *along the track* rather than pushed sideways
        off it, so everything stays in single file on one path line. Spreading
        them perpendicular to the path made a popped ceramic look like four
        parallel lanes of balloons.

        Children inherit camo, regen, and fortified from their parent.
        """
        out: list[Balloon] = []
        for i, child_name in enumerate(self.kind.children):
            kind = modified(
                child_name,
                camo=self.kind.camo,
                regen=self.kind.regen,
                fortified=self.kind.fortified,
            )
            child = Balloon(
                kind,
                distance=max(0.0, self.distance - i * self.CHILD_GAP),
                hp_scale=hp_scale,
                speed_scale=speed_scale,
            )
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
