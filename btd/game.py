"""
The simulation: one run of the game on one map.

Everything that changes as you play lives here -- balloons, towers, money,
lives, and the round schedule. Rendering of the map layer lives here too; the
sidebar and menus are in :mod:`btd.ui`.

Two structural differences from the original:

* The simulation runs on a **fixed timestep**. ``advance`` accumulates real
  elapsed time and runs whole ticks of :data:`~btd.config.TICK` seconds, so a
  144 Hz machine and a 60 Hz machine produce identical play. The original tied
  movement to frames and implemented 2x speed by raising the frame-rate cap,
  which meant the game already ran fast on a high-refresh display.
* Targeting and collision go through a **uniform grid** rebuilt once per tick.
  A late round can have a few thousand balloons on screen, and checking every
  tower against every balloon is what would otherwise make those rounds crawl.
"""

from __future__ import annotations

import math

import pygame

from . import maps, sprites
from .balloons import Balloon, resolve_hit, sprite_for
from .config import (
    DIFFICULTIES, MAP_H, MAP_W, MAX_STEPS_PER_FRAME, ROUND_BONUS_BASE,
    ROUND_BONUS_PER_ROUND, TICK,
)
from .effects import Effects
from .projectiles import collide
from .towers import FARM, DirectHit, PulseEffect, Tower
from .towers import KINDS as TOWER_KINDS
from .waves import build_schedule, round_bonus, wave_for

# Run outcomes.
RUNNING = "running"
WON = "won"
LOST = "lost"


class BalloonIndex:
    """A uniform grid over live balloons, rebuilt every tick.

    Keeps targeting and projectile collision proportional to the number of
    balloons actually near a query point rather than the total on the map.
    """

    CELL = 64

    def __init__(self):
        self.cells: dict[tuple[int, int], list[Balloon]] = {}
        self.all: list[Balloon] = []

    def build(self, balloons: list[Balloon]) -> None:
        """Bucket every live balloon by grid cell."""
        self.cells = {}
        self.all = balloons
        cell = self.CELL
        for balloon in balloons:
            if not balloon.alive:
                continue
            key = (int(balloon.x) // cell, int(balloon.y) // cell)
            bucket = self.cells.get(key)
            if bucket is None:
                self.cells[key] = [balloon]
            else:
                bucket.append(balloon)

    def query(self, x: float, y: float, radius: float) -> list[Balloon]:
        """Return balloons whose cell lies within ``radius`` of a point.

        Falls back to the full list when the radius covers most of the map,
        which is the case for the sniper's map-wide range.
        """
        if radius >= MAP_W:
            return [b for b in self.all if b.alive]

        cell = self.CELL
        reach = int(radius // cell) + 1
        c_x, c_y = int(x) // cell, int(y) // cell
        out: list[Balloon] = []
        for g_y in range(c_y - reach, c_y + reach + 1):
            for g_x in range(c_x - reach, c_x + reach + 1):
                bucket = self.cells.get((g_x, g_y))
                if bucket:
                    out.extend(bucket)
        return out


class Run:
    """A single playthrough.

    Attributes:
        map_def: The map being played.
        path: Track geometry.
        background: Pre-rendered map surface.
        difficulty: Difficulty key, one of :data:`~btd.config.DIFFICULTIES`.
        money: Current cash.
        lives: Remaining lives.
        round_number: Round currently being played or about to start.
        round_active: Whether balloons are still being released or alive.
        towers: Placed towers.
        balloons: Live balloons.
        projectiles: Shots in flight.
        effects: Transient visuals.
        outcome: One of :data:`RUNNING`, :data:`WON`, :data:`LOST`.
        speed: Simulation speed multiplier.
        paused: Whether the simulation is frozen.
    """

    def __init__(self, map_key: str, difficulty: str):
        self.map_def = maps.MAPS[map_key]
        self.path = maps.build_path(self.map_def)
        self.background = maps.build_background(self.map_def, self.path)
        self.clearance = maps.track_clearance(self.map_def)

        self.difficulty = difficulty
        rules = DIFFICULTIES[difficulty]
        self.hp_scale = rules["hp_scale"]
        self.speed_scale = rules["speed_scale"]
        self.cost_scale = rules["cost_scale"]
        self.count_scale = rules["count_scale"]
        self.max_rounds = rules["rounds"]

        self.money = rules["money"]
        self.lives = rules["lives"]
        self.max_lives = rules["lives"]

        self.round_number = 1
        self.round_active = False
        self.round_clock = 0.0
        self.schedule: list[tuple[float, object]] = []
        self.spawned_this_round = 0

        self.towers: list[Tower] = []
        self.balloons: list[Balloon] = []
        self.projectiles: list = []
        self.effects = Effects()
        self.index = BalloonIndex()

        self.outcome = RUNNING
        self.speed = 1
        self.paused = False
        self.auto_start = False

        self.total_pops = 0
        self.total_earned = 0
        self.elapsed = 0.0
        self._accumulator = 0.0

        self.sfx_hook = None  # set by the app; called with a sound name

    # -- queries ----------------------------------------------------------

    @property
    def wave(self):
        """The :class:`~btd.waves.Wave` for the current round."""
        return wave_for(self.round_number)

    @property
    def round_progress(self) -> float:
        """Fraction of the current round's balloons already released."""
        total = self.spawned_this_round + len(self.schedule)
        if total <= 0:
            return 0.0
        return self.spawned_this_round / total

    def tower_cost(self, key: str) -> int:
        """Purchase price of a tower type on this difficulty."""
        return int(round(TOWER_KINDS[key].cost * self.cost_scale))

    def can_place(self, key: str, x: float, y: float) -> bool:
        """Whether a tower of this type may be placed at a point.

        Rejects positions off the map, too close to the track, or overlapping
        an existing tower. Farms are exempt from the track clearance rule
        because they never need line of sight.
        """
        radius = 18
        if not (radius <= x <= MAP_W - radius and radius <= y <= MAP_H - radius):
            return False
        if TOWER_KINDS[key].mode != FARM:
            if self.path.distance_to(x, y, self.clearance) < self.clearance:
                return False
        elif self.path.distance_to(x, y, self.clearance) < self.clearance * 0.6:
            return False
        for tower in self.towers:
            if math.hypot(tower.x - x, tower.y - y) < 34:
                return False
        return True

    def tower_at(self, x: float, y: float) -> Tower | None:
        """Return the tower under a point, if any."""
        for tower in self.towers:
            if math.hypot(tower.x - x, tower.y - y) <= 20:
                return tower
        return None

    # -- player actions ---------------------------------------------------

    def place_tower(self, key: str, x: float, y: float) -> Tower | None:
        """Buy and place a tower. Returns it, or ``None`` if not allowed."""
        cost = self.tower_cost(key)
        if self.money < cost or not self.can_place(key, x, y):
            return None
        tower = Tower(TOWER_KINDS[key], x, y, self.cost_scale)
        self.money -= cost
        self.towers.append(tower)
        self.effects.ring(x, y, 30, TOWER_KINDS[key].colour, width=2)
        self._sfx("place")
        return tower

    def upgrade_tower(self, tower: Tower, path: int) -> bool:
        """Buy the next upgrade on a path. Returns whether it succeeded."""
        cost = tower.upgrade_cost(path)
        if cost is None or self.money < cost:
            return False
        self.money -= cost
        tower.apply_upgrade(path)
        self.effects.ring(tower.x, tower.y, 38, (255, 232, 150), width=2)
        self.effects.text(tower.x, tower.y - 26, "UPGRADED", (255, 232, 150), 15)
        self._sfx("upgrade")
        return True

    def sell_tower(self, tower: Tower) -> None:
        """Sell a tower and refund part of what was spent on it."""
        if tower not in self.towers:
            return
        refund = tower.sell_value
        self.money += refund
        self.towers.remove(tower)
        self.effects.text(tower.x, tower.y - 20, f"+${refund}", (255, 205, 74))
        self._sfx("sell")

    def start_round(self) -> bool:
        """Begin the next round. Returns whether it actually started."""
        if self.round_active or self.outcome != RUNNING:
            return False
        self.schedule = build_schedule(self.wave, self.count_scale)
        self.spawned_this_round = 0
        self.round_clock = 0.0
        self.round_active = True
        return True

    def toggle_speed(self) -> None:
        """Cycle the simulation speed multiplier."""
        self.speed = 1 if self.speed >= 3 else self.speed + 1

    # -- simulation -------------------------------------------------------

    def advance(self, real_dt: float) -> None:
        """Run the simulation forward by real elapsed time.

        Time is accumulated and consumed in fixed :data:`~btd.config.TICK`
        steps. ``speed`` multiplies how many steps a given amount of real time
        buys, which is what makes fast-forward exact rather than approximate.
        """
        if self.paused or self.outcome != RUNNING:
            self.effects.advance(min(real_dt, 0.05))
            return

        self._accumulator += min(real_dt, 0.25) * self.speed
        budget = MAX_STEPS_PER_FRAME * self.speed
        steps = 0

        while self._accumulator >= TICK and steps < budget:
            self._accumulator -= TICK
            steps += 1
            self._step(TICK)

        if steps >= budget:
            # Behind schedule; drop the backlog rather than spiralling.
            self._accumulator = 0.0

        self.effects.advance(min(real_dt, 0.05) * self.speed)

    def _step(self, dt: float) -> None:
        """Advance the simulation by exactly one tick."""
        self.elapsed += dt

        self._spawn(dt)
        self._move_balloons(dt)
        self.index.build(self.balloons)
        self._fire_towers(dt)
        self._move_projectiles(dt)
        self._check_round_end()

    def _spawn(self, dt: float) -> None:
        """Release any balloons whose scheduled time has arrived."""
        if not self.round_active:
            return
        self.round_clock += dt
        while self.schedule and self.schedule[0][0] <= self.round_clock:
            _, kind = self.schedule.pop(0)
            self.balloons.append(Balloon(
                kind, distance=0.0,
                hp_scale=self.hp_scale, speed_scale=self.speed_scale,
            ))
            self.spawned_this_round += 1

    def _move_balloons(self, dt: float) -> None:
        """Advance balloons and handle leaks."""
        survivors: list[Balloon] = []
        leaked = 0
        for balloon in self.balloons:
            if not balloon.alive:
                continue
            if balloon.advance(dt, self.path):
                leaked += balloon.leak_damage
                end = self.path.position_at(self.path.length)
                self.effects.text(end[0], end[1] - 18,
                                  f"-{balloon.leak_damage}", (255, 96, 104), 18)
                continue
            survivors.append(balloon)

        self.balloons = survivors
        if leaked:
            self.lives -= leaked
            self.effects.kick(6)
            self._sfx("leak")
            if self.lives <= 0:
                self.lives = 0
                self.outcome = LOST

    def _fire_towers(self, dt: float) -> None:
        """Let every tower act, and resolve instant effects."""
        new_projectiles = []
        for tower in self.towers:
            if tower.kind.mode == FARM:
                continue
            nearby = self.index.query(tower.x, tower.y, tower.range)
            shots, instants = tower.update(dt, nearby)
            new_projectiles.extend(shots)
            for effect in instants:
                self._apply_instant(effect)
        self.projectiles.extend(new_projectiles)

    def _apply_instant(self, effect) -> None:
        """Resolve a hitscan hit, an area pulse, or register a beam."""
        if isinstance(effect, DirectHit):
            target = effect.target
            if not target.alive:
                return
            result = resolve_hit(
                target, effect.tower.damage + (
                    effect.tower.moab_bonus if target.kind.moab else 0
                ),
                effect.tower.damage_type, self.hp_scale, self.speed_scale,
            )
            self._collect(result, effect.tower, target.x, target.y)
            return

        if isinstance(effect, PulseEffect):
            tower = effect.tower
            self.effects.ring(tower.x, tower.y, tower.range,
                              tower.kind.colour, width=2)
            for balloon in self.index.query(tower.x, tower.y, tower.range):
                if not balloon.alive or not tower.can_see(balloon):
                    continue
                if not tower.in_range(balloon):
                    continue
                balloon.slow(tower.slow_factor, tower.slow_time)
                if tower.damage > 0:
                    result = resolve_hit(
                        balloon, tower.damage, tower.damage_type,
                        self.hp_scale, self.speed_scale,
                    )
                    self._collect(result, tower, balloon.x, balloon.y)
            return

        self.effects.beam(effect)

    def _move_projectiles(self, dt: float) -> None:
        """Advance shots and resolve their collisions."""
        if not self.projectiles:
            return

        alive = []
        for shot in self.projectiles:
            shot.advance(dt, (MAP_W, MAP_H))
            if not shot.alive:
                if shot.splash > 0:
                    self.effects.ring(shot.x, shot.y, shot.splash,
                                      (255, 176, 96), width=2)
                continue

            nearby = self.index.query(shot.x, shot.y,
                                      max(shot.radius, shot.splash) + 24)
            if nearby:
                result = collide(shot, nearby, self.hp_scale, self.speed_scale)
                if result.pops or result.money:
                    self._collect(result, None, shot.x, shot.y)
                if shot.splash > 0 and not shot.alive:
                    self.effects.ring(shot.x, shot.y, shot.splash,
                                      (255, 176, 96), width=2)
                    self.effects.kick(2)

            if shot.alive:
                alive.append(shot)

        self.projectiles = alive

    def _collect(self, result, tower, x: float, y: float) -> None:
        """Fold a hit result into the run: money, effects, and new balloons."""
        if result.pops:
            self.total_pops += result.pops
            self.effects.pop(x, y, (250, 240, 235), min(6, result.pops * 2))
            self._sfx("pop")
        if result.money:
            self.money += result.money
            self.total_earned += result.money
            if result.money >= 10:
                self.effects.text(x, y - 14, f"+${result.money}", (255, 205, 74))
        if tower is not None:
            tower.pops += result.pops
            tower.cash_earned += result.money
        if result.spawned:
            self.balloons.extend(result.spawned)

    def _check_round_end(self) -> None:
        """Detect the end of a round and award its bonus."""
        if not self.round_active:
            return
        if self.schedule or any(b.alive for b in self.balloons):
            return

        self.round_active = False
        bonus = round_bonus(self.round_number, ROUND_BONUS_BASE,
                            ROUND_BONUS_PER_ROUND)
        income = sum(t.income for t in self.towers)
        self.money += bonus + income
        self.total_earned += bonus + income

        if income:
            for tower in self.towers:
                if tower.income:
                    self.effects.text(tower.x, tower.y - 22,
                                      f"+${tower.income}", (226, 196, 78))

        if self.round_number >= self.max_rounds:
            self.outcome = WON
            return

        self.round_number += 1
        self._sfx("round")
        if self.auto_start:
            self.start_round()

    def _sfx(self, name: str) -> None:
        """Forward a sound cue to the app, if one is listening."""
        if self.sfx_hook is not None:
            self.sfx_hook(name)

    # -- rendering --------------------------------------------------------

    def draw_map(self, surface: pygame.Surface) -> None:
        """Draw the map layer: background, balloons, towers, shots, effects."""
        shake = self.effects.offset()
        surface.blit(self.background, shake)

        for balloon in self.balloons:
            if not balloon.alive:
                continue
            sprite = sprite_for(balloon.kind)
            if balloon.kind.moab:
                sprite = pygame.transform.rotate(
                    sprite, self.path.heading_at(balloon.distance)
                )
            rect = sprite.get_rect(center=(int(balloon.x) + shake[0],
                                           int(balloon.y) + shake[1]))
            surface.blit(sprite, rect)
            if balloon.slow_timer > 0:
                pygame.draw.circle(
                    surface, (150, 220, 255),
                    (int(balloon.x) + shake[0], int(balloon.y) + shake[1]),
                    balloon.kind.radius + 3, 1,
                )

        for tower in self.towers:
            self._draw_tower(surface, tower, shake)

        for shot in self.projectiles:
            self._draw_projectile(surface, shot, shake)

        self.effects.draw(surface)

    def _draw_tower(self, surface: pygame.Surface, tower: Tower,
                    shake: tuple[int, int]) -> None:
        """Draw one tower, rotated to face its target and kicked by recoil.

        The recoil offset is driven by the tower's own fire rate (see
        :attr:`~btd.towers.Tower.recoil_time`), so every tower's animation is
        in step with the shots it is actually taking.
        """
        pos_x = tower.x + shake[0]
        pos_y = tower.y + shake[1]

        kick = tower.recoil
        if kick:
            radians = math.radians(tower.angle)
            pos_x -= math.cos(radians) * kick
            pos_y += math.sin(radians) * kick

        pos = (int(pos_x), int(pos_y))
        sprite = tower_sprite(tower)
        if sprites.has_overhead(tower.kind.key) and tower.kind.mode != FARM:
            # Only real top-down art is rotated. Spinning a portrait logo
            # because no overhead was supplied looks broken, so it stays put.
            sprite = pygame.transform.rotate(sprite, tower.angle - 90)
        surface.blit(sprite, sprite.get_rect(center=pos))

        # Muzzle flash on the frame the shot leaves.
        if tower.fire_anim > 0.75 and tower.kind.mode != FARM:
            radians = math.radians(tower.angle)
            tip = (int(pos_x + math.cos(radians) * 18),
                   int(pos_y - math.sin(radians) * 18))
            flash = int(3 + 3 * (tower.fire_anim - 0.75) * 4)
            pygame.draw.circle(surface, (255, 246, 206), tip, flash)

        total = sum(tower.tiers)
        if total:
            for i in range(total):
                pygame.draw.circle(
                    surface, (255, 226, 130),
                    (pos[0] - 9 + i * 5, pos[1] + 17), 2,
                )

    @staticmethod
    def _draw_projectile(surface: pygame.Surface, shot,
                         shake: tuple[int, int]) -> None:
        """Draw one projectile."""
        pos = (int(shot.x) + shake[0], int(shot.y) + shake[1])
        if shot.splash > 0:
            pygame.draw.circle(surface, (52, 54, 66), pos, 5)
            pygame.draw.circle(surface, (232, 128, 72), pos, 2)
            return
        if shot.trail:
            tail = (int(pos[0] - shot.v_x * 0.018), int(pos[1] - shot.v_y * 0.018))
            pygame.draw.line(surface, shot.colour, tail, pos, 3)
        pygame.draw.circle(surface, (255, 253, 245), pos, 3)


_TOWER_SPRITES: dict[str, pygame.Surface] = {}


#: On-screen size of a tower on the map, in pixels.
TOWER_SPRITE_SIZE = 48


def tower_sprite(tower: Tower) -> pygame.Surface:
    """Return the cached map sprite for a tower.

    Prefers the top-down overhead art, falls back to the portrait logo, and
    finally to a drawn glyph. See :mod:`btd.sprites`.
    """
    key = tower.kind.key
    cached = _TOWER_SPRITES.get(key)
    if cached is not None:
        return cached

    art = sprites.character(key, sprites.OVERHEAD, TOWER_SPRITE_SIZE)
    if art is None:
        art = _draw_tower_glyph(TOWER_SPRITE_SIZE, tower.kind.colour,
                               tower.kind.mode)

    _TOWER_SPRITES[key] = art
    return art


def _draw_tower_glyph(size: int, colour: tuple[int, int, int],
                      mode: str) -> pygame.Surface:
    """Draw a tower placeholder for the types with no sprite in the repo."""
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    centre = size // 2
    pygame.draw.circle(surf, (26, 28, 36), (centre, centre), centre - 2)
    pygame.draw.circle(surf, colour, (centre, centre), centre - 5)
    pygame.draw.circle(surf, (18, 20, 26), (centre, centre), centre - 5, 2)

    if mode == FARM:
        pygame.draw.arc(surf, (60, 46, 20),
                        pygame.Rect(centre - 10, centre - 10, 20, 20),
                        3.6, 5.9, 4)
    else:
        # A barrel pointing "up", since sprites are rotated from that origin.
        pygame.draw.rect(surf, (32, 34, 42),
                         pygame.Rect(centre - 3, 3, 6, centre - 4),
                         border_radius=2)
    return surf
