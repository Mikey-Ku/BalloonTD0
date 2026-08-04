"""
Character artwork: logos for the sidebar, overheads for the map.

Each tower can have two pieces of art:

``<key>_logo.png``
    A three-quarter portrait, shown in the shop rack. Never rotated.

``<key>_overhead.png``
    A top-down view, drawn on the map and rotated to face the target. Must be
    drawn pointing **up**.

Either may be missing. A tower with only a logo uses it in both places, and a
tower with only an overhead likewise -- so art can land one piece at a time
without anything breaking.

Sizing is normalised by **content**, not by canvas. The supplied art has the
subject filling anywhere between 37% and 100% of its image, and some sheets
are 1024x1024 while others are 1024x1536. Scaling whole canvases to a common
size would therefore have made the same character appear at wildly different
sizes depending on how it happened to be exported. Instead each sprite is
cropped to its visible pixels and scaled so that *that* fits the target box,
which is what makes the set look consistent.
"""

from __future__ import annotations

import pygame

from . import assets

LOGO = "logo"
OVERHEAD = "overhead"

#: Alpha below this counts as empty when measuring a sprite's extent. A hard
#: zero would let a stray semi-transparent pixel or a soft glow inflate the
#: box and shrink the character.
ALPHA_FLOOR = 24

#: Fraction of the target box the artwork fills, leaving a little air so
#: neighbouring towers do not touch and rotation has room.
FILL = 0.94

#: Extra filename stems accepted per tower, so the descriptive names the art
#: was delivered under work as-is alongside the key-based convention.
ALIASES: dict[str, tuple[str, ...]] = {
    "dart": ("dart", "Dart-Monkey", "Dart Monkey"),
    "sniper": ("sniper", "Sniper-Monkey", "Sniper"),
    "tack": ("tack", "Tac-Shooter", "Tack-Shooter"),
    "bomb": ("bomb", "Cannon"),
    "ice": ("ice", "Ice-Monkey"),
    "super": ("super", "Super-Monkey"),
    "farm": ("farm", "Banana-Tree", "Banana Tree"),
}

_CACHE: dict[tuple[str, str, int], pygame.Surface] = {}
_FOUND: dict[tuple[str, str], str | None] = {}


def candidates(key: str, role: str) -> list[str]:
    """Filenames checked for one tower's art, in priority order."""
    out = []
    for stem in ALIASES.get(key, (key,)):
        out.append(f"monkey_images/{stem}_{role}.png")
        out.append(f"monkey_images/{stem}-{role.capitalize()}.png")
    return out


def find(key: str, role: str) -> str | None:
    """Return the path to a tower's art for a role, or ``None``."""
    cache_key = (key, role)
    if cache_key in _FOUND:
        return _FOUND[cache_key]

    match = next((c for c in candidates(key, role) if assets.exists(c)), None)
    _FOUND[cache_key] = match
    return match


def has_overhead(key: str) -> bool:
    """Whether a real top-down sprite exists for this tower.

    Callers use this to decide whether to rotate: spinning a portrait logo
    because no overhead was supplied looks wrong, so they leave it upright.
    """
    return find(key, OVERHEAD) is not None


def resolve(key: str, role: str) -> str | None:
    """Pick the best available art for a role, falling back to the other one."""
    other = LOGO if role == OVERHEAD else OVERHEAD
    return find(key, role) or find(key, other)


def character(key: str, role: str, size: int) -> pygame.Surface | None:
    """Load a tower's art, normalised to a square ``size`` box.

    Args:
        key: Tower key, e.g. ``"bomb"``.
        role: :data:`LOGO` or :data:`OVERHEAD`.
        size: Side length of the square canvas returned.

    Returns:
        The normalised sprite, or ``None`` when the tower has no art at all.
    """
    cache_key = (key, role, size)
    cached = _CACHE.get(cache_key)
    if cached is not None:
        return cached

    path = resolve(key, role)
    if path is None:
        return None

    surface = normalise(assets.image(path), size)
    _CACHE[cache_key] = surface
    return surface


def normalise(source: pygame.Surface, size: int) -> pygame.Surface:
    """Crop to visible content, scale to fit, and centre on a square canvas.

    Args:
        source: The loaded artwork.
        size: Side length of the square canvas returned.

    Returns:
        A new surface of exactly ``size`` x ``size``.
    """
    surface = source.convert_alpha() if pygame.display.get_init() else source

    # get_bounding_rect is implemented in C, so measuring a 1024x1536 sheet is
    # cheap enough to do at load time rather than in a preprocessing step.
    box = surface.get_bounding_rect(min_alpha=ALPHA_FLOOR)
    if box.width < 2 or box.height < 2:
        box = surface.get_rect()

    content = surface.subsurface(box)

    target = size * FILL
    scale = min(target / box.width, target / box.height)
    scaled = pygame.transform.smoothscale(
        content,
        (max(1, round(box.width * scale)), max(1, round(box.height * scale))),
    )

    canvas = pygame.Surface((size, size), pygame.SRCALPHA)
    canvas.blit(scaled, scaled.get_rect(center=(size // 2, size // 2)))
    return canvas


def missing() -> list[tuple[str, str]]:
    """List ``(key, role)`` pairs that have no artwork of their own."""
    gaps = []
    for key in ALIASES:
        for role in (LOGO, OVERHEAD):
            if find(key, role) is None:
                gaps.append((key, role))
    return gaps
