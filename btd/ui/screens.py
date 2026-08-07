"""
Full-screen interfaces: title, map select, settings, pause, and results.

The original game had a title screen, a static instructions page, and a
game-over screen that restarted by constructing a new ``Game`` inside the
running one's call stack. Screens here are plain objects that return an action
string; the app owns all state transitions, so nothing recurses.
"""

from __future__ import annotations

import pygame

from .. import assets, maps
from ..config import (
    ACCENT, BERRY, DIFFICULTIES, INK, INK_SOFT, LEAF_LIGHT, PAPER,
    SCREEN_W, SUN, TEXT_GOLD, WOOD,
)
from . import chrome
from .widgets import Button, CENTER, Slider, draw_text, raised_panel


class Screen:
    """Base class for a full-screen interface.

    Subclasses populate ``buttons`` and override :meth:`draw_content`.
    """

    title = ""
    subtitle = ""

    def __init__(self, app):
        self.app = app
        self.buttons: list[Button] = []
        self.sliders: list[Slider] = []

    def update(self, dt: float, mouse: tuple[int, int]) -> None:
        """Refresh hover states.

        ``dt`` is unused here but is part of the signature every screen
        implements, and screens with animation do use it.
        """
        del dt
        for button in self.buttons:
            button.update_hover(mouse)

    def handle_click(self, pos: tuple[int, int]) -> str | None:
        """Return the action of whichever control was clicked."""
        for slider in self.sliders:
            if slider.hit(pos):
                return f"slide:{slider.action}"
        for button in self.buttons:
            action = button.hit(pos)
            if action:
                return action
        return None

    def handle_drag(self, pos: tuple[int, int]) -> str | None:
        """Continue a slider drag, if one is active."""
        for slider in self.sliders:
            if slider.dragging:
                slider.set_from_x(pos[0])
                return f"slide:{slider.action}"
        return None

    def release(self) -> None:
        """End any slider drag."""
        for slider in self.sliders:
            slider.release()

    def handle_key(self, key: int) -> str | None:
        """Handle a key press. Escape backs out by default."""
        if key == pygame.K_ESCAPE:
            return "back"
        return None

    #: Where the heading sign sits. Subclasses may move it.
    title_top = 40

    def draw(self, surface: pygame.Surface) -> None:
        """Draw the backdrop, heading, and the subclass's content."""
        self.app.draw_backdrop(surface)
        self.draw_heading(surface)
        self.draw_content(surface)
        for slider in self.sliders:
            slider.draw(surface)
        for button in self.buttons:
            button.draw(surface)

    def draw_heading(self, surface: pygame.Surface) -> pygame.Rect | None:
        """Draw the title, and subtitle if any, on a wooden sign.

        Returns the sign's rect so subclasses can lay out beneath it.
        """
        if not self.title:
            return None

        title_size = 50
        title = chrome.outlined_text(self.title, title_size, TEXT_GOLD,
                                     thickness=2)
        width = title.get_width() + 88
        height = 100 if self.subtitle else 74

        if self.subtitle:
            sub = assets.font(18).render(self.subtitle, True, PAPER)
            width = max(width, sub.get_width() + 72)

        board = pygame.Rect(0, self.title_top, width, height)
        board.centerx = SCREEN_W // 2
        chrome.sign(surface, board)

        surface.blit(title, title.get_rect(midtop=(board.centerx,
                                                   board.y + 12)))
        if self.subtitle:
            surface.blit(sub, sub.get_rect(midtop=(board.centerx,
                                                   board.y + 16 + title_size)))
        return board

    def draw_content(self, surface: pygame.Surface) -> None:
        """Draw anything beyond the heading and controls."""


class MenuScreen(Screen):
    """Title screen."""

    title = "BALLOON TD"
    subtitle = "Place monkeys. Pop balloons. Do not let them through."
    title_top = 183

    def __init__(self, app):
        super().__init__(app)
        # Sign plus three buttons, centred as one block rather than pinned
        # near the top with empty space below.
        mid = SCREEN_W // 2
        top = 348
        self.buttons = [
            Button((mid - 150, top, 300, 58), "Play", "play", size=23),
            Button((mid - 150, top + 74, 300, 50), "Settings", "settings", size=18),
            Button((mid - 150, top + 138, 300, 50), "Quit", "quit", size=18),
        ]

    def handle_key(self, key: int) -> str | None:
        """Enter starts, Escape quits."""
        if key in (pygame.K_RETURN, pygame.K_SPACE):
            return "play"
        if key == pygame.K_ESCAPE:
            return "quit"
        return None


#: Map card size. Cards wrap to a second row rather than shrinking.
CARD_W, CARD_H = 258, 184


class MapSelectScreen(Screen):
    """Map and difficulty picker."""

    title = "Choose a Map"

    #: Thumbnails are rendered once and reused.
    _thumbs: dict[str, pygame.Surface] = {}

    def __init__(self, app):
        super().__init__(app)
        self.map_key = maps.MAP_ORDER[0]
        self.difficulty = "normal"
        self.card_rects: dict[str, pygame.Rect] = {}
        self._build()

    def _build(self) -> None:
        """Lay out the map cards, difficulty buttons, and actions.

        Cards wrap onto a second row rather than shrinking, so the layout
        keeps working as maps are added.
        """
        self.buttons = []
        card_w, card_h = CARD_W, CARD_H
        gap = 16
        per_row = min(3, len(maps.MAP_ORDER))
        rows = (len(maps.MAP_ORDER) + per_row - 1) // per_row
        top = 118 if rows > 1 else 202

        self.card_rects = {}
        for i, key in enumerate(maps.MAP_ORDER):
            row, col = i // per_row, i % per_row
            in_row = min(per_row, len(maps.MAP_ORDER) - row * per_row)
            span = in_row * card_w + (in_row - 1) * gap
            start_x = (SCREEN_W - span) // 2
            self.card_rects[key] = pygame.Rect(
                start_x + col * (card_w + gap),
                top + row * (card_h + gap),
                card_w, card_h,
            )

        controls_y = top + rows * (card_h + gap) + 8

        diff_w = 140
        diff_total = len(DIFFICULTIES) * diff_w + (len(DIFFICULTIES) - 1) * 12
        diff_x = (SCREEN_W - diff_total) // 2
        for i, key in enumerate(DIFFICULTIES):
            button = Button(
                (diff_x + i * (diff_w + 12), controls_y, diff_w, 42),
                DIFFICULTIES[key]["label"], f"diff:{key}", size=17,
            )
            button.selected = key == self.difficulty
            self.buttons.append(button)

        self.rules_y = controls_y + 60
        self.buttons.append(
            Button((SCREEN_W // 2 - 150, controls_y + 96, 300, 46),
                   "Start Run", "start", size=20)
        )
        self.buttons.append(
            Button((SCREEN_W // 2 - 150, controls_y + 152, 300, 36),
                   "Back", "back", size=16)
        )

    def thumb(self, key: str) -> pygame.Surface:
        """Return a small preview of a map, rendering it on first use."""
        cached = self._thumbs.get(key)
        if cached is not None:
            return cached
        map_def = maps.MAPS[key]
        path = maps.build_path(map_def)
        full = maps.build_background(map_def, path)
        thumb = pygame.transform.smoothscale(full, (CARD_W - 16, CARD_H - 58))
        self._thumbs[key] = thumb
        return thumb

    def handle_click(self, pos: tuple[int, int]) -> str | None:
        """Select a card, or fall through to the buttons."""
        for key, rect in self.card_rects.items():
            if rect.collidepoint(pos):
                self.map_key = key
                return None

        action = super().handle_click(pos)
        if action and action.startswith("diff:"):
            self.difficulty = action.split(":")[1]
            for button in self.buttons:
                if button.action.startswith("diff:"):
                    button.selected = button.action == f"diff:{self.difficulty}"
            return None
        if action == "start":
            return f"start:{self.map_key}:{self.difficulty}"
        return action

    def draw_content(self, surface: pygame.Surface) -> None:
        """Draw the map cards and the selected difficulty's rules."""
        for key, rect in self.card_rects.items():
            map_def = maps.MAPS[key]
            chosen = key == self.map_key
            raised_panel(surface, rect, edge=ACCENT if chosen else WOOD)
            surface.blit(self.thumb(key), (rect.x + 8, rect.y + 8))
            draw_text(surface, map_def.name,
                      (rect.centerx, rect.bottom - 44), 16, INK,
                      bold=True, align=CENTER)
            best = self.app.save.best_round(key, self.difficulty)
            label = f"{map_def.difficulty}   -   best round {best}" if best \
                else map_def.difficulty
            draw_text(surface, label, (rect.centerx, rect.bottom - 24), 12,
                      INK_SOFT, align=CENTER)

        rules = DIFFICULTIES[self.difficulty]
        summary = (
            f"${rules['money']:,} starting cash   -   {rules['lives']} lives   -   "
            f"{rules['rounds']} rounds   -   "
            f"balloon health x{rules['hp_scale']:.2f}"
        )
        label = assets.font(16, bold=True).render(summary, True, PAPER)
        strip = label.get_rect(midtop=(SCREEN_W // 2, self.rules_y))
        chrome.plank_strip(surface, strip.inflate(40, 16))
        surface.blit(label, strip)


class SettingsScreen(Screen):
    """Audio and display options."""

    title = "Settings"

    def __init__(self, app):
        super().__init__(app)
        mid = SCREEN_W // 2
        self.sliders = [
            Slider((mid - 130, 216, 260, 8), app.save.get("music_volume"), "music"),
            Slider((mid - 130, 300, 260, 8), app.save.get("sfx_volume"), "sfx"),
        ]
        self.buttons = [
            Button((mid - 150, 352, 300, 46), "", "toggle_ranges", size=17),
            Button((mid - 130, 418, 260, 46), "Back", "back", size=18),
        ]
        self._sync()

    def _sync(self) -> None:
        """Refresh the toggle label from saved state."""
        on = self.app.save.get("show_ranges")
        self.buttons[0].label = f"Show tower ranges: {'On' if on else 'Off'}"

    def handle_click(self, pos: tuple[int, int]) -> str | None:
        """Handle the toggle in place; everything else bubbles up."""
        action = super().handle_click(pos)
        if action == "toggle_ranges":
            self.app.save.set("show_ranges", not self.app.save.get("show_ranges"))
            self._sync()
            return None
        return action

    def draw_content(self, surface: pygame.Surface) -> None:
        """Draw the panel the sliders sit on, and their current values."""
        mid = SCREEN_W // 2
        board = pygame.Rect(mid - 210, 160, 420, 172)
        raised_panel(surface, board)

        draw_text(surface, f"Music  {int(self.sliders[0].value * 100)}%",
                  (mid, 176), 19, INK, bold=True, align=CENTER)
        draw_text(surface, f"Sound effects  {int(self.sliders[1].value * 100)}%",
                  (mid, 260), 19, INK, bold=True, align=CENTER)
        if not self.app.save.writable:
            draw_text(surface, "Settings cannot be saved here.",
                      (mid, 302), 15, INK_SOFT, align=CENTER)


class PauseScreen(Screen):
    """Modal shown over a paused run."""

    title = "Paused"

    def __init__(self, app):
        super().__init__(app)
        mid = SCREEN_W // 2
        self.buttons = [
            Button((mid - 130, 210, 260, 50), "Resume", "resume", size=20),
            Button((mid - 130, 272, 260, 46), "Restart Run", "restart", size=17),
            Button((mid - 130, 328, 260, 46), "Settings", "settings", size=17),
            Button((mid - 130, 384, 260, 46), "Main Menu", "menu", size=17),
        ]

    def handle_key(self, key: int) -> str | None:
        """Escape resumes."""
        if key in (pygame.K_ESCAPE, pygame.K_p):
            return "resume"
        return None

    def draw_content(self, surface: pygame.Surface) -> None:
        """Show a snapshot of the run in progress."""
        run = self.app.run
        if run is None:
            return
        lines = [
            f"{run.map_def.name}  -  {DIFFICULTIES[run.difficulty]['label']}",
            f"Round {run.round_number} of {run.max_rounds}",
            f"${run.money:,}  -  {run.lives} lives  -  {len(run.towers)} towers",
        ]
        board = pygame.Rect(SCREEN_W // 2 - 230, 452, 460, 26 + 26 * len(lines))
        raised_panel(surface, board)
        for i, line in enumerate(lines):
            draw_text(surface, line, (board.centerx, board.y + 13 + i * 26), 17,
                      INK, align=CENTER)


class ResultScreen(Screen):
    """End-of-run summary."""

    def __init__(self, app, won: bool, record: bool):
        super().__init__(app)
        self.won = won
        self.record = record
        self.title = "Victory" if won else "Game Over"
        mid = SCREEN_W // 2
        self.buttons = [
            Button((mid - 130, 470, 260, 50), "Play Again", "restart", size=20),
            Button((mid - 130, 532, 260, 46), "Choose Map", "play", size=17),
            Button((mid - 130, 588, 260, 46), "Main Menu", "menu", size=17),
        ]

    def handle_key(self, key: int) -> str | None:
        """Enter replays, Escape returns to the menu."""
        if key == pygame.K_RETURN:
            return "restart"
        if key == pygame.K_ESCAPE:
            return "menu"
        return None

    def draw_content(self, surface: pygame.Surface) -> None:
        """Show run statistics and any new record."""
        run = self.app.run
        if run is None:
            return

        colour = LEAF_LIGHT if self.won else BERRY
        headline = (
            f"Cleared all {run.max_rounds} rounds"
            if self.won else
            f"Survived to round {run.round_number}"
        )
        banner = assets.font(22, bold=True).render(headline, True, colour)
        rect = banner.get_rect(midtop=(SCREEN_W // 2, 134))
        chrome.plank_strip(surface, rect.inflate(52, 18))
        surface.blit(banner, rect)

        if self.record:
            best = chrome.outlined_text("New personal best", 17, SUN)
            surface.blit(best, best.get_rect(midtop=(SCREEN_W // 2, 176)))

        box = pygame.Rect(SCREEN_W // 2 - 220, 208, 440, 258)
        raised_panel(surface, box)

        rows = [
            ("Map", run.map_def.name),
            ("Difficulty", DIFFICULTIES[run.difficulty]["label"]),
            ("Round reached", f"{run.round_number} / {run.max_rounds}"),
            ("Balloons popped", f"{run.total_pops:,}"),
            ("Money earned", f"${run.total_earned:,}"),
            ("Towers built", str(len(run.towers))),
            ("Lives left", f"{run.lives} / {run.max_lives}"),
            ("Time played", _clock(run.elapsed)),
        ]
        for i, (label, value) in enumerate(rows):
            y = box.y + 16 + i * 26
            draw_text(surface, label, (box.x + 20, y), 16, INK_SOFT)
            draw_text(surface, value, (box.right - 20, y), 16, INK,
                      align="right", bold=True)

        top = run.towers and max(run.towers, key=lambda t: t.pops)
        if top:
            draw_text(surface, "Top tower", (box.x + 20, box.bottom - 34), 16,
                      INK_SOFT)
            draw_text(surface,
                      f"{top.kind.label} ({top.tier_label}) - "
                      f"{top.pops:,} pops",
                      (box.right - 20, box.bottom - 34), 16, INK,
                      align="right", bold=True)


def _clock(seconds: float) -> str:
    """Format elapsed seconds as ``m:ss``."""
    minutes, secs = divmod(int(seconds), 60)
    return f"{minutes}:{secs:02d}"
