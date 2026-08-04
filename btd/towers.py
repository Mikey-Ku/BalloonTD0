"""
Towers, upgrade paths, and targeting.

The original towers were four near-identical objects whose only upgrade was
``damage += 1; range *= 1.1; attack_speed *= 1.1``, applied forever for an
ever-rising price. There was nothing to choose between them beyond cost.

Here each tower has a distinct firing mode and damage type, and two upgrade
paths of three tiers that pull it in different directions. As in Bloons, only
one path may be taken to its final tier, so a tower is a real decision rather
than a savings goal.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from .balloons import ENERGY, EXPLOSIVE, NORMAL, SHARP, Balloon
from .config import SELL_REFUND
from .projectiles import Beam, Projectile

# Firing modes.
SINGLE = "single"      # one travelling shot at the target
RADIAL = "radial"      # a ring of shots, ignores target selection
HITSCAN = "hitscan"    # instant damage plus a cosmetic beam
PULSE = "pulse"        # area effect centred on the tower
FARM = "farm"          # generates income, never fires

# Targeting priorities.
FIRST = "First"
LAST = "Last"
CLOSE = "Close"
STRONG = "Strong"
TARGETING_MODES = (FIRST, LAST, CLOSE, STRONG)


@dataclass(frozen=True)
class Upgrade:
    """One purchasable step on a tower's upgrade path.

    Attributes:
        name: Display name.
        cost: Price in game money, before difficulty scaling.
        desc: One-line explanation shown in the sidebar.
        effects: Stat modifiers, applied by :meth:`Tower.recompute`.
    """

    name: str
    cost: int
    desc: str
    effects: dict = field(default_factory=dict)


@dataclass(frozen=True)
class TowerKind:
    """Immutable definition of a tower type.

    Attributes:
        key: Unique identifier used in save files and the UI.
        label: Display name.
        cost: Base purchase price.
        blurb: Short description shown before purchase.
        mode: One of :data:`SINGLE`, :data:`RADIAL`, :data:`HITSCAN`,
            :data:`PULSE`, :data:`FARM`.
        damage_type: Damage type dealt, from :mod:`btd.balloons`.
        range: Attack radius in pixels.
        damage: Damage per hit.
        pierce: Balloons a single shot can hit.
        rate: Shots per second.
        shots: Projectiles emitted per shot (used by :data:`RADIAL`).
        projectile_speed: Shot speed in pixels per second.
        splash: Explosion radius, for explosive towers.
        camo: Whether it can target camo balloons without upgrades.
        slow_factor: Speed multiplier applied by :data:`PULSE` towers.
        slow_time: Duration in seconds of the slow applied.
        income: Money generated at the end of each round.
        colour: Accent colour used in the UI and for projectiles.
        paths: Two upgrade paths of three tiers each.
    """

    key: str
    label: str
    cost: int
    blurb: str
    mode: str
    damage_type: str = SHARP
    range: float = 110.0
    damage: int = 1
    pierce: int = 1
    rate: float = 1.0
    shots: int = 1
    projectile_speed: float = 520.0
    splash: float = 0.0
    camo: bool = False
    slow_factor: float = 1.0
    slow_time: float = 0.0
    income: int = 0
    colour: tuple[int, int, int] = (200, 200, 210)
    paths: tuple[tuple[Upgrade, ...], tuple[Upgrade, ...]] = ((), ())


KINDS: dict[str, TowerKind] = {}


def _register(kind: TowerKind) -> TowerKind:
    """Add a tower definition to the registry."""
    KINDS[kind.key] = kind
    return kind


_register(TowerKind(
    key="dart",
    label="Dart Monkey",
    cost=200,
    blurb="Cheap, reliable single-target damage. The backbone of any defence.",
    mode=SINGLE,
    damage_type=SHARP,
    range=115, damage=1, pierce=2, rate=1.1,
    colour=(150, 110, 74),
    paths=(
        (
            Upgrade("Sharp Shots", 140, "+1 pierce.", {"pierce": 1}),
            Upgrade("Razor Darts", 260, "+1 damage.", {"damage": 1}),
            Upgrade("Triple Shot", 620, "Fires three darts at once.", {"shots": 2}),
        ),
        (
            Upgrade("Long Range", 120, "+30% range.", {"range_mul": 1.30}),
            Upgrade("Quick Hands", 250, "+45% attack speed.", {"rate_mul": 1.45}),
            Upgrade("Night Crossbow", 700,
                    "Sees camo. +2 damage, +2 pierce.",
                    {"camo": True, "damage": 2, "pierce": 2}),
        ),
    ),
))

_register(TowerKind(
    key="sniper",
    label="Sniper Monkey",
    cost=380,
    blurb="Hits anywhere on the map for heavy single-target damage. Slow.",
    mode=HITSCAN,
    damage_type=SHARP,
    range=9999, damage=4, pierce=1, rate=0.55,
    colour=(96, 116, 96),
    paths=(
        (
            Upgrade("Full Metal Jacket", 320, "+4 damage. Pops lead.",
                    {"damage": 4, "damage_type": NORMAL}),
            Upgrade("Large Calibre", 800, "+10 damage.", {"damage": 10}),
            Upgrade("Cripple MOAB", 2200, "+40 damage to MOAB-class.",
                    {"moab_bonus": 40}),
        ),
        (
            Upgrade("Night Vision", 300, "Sees camo balloons.", {"camo": True}),
            Upgrade("Fast Firing", 560, "+80% attack speed.", {"rate_mul": 1.80}),
            Upgrade("Supply Drop", 2400, "Earns $250 at the end of each round.",
                    {"income": 250}),
        ),
    ),
))

_register(TowerKind(
    key="tack",
    label="Tack Shooter",
    cost=300,
    blurb="Sprays tacks in every direction. Devastating on a tight corner.",
    mode=RADIAL,
    damage_type=SHARP,
    range=95, damage=1, pierce=1, rate=1.15, shots=8,
    projectile_speed=340,
    colour=(178, 150, 96),
    paths=(
        (
            Upgrade("More Tacks", 180, "Fires 10 tacks instead of 8.", {"shots": 2}),
            Upgrade("Even More Tacks", 340, "Fires 12 tacks.", {"shots": 2}),
            Upgrade("Blade Shooter", 900, "+1 damage, +2 pierce.",
                    {"damage": 1, "pierce": 2}),
        ),
        (
            Upgrade("Wider Spray", 220, "+35% range.", {"range_mul": 1.35}),
            Upgrade("Faster Shooting", 400, "+55% attack speed.", {"rate_mul": 1.55}),
            Upgrade("Ring of Fire", 1900,
                    "Explosive tacks with splash. Sees camo.",
                    {"damage_type": EXPLOSIVE, "splash": 26, "camo": True,
                     "damage": 1}),
        ),
    ),
))

_register(TowerKind(
    key="bomb",
    label="Bomb Shooter",
    cost=560,
    blurb="Lobs explosives that damage everything nearby. Cannot pop black.",
    mode=SINGLE,
    damage_type=EXPLOSIVE,
    range=140, damage=2, pierce=1, rate=0.85,
    projectile_speed=360, splash=34,
    colour=(72, 76, 92),
    paths=(
        (
            Upgrade("Bigger Bombs", 380, "+45% blast radius, +1 damage.",
                    {"splash": 16, "damage": 1}),
            Upgrade("Heavy Shells", 700, "+3 damage.", {"damage": 3}),
            Upgrade("Bloon Crush", 2600, "+30 damage to MOAB-class.",
                    {"moab_bonus": 30}),
        ),
        (
            Upgrade("Faster Reload", 340, "+50% attack speed.", {"rate_mul": 1.50}),
            Upgrade("Extra Range", 420, "+30% range.", {"range_mul": 1.30}),
            Upgrade("Cluster Bombs", 1800,
                    "Sees camo. +30 blast radius, +2 damage.",
                    {"camo": True, "splash": 30, "damage": 2}),
        ),
    ),
))

_register(TowerKind(
    key="ice",
    label="Ice Monkey",
    cost=420,
    blurb="Chills every balloon in range, slowing them. Light damage.",
    mode=PULSE,
    damage_type=NORMAL,
    range=105, damage=1, rate=0.8,
    slow_factor=0.55, slow_time=2.0,
    colour=(126, 196, 226),
    paths=(
        (
            Upgrade("Deep Freeze", 300, "Slows to 40% speed for 3s.",
                    {"slow_factor": 0.40, "slow_time": 3.0}),
            Upgrade("Arctic Blast", 620, "+2 damage.", {"damage": 2}),
            Upgrade("Absolute Zero", 2100, "Slows to 22% speed for 4s. +3 damage.",
                    {"slow_factor": 0.22, "slow_time": 4.0, "damage": 3}),
        ),
        (
            Upgrade("Cold Snap", 260, "+35% range.", {"range_mul": 1.35}),
            Upgrade("Arctic Wind", 520, "Sees camo. +45% attack speed.",
                    {"camo": True, "rate_mul": 1.45}),
            Upgrade("Viral Frost", 1700, "+55% range, +70% attack speed.",
                    {"range_mul": 1.55, "rate_mul": 1.70}),
        ),
    ),
))

_register(TowerKind(
    key="super",
    label="Super Monkey",
    cost=2800,
    blurb="Overwhelming rate of fire at long range. Expensive.",
    mode=SINGLE,
    damage_type=ENERGY,
    range=190, damage=1, pierce=1, rate=9.0,
    projectile_speed=760,
    colour=(198, 96, 190),
    paths=(
        (
            Upgrade("Laser Blasts", 1900, "+1 damage, +1 pierce.",
                    {"damage": 1, "pierce": 1}),
            Upgrade("Plasma Blasts", 3800, "+2 damage, +55% attack speed.",
                    {"damage": 2, "rate_mul": 1.55}),
            Upgrade("Sun Avatar", 9000, "+6 damage, +4 pierce. Sees camo.",
                    {"damage": 6, "pierce": 4, "camo": True}),
        ),
        (
            Upgrade("Epic Range", 1400, "+35% range. Sees camo.",
                    {"range_mul": 1.35, "camo": True}),
            Upgrade("Robo Monkey", 3200, "+70% attack speed.", {"rate_mul": 1.70}),
            Upgrade("Tech Terror", 7500, "+3 damage, +2 pierce, +40% range.",
                    {"damage": 3, "pierce": 2, "range_mul": 1.40}),
        ),
    ),
))

_register(TowerKind(
    key="farm",
    label="Banana Farm",
    cost=1100,
    blurb="Does not attack. Produces money at the end of every round.",
    mode=FARM,
    range=0, damage=0, rate=0,
    income=180,
    colour=(226, 196, 78),
    paths=(
        (
            Upgrade("Better Yield", 600, "+$120 per round.", {"income": 120}),
            Upgrade("Greater Harvest", 1300, "+$240 per round.", {"income": 240}),
            Upgrade("Plantation", 3400, "+$620 per round.", {"income": 620}),
        ),
        (
            Upgrade("Long Life Bananas", 500, "+$90 per round.", {"income": 90}),
            Upgrade("Valuable Bananas", 1500, "+$300 per round.", {"income": 300}),
            Upgrade("Monkey Bank", 3800, "+$700 per round.", {"income": 700}),
        ),
    ),
))


#: Order the towers appear in the sidebar.
TOWER_ORDER = ("dart", "sniper", "tack", "bomb", "ice", "super", "farm")


class Tower:
    """A placed tower.

    Base stats come from the :class:`TowerKind`; purchased upgrades are
    re-applied from scratch by :meth:`recompute` whenever anything changes, so
    stats can never drift out of sync with what the player has bought.

    Attributes:
        kind: The tower's immutable definition.
        x, y: Position on the map.
        tiers: Purchased tier count for each of the two paths.
        total_spent: Everything paid for this tower, used for the sell price.
        targeting: Current targeting priority.
        angle: Facing in degrees, for sprite rotation.
        cooldown: Seconds until it may fire again.
    """

    #: A tower may only take one path to its final tier.
    MAX_CROSSPATH = 2

    def __init__(self, kind: TowerKind, x: float, y: float, cost_scale: float = 1.0):
        self.kind = kind
        self.x = float(x)
        self.y = float(y)
        self.tiers = [0, 0]
        self.cost_scale = cost_scale
        self.total_spent = int(round(kind.cost * cost_scale))
        self.targeting = FIRST
        self.angle = 90.0
        self.cooldown = 0.0
        self.pops = 0
        self.cash_earned = 0
        #: Recoil animation, 1.0 the instant a shot leaves and decaying to 0.
        self.fire_anim = 0.0

        # Live stats, filled in by recompute().
        self.range = 0.0
        self.damage = 0
        self.pierce = 0
        self.rate = 0.0
        self.shots = 0
        self.splash = 0.0
        self.damage_type = SHARP
        self.camo = False
        self.moab_bonus = 0
        self.slow_factor = 1.0
        self.slow_time = 0.0
        self.income = 0
        self.recompute()

    # -- upgrades ---------------------------------------------------------

    def recompute(self) -> None:
        """Rebuild live stats from the base kind plus every purchased upgrade."""
        kind = self.kind
        self.range = kind.range
        self.damage = kind.damage
        self.pierce = kind.pierce
        self.rate = kind.rate
        self.shots = kind.shots
        self.splash = kind.splash
        self.damage_type = kind.damage_type
        self.camo = kind.camo
        self.moab_bonus = 0
        self.slow_factor = kind.slow_factor
        self.slow_time = kind.slow_time
        self.income = kind.income

        range_mul = 1.0
        rate_mul = 1.0

        for path_index, tier in enumerate(self.tiers):
            for step in range(tier):
                effects = kind.paths[path_index][step].effects
                self.damage += effects.get("damage", 0)
                self.pierce += effects.get("pierce", 0)
                self.shots += effects.get("shots", 0)
                self.splash += effects.get("splash", 0)
                self.moab_bonus += effects.get("moab_bonus", 0)
                self.income += effects.get("income", 0)
                range_mul *= effects.get("range_mul", 1.0)
                rate_mul *= effects.get("rate_mul", 1.0)
                if effects.get("camo"):
                    self.camo = True
                if "damage_type" in effects:
                    self.damage_type = effects["damage_type"]
                if "slow_factor" in effects:
                    self.slow_factor = effects["slow_factor"]
                if "slow_time" in effects:
                    self.slow_time = effects["slow_time"]

        self.range *= range_mul
        self.rate *= rate_mul

    def upgrade_cost(self, path: int) -> int | None:
        """Price of the next upgrade on ``path``, or ``None`` if unavailable."""
        tier = self.tiers[path]
        if tier >= len(self.kind.paths[path]):
            return None
        if not self.can_upgrade(path):
            return None
        return int(round(self.kind.paths[path][tier].cost * self.cost_scale))

    def next_upgrade(self, path: int) -> Upgrade | None:
        """The next :class:`Upgrade` on ``path``, or ``None`` if maxed."""
        tier = self.tiers[path]
        if tier >= len(self.kind.paths[path]):
            return None
        return self.kind.paths[path][tier]

    def can_upgrade(self, path: int) -> bool:
        """Whether ``path`` may be advanced under the cross-path rule.

        A tower may push exactly one path past tier 2; the other is capped
        there. This is what forces a genuine choice between two builds
        instead of eventually buying everything.
        """
        tier = self.tiers[path]
        if tier >= len(self.kind.paths[path]):
            return False
        other = self.tiers[1 - path]
        # Advancing past the cross-path cap requires the other path to still
        # be at or below it.
        return not (tier + 1 > self.MAX_CROSSPATH and other > self.MAX_CROSSPATH)

    def apply_upgrade(self, path: int) -> None:
        """Purchase the next upgrade on ``path``. Caller must check funds."""
        cost = self.upgrade_cost(path)
        if cost is None:
            return
        self.tiers[path] += 1
        self.total_spent += cost
        self.recompute()

    @property
    def sell_value(self) -> int:
        """Money refunded when this tower is sold."""
        return int(self.total_spent * SELL_REFUND)

    @property
    def tier_label(self) -> str:
        """Compact representation of the upgrade state, e.g. ``2-1``."""
        return f"{self.tiers[0]}-{self.tiers[1]}"

    def cycle_targeting(self, backwards: bool = False) -> None:
        """Step to the next targeting priority."""
        idx = TARGETING_MODES.index(self.targeting)
        idx = (idx - 1 if backwards else idx + 1) % len(TARGETING_MODES)
        self.targeting = TARGETING_MODES[idx]

    # -- animation --------------------------------------------------------

    @property
    def recoil_time(self) -> float:
        """Seconds the firing animation takes to settle.

        Derived from the tower's own fire rate rather than being a fixed
        constant, so the animation is always finished before the next shot.
        A Super Monkey at 9 shots/second flickers; a Sniper at 0.55 gets a
        slow, deliberate kick. Clamped so very slow towers do not animate for
        a whole second and very fast ones still show something.
        """
        if self.rate <= 0:
            return 0.0
        return max(0.05, min(0.22, (1.0 / self.rate) * 0.55))

    @property
    def recoil(self) -> float:
        """Current recoil offset in pixels, opposite the facing direction."""
        if self.fire_anim <= 0:
            return 0.0
        # Snappy out, eased back: the shot should feel like a kick, not a sway.
        return 5.0 * (self.fire_anim ** 0.6)

    def _advance_anim(self, dt: float) -> None:
        """Decay the firing animation."""
        if self.fire_anim > 0 and self.recoil_time > 0:
            self.fire_anim = max(0.0, self.fire_anim - dt / self.recoil_time)

    # -- combat -----------------------------------------------------------

    def can_see(self, balloon: Balloon) -> bool:
        """Whether this tower is allowed to target a balloon."""
        return self.camo or not balloon.kind.camo

    def in_range(self, balloon: Balloon) -> bool:
        """Whether a balloon is inside the attack radius."""
        return math.hypot(balloon.x - self.x, balloon.y - self.y) <= self.range

    def find_target(self, balloons: list[Balloon]) -> Balloon | None:
        """Pick a balloon according to the current targeting priority."""
        candidates = [
            b for b in balloons
            if b.alive and self.can_see(b) and self.in_range(b)
        ]
        if not candidates:
            return None

        if self.targeting == FIRST:
            return max(candidates, key=lambda b: b.distance)
        if self.targeting == LAST:
            return min(candidates, key=lambda b: b.distance)
        if self.targeting == CLOSE:
            return min(candidates, key=lambda b: math.hypot(b.x - self.x, b.y - self.y))
        return max(candidates, key=lambda b: (b.kind.moab, b.hp, b.distance))

    def update(self, dt: float, balloons: list[Balloon]) -> tuple[list, list]:
        """Advance cooldown and fire if able.

        Args:
            dt: Simulation step in seconds.
            balloons: Live balloons, used for targeting.

        Returns:
            ``(projectiles, effects)`` -- new :class:`~btd.projectiles.Projectile`
            objects and cosmetic effects such as beams and pulses. Damage from
            hitscan and pulse towers is applied by the caller via the returned
            effect objects, so this method never mutates balloons directly.
        """
        if self.kind.mode == FARM or self.rate <= 0:
            return [], []

        self._advance_anim(dt)
        self.cooldown -= dt
        target = self.find_target(balloons)
        if target is not None:
            self.angle = math.degrees(
                math.atan2(-(target.y - self.y), target.x - self.x)
            )

        if self.cooldown > 0:
            return [], []

        if self.kind.mode == PULSE:
            if not any(self.can_see(b) and self.in_range(b)
                       for b in balloons if b.alive):
                return [], []
            self.cooldown = 1.0 / self.rate
            self.fire_anim = 1.0
            return [], [PulseEffect(self)]

        if target is None:
            return [], []

        self.cooldown = 1.0 / self.rate
        self.fire_anim = 1.0

        if self.kind.mode == HITSCAN:
            return [], [
                Beam(self.x, self.y, target.x, target.y,
                     colour=(255, 244, 206), width=2),
                DirectHit(self, target),
            ]

        if self.kind.mode == RADIAL:
            return self._radial_shots(), []

        return self._aimed_shots(target), []

    def _spawn(self, v_x: float, v_y: float, life: float) -> Projectile:
        """Construct one projectile with this tower's current stats."""
        return Projectile(
            self.x, self.y, v_x, v_y,
            damage=self.damage,
            damage_type=self.damage_type,
            pierce=self.pierce,
            life=life,
            radius=5 if self.splash <= 0 else 6,
            splash=self.splash,
            moab_bonus=self.moab_bonus,
            colour=self.kind.colour,
            trail=self.kind.mode == SINGLE,
        )

    def _aimed_shots(self, target: Balloon) -> list[Projectile]:
        """Fire ``shots`` projectiles at a target, fanned if there is more than one."""
        speed = self.kind.projectile_speed
        life = max(0.25, self.range / speed + 0.35)
        base = math.atan2(target.y - self.y, target.x - self.x)

        out = []
        spread = math.radians(9)
        for i in range(max(1, self.shots)):
            offset = 0.0 if self.shots == 1 else (i - (self.shots - 1) / 2) * spread
            ang = base + offset
            out.append(self._spawn(math.cos(ang) * speed, math.sin(ang) * speed, life))
        return out

    def _radial_shots(self) -> list[Projectile]:
        """Fire a ring of projectiles outward from the tower."""
        speed = self.kind.projectile_speed
        life = max(0.15, self.range / speed)
        count = max(1, self.shots)
        out = []
        for i in range(count):
            ang = (2 * math.pi) * i / count
            out.append(self._spawn(math.cos(ang) * speed, math.sin(ang) * speed, life))
        return out


class DirectHit:
    """Instant damage applied to one balloon by a hitscan tower."""

    __slots__ = ("tower", "target")

    def __init__(self, tower: Tower, target: Balloon):
        self.tower = tower
        self.target = target


class PulseEffect:
    """An area effect centred on a tower: damage plus a slow."""

    __slots__ = ("tower",)

    def __init__(self, tower: Tower):
        self.tower = tower
