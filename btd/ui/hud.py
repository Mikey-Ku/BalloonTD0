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
    BAD, BERRY, INK, INK_SOFT, LEAF_DARK, LIVES, MAP_H, MAP_W, MONEY, PAPER,
    RANGE_BAD, RANGE_OK, SCREEN_H, SIDEBAR_W, SUN, WOOD_DARK,
)
from ..game import Run, tower_sprite
from ..towers import FARM, PULSE, Tower
from ..towers import KINDS as TOWER_KINDS
from ..towers import TOWER_ORDER
from .widgets import (
    Button, IconButton, CENTER, RIGHT, draw_text, panel, progress_bar,
    raised_panel, tooltip, wood_backdrop,
)

SIDEBAR_X = MAP_W
PAD = 10

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

        self.shop_buttons: list[Button] = []
        self.control_buttons: list[Button] = []
        self.panel_buttons: list[Button] = []
        self._build_static()

    # -- layout -----------------------------------------------------------

    def _build_static(self) -> None:
        """Create the shop grid and the always-present run controls."""
        col_w = (SIDEBAR_W - PAD * 3) // 2
        for i, key in enumerate(TOWER_ORDER):
            kind = TOWER_KINDS[key]
            col, row = i % 2, i // 2
            rect = pygame.Rect(
                SIDEBAR_X + PAD + col * (col_w + PAD),
                112 + row * 62,
                col_w, 54,
            )
            self.shop_buttons.append(
                Button(rect, kind.label, f"buy:{key}", accent=kind.colour,
                       size=15, draw_label=False)
            )

        # All four run controls share the bottom row. The menu button used to
        # sit in the top-right corner, where it covered the lives counter.
        bottom = SCREEN_H - 60
        icon_w, gap = 46, 6
        usable = SIDEBAR_W - PAD * 2
        start_w = usable - icon_w * 3 - gap * 3
        x = SIDEBAR_X + PAD

        self.start_button = Button(
            (x, bottom, start_w, 48), "Start Round", "start", size=17
        )
        x += start_w + gap
        self.speed_button = IconButton(
            (x, bottom, icon_w, 48), "1x", "speed", size=17
        )
        x += icon_w + gap
        self.pause_button = IconButton(
            (x, bottom, icon_w, 48), "Pause", "pause", glyph="pause", size=17
        )
        x += icon_w + gap
        self.menu_button = IconButton(
            (x, bottom, icon_w, 48), "Menu", "menu", glyph="menu", size=17
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
        top = 372
        width = SIDEBAR_W - PAD * 2
        out: list[Button] = []

        for path in (0, 1):
            upgrade = tower.next_upgrade(path)
            cost = tower.upgrade_cost(path)
            rect = pygame.Rect(SIDEBAR_X + PAD, top + path * 60, width, 52)

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

        target_rect = pygame.Rect(SIDEBAR_X + PAD, top + 128, width - 108, 40)
        out.append(Button(target_rect, f"Target: {tower.targeting}",
                          "targeting", size=15))
        sell_rect = pygame.Rect(SIDEBAR_X + SIDEBAR_W - PAD - 98, top + 128, 98, 40)
        sell = Button(sell_rect, f"Sell ${tower.sell_value:,}", "sell",
                      accent=BAD, size=14)
        out.append(sell)
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

        self.hover_shop = None
        for button, key in zip(self.shop_buttons, TOWER_ORDER):
            cost = self.run.tower_cost(key)
            button.enabled = self.run.money >= cost
            button.selected = self.shop_selection == key
            button.update_hover(mouse)
            if button.rect.collidepoint(mouse):
                self.hover_shop = key

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
        """Draw the whole sidebar."""
        rect = pygame.Rect(SIDEBAR_X, 0, SIDEBAR_W, SCREEN_H)
        wood_backdrop(surface, rect)

        self._draw_stats(surface)
        if self.selected is not None:
            self._draw_tower_panel(surface)
        else:
            self._draw_shop(surface)

        for widget in self.control_buttons:
            widget.draw(surface)

        if self.run.auto_start:
            draw_text(surface, "AUTO", (SIDEBAR_X + PAD, SCREEN_H - 78), 13,
                      SUN, bold=True)

        self._draw_hover_tooltip(surface)

    def _draw_stats(self, surface: pygame.Surface) -> None:
        """Draw money, lives, round number, and round progress."""
        run = self.run
        card = pygame.Rect(SIDEBAR_X + PAD, 8, SIDEBAR_W - PAD * 2, 94)
        raised_panel(surface, card)

        draw_text(surface, f"${run.money:,}", (card.x + 12, card.y + 8), 26,
                  MONEY, bold=True)
        draw_text(surface, f"{run.lives}", (card.right - 12, card.y + 8), 26,
                  LIVES, bold=True, align=RIGHT)

        lives_bar = pygame.Rect(card.x + 12, card.y + 40, card.width - 24, 7)
        progress_bar(surface, lives_bar, run.lives / max(1, run.max_lives),
                     fill=BERRY)

        draw_text(surface, f"Round {run.round_number} / {run.max_rounds}",
                  (card.x + 12, card.y + 52), 16, INK, bold=True)
        draw_text(surface, run.wave.describe()[:42],
                  (card.x + 12, card.y + 71), 13, INK_SOFT)

        if run.round_active:
            bar = pygame.Rect(card.x + 12, card.bottom - 9, card.width - 24, 5)
            progress_bar(surface, bar, run.round_progress)

        if self.message_timer > 0:
            banner = pygame.Rect(SIDEBAR_X + PAD, 106, SIDEBAR_W - PAD * 2, 24)
            panel(surface, banner, BERRY, WOOD_DARK, radius=6, width=2)
            draw_text(surface, self.message, (banner.centerx, banner.y + 4), 15,
                      PAPER, bold=True, align=CENTER)

    def _draw_shop(self, surface: pygame.Surface) -> None:
        """Draw the tower shop grid and details for the hovered entry."""
        for widget, key in zip(self.shop_buttons, TOWER_ORDER):
            kind = TOWER_KINDS[key]
            cost = self.run.tower_cost(key)
            widget.draw(surface)
            face = widget.body_rect()

            icon = pygame.transform.smoothscale(tower_sprite_for_kind(key), (28, 28))
            if not widget.enabled:
                icon = icon.copy()
                icon.set_alpha(100)
            surface.blit(icon, (face.x + 8, face.y + 13))

            _, _, text_colour = widget.palette()
            draw_text(surface, kind.label, (face.x + 42, face.y + 8), 14,
                      text_colour, bold=True)
            draw_text(surface, f"${cost:,}", (face.x + 42, face.y + 28), 14,
                      MONEY if widget.enabled else text_colour)

        hint_y = 112 + ((len(TOWER_ORDER) + 1) // 2) * 62 + 8
        info = pygame.Rect(SIDEBAR_X + PAD, hint_y, SIDEBAR_W - PAD * 2,
                           SCREEN_H - 74 - hint_y)
        raised_panel(surface, info)

        key = self.hover_shop or self.shop_selection
        if key is None:
            draw_text(surface, "Build a defence",
                      (info.x + 12, info.y + 10), 16, INK, bold=True)
            lines = [
                "Pick a tower, then click the map.",
                "",
                "1-7   select tower",
                "SPACE  start round",
                "F  fast-forward      P  pause",
                "A  auto-start        ESC  cancel",
                "",
                "Click a placed tower for upgrades,",
                "targeting, and its sell price.",
            ]
            for i, line in enumerate(lines):
                draw_text(surface, line, (info.x + 12, info.y + 34 + i * 17),
                          13, INK_SOFT)
            return

        self._draw_kind_details(surface, info, key)

    def _draw_kind_details(self, surface: pygame.Surface, info: pygame.Rect,
                           key: str) -> None:
        """Describe an unpurchased tower type."""
        kind = TOWER_KINDS[key]
        draw_text(surface, kind.label, (info.x + 12, info.y + 9), 17, INK,
                  bold=True)

        y = info.y + 33
        for line in _wrap(kind.blurb, 40):
            draw_text(surface, line, (info.x + 12, y), 13, INK_SOFT)
            y += 16

        y += 6
        for label, value in _kind_stats(kind):
            draw_text(surface, label, (info.x + 12, y), 13, INK_SOFT)
            draw_text(surface, value, (info.right - 12, y), 13, INK,
                      bold=True, align=RIGHT)
            y += 17

        y += 8
        for path in (0, 1):
            names = " > ".join(u.name for u in kind.paths[path])
            draw_text(surface, f"Path {path + 1}", (info.x + 12, y), 12,
                      LEAF_DARK, bold=True)
            y += 15
            for line in _wrap(names, 42):
                draw_text(surface, line, (info.x + 12, y), 12, INK_SOFT)
                y += 14
            y += 4

    def _draw_tower_panel(self, surface: pygame.Surface) -> None:
        """Draw the inspector for the currently selected tower."""
        tower = self.selected
        top = pygame.Rect(SIDEBAR_X + PAD, 112, SIDEBAR_W - PAD * 2, 248)
        raised_panel(surface, top)

        icon = pygame.transform.smoothscale(tower_sprite(tower), (36, 36))
        surface.blit(icon, (top.x + 11, top.y + 9))
        draw_text(surface, tower.kind.label, (top.x + 55, top.y + 9), 17, INK,
                  bold=True)
        draw_text(surface, f"Tier {tower.tier_label}", (top.x + 55, top.y + 29),
                  13, LEAF_DARK, bold=True)

        y = top.y + 56
        for label, value in _tower_stats(tower):
            draw_text(surface, label, (top.x + 12, y), 13, INK_SOFT)
            draw_text(surface, value, (top.right - 12, y), 13, INK,
                      bold=True, align=RIGHT)
            y += 18

        y += 6
        draw_text(surface, f"Pops {tower.pops:,}   Earned ${tower.cash_earned:,}",
                  (top.x + 12, y), 12, INK_SOFT)

        for widget in self.panel_buttons:
            widget.draw(surface)

        for path in (0, 1):
            upgrade = tower.next_upgrade(path)
            if upgrade is None:
                continue
            face = self.panel_buttons[path].body_rect()
            _, _, text_colour = self.panel_buttons[path].palette()
            for line in _wrap(upgrade.desc, 42)[:1]:
                draw_text(surface, line, (face.centerx, face.bottom - 17), 11,
                          text_colour, align=CENTER)

        draw_text(surface, "ESC deselect  -  TAB target  -  U / I upgrade",
                  (SIDEBAR_X + SIDEBAR_W // 2, 372 + 182), 12, PAPER,
                  align=CENTER, shadow=True)

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


#: Throwaway tower instances used purely to render shop icons.
_PROBES: dict[str, Tower] = {}


def tower_sprite_for_kind(key: str) -> pygame.Surface:
    """Return a sprite for a tower type without needing a placed instance."""
    probe = _PROBES.get(key)
    if probe is None:
        probe = Tower(TOWER_KINDS[key], 0, 0)
        _PROBES[key] = probe
    return tower_sprite(probe)


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
