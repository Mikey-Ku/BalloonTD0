"""
The in-game heads-up display.

Covers the sidebar -- stats, tower shop, the selected-tower inspector, and the
run controls -- plus the placement preview drawn over the map.

The original UI drew a tower shop directly on top of the playfield, hid it
behind a collapse toggle, and showed a range circle whose radius was a
hardcoded number that did not match the tower's actual range. Here the sidebar
has its own space, and every number shown is read from the live tower.
"""

from __future__ import annotations

import math

import pygame

from ..balloons import ENERGY, EXPLOSIVE, SHARP
from ..config import (
    BAD, BERRY, BUTTON_RED, BUTTON_RED_DARK, INK, INK_SOFT, LEAF_DARK, MAP_H,
    MAP_W, MONEY, PAPER, RANGE_BAD, RANGE_OK, SCREEN_H, SIDEBAR_W, SUN,
    TEXT_GOLD, TEXT_WHITE, WOOD, WOOD_FACE, WOOD_SHADE,
)
from ..game import Run, tower_sprite
from ..towers import FARM, PULSE, Tower
from ..towers import KINDS as TOWER_KINDS
from ..towers import TOWER_ORDER
from .. import sprites
from . import chrome
from .widgets import (
    Button, CENTER, RIGHT, RoundIconButton, draw_text, panel, progress_bar,
    raised_panel, tooltip,
)

SIDEBAR_X = MAP_W
PAD = 10

#: Tower rack cell geometry.
CELL_GAP = 8
CELL_H = 72

DAMAGE_LABELS = {
    SHARP: "Sharp",
    EXPLOSIVE: "Explosive",
    ENERGY: "Energy",
    "normal": "Normal",
}


class Hud:
    """Sidebar and map overlay for an active run.

    Attributes:
        run: The run being displayed.
        shop_selection: Tower key currently armed for placement, if any.
        selected: Tower currently inspected, if any.
    """

    def __init__(self, run: Run):
        self.run = run
        self.shop_selection: str | None = None
        self.selected = None
        self.hover_shop: str | None = None
        self.mouse = (0, 0)
        self.message = ""
        self.message_timer = 0.0
        self.detail_scroll = 0.0
        self._detail_overflow = 0.0

        self.shop_buttons: list[Button] = []
        self.control_buttons: list[Button] = []
        self.panel_buttons: list[Button] = []
        self._build_static()

    # -- layout -----------------------------------------------------------

    def _build_static(self) -> None:
        """Create the shop rack and the always-present run controls.

        The sidebar is laid out as a shelf unit: a stat plaque, a round strip,
        a rack of recessed cubbies holding the towers, a detail panel, and a
        row of controls along the bottom.
        """
        self.frame_rect = pygame.Rect(SIDEBAR_X, 0, SIDEBAR_W, SCREEN_H)
        self.stats_rect = pygame.Rect(SIDEBAR_X + 8, 8, SIDEBAR_W - 16, 84)
        self.round_rect = pygame.Rect(SIDEBAR_X + 8, 98, SIDEBAR_W - 16, 32)
        self.rack_rect = pygame.Rect(SIDEBAR_X + 8, 136, SIDEBAR_W - 16, 328)
        self.detail_rect = pygame.Rect(SIDEBAR_X + 8, 472, SIDEBAR_W - 16, 172)

        cell_w = (self.rack_rect.width - CELL_GAP * 3) // 2
        for i, key in enumerate(TOWER_ORDER):
            kind = TOWER_KINDS[key]
            col, row = i % 2, i // 2
            rect = pygame.Rect(
                self.rack_rect.x + CELL_GAP + col * (cell_w + CELL_GAP),
                self.rack_rect.y + CELL_GAP + row * (CELL_H + CELL_GAP),
                cell_w, CELL_H,
            )
            self.shop_buttons.append(
                Button(rect, kind.label, f"buy:{key}", accent=kind.colour,
                       size=15, draw_label=False)
            )

        # Controls: a wide wooden Start plate, then three glossy round
        # buttons. The menu button used to sit in the top-right corner, where
        # it covered the lives counter.
        bottom = SCREEN_H - 64
        dia, gap = 52, 8
        start_w = SIDEBAR_W - 16 - dia * 3 - gap * 3
        x = SIDEBAR_X + 8

        self.start_button = Button(
            (x, bottom + 2, start_w, 48), "Start Round", "start", size=17
        )
        x += start_w + gap
        self.speed_button = RoundIconButton(
            (x, bottom, dia, dia), "1x", "speed", size=17
        )
        x += dia + gap
        self.pause_button = RoundIconButton(
            (x, bottom, dia, dia), "Pause", "pause", glyph="pause", size=17
        )
        x += dia + gap
        self.menu_button = RoundIconButton(
            (x, bottom, dia, dia), "Menu", "menu", glyph="menu", size=17,
            face=BUTTON_RED, dark=BUTTON_RED_DARK,
        )
        self.control_buttons = [
            self.start_button, self.speed_button, self.pause_button,
            self.menu_button,
        ]

    def _build_panel_buttons(self) -> list[Button]:
        """Create buttons for the selected-tower inspector."""
        if self.selected is None:
            return []

        tower = self.selected
        top = self.rack_rect.y + 206
        width = self.rack_rect.width
        out: list[Button] = []

        for path in (0, 1):
            upgrade = tower.next_upgrade(path)
            cost = tower.upgrade_cost(path)
            rect = pygame.Rect(self.rack_rect.x, top + path * 62, width, 56)

            if upgrade is None:
                button = Button(rect, "Path maxed", f"none:{path}", size=15)
                button.enabled = False
            elif cost is None:
                button = Button(rect, upgrade.name, f"none:{path}",
                                "locked by the other path", size=15)
                button.enabled = False
            else:
                button = Button(rect, upgrade.name, f"upgrade:{path}",
                                f"${cost:,}", size=15)
                button.enabled = self.run.money >= cost
            out.append(button)

        target_rect = pygame.Rect(self.rack_rect.x, top + 130, width - 106, 40)
        out.append(Button(target_rect, f"Target: {tower.targeting}",
                          "targeting", size=15))
        sell_rect = pygame.Rect(self.rack_rect.right - 100, top + 130, 100, 40)
        out.append(Button(sell_rect, f"Sell ${tower.sell_value:,}", "sell",
                          accent=BAD, size=14))
        return out

    # -- state ------------------------------------------------------------

    def notify(self, text: str) -> None:
        """Show a transient message under the stats bar."""
        self.message = text
        self.message_timer = 2.2

    def update(self, dt: float, mouse: tuple[int, int]) -> None:
        """Refresh hover states and time out the transient message."""
        self.mouse = mouse
        self.message_timer = max(0.0, self.message_timer - dt)

        if self.selected is not None and self.selected not in self.run.towers:
            self.selected = None

        self.panel_buttons = self._build_panel_buttons()

        previous_hover = self.hover_shop
        self.hover_shop = None
        for button, key in zip(self.shop_buttons, TOWER_ORDER):
            cost = self.run.tower_cost(key)
            button.enabled = self.run.money >= cost
            button.selected = self.shop_selection == key
            button.update_hover(mouse)
            if button.rect.collidepoint(mouse):
                self.hover_shop = key

        if self.hover_shop != previous_hover:
            self.detail_scroll = 0.0

        self.start_button.label = (
            "Round in progress" if self.run.round_active else "Start Round"
        )
        self.start_button.enabled = not self.run.round_active
        self.speed_button.label = f"{self.run.speed}x"
        self.pause_button.glyph = "play" if self.run.paused else "pause"

        for button in self.control_buttons + self.panel_buttons:
            button.update_hover(mouse)

    # -- input ------------------------------------------------------------

    def handle_click(self, pos: tuple[int, int], button: int = 1) -> str | None:
        """Route a mouse click. Returns an app-level action, if any.

        Args:
            pos: Cursor position in screen coordinates.
            button: Mouse button index; 3 (right) cancels placement.

        Returns:
            ``"menu"`` to open the pause menu, otherwise ``None``.
        """
        if button == 3:
            self.shop_selection = None
            self.selected = None
            return None

        if pos[0] < MAP_W:
            return self._click_map(pos)

        for widget in self.control_buttons:
            action = widget.hit(pos)
            if action == "start":
                if not self.run.start_round():
                    self.notify("Round already running")
                return None
            if action == "speed":
                self.run.toggle_speed()
                return None
            if action == "pause":
                self.run.paused = not self.run.paused
                return None
            if action == "menu":
                return "menu"

        for widget in self.panel_buttons:
            action = widget.hit(pos)
            if action is None:
                continue
            if action.startswith("upgrade:"):
                path = int(action.split(":")[1])
                if not self.run.upgrade_tower(self.selected, path):
                    self.notify("Not enough money")
                return None
            if action == "targeting":
                self.selected.cycle_targeting()
                return None
            if action == "sell":
                self.run.sell_tower(self.selected)
                self.selected = None
                return None

        for widget in self.shop_buttons:
            action = widget.hit(pos)
            if action and action.startswith("buy:"):
                key = action.split(":")[1]
                self.shop_selection = None if self.shop_selection == key else key
                self.selected = None
                return None

        return None

    def _click_map(self, pos: tuple[int, int]) -> None:
        """Handle a click on the playfield: place a tower or select one."""
        if self.shop_selection:
            placed = self.run.place_tower(self.shop_selection, pos[0], pos[1])
            if placed is None:
                if self.run.money < self.run.tower_cost(self.shop_selection):
                    self.notify("Not enough money")
                else:
                    self.notify("Cannot build there")
            else:
                self.selected = placed
                # Keep the type armed so several can be placed in a row, but
                # drop it once the next one is unaffordable.
                if self.run.money < self.run.tower_cost(self.shop_selection):
                    self.shop_selection = None
            return None

        self.selected = self.run.tower_at(pos[0], pos[1])
        return None

    def handle_wheel(self, amount: int) -> None:
        """Scroll the detail panel when the cursor is over it."""
        if not self.detail_rect.collidepoint(self.mouse):
            return
        self.detail_scroll = max(
            0.0, min(self._detail_overflow, self.detail_scroll - amount * 28)
        )

    def handle_key(self, key: int) -> str | None:
        """Route a keyboard shortcut. Returns an app-level action, if any."""
        if pygame.K_1 <= key <= pygame.K_7:
            index = key - pygame.K_1
            if index < len(TOWER_ORDER):
                chosen = TOWER_ORDER[index]
                self.shop_selection = None if self.shop_selection == chosen else chosen
                self.selected = None
            return None
        if key == pygame.K_ESCAPE:
            if self.shop_selection or self.selected:
                self.shop_selection = None
                self.selected = None
                return None
            return "menu"
        if key == pygame.K_SPACE:
            if not self.run.start_round():
                self.notify("Round already running")
            return None
        if key == pygame.K_p:
            self.run.paused = not self.run.paused
            return None
        if key == pygame.K_f:
            self.run.toggle_speed()
            return None
        if key == pygame.K_a:
            self.run.auto_start = not self.run.auto_start
            self.notify(f"Auto-start {'on' if self.run.auto_start else 'off'}")
            return None
        if self.selected is not None:
            if key == pygame.K_TAB:
                self.selected.cycle_targeting()
            elif key == pygame.K_u:
                if not self.run.upgrade_tower(self.selected, 0):
                    self.notify("Cannot upgrade")
            elif key == pygame.K_i:
                if not self.run.upgrade_tower(self.selected, 1):
                    self.notify("Cannot upgrade")
            elif key in (pygame.K_BACKSPACE, pygame.K_DELETE):
                self.run.sell_tower(self.selected)
                self.selected = None
        return None

    # -- drawing ----------------------------------------------------------

    def draw_map_overlay(self, surface: pygame.Surface) -> None:
        """Draw range circles and the placement ghost over the playfield."""
        if self.selected is not None and self.selected.kind.mode != FARM:
            self._draw_range(surface, self.selected.x, self.selected.y,
                             self.selected.range, (120, 180, 255))
            pygame.draw.circle(surface, (255, 226, 130),
                               (int(self.selected.x), int(self.selected.y)), 22, 2)

        if not self.shop_selection:
            return

        m_x, m_y = self.mouse
        if m_x >= MAP_W:
            return

        kind = TOWER_KINDS[self.shop_selection]
        valid = self.run.can_place(self.shop_selection, m_x, m_y)
        affordable = self.run.money >= self.run.tower_cost(self.shop_selection)
        ok = valid and affordable

        if kind.mode != FARM:
            self._draw_range(surface, m_x, m_y, kind.range,
                             RANGE_OK if ok else RANGE_BAD)

        ghost = tower_sprite_for_kind(self.shop_selection)
        ghost = ghost.copy()
        ghost.set_alpha(190 if ok else 90)
        surface.blit(ghost, ghost.get_rect(center=(m_x, m_y)))

        if not ok:
            pygame.draw.line(surface, RANGE_BAD, (m_x - 13, m_y - 13),
                             (m_x + 13, m_y + 13), 3)
            pygame.draw.line(surface, RANGE_BAD, (m_x + 13, m_y - 13),
                             (m_x - 13, m_y + 13), 3)

    @staticmethod
    def _draw_range(surface: pygame.Surface, x: float, y: float,
                    radius: float, colour) -> None:
        """Draw a translucent range circle, clipped to the map."""
        radius = min(radius, math.hypot(MAP_W, MAP_H))
        size = int(radius * 2) + 4
        layer = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.circle(layer, (*colour, 34), (size // 2, size // 2), int(radius))
        pygame.draw.circle(layer, (*colour, 170), (size // 2, size // 2),
                           int(radius), 2)
        surface.blit(layer, (int(x) - size // 2, int(y) - size // 2))

    def draw(self, surface: pygame.Surface) -> None:
        """Draw the whole sidebar as a wooden cabinet."""
        chrome.beveled(surface, self.frame_rect, WOOD_FACE, radius=0, depth=6)

        self._draw_stats(surface)
        self._draw_round_strip(surface)
        if self.selected is not None:
            self._draw_tower_panel(surface)
        else:
            self._draw_shop(surface)

        for widget in self.control_buttons:
            widget.draw(surface)

        if self.run.auto_start:
            chrome.blit_outlined(surface, "AUTO",
                                 (SIDEBAR_X + 12, SCREEN_H - 82), 13, SUN)

        self._draw_hover_tooltip(surface)

    def _draw_stats(self, surface: pygame.Surface) -> None:
        """Draw the money and lives plaque with icons and outlined numerals."""
        run = self.run
        card = self.stats_rect
        chrome.beveled(surface, card, WOOD_FACE, radius=10, depth=4)

        chrome.coin_icon(surface, (card.x + 28, card.y + 24), 14)
        chrome.blit_outlined(surface, f"{run.money:,}",
                             (card.x + 52, card.y + 8), 29, TEXT_GOLD)

        chrome.heart_icon(surface, (card.x + 28, card.y + 56), 24)
        chrome.blit_outlined(surface, f"{run.lives}",
                             (card.x + 52, card.y + 42), 29, TEXT_WHITE)

        lives_bar = pygame.Rect(card.x + 52, card.y + 70, card.width - 66, 7)
        progress_bar(surface, lives_bar, run.lives / max(1, run.max_lives),
                     fill=BERRY, back=WOOD_SHADE)

        if self.message_timer > 0:
            banner = pygame.Rect(card.x, card.bottom - 22, card.width, 22)
            panel(surface, banner, BERRY, WOOD_SHADE, radius=6, width=2)
            draw_text(surface, self.message, (banner.centerx, banner.y + 3), 14,
                      PAPER, bold=True, align=CENTER)

    def _draw_round_strip(self, surface: pygame.Surface) -> None:
        """Draw the round counter and next-wave summary on a wooden strip."""
        run = self.run
        strip = self.round_rect
        chrome.plank_strip(surface, strip)

        chrome.blit_outlined(surface, f"Round {run.round_number}/{run.max_rounds}",
                             (strip.x + 10, strip.y + 6), 17, TEXT_WHITE)
        chrome.blit_outlined(surface, run.wave.describe()[:28],
                             (strip.right - 10, strip.y + 8), 14, TEXT_GOLD,
                             align=RIGHT)

        if run.round_active:
            bar = pygame.Rect(strip.x + 4, strip.bottom - 6, strip.width - 8, 4)
            progress_bar(surface, bar, run.round_progress, back=WOOD_SHADE)

    def _draw_shop(self, surface: pygame.Surface) -> None:
        """Draw the tower rack and details for the hovered entry.

        Each tower sits in a recessed cubby rather than on a flat button, so
        the rack reads as a shelf unit built into the sidebar.
        """
        chrome.beveled(surface, self.rack_rect, WOOD_SHADE, radius=10,
                       depth=4, raised=False)

        for widget, key in zip(self.shop_buttons, TOWER_ORDER):
            kind = TOWER_KINDS[key]
            cost = self.run.tower_cost(key)
            cell = widget.rect
            chrome.cubby(surface, cell)

            if widget.selected:
                pygame.draw.rect(surface, TEXT_GOLD, cell, 3, border_radius=8)
            elif widget.hovered:
                pygame.draw.rect(surface, chrome.mix(TEXT_GOLD, WOOD_FACE, 0.5),
                                 cell, 2, border_radius=8)

            icon = tower_sprite_for_kind(key)
            if not widget.enabled:
                icon = icon.copy()
                icon.set_alpha(95)
            surface.blit(icon, (cell.x + 8, cell.centery - ICON_SIZE // 2))

            name_colour = TEXT_WHITE if widget.enabled else (166, 150, 132)
            cost_colour = TEXT_GOLD if widget.enabled else (170, 132, 88)
            # Full label, not a stripped one: dropping "Monkey" left the rack
            # reading "Dart / Sniper / Tack Shooter / Banana Farm".
            chrome.blit_outlined(surface, kind.label,
                                 (cell.x + 60, cell.y + 14), 15, name_colour)
            chrome.blit_outlined(surface, f"${cost:,}",
                                 (cell.x + 60, cell.y + 38), 17, cost_colour)

        info = self.detail_rect
        raised_panel(surface, info)

        key = self.hover_shop or self.shop_selection
        if key is None:
            draw_text(surface, "Build a defence",
                      (info.x + 12, info.y + 10), 16, INK, bold=True)
            lines = [
                "Pick a tower, then click the map.",
                "",
                "1-7  select tower",
                "SPACE  start round",
                "F  fast-forward      P  pause",
                "A  auto-start        ESC  cancel",
                "",
                "Click a placed tower to upgrade it.",
            ]
            for i, line in enumerate(lines):
                draw_text(surface, line, (info.x + 12, info.y + 34 + i * 17),
                          14, INK_SOFT)
            return

        self._draw_kind_details(surface, info, key)

    def _draw_kind_details(self, surface: pygame.Surface, info: pygame.Rect,
                           key: str) -> None:
        """Describe an unpurchased tower type, scrolling if it does not fit.

        Tower descriptions vary a lot in length -- the Bomb Shooter's blurb
        plus six stat rows plus two upgrade paths overran the panel and spilled
        across the sidebar. Rendering to a tall surface and showing a window
        onto it keeps everything readable at full size instead of forcing the
        text smaller to fit the worst case.
        """
        kind = TOWER_KINDS[key]
        pad = 12
        width = info.width - pad * 2
        page = pygame.Surface((width, 900), pygame.SRCALPHA)
        page.fill(PAPER)

        draw_text(page, kind.label, (0, 0), 17, INK, bold=True)

        y = 24
        for line in _wrap(kind.blurb, 38):
            draw_text(page, line, (0, y), 14, INK_SOFT)
            y += 17

        y += 6
        for label, value in _kind_stats(kind):
            draw_text(page, label, (0, y), 14, INK_SOFT)
            draw_text(page, value, (width, y), 14, INK, bold=True, align=RIGHT)
            y += 18

        y += 8
        for path in (0, 1):
            draw_text(page, f"Path {path + 1}", (0, y), 13, LEAF_DARK, bold=True)
            y += 17
            for step, upgrade in enumerate(kind.paths[path], 1):
                draw_text(page, f"{step}. {upgrade.name}", (0, y), 13, INK)
                y += 16
                for line in _wrap(upgrade.desc, 40):
                    draw_text(page, line, (10, y), 12, INK_SOFT)
                    y += 14
            y += 8

        self._blit_scrolled(surface, info, page, y, pad)

    def _blit_scrolled(self, surface: pygame.Surface, info: pygame.Rect,
                       page: pygame.Surface, content_h: int, pad: int) -> None:
        """Show a scrollable window onto ``page`` inside ``info``."""
        view_h = info.height - pad * 2
        self._detail_overflow = max(0.0, content_h - view_h)
        self.detail_scroll = min(self.detail_scroll, self._detail_overflow)
        offset = int(self.detail_scroll)

        surface.blit(page, (info.x + pad, info.y + pad),
                     pygame.Rect(0, offset, page.get_width(), view_h))

        if self._detail_overflow <= 0:
            return

        # Track and thumb, plus a fade at whichever edge has more to show.
        track = pygame.Rect(info.right - 8, info.y + pad, 4, view_h)
        pygame.draw.rect(surface, chrome.mix(PAPER, WOOD_SHADE, 0.25), track,
                         border_radius=2)
        span = view_h / (content_h or 1)
        thumb_h = max(24, int(view_h * span))
        travel = view_h - thumb_h
        thumb_y = track.y + int(travel * (offset / self._detail_overflow))
        pygame.draw.rect(surface, WOOD, (track.x, thumb_y, 4, thumb_h),
                         border_radius=2)

        for at_top, edge_y in ((True, info.y + pad), (False, info.bottom - pad - 12)):
            showing = offset > 2 if at_top else offset < self._detail_overflow - 2
            if not showing:
                continue
            fade = pygame.Surface((info.width - pad * 2 - 6, 12), pygame.SRCALPHA)
            for i in range(12):
                a = int(190 * ((12 - i) / 12 if at_top else (i + 1) / 12))
                pygame.draw.line(fade, (*PAPER, a), (0, i),
                                 (fade.get_width(), i))
            surface.blit(fade, (info.x + pad, edge_y))

    def _draw_tower_panel(self, surface: pygame.Surface) -> None:
        """Draw the inspector for the currently selected tower."""
        tower = self.selected
        top = pygame.Rect(self.rack_rect.x, self.rack_rect.y,
                          self.rack_rect.width, 196)
        raised_panel(surface, top)

        icon = tower_sprite_for_kind(tower.kind.key)
        surface.blit(icon, (top.x + 11, top.y + 9))
        draw_text(surface, tower.kind.label, (top.x + 57, top.y + 10), 17, INK,
                  bold=True)
        draw_text(surface, f"Tier {tower.tier_label}", (top.x + 57, top.y + 30),
                  13, LEAF_DARK, bold=True)

        y = top.y + 56
        for label, value in _tower_stats(tower):
            draw_text(surface, label, (top.x + 12, y), 13, INK_SOFT)
            draw_text(surface, value, (top.right - 12, y), 13, INK,
                      bold=True, align=RIGHT)
            y += 17

        draw_text(surface, f"Pops {tower.pops:,}   Earned ${tower.cash_earned:,}",
                  (top.x + 12, top.bottom - 22), 13, INK_SOFT)

        for widget in self.panel_buttons:
            widget.draw(surface)

        for path in (0, 1):
            upgrade = tower.next_upgrade(path)
            if upgrade is None:
                continue
            face = self.panel_buttons[path].body_rect()
            _, _, text_colour = self.panel_buttons[path].palette()
            for line in _wrap(upgrade.desc, 42)[:1]:
                draw_text(surface, line, (face.centerx, face.bottom - 18), 12,
                          text_colour, align=CENTER)

        self._draw_path_overview(surface, tower)

        chrome.blit_outlined(
            surface, "ESC deselect - TAB target - U / I upgrade",
            (SIDEBAR_X + SIDEBAR_W // 2, self.detail_rect.bottom - 4), 13,
            TEXT_WHITE, align=CENTER, thickness=2)

    def _draw_path_overview(self, surface: pygame.Surface, tower: Tower) -> None:
        """Show both upgrade paths with the purchased tiers filled in.

        Occupies the space below the action buttons, which was otherwise a
        blank stretch of sidebar, and makes the cross-path rule visible: once
        one path reaches its final tier the other is capped, and that shows
        here as greyed pips.
        """
        box = pygame.Rect(self.rack_rect.x, self.rack_rect.y + 382,
                          self.rack_rect.width, 116)
        raised_panel(surface, box)

        draw_text(surface, "Upgrade paths", (box.x + 12, box.y + 8), 14, INK,
                  bold=True)

        for path in (0, 1):
            top = box.y + 30 + path * 43
            tier = tower.tiers[path]
            available = tower.can_upgrade(path)

            draw_text(surface, f"Path {path + 1}", (box.x + 12, top), 13,
                      LEAF_DARK, bold=True)

            for step in range(len(tower.kind.paths[path])):
                centre = (box.x + 84 + step * 22, top + 7)
                if step < tier:
                    pygame.draw.circle(surface, LEAF_DARK, centre, 8)
                    pygame.draw.circle(surface, INK, centre, 8, 2)
                elif step == tier and available:
                    pygame.draw.circle(surface, PAPER, centre, 8)
                    pygame.draw.circle(surface, LEAF_DARK, centre, 8, 2)
                else:
                    pygame.draw.circle(surface, (206, 196, 176), centre, 7)
                    pygame.draw.circle(surface, INK_SOFT, centre, 7, 1)

            nxt = tower.next_upgrade(path)
            if nxt is None:
                caption = "complete"
            elif not available:
                caption = "capped by the other path"
            else:
                caption = nxt.name
            draw_text(surface, caption[:32], (box.x + 12, top + 21), 13,
                      INK_SOFT)

    def _draw_hover_tooltip(self, surface: pygame.Surface) -> None:
        """Show a compact tooltip when hovering a placed tower on the map."""
        if self.mouse[0] >= MAP_W or self.shop_selection:
            return
        tower = self.run.tower_at(*self.mouse)
        if tower is None or tower is self.selected:
            return

        lines = [(f"{tower.kind.label}  ({tower.tier_label})", INK)]
        lines += [(f"{label} {value}", INK_SOFT)
                  for label, value in _tower_stats(tower)]
        lines.append((f"Sell ${tower.sell_value:,}", MONEY))
        tooltip(surface, lines, (self.mouse[0] + 16, self.mouse[1] + 12),
                pygame.Rect(0, 0, MAP_W, MAP_H), width=220)


#: Size of the tower icons in the shop rack.
ICON_SIZE = 46


def tower_sprite_for_kind(key: str) -> pygame.Surface:
    """Return the shop-rack icon for a tower type.

    Prefers the portrait logo; falls back to the overhead, then to the same
    drawn glyph the map uses.
    """
    art = sprites.character(key, sprites.LOGO, ICON_SIZE)
    if art is not None:
        return art
    return tower_sprite(_probe(key))


_PROBES: dict[str, Tower] = {}


def _probe(key: str) -> Tower:
    """A throwaway tower instance, used only to render a glyph fallback."""
    probe = _PROBES.get(key)
    if probe is None:
        probe = Tower(TOWER_KINDS[key], 0, 0)
        _PROBES[key] = probe
    return probe


def _kind_stats(kind) -> list[tuple[str, str]]:
    """Summarise an unpurchased tower type for the shop panel."""
    if kind.mode == FARM:
        return [("Income / round", f"${kind.income:,}")]
    return [
        ("Damage", str(kind.damage)),
        ("Type", DAMAGE_LABELS.get(kind.damage_type, kind.damage_type)),
        ("Range", "map-wide" if kind.range > 2000 else str(int(kind.range))),
        ("Rate", f"{kind.rate:.2f}/s"),
        ("Camo", "yes" if kind.camo else "no"),
    ]


def _tower_stats(tower) -> list[tuple[str, str]]:
    """Summarise a placed tower's live stats."""
    if tower.kind.mode == FARM:
        return [("Income / round", f"${tower.income:,}")]

    rows = [
        ("Damage", str(tower.damage)),
        ("Type", DAMAGE_LABELS.get(tower.damage_type, tower.damage_type)),
        ("Range", "map-wide" if tower.range > 2000 else str(int(tower.range))),
        ("Rate", f"{tower.rate:.2f}/s"),
    ]
    if tower.kind.mode != PULSE:
        rows.append(("Pierce", str(tower.pierce)))
    if tower.splash:
        rows.append(("Blast", str(int(tower.splash))))
    if tower.moab_bonus:
        rows.append(("vs MOAB", f"+{tower.moab_bonus}"))
    if tower.slow_factor < 1.0:
        rows.append(("Slow", f"{int(tower.slow_factor * 100)}% for {tower.slow_time:.0f}s"))
    rows.append(("Camo", "yes" if tower.camo else "no"))
    if tower.income:
        rows.append(("Income", f"${tower.income:,}"))
    return rows


def _wrap(text: str, width: int) -> list[str]:
    """Greedy word wrap to a character width."""
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if len(candidate) <= width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines
