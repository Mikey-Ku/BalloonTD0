"""
Application shell: window, state machine, and the main loop.

The loop is ``async`` and yields once per frame. That costs nothing on the
desktop and is what lets the same file run under pygbag in a browser, where
the single-threaded runtime needs the frame to hand control back.

State transitions all happen here. Screens and the HUD only ever return an
action string, so nothing re-enters the loop the way the original game's
restart did by constructing a new ``Game`` inside the running one.
"""

from __future__ import annotations

import asyncio
import os

import pygame

from . import maps
from .audio import Audio
from .config import FPS, MAP_W, SCREEN_H, SCREEN_W
from .game import RUNNING, WON, Run
from .save import SaveData
from .ui.hud import Hud
from .ui.screens import (
    MapSelectScreen, MenuScreen, PauseScreen, ResultScreen, SettingsScreen,
)
from .ui.widgets import dim

MENU = "menu"
MAPSELECT = "mapselect"
SETTINGS = "settings"
PLAYING = "playing"
PAUSED = "paused"
RESULT = "result"


class App:
    """Owns the window, the current screen, and the active run.

    Attributes:
        screen: The display surface.
        save: Persistent settings and records.
        audio: Music and sound effects.
        state: Current application state.
        run: The active :class:`~btd.game.Run`, if any.
        hud: The HUD bound to ``run``, if any.
    """

    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        pygame.display.set_caption("Balloon TD")

        self.clock = pygame.time.Clock()
        self.running = True

        self.save = SaveData()
        self.audio = Audio()
        self.audio.set_volumes(self.save.get("music_volume"),
                               self.save.get("sfx_volume"))

        self.state = MENU
        self.run: Run | None = None
        self.hud: Hud | None = None
        self.screen_obj = MenuScreen(self)
        self.settings_return = MENU
        self.last_setup = (maps.MAP_ORDER[0], "normal")

        self._backdrop: pygame.Surface | None = None

    # -- presentation -----------------------------------------------------

    def draw_backdrop(self, surface: pygame.Surface) -> None:
        """Fill the window with the shared menu background.

        Over an active run the live playfield is used instead, dimmed, so a
        paused game still shows what is happening behind the modal.
        """
        if self.state in (PAUSED, RESULT) and self.run is not None:
            self.run.draw_map(surface)
            if self.hud is not None:
                self.hud.draw(surface)
            dim(surface, 190)
            return

        surface.blit(self._menu_backdrop(), (0, 0))

    def _menu_backdrop(self) -> pygame.Surface:
        """Build (once) a blurred, darkened background for the menus."""
        if self._backdrop is not None:
            return self._backdrop

        from . import assets
        source = "background_images/Background_blurred.png"
        if os.path.exists(assets.path(source)):
            base = assets.image(source, (SCREEN_W, SCREEN_H))
        else:
            map_def = maps.MAPS[maps.MAP_ORDER[0]]
            path = maps.build_path(map_def)
            base = maps.build_background(map_def, path)
            base = pygame.transform.smoothscale(base, (SCREEN_W, SCREEN_H))

        backdrop = maps.blurred(base.convert(), passes=2)
        # Warm brown wash rather than a cold slate one, so the menus read as
        # part of the same jungle as the map instead of an overlay on top.
        shade = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        shade.fill((58, 36, 20, 140))
        backdrop.blit(shade, (0, 0))
        self._backdrop = backdrop
        return backdrop

    # -- transitions ------------------------------------------------------

    def go(self, state: str) -> None:
        """Switch state, constructing the matching screen."""
        self.state = state
        if state == MENU:
            self.screen_obj = MenuScreen(self)
        elif state == MAPSELECT:
            self.screen_obj = MapSelectScreen(self)
        elif state == SETTINGS:
            self.screen_obj = SettingsScreen(self)
        elif state == PAUSED:
            self.screen_obj = PauseScreen(self)

    def start_run(self, map_key: str, difficulty: str) -> None:
        """Begin a new run and switch to the playing state."""
        self.last_setup = (map_key, difficulty)
        self.run = Run(map_key, difficulty)
        self.run.sfx_hook = self.audio.play
        self.hud = Hud(self.run)
        self.state = PLAYING
        self.screen_obj = None

    def finish_run(self) -> None:
        """Record the finished run and show the results screen."""
        run = self.run
        if run is None:
            return
        record = self.save.record_run(
            run.map_def.key, run.difficulty, run.round_number,
            run.total_pops, run.outcome == WON,
        )
        self.screen_obj = ResultScreen(self, run.outcome == WON, record)
        self.state = RESULT

    def handle_action(self, action: str | None) -> None:
        """Apply an action string returned by a screen or the HUD."""
        if not action:
            return

        if action == "quit":
            self.running = False
        elif action == "play":
            self.go(MAPSELECT)
        elif action == "settings":
            self.settings_return = self.state
            self.go(SETTINGS)
        elif action == "menu":
            if self.state == PLAYING:
                self.run.paused = True
                self.go(PAUSED)
            else:
                self.run = None
                self.hud = None
                self.go(MENU)
        elif action == "back":
            if self.state == SETTINGS:
                target = self.settings_return
                self.go(target if target != PLAYING else PAUSED)
            elif self.state == MAPSELECT:
                self.go(MENU)
            else:
                self.go(MENU)
        elif action == "resume":
            if self.run is not None:
                self.run.paused = False
                self.state = PLAYING
                self.screen_obj = None
        elif action == "restart":
            self.start_run(*self.last_setup)
        elif action.startswith("start:"):
            _, map_key, difficulty = action.split(":")
            self.start_run(map_key, difficulty)
        elif action.startswith("slide:"):
            self._apply_sliders()

    def _apply_sliders(self) -> None:
        """Push settings-screen slider values into audio and the save file."""
        screen = self.screen_obj
        if not isinstance(screen, SettingsScreen):
            return
        music, sfx = screen.sliders[0].value, screen.sliders[1].value
        self.audio.set_volumes(music, sfx)
        self.save.data["music_volume"] = music
        self.save.data["sfx_volume"] = sfx

    # -- events -----------------------------------------------------------

    def handle_event(self, event: pygame.event.Event) -> None:
        """Dispatch one pygame event to whatever currently owns input."""
        if event.type == pygame.QUIT:
            self.running = False
            return

        if self.state == PLAYING:
            self._handle_playing_event(event)
            return

        screen = self.screen_obj
        if screen is None:
            return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.handle_action(screen.handle_click(event.pos))
        elif event.type == pygame.MOUSEMOTION:
            self.handle_action(screen.handle_drag(event.pos))
        elif event.type == pygame.MOUSEBUTTONUP:
            screen.release()
            if isinstance(screen, SettingsScreen):
                self.save.flush()
        elif event.type == pygame.KEYDOWN:
            self.handle_action(screen.handle_key(event.key))

    def _handle_playing_event(self, event: pygame.event.Event) -> None:
        """Dispatch an event while a run is in progress."""
        if self.hud is None:
            return
        if event.type == pygame.MOUSEBUTTONDOWN:
            self.handle_action(self.hud.handle_click(event.pos, event.button))
        elif event.type == pygame.KEYDOWN:
            self.handle_action(self.hud.handle_key(event.key))

    # -- frame ------------------------------------------------------------

    def update(self, dt: float) -> None:
        """Advance whatever is active for one frame."""
        mouse = pygame.mouse.get_pos()

        if self.state == PLAYING and self.run is not None:
            self.run.advance(dt)
            self.hud.update(dt, mouse)
            if self.run.outcome != RUNNING:
                self.finish_run()
            return

        if self.screen_obj is not None:
            self.screen_obj.update(dt, mouse)

    def draw(self) -> None:
        """Render one frame."""
        if self.state == PLAYING and self.run is not None:
            self.run.draw_map(self.screen)
            if self.save.get("show_ranges"):
                self.hud.draw_map_overlay(self.screen)
            self.hud.draw(self.screen)
            if self.run.paused:
                self._draw_pause_hint()
        elif self.screen_obj is not None:
            self.screen_obj.draw(self.screen)

        pygame.display.flip()

    def _draw_pause_hint(self) -> None:
        """Overlay a banner when the simulation is frozen but not in a modal."""
        from .ui.widgets import CENTER, draw_text
        banner = pygame.Surface((MAP_W, 44), pygame.SRCALPHA)
        banner.fill((10, 13, 20, 190))
        self.screen.blit(banner, (0, SCREEN_H // 2 - 22))
        draw_text(self.screen, "PAUSED  -  press P to resume",
                  (MAP_W // 2, SCREEN_H // 2 - 12), 22, (238, 241, 246),
                  bold=True, align=CENTER)

    async def loop(self) -> None:
        """Run the main loop until the window closes.

        Yields to the event loop once per frame so the browser build stays
        responsive.
        """
        self.audio.start_music()

        while self.running:
            dt = self.clock.tick(FPS) / 1000.0

            for event in pygame.event.get():
                self.handle_event(event)

            self.update(dt)
            self.draw()

            await asyncio.sleep(0)

        pygame.quit()


async def main() -> None:
    """Entry point used by both the desktop and browser builds."""
    app = App()
    await app.loop()
