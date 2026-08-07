"""
Transient visual effects: pop particles, floating text, and explosion rings.

None of this affects the simulation. It exists because the original game gave
no feedback at all when a balloon popped -- sprites simply vanished -- which
made it impossible to tell whether a tower was doing anything useful.
"""

from __future__ import annotations

import math
import random

import pygame

from . import assets


class Particle:
    """A single scrap of popped balloon.

    Attributes:
        x, y: Position.
        v_x, v_y: Velocity in pixels per second.
        life: Seconds remaining.
        max_life: Initial lifetime, used to fade out.
        colour: Fill colour.
        size: Radius in pixels.
    """

    __slots__ = ("x", "y", "v_x", "v_y", "life", "max_life", "colour", "size")

    GRAVITY = 260.0

    def __init__(self, x, y, v_x, v_y, life, colour, size):
        self.x = x
        self.y = y
        self.v_x = v_x
        self.v_y = v_y
        self.life = life
        self.max_life = life
        self.colour = colour
        self.size = size

    @property
    def alive(self) -> bool:
        """Whether the particle still has time left."""
        return self.life > 0

    def advance(self, dt: float) -> None:
        """Integrate motion and age the particle."""
        self.v_y += self.GRAVITY * dt
        self.x += self.v_x * dt
        self.y += self.v_y * dt
        self.life -= dt


class FloatingText:
    """A short string that drifts upward and fades, e.g. ``+$12``."""

    __slots__ = ("x", "y", "text", "colour", "life", "max_life", "size")

    def __init__(self, x, y, text, colour=(255, 255, 255), life=0.9, size=17):
        self.x = x
        self.y = y
        self.text = text
        self.colour = colour
        self.life = life
        self.max_life = life
        self.size = size

    @property
    def alive(self) -> bool:
        """Whether the text is still visible."""
        return self.life > 0

    def advance(self, dt: float) -> None:
        """Drift upward and age."""
        self.y -= 34 * dt
        self.life -= dt


class Ring:
    """An expanding circle, used for explosions and ice pulses."""

    __slots__ = ("x", "y", "radius", "max_radius", "life", "max_life",
                 "colour", "width")

    def __init__(self, x, y, max_radius, colour, life=0.32, width=3):
        self.x = x
        self.y = y
        self.radius = 0.0
        self.max_radius = max_radius
        self.life = life
        self.max_life = life
        self.colour = colour
        self.width = width

    @property
    def alive(self) -> bool:
        """Whether the ring is still expanding."""
        return self.life > 0

    def advance(self, dt: float) -> None:
        """Grow toward the maximum radius and age."""
        self.life -= dt
        progress = 1.0 - max(0.0, self.life) / self.max_life
        self.radius = self.max_radius * progress


class Effects:
    """Owns every transient effect and draws them in one pass."""

    #: Hard cap so a huge round cannot fill memory with particles.
    MAX_PARTICLES = 600

    def __init__(self):
        self.particles: list[Particle] = []
        self.texts: list[FloatingText] = []
        self.rings: list[Ring] = []
        self.beams: list = []
        self.shake = 0.0

    def clear(self) -> None:
        """Drop everything, e.g. when restarting."""
        self.particles.clear()
        self.texts.clear()
        self.rings.clear()
        self.beams.clear()
        self.shake = 0.0

    # -- spawning ---------------------------------------------------------

    def pop(self, x: float, y: float, colour, count: int = 6) -> None:
        """Emit a small burst of debris where a balloon popped."""
        if len(self.particles) > self.MAX_PARTICLES:
            return
        for _ in range(count):
            angle = random.uniform(0, math.tau)
            speed = random.uniform(40, 155)
            self.particles.append(Particle(
                x, y,
                math.cos(angle) * speed,
                math.sin(angle) * speed - 40,
                random.uniform(0.25, 0.55),
                colour,
                random.randint(2, 4),
            ))

    def text(self, x: float, y: float, message: str, colour=(255, 255, 255),
             size: int = 17) -> None:
        """Add a floating label."""
        if len(self.texts) < 60:
            self.texts.append(FloatingText(x, y, message, colour, size=size))

    def ring(self, x: float, y: float, radius: float, colour, width: int = 3) -> None:
        """Add an expanding ring."""
        if len(self.rings) < 60:
            self.rings.append(Ring(x, y, radius, colour, width=width))

    def beam(self, beam) -> None:
        """Register a hitscan beam for drawing."""
        self.beams.append(beam)

    def kick(self, amount: float) -> None:
        """Add screen shake, keeping the strongest pending value."""
        self.shake = max(self.shake, amount)

    # -- lifecycle --------------------------------------------------------

    def advance(self, dt: float) -> None:
        """Age every effect and drop the dead ones."""
        for group in (self.particles, self.texts, self.rings, self.beams):
            for item in group:
                item.advance(dt)
        self.particles = [p for p in self.particles if p.alive]
        self.texts = [t for t in self.texts if t.alive]
        self.rings = [r for r in self.rings if r.alive]
        self.beams = [b for b in self.beams if b.alive]
        if self.shake > 0:
            self.shake = max(0.0, self.shake - dt * 26)

    def offset(self) -> tuple[int, int]:
        """Current screen-shake offset in pixels."""
        if self.shake <= 0:
            return (0, 0)
        return (
            random.randint(-int(self.shake), int(self.shake)),
            random.randint(-int(self.shake), int(self.shake)),
        )

    def draw(self, surface: pygame.Surface) -> None:
        """Render every effect onto a surface."""
        for beam in self.beams:
            alpha = max(0.0, beam.life / beam.max_life)
            width = max(1, int(beam.width * (0.4 + alpha)))
            pygame.draw.line(
                surface, beam.colour,
                (beam.x1, beam.y1), (beam.x2, beam.y2), width,
            )

        for ring in self.rings:
            alpha = max(0.0, ring.life / ring.max_life)
            if ring.radius < 1:
                continue
            layer = pygame.Surface(
                (int(ring.radius * 2 + 8), int(ring.radius * 2 + 8)), pygame.SRCALPHA
            )
            pygame.draw.circle(
                layer, (*ring.colour, int(210 * alpha)),
                (layer.get_width() // 2, layer.get_height() // 2),
                int(ring.radius), ring.width,
            )
            surface.blit(layer, (ring.x - layer.get_width() // 2,
                                 ring.y - layer.get_height() // 2))

        for p in self.particles:
            fade = max(0.0, p.life / p.max_life)
            size = max(1, int(p.size * (0.4 + fade)))
            pygame.draw.circle(surface, p.colour, (int(p.x), int(p.y)), size)

        for t in self.texts:
            fade = max(0.0, min(1.0, t.life / t.max_life * 1.6))
            font = assets.font(t.size, bold=True)
            label = font.render(t.text, True, t.colour)
            label.set_alpha(int(255 * fade))
            surface.blit(label, (t.x - label.get_width() // 2, t.y))
