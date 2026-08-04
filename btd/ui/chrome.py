"""
Cabinet woodwork, glossy controls, and outlined display text.

These are the pieces that give the sidebar its shelf-unit look: beveled wooden
frames, recessed cubbies for the tower rack, raised plaques for the stat
readouts, circular glossy buttons, and the chunky dark-outlined numerals used
for money and lives.

Everything is drawn with primitives and cached, so there is no artwork to
produce and the whole interface still works in the browser build, where only
pygame's built-in font is available.
"""

from __future__ import annotations

import pygame

from .. import assets
from ..config import (
    TEXT_OUTLINE, WOOD_FACE, WOOD_HILITE, WOOD_RECESS, WOOD_SHADE,
)

#: Cached outlined-text surfaces, keyed by everything that affects the render.
_TEXT_CACHE: dict[tuple, pygame.Surface] = {}

#: Cached wood-grain overlays, keyed by size.
_GRAIN_CACHE: dict[tuple[int, int], pygame.Surface] = {}


def mix(a, b, amount: float) -> tuple[int, int, int]:
    """Blend two colours, ``amount`` of ``b`` into ``a``."""
    return tuple(int(x + (y - x) * amount) for x, y in zip(a[:3], b[:3]))


# --- text ----------------------------------------------------------------

def outlined_text(text: str, size: int, colour, outline=TEXT_OUTLINE,
                  thickness: int = 2, bold: bool = True) -> pygame.Surface:
    """Render text with a solid outline, cached.

    The original code produced this effect by blitting the same string up to
    nine times at every call site, every frame. Here it is rendered once and
    reused, so the look costs one blit.

    Args:
        text: String to render.
        size: Font size.
        colour: Fill colour.
        outline: Outline colour.
        thickness: Outline width in pixels.
        bold: Use the bold face.

    Returns:
        A surface with a transparent background.
    """
    key = (text, size, tuple(colour), tuple(outline), thickness, bold)
    cached = _TEXT_CACHE.get(key)
    if cached is not None:
        return cached

    font = assets.font(size, bold=bold)
    body = font.render(text, True, colour)
    edge = font.render(text, True, outline)

    pad = thickness
    surf = pygame.Surface(
        (body.get_width() + pad * 2, body.get_height() + pad * 2), pygame.SRCALPHA
    )

    # Eight-way offset outline. Diagonals at full thickness would look bloated,
    # so they are pulled in slightly.
    diag = max(1, int(thickness * 0.75))
    offsets = [
        (-thickness, 0), (thickness, 0), (0, -thickness), (0, thickness),
        (-diag, -diag), (diag, -diag), (-diag, diag), (diag, diag),
    ]
    for o_x, o_y in offsets:
        surf.blit(edge, (pad + o_x, pad + o_y))
    surf.blit(body, (pad, pad))

    _TEXT_CACHE[key] = surf
    return surf


def blit_outlined(surface: pygame.Surface, text: str, pos, size: int, colour,
                  align: str = "left", **kwargs) -> pygame.Rect:
    """Draw outlined text and return its rect.

    ``align`` accepts ``"left"``, ``"center"``, or ``"right"``, anchored at the
    top of ``pos``.
    """
    label = outlined_text(text, size, colour, **kwargs)
    rect = label.get_rect()
    if align == "center":
        rect.midtop = pos
    elif align == "right":
        rect.topright = pos
    else:
        rect.topleft = pos
    surface.blit(label, rect)
    return rect


# --- woodwork ------------------------------------------------------------

def _grain(size: tuple[int, int]) -> pygame.Surface:
    """Return a cached translucent wood-grain overlay."""
    cached = _GRAIN_CACHE.get(size)
    if cached is not None:
        return cached

    width, height = size
    surf = pygame.Surface(size, pygame.SRCALPHA)
    # Deterministic streaks: a hash of the row keeps it stable frame to frame
    # without needing a seeded RNG threaded through every call. Kept faint and
    # sparse -- dense bright lines read as corduroy rather than as timber.
    for y in range(0, height, 7):
        step = (y * 2654435761) >> 8
        if step % 3 == 0:
            continue
        wobble = step % 7
        alpha = 9 + ((y * 40503) >> 4) % 8
        tint = (255, 232, 196, alpha) if step % 2 else (40, 22, 8, alpha)
        pygame.draw.line(surf, tint, (wobble, y), (width - wobble, y))
    _GRAIN_CACHE[size] = surf
    return surf


def wood_fill(surface: pygame.Surface, rect: pygame.Rect, face=WOOD_FACE,
              radius: int = 0) -> None:
    """Fill a region with grained wood."""
    pygame.draw.rect(surface, face, rect, border_radius=radius)
    grain = _grain((rect.width, rect.height))
    surface.blit(grain, rect.topleft)


def beveled(surface: pygame.Surface, rect: pygame.Rect, face=WOOD_FACE,
            radius: int = 10, depth: int = 3, raised: bool = True) -> None:
    """Draw a beveled wooden slab.

    A lit top edge and a shaded bottom edge is what makes the cabinet read as
    carved rather than as flat brown rectangles.

    Args:
        surface: Target surface.
        rect: Area to fill.
        face: Mid-tone wood colour.
        radius: Corner rounding.
        depth: Bevel thickness in pixels.
        raised: True for a raised slab, False for a sunken one.
    """
    top = WOOD_HILITE if raised else WOOD_SHADE
    bottom = WOOD_SHADE if raised else WOOD_HILITE

    pygame.draw.rect(surface, bottom, rect, border_radius=radius)
    pygame.draw.rect(surface, top, rect.inflate(0, -depth).move(0, -depth // 2),
                     border_radius=radius)
    inner = rect.inflate(-depth * 2, -depth * 2)
    wood_fill(surface, inner, face, radius=max(0, radius - depth))


def cubby(surface: pygame.Surface, rect: pygame.Rect, radius: int = 8) -> None:
    """Draw a recessed shelf compartment.

    Used for each tower slot in the rack: a dark recess with a lit lower lip,
    so items sitting in it look like they are inside the cabinet.
    """
    pygame.draw.rect(surface, WOOD_SHADE, rect, border_radius=radius)
    inset = rect.inflate(-4, -4)
    pygame.draw.rect(surface, WOOD_RECESS, inset, border_radius=radius - 2)
    # Depth cues: a dark line under the top lip and a lit line above the
    # bottom one. Drawn as straight segments -- arcs across a wide rect trace
    # a wide ellipse and read as stray curves rather than as an inner edge.
    pygame.draw.line(surface, mix(WOOD_RECESS, (0, 0, 0), 0.5),
                     (inset.x + radius, inset.y + 1),
                     (inset.right - radius, inset.y + 1), 2)
    pygame.draw.line(surface, mix(WOOD_RECESS, WOOD_HILITE, 0.30),
                     (inset.x + radius, inset.bottom - 2),
                     (inset.right - radius, inset.bottom - 2), 2)


def plank_strip(surface: pygame.Surface, rect: pygame.Rect) -> None:
    """Draw a horizontal wooden strip, as used for the round-info bar."""
    pygame.draw.rect(surface, WOOD_SHADE, rect)
    wood_fill(surface, rect.inflate(-4, -6), WOOD_FACE)
    pygame.draw.line(surface, WOOD_HILITE, (rect.x + 2, rect.y + 3),
                     (rect.right - 2, rect.y + 3), 2)
    pygame.draw.line(surface, mix(WOOD_SHADE, (0, 0, 0), 0.4),
                     (rect.x, rect.bottom - 2), (rect.right, rect.bottom - 2), 2)


#: Pale highlight used on nail heads.
PAPER_TINT = (250, 240, 216)


def sign(surface: pygame.Surface, rect: pygame.Rect, radius: int = 14) -> None:
    """Draw a hanging wooden sign, for headings and standalone captions.

    Text over the blurred menu backdrop used to rely on a heavy outline to
    stay legible. At small sizes the outlines of adjacent letters merge into a
    solid dark slab, so the text looked like it had a black box behind it.
    Putting the text on a board instead removes the need for an outline at
    all, and matches the rest of the woodwork.
    """
    pygame.draw.rect(surface, mix(WOOD_SHADE, (0, 0, 0), 0.45),
                     rect.move(0, 5), border_radius=radius)
    pygame.draw.rect(surface, WOOD_SHADE, rect, border_radius=radius)

    face = rect.inflate(-10, -10)
    wood_fill(surface, face, WOOD_FACE, radius=max(0, radius - 5))
    pygame.draw.rect(surface, WOOD_HILITE, face, 2,
                     border_radius=max(0, radius - 5))

    # Nail heads, so the board reads as fixed to something.
    for n_x in (rect.x + 15, rect.right - 15):
        for n_y in (rect.y + 15, rect.bottom - 15):
            pygame.draw.circle(surface, mix(WOOD_SHADE, (0, 0, 0), 0.4),
                               (n_x, n_y + 1), 4)
            pygame.draw.circle(surface, mix(WOOD_HILITE, PAPER_TINT, 0.3),
                               (n_x, n_y), 3)


def round_button(surface: pygame.Surface, centre: tuple[int, int], radius: int,
                 face, dark, pressed: bool = False,
                 enabled: bool = True) -> None:
    """Draw a glossy circular button.

    Args:
        surface: Target surface.
        centre: Button centre.
        radius: Button radius.
        face: Main colour.
        dark: Rim and shadow colour.
        pressed: Sink the button by a pixel.
        enabled: Desaturate when False.
    """
    c_x, c_y = centre
    if pressed:
        c_y += 2
    if not enabled:
        face = mix(face, (120, 120, 120), 0.6)
        dark = mix(dark, (90, 90, 90), 0.5)

    pygame.draw.circle(surface, mix(dark, (0, 0, 0), 0.35), (c_x, c_y + 3), radius)
    pygame.draw.circle(surface, dark, (c_x, c_y), radius)
    pygame.draw.circle(surface, face, (c_x, c_y), radius - 3)
    # Gloss: a bright cap across the upper third.
    gloss = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
    pygame.draw.ellipse(gloss, (255, 255, 255, 92),
                        pygame.Rect(radius * 0.32, radius * 0.24,
                                    radius * 1.36, radius * 0.86))
    surface.blit(gloss, (c_x - radius, c_y - radius))


# --- icons ---------------------------------------------------------------

def coin_icon(surface: pygame.Surface, centre: tuple[int, int],
              radius: int = 11) -> None:
    """Draw a gold coin."""
    c_x, c_y = centre
    pygame.draw.circle(surface, (146, 96, 16), (c_x, c_y + 1), radius)
    pygame.draw.circle(surface, (250, 196, 52), (c_x, c_y), radius)
    pygame.draw.circle(surface, (206, 148, 22), (c_x, c_y), radius, 2)
    pygame.draw.circle(surface, (255, 232, 150), (c_x - radius // 3,
                                                  c_y - radius // 3),
                       max(2, radius // 3))
    label = outlined_text("$", int(radius * 1.7), (146, 96, 16),
                          outline=(250, 196, 52), thickness=1)
    surface.blit(label, label.get_rect(center=(c_x, c_y)))


def heart_icon(surface: pygame.Surface, centre: tuple[int, int],
               size: int = 20) -> None:
    """Draw a red heart."""
    c_x, c_y = centre
    lobe = size // 3
    dark = (150, 28, 30)
    red = (228, 58, 56)

    for colour, offset in ((dark, 2), (red, 0)):
        top = c_y - lobe // 2 + offset
        pygame.draw.circle(surface, colour, (c_x - lobe // 2, top), lobe)
        pygame.draw.circle(surface, colour, (c_x + lobe // 2, top), lobe)
        pygame.draw.polygon(surface, colour, [
            (c_x - lobe - lobe // 2 + 1, top + 1),
            (c_x + lobe + lobe // 2 - 1, top + 1),
            (c_x, c_y + size // 2 + offset),
        ])
    pygame.draw.circle(surface, (255, 150, 148), (c_x - lobe // 2, c_y - lobe),
                       max(2, lobe // 3))


def chevron(surface: pygame.Surface, centre: tuple[int, int], width: int,
            up: bool, colour) -> None:
    """Draw a filled triangular chevron, as used by the rack scroll arrows."""
    c_x, c_y = centre
    half = width // 2
    rise = width // 3
    points = ([(c_x - half, c_y + rise // 2), (c_x + half, c_y + rise // 2),
               (c_x, c_y - rise)]
              if up else
              [(c_x - half, c_y - rise // 2), (c_x + half, c_y - rise // 2),
               (c_x, c_y + rise)])
    pygame.draw.polygon(surface, mix(colour, (0, 0, 0), 0.4),
                        [(x, y + 2) for x, y in points])
    pygame.draw.polygon(surface, colour, points)
