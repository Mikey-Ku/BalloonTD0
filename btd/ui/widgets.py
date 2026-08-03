"""
Reusable interface primitives.

The original UI drew text outlines by blitting the same string up to nine
times in a nested loop at every call site, and every button rolled its own
rectangle-and-label drawing. These helpers centralise both so the interface
stays visually consistent and the screen code stays readable.
"""

from __future__ import annotations

import pygame

from .. import assets
from ..config import (
    ACCENT, ACCENT_DIM, BAD, INK, MUTED, PANEL, PANEL_EDGE, PANEL_LIGHT, PAPER,
)

LEFT = "left"
CENTER = "center"
RIGHT = "right"


def draw_text(surface: pygame.Surface, text: str, pos: tuple[int, int],
              size: int = 18, colour=PAPER, bold: bool = False,
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
        shadow: Draw a one-pixel dark offset behind the text, for legibility
            over busy map art.

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
        dark = font.render(text, True, (0, 0, 0))
        dark.set_alpha(150)
        surface.blit(dark, (rect.x + 1, rect.y + 1))

    surface.blit(label, rect)
    return rect


def panel(surface: pygame.Surface, rect: pygame.Rect, fill=PANEL,
          edge=PANEL_EDGE, radius: int = 8, width: int = 1) -> None:
    """Draw a rounded panel with a subtle border."""
    pygame.draw.rect(surface, fill, rect, border_radius=radius)
    if width:
        pygame.draw.rect(surface, edge, rect, width, border_radius=radius)


def progress_bar(surface: pygame.Surface, rect: pygame.Rect, fraction: float,
                 fill=ACCENT, back=(28, 32, 42)) -> None:
    """Draw a horizontal progress bar clamped to ``[0, 1]``."""
    fraction = max(0.0, min(1.0, fraction))
    pygame.draw.rect(surface, back, rect, border_radius=rect.height // 2)
    if fraction > 0:
        inner = pygame.Rect(rect.x, rect.y, max(2, int(rect.width * fraction)),
                            rect.height)
        pygame.draw.rect(surface, fill, inner, border_radius=rect.height // 2)


class Button:
    """A clickable rectangle with a label.

    Attributes:
        rect: Screen area.
        label: Text drawn in the middle.
        action: Identifier returned by :meth:`hit` when clicked.
        enabled: Whether the button responds and draws at full strength.
        subtitle: Optional second line, e.g. a price.
        accent: Border and highlight colour.
        hovered: Updated by :meth:`update_hover`.
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
        # Shop entries draw their own icon and two-line text, so they ask the
        # button to render the frame only.
        self.draw_label = draw_label

    def update_hover(self, mouse_pos: tuple[int, int]) -> None:
        """Refresh the hover state from the current cursor position."""
        self.hovered = self.enabled and self.rect.collidepoint(mouse_pos)

    def hit(self, pos: tuple[int, int]) -> str | None:
        """Return this button's action if ``pos`` falls inside it."""
        if self.enabled and self.rect.collidepoint(pos):
            return self.action
        return None

    def draw(self, surface: pygame.Surface) -> None:
        """Render the button in its current state."""
        if not self.enabled:
            fill, edge, text_colour = (26, 29, 37), (44, 48, 60), (96, 102, 118)
        elif self.selected:
            fill, edge, text_colour = ACCENT_DIM, self.accent, PAPER
        elif self.hovered:
            fill, edge, text_colour = PANEL_LIGHT, self.accent, PAPER
        else:
            fill, edge, text_colour = PANEL, PANEL_EDGE, PAPER

        panel(surface, self.rect, fill, edge, radius=7,
              width=2 if (self.selected or self.hovered) else 1)

        if not self.draw_label:
            return

        if self.subtitle:
            draw_text(surface, self.label, (self.rect.centerx, self.rect.y + 7),
                      self.size, text_colour, bold=True, align=CENTER)
            draw_text(surface, self.subtitle,
                      (self.rect.centerx, self.rect.y + 8 + self.size),
                      self.size - 4,
                      text_colour if self.enabled else (92, 96, 110),
                      align=CENTER)
        else:
            font = assets.font(self.size, bold=True)
            label = font.render(self.label, True, text_colour)
            surface.blit(label, label.get_rect(center=self.rect.center))


class IconButton(Button):
    """A small square button that draws a glyph instead of a text label."""

    def draw(self, surface: pygame.Surface) -> None:
        """Render the button with its glyph centred."""
        fill = PANEL_LIGHT if self.hovered else PANEL
        edge = self.accent if (self.hovered or self.selected) else PANEL_EDGE
        panel(surface, self.rect, fill, edge, radius=6,
              width=2 if self.selected else 1)
        font = assets.font(self.size, bold=True)
        label = font.render(self.label, True, PAPER if self.enabled else MUTED)
        surface.blit(label, label.get_rect(center=self.rect.center))


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
        grab = self.rect.inflate(0, 16)
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
        track = pygame.Rect(self.rect.x, self.rect.centery - 3,
                            self.rect.width, 6)
        progress_bar(surface, track, self.value)
        handle_x = self.rect.x + int(self.rect.width * self.value)
        pygame.draw.circle(surface, PAPER, (handle_x, self.rect.centery), 8)
        pygame.draw.circle(surface, INK, (handle_x, self.rect.centery), 8, 2)


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
    height = 14 + line_h * len(lines)
    rect = pygame.Rect(anchor[0], anchor[1], width, height)

    if rect.right > bounds.right - 6:
        rect.right = bounds.right - 6
    if rect.left < bounds.left + 6:
        rect.left = bounds.left + 6
    if rect.bottom > bounds.bottom - 6:
        rect.bottom = bounds.bottom - 6
    if rect.top < bounds.top + 6:
        rect.top = bounds.top + 6

    shade = pygame.Surface(rect.size, pygame.SRCALPHA)
    shade.fill((10, 12, 18, 242))
    surface.blit(shade, rect.topleft)
    pygame.draw.rect(surface, PANEL_EDGE, rect, 1, border_radius=6)

    for i, (text, colour) in enumerate(lines):
        draw_text(surface, text, (rect.x + 10, rect.y + 7 + i * line_h),
                  15, colour)


def dim(surface: pygame.Surface, alpha: int = 170,
        colour: tuple[int, int, int] = (8, 10, 15)) -> None:
    """Darken an entire surface, used behind modal screens."""
    layer = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    layer.fill((*colour, alpha))
    surface.blit(layer, (0, 0))


def money_colour(affordable: bool) -> tuple[int, int, int]:
    """Colour for a price label, based on whether the player can pay it."""
    return PAPER if affordable else BAD
