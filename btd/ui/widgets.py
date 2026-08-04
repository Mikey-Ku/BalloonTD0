"""
Reusable interface primitives.

The original UI drew text outlines by blitting the same string up to nine
times in a nested loop at every call site, and every button rolled its own
rectangle-and-label drawing.

Everything here shares one visual language, chosen to sit with the bright
cartoon map art rather than against it: carved wood frames, cream panels, and
chunky buttons that physically depress when hovered. The earlier dark-slate
scheme was readable but looked like a dashboard bolted onto a children's game.
"""

from __future__ import annotations

import pygame

from .. import assets
from ..config import (
    ACCENT, BERRY, BUTTON_BLUE, BUTTON_BLUE_DARK, INK, INK_SOFT, LEAF,
    LEAF_DARK, LEAF_LIGHT, PAPER, PAPER_DIM, TEXT_WHITE, WOOD, WOOD_DARK,
    WOOD_LIGHT,
)
from . import chrome

LEFT = "left"
CENTER = "center"
RIGHT = "right"

#: How far a raised element is offset from its shadow, in pixels.
LIFT = 3


def draw_text(surface: pygame.Surface, text: str, pos: tuple[int, int],
              size: int = 18, colour=INK, bold: bool = False,
              align: str = LEFT, shadow: bool = False) -> pygame.Rect:
    """Draw a string and return the rect it occupied.

    Args:
        surface: Target surface.
        text: The string to draw.
        pos: Anchor point, interpreted according to ``align``.
        size: Font size in points.
        colour: Text colour.
        bold: Whether to use the bold face.
        align: ``"left"``, ``"center"``, or ``"right"``.
        shadow: Draw a soft dark offset behind the text, for legibility over
            busy map art.

    Returns:
        The blitted rect.
    """
    font = assets.font(size, bold=bold)
    label = font.render(text, True, colour)
    rect = label.get_rect()
    if align == CENTER:
        rect.midtop = pos
    elif align == RIGHT:
        rect.topright = pos
    else:
        rect.topleft = pos

    if shadow:
        dark = font.render(text, True, (46, 30, 18))
        dark.set_alpha(165)
        surface.blit(dark, (rect.x + 2, rect.y + 2))

    surface.blit(label, rect)
    return rect


def panel(surface: pygame.Surface, rect: pygame.Rect, fill=PAPER,
          edge=WOOD, radius: int = 10, width: int = 3) -> None:
    """Draw a cream panel in a wooden frame."""
    pygame.draw.rect(surface, fill, rect, border_radius=radius)
    if width:
        pygame.draw.rect(surface, edge, rect, width, border_radius=radius)


def raised_panel(surface: pygame.Surface, rect: pygame.Rect, fill=PAPER,
                 edge=WOOD, radius: int = 10) -> None:
    """Draw a panel sitting above a soft shadow, so it reads as raised."""
    shadow = rect.move(0, LIFT)
    pygame.draw.rect(surface, WOOD_DARK, shadow, border_radius=radius)
    panel(surface, rect, fill, edge, radius)


def wood_backdrop(surface: pygame.Surface, rect: pygame.Rect) -> None:
    """Fill a region with vertical wooden planks.

    Used for the sidebar. Plank seams are drawn at fixed positions rather than
    randomly so the sidebar never shimmers between frames.
    """
    pygame.draw.rect(surface, WOOD_DARK, rect)
    plank = 52
    seam = _mix(WOOD_DARK, (0, 0, 0), 0.42)
    for i, x in enumerate(range(rect.x, rect.right, plank)):
        shade = _mix(WOOD_DARK, WOOD, 0.26) if i % 2 else _mix(WOOD_DARK, WOOD, 0.08)
        pygame.draw.rect(surface, shade, (x, rect.y, plank - 3, rect.height))
        # Grain: a couple of long, slightly lighter strokes per plank.
        for offset in (plank // 4, plank * 3 // 5):
            pygame.draw.line(surface, _mix(shade, WOOD_LIGHT, 0.18),
                             (x + offset, rect.y), (x + offset, rect.bottom))
        pygame.draw.line(surface, seam, (x + plank - 3, rect.y),
                         (x + plank - 3, rect.bottom), 3)
    pygame.draw.line(surface, seam, (rect.x, rect.y), (rect.x, rect.bottom), 4)


def progress_bar(surface: pygame.Surface, rect: pygame.Rect, fraction: float,
                 fill=LEAF, back=None) -> None:
    """Draw a horizontal progress bar clamped to ``[0, 1]``."""
    fraction = max(0.0, min(1.0, fraction))
    radius = max(2, rect.height // 2)
    pygame.draw.rect(surface, back or _mix(WOOD, (0, 0, 0), 0.3), rect,
                     border_radius=radius)
    if fraction > 0:
        inner = pygame.Rect(rect.x, rect.y, max(3, int(rect.width * fraction)),
                            rect.height)
        pygame.draw.rect(surface, fill, inner, border_radius=radius)
    pygame.draw.rect(surface, _mix(WOOD_DARK, (0, 0, 0), 0.2), rect, 1,
                     border_radius=radius)


class Button:
    """A chunky clickable panel with a label.

    Draws above a shadow and drops onto it when hovered, which gives a
    physical press without needing a separate pressed state.

    Attributes:
        rect: Screen area.
        label: Text drawn in the middle.
        action: Identifier returned by :meth:`hit` when clicked.
        enabled: Whether the button responds and draws at full strength.
        subtitle: Optional second line, e.g. a price.
        accent: Highlight colour used when selected.
        hovered: Updated by :meth:`update_hover`.
        draw_label: False for shop entries, which draw their own contents.
    """

    def __init__(self, rect, label: str, action: str, subtitle: str = "",
                 accent=ACCENT, size: int = 18, draw_label: bool = True):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.action = action
        self.subtitle = subtitle
        self.accent = accent
        self.size = size
        self.enabled = True
        self.hovered = False
        self.selected = False
        self.draw_label = draw_label

    def update_hover(self, mouse_pos: tuple[int, int]) -> None:
        """Refresh the hover state from the current cursor position."""
        self.hovered = self.enabled and self.rect.collidepoint(mouse_pos)

    def hit(self, pos: tuple[int, int]) -> str | None:
        """Return this button's action if ``pos`` falls inside it."""
        if self.enabled and self.rect.collidepoint(pos):
            return self.action
        return None

    def palette(self) -> tuple:
        """Return ``(fill, edge, text)`` for the current state."""
        if not self.enabled:
            return (_mix(PAPER_DIM, WOOD, 0.28), _mix(WOOD, (0, 0, 0), 0.15),
                    _mix(INK_SOFT, PAPER, 0.15))
        if self.selected:
            return LEAF_LIGHT, LEAF_DARK, INK
        if self.hovered:
            return PAPER, WOOD_LIGHT, INK
        return PAPER_DIM, WOOD, INK

    def body_rect(self) -> pygame.Rect:
        """Where the face of the button sits, accounting for the press."""
        return self.rect.move(0, LIFT if (self.hovered and self.enabled) else 0)

    def draw(self, surface: pygame.Surface) -> None:
        """Render the button in its current state."""
        fill, edge, text_colour = self.palette()
        face = self.body_rect()

        # Shadow slab, always at the resting depth.
        pygame.draw.rect(surface, _mix(WOOD_DARK, (0, 0, 0), 0.25),
                         self.rect.move(0, LIFT), border_radius=9)
        pygame.draw.rect(surface, fill, face, border_radius=9)
        pygame.draw.rect(surface, edge, face, 3, border_radius=9)

        if not self.draw_label:
            return

        if self.subtitle:
            draw_text(surface, self.label, (face.centerx, face.y + 6),
                      self.size, text_colour, bold=True, align=CENTER)
            draw_text(surface, self.subtitle,
                      (face.centerx, face.y + 8 + self.size),
                      self.size - 4, text_colour, align=CENTER)
        else:
            font = assets.font(self.size, bold=True)
            label = font.render(self.label, True, text_colour)
            surface.blit(label, label.get_rect(center=face.center))


class IconButton(Button):
    """A small square button showing a drawn glyph or a short label.

    Glyphs are drawn with primitives rather than typed as characters. Symbols
    like U+2261 and U+25B6 are missing from pygame's built-in font, and that
    font is what the browser build falls back to, so a typed glyph renders as
    an empty box there.

    Set ``glyph`` to ``"menu"``, ``"pause"``, or ``"play"``; anything else
    falls back to drawing ``label`` as text.
    """

    def __init__(self, rect, label: str, action: str, glyph: str = "",
                 **kwargs):
        super().__init__(rect, label, action, **kwargs)
        self.glyph = glyph

    def draw(self, surface: pygame.Surface) -> None:
        """Render the button with its glyph or label centred."""
        fill, edge, text_colour = self.palette()
        face = self.body_rect()
        pygame.draw.rect(surface, _mix(WOOD_DARK, (0, 0, 0), 0.25),
                         self.rect.move(0, LIFT), border_radius=8)
        pygame.draw.rect(surface, fill, face, border_radius=8)
        pygame.draw.rect(surface, edge, face, 3, border_radius=8)

        if self.glyph:
            _draw_glyph(surface, self.glyph, face.center, text_colour)
            return

        font = assets.font(self.size, bold=True)
        label = font.render(self.label, True, text_colour)
        surface.blit(label, label.get_rect(center=face.center))


class RoundIconButton(Button):
    """A glossy circular control, as used for speed, pause, and the menu.

    Hit-testing still uses the bounding rect, which is close enough for a
    circle this size and keeps the click routing identical to every other
    button.
    """

    def __init__(self, rect, label: str, action: str, glyph: str = "",
                 face=None, dark=None, **kwargs):
        super().__init__(rect, label, action, **kwargs)
        self.glyph = glyph
        self.face = face or BUTTON_BLUE
        self.dark = dark or BUTTON_BLUE_DARK

    def draw(self, surface: pygame.Surface) -> None:
        """Render the circular button and its glyph."""
        radius = min(self.rect.width, self.rect.height) // 2
        centre = self.rect.center
        chrome.round_button(surface, centre, radius, self.face, self.dark,
                            pressed=self.hovered, enabled=self.enabled)

        ink = TEXT_WHITE if self.enabled else (206, 206, 206)
        c_y = centre[1] + (2 if self.hovered else 0)
        if self.glyph:
            _draw_glyph(surface, self.glyph, (centre[0], c_y), ink)
        else:
            label = chrome.outlined_text(self.label, self.size, ink,
                                         thickness=2)
            surface.blit(label, label.get_rect(center=(centre[0], c_y)))


def _draw_glyph(surface: pygame.Surface, glyph: str,
                centre: tuple[int, int], colour) -> None:
    """Draw one of the built-in control icons."""
    c_x, c_y = centre
    if glyph == "menu":
        for i in (-7, 0, 7):
            pygame.draw.rect(surface, colour, (c_x - 9, c_y + i - 2, 18, 4),
                             border_radius=2)
    elif glyph == "pause":
        pygame.draw.rect(surface, colour, (c_x - 7, c_y - 8, 5, 16),
                         border_radius=2)
        pygame.draw.rect(surface, colour, (c_x + 2, c_y - 8, 5, 16),
                         border_radius=2)
    elif glyph == "play":
        pygame.draw.polygon(surface, colour, [
            (c_x - 6, c_y - 9), (c_x + 9, c_y), (c_x - 6, c_y + 9),
        ])


class Slider:
    """A horizontal value slider in the range ``[0, 1]``.

    Attributes:
        rect: Track area.
        value: Current value.
        action: Identifier used by the owning screen.
        dragging: True while the handle is held.
    """

    def __init__(self, rect, value: float, action: str):
        self.rect = pygame.Rect(rect)
        self.value = max(0.0, min(1.0, value))
        self.action = action
        self.dragging = False

    def hit(self, pos: tuple[int, int]) -> bool:
        """Begin dragging if ``pos`` is on the track, and jump to that value."""
        grab = self.rect.inflate(0, 22)
        if grab.collidepoint(pos):
            self.dragging = True
            self.set_from_x(pos[0])
            return True
        return False

    def set_from_x(self, x: int) -> None:
        """Set the value from a screen x coordinate."""
        self.value = max(0.0, min(1.0, (x - self.rect.x) / max(1, self.rect.width)))

    def release(self) -> None:
        """Stop dragging."""
        self.dragging = False

    def draw(self, surface: pygame.Surface) -> None:
        """Render the track and handle."""
        track = pygame.Rect(self.rect.x, self.rect.centery - 5,
                            self.rect.width, 10)
        progress_bar(surface, track, self.value)
        handle_x = self.rect.x + int(self.rect.width * self.value)
        centre = (handle_x, self.rect.centery)
        pygame.draw.circle(surface, WOOD_DARK, (centre[0], centre[1] + 2), 11)
        pygame.draw.circle(surface, PAPER, centre, 11)
        pygame.draw.circle(surface, WOOD, centre, 11, 3)


def tooltip(surface: pygame.Surface, lines: list[tuple[str, tuple[int, int, int]]],
            anchor: tuple[int, int], bounds: pygame.Rect,
            width: int = 260) -> None:
    """Draw a bordered tooltip, nudged to stay inside ``bounds``.

    Args:
        surface: Target surface.
        lines: ``(text, colour)`` pairs, drawn top to bottom.
        anchor: Preferred top-left corner.
        bounds: Region the tooltip must stay within.
        width: Tooltip width in pixels.
    """
    if not lines:
        return

    line_h = 19
    height = 16 + line_h * len(lines)
    rect = pygame.Rect(anchor[0], anchor[1], width, height)

    if rect.right > bounds.right - 6:
        rect.right = bounds.right - 6
    if rect.left < bounds.left + 6:
        rect.left = bounds.left + 6
    if rect.bottom > bounds.bottom - 6:
        rect.bottom = bounds.bottom - 6
    if rect.top < bounds.top + 6:
        rect.top = bounds.top + 6

    raised_panel(surface, rect, PAPER, WOOD, radius=8)
    for i, (text, colour) in enumerate(lines):
        draw_text(surface, text, (rect.x + 11, rect.y + 8 + i * line_h),
                  15, colour)


def dim(surface: pygame.Surface, alpha: int = 170,
        colour: tuple[int, int, int] = (36, 22, 12)) -> None:
    """Darken an entire surface, used behind modal screens."""
    layer = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    layer.fill((*colour, alpha))
    surface.blit(layer, (0, 0))


def money_colour(affordable: bool) -> tuple[int, int, int]:
    """Colour for a price label, based on whether the player can pay it."""
    return INK if affordable else BERRY


def _mix(a: tuple[int, int, int], b: tuple[int, int, int],
         amount: float) -> tuple[int, int, int]:
    """Blend two colours, ``amount`` of ``b`` into ``a``."""
    return tuple(int(x + (y - x) * amount) for x, y in zip(a, b))
