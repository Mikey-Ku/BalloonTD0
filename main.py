"""
Main game file that initializes and runs the game loop.
"""

import pygame
from rounds import rounds_config
from track import load_waypoints_from_csv, Track
from balloon import (
    RedBalloon,
    BlueBalloon,
    GreenBalloon,
    YellowBalloon,
    PinkBalloon,
    MoabBalloon,
)
from user_interface import GameUI


class Game:
    def __init__(self):

        self.round_started = False
        self.balloons_to_spawn = 0
        self.current_round = 1
        self.last_round = 20

        self.round_spawn_list = rounds_config

        pygame.init()
        pygame.mixer.init()
        pygame.mixer.music.load(
            "soundtrack/SpotiDownloader.com - Main Theme - Tim Haywood.mp3"
        )
        pygame.mixer.music.play(loops=-1)

        self.clock_ticks = 0  # Add this line after pygame.init()
        self.screen = pygame.display.set_mode((800, 600))
        pygame.display.set_caption("Balloon TD")
        self.background = pygame.image.load(
            "background_images/Background.webp"
        ).convert()
        self.background = pygame.transform.scale(self.background, (800, 600))
        self.track = Track()
        self.waypoints = load_waypoints_from_csv("equidistant_points.csv")
        self.track.waypoints = self.waypoints
        self.balloons = []
        self.towers = []
        self.tower_sprites = pygame.sprite.Group()
        self.money = 200
        self.lives = 100
        self.round_started = False
        self.balloons_to_spawn = 10
        self.spawn_delay = 500  # Default spawn delay in milliseconds
        self.last_spawn_time = 0
        self.next_balloon_time = 0  # Track exact spawn timing
        self.current_wave = 1
        self.ui = GameUI(self)
        self.font = pygame.font.SysFont(None, 36)
        self.end_font = pygame.font.SysFont(None, 72)
        self.round_started = False
        self.balloons_to_spawn = 0
        self.current_round = 1
        self.passive_income_amount = 2
        self.speed_multiplier = 1  # Normal speed
        self.play_button_rect = pygame.Rect(700, 10, 90, 40)  # Top-right corner
        self.state = "menu"
        self.play_button = pygame.Rect(300, 200, 200, 50)
        self.ctrl_button = pygame.Rect(300, 270, 200, 50)
        self.back_button = pygame.Rect(300, 520, 200, 50)
        # load a background for the menu
        self.menu_background = pygame.image.load(
            "background_images/Background_blurred.png"
        ).convert()
        # scale it to exactly your window size
        self.menu_background = pygame.transform.scale(
            self.menu_background,
            (self.screen.get_width(), self.screen.get_height()),
        )

    def draw_menu(self):
        # draw blurred background
        self.screen.blit(self.menu_background, (0, 0))

        # ——— outline + draw title ———
        title_text = "Balloon TD"
        cx = self.screen.get_width() // 2
        cy = 100
        # 1px black outline in each direction
        for ox, oy in [(-2, 0), (2, 0), (0, -2), (0, 2)]:
            outline = self.end_font.render(title_text, True, (0, 0, 0))
            outline_rect = outline.get_rect(center=(cx + ox, cy + oy))
            self.screen.blit(outline, outline_rect)
        # then the white text on top
        title_surf = self.end_font.render(title_text, True, (255, 255, 255))
        title_rect = title_surf.get_rect(center=(cx, cy))
        self.screen.blit(title_surf, title_rect)

        # ——— Play button ———
        # gray fill
        pygame.draw.rect(self.screen, (100, 100, 100), self.play_button)
        # black border (3px)
        pygame.draw.rect(self.screen, (0, 0, 0), self.play_button, 3)
        # label
        play_surf = self.font.render("Play", True, (0, 0, 0))
        play_rect = play_surf.get_rect(center=self.play_button.center)
        self.screen.blit(play_surf, play_rect)

        # ——— Instructions button ———
        pygame.draw.rect(self.screen, (100, 100, 100), self.ctrl_button)
        pygame.draw.rect(self.screen, (0, 0, 0), self.ctrl_button, 3)
        instr_surf = self.font.render("Instructions", True, (0, 0, 0))
        instr_rect = instr_surf.get_rect(center=self.ctrl_button.center)
        self.screen.blit(instr_surf, instr_rect)

    def draw_instructions(self):
        # draw the same blurred background
        self.screen.blit(self.menu_background, (0, 0))

        lines = [
            "INSTRUCTIONS",
            "– Drag and drop a tower from the UI onto the map to place it",
            "– Press SPACE or use the Play button to start each round",
            "– Use the bottom-right buttons to upgrade/sell towers",
            "– Survive as many rounds as you can!",
        ]

        for i, txt in enumerate(lines):
            x, y = 50, 100 + i * 40
            thickness = 1
            for dx in range(-thickness, thickness + 1):
                for dy in range(-thickness, thickness + 1):
                    if dx == 0 and dy == 0:
                        continue
                    outline = self.font.render(txt, True, (0, 0, 0))
                    self.screen.blit(outline, (x + dx, y + dy))
            # white text on top
            text_surf = self.font.render(txt, True, (255, 255, 255))
            self.screen.blit(text_surf, (x, y))

        # draw Back button with thicker border
        pygame.draw.rect(self.screen, (100, 100, 100), self.back_button)
        pygame.draw.rect(
            self.screen, (0, 0, 0), self.back_button, 4
        )  # 4px border

        back_txt = "Back"
        bx, by = (
            (self.back_button.centerx, self.back_button.centery)
            if hasattr(self.back_button, "centerx")
            else (0, 0)
        )
        # outline for Back label
        for dx in range(-thickness, thickness + 1):
            for dy in range(-thickness, thickness + 1):
                if dx == 0 and dy == 0:
                    continue
                ol = self.font.render(back_txt, True, (0, 0, 0))
                r = ol.get_rect(center=(bx + dx, by + dy))
                self.screen.blit(ol, r)
        # white Back text
        back_surf = self.font.render(back_txt, True, (255, 255, 255))
        back_rect = back_surf.get_rect(center=(bx, by))
        self.screen.blit(back_surf, back_rect)

    def toggle_speed(self):
        """Toggle between normal and 2x speed."""
        if self.speed_multiplier == 1:
            self.speed_multiplier = 2
        else:
            self.speed_multiplier = 1

    def draw_stats(self):
        """Draw money, lives, round counter, and play/speed button on screen."""
        outline_color = (0, 0, 0)
        # ——— Money with black outline ———
        money_str = f"Money: ${self.money}"
        mx, my = 10, 10
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                surf = self.font.render(money_str, True, outline_color)
                self.screen.blit(surf, (mx + dx, my + dy))
        money_surf = self.font.render(money_str, True, (255, 255, 0))
        self.screen.blit(money_surf, (mx, my))

        # ——— Lives with black outline ———
        lives_str = f"Lives: {self.lives}"
        lx, ly = 10, 50
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                surf = self.font.render(lives_str, True, outline_color)
                self.screen.blit(surf, (lx + dx, ly + dy))
        lives_surf = self.font.render(lives_str, True, (255, 0, 0))
        self.screen.blit(lives_surf, (lx, ly))

        # ——— Round counter with black outline ———
        round_str = f"Round {self.current_round}"
        rx, ry = 10, 570
        # draw outline
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                outline_surf = self.font.render(round_str, True, outline_color)
                self.screen.blit(outline_surf, (rx + dx, ry + dy))
        # draw white text
        round_surf = self.font.render(round_str, True, (255, 255, 255))
        self.screen.blit(round_surf, (rx, ry))

        # ——— Play / Speed button ———
        button_text = (
            "Play"
            if not self.round_started
            else "1x" if self.speed_multiplier == 1 else "2x"
        )
        pygame.draw.rect(self.screen, (100, 100, 100), self.play_button_rect)
        pygame.draw.rect(self.screen, (0, 0, 0), self.play_button_rect, 2)
        text_surface = self.font.render(button_text, True, (0, 0, 0))
        text_rect = text_surface.get_rect(center=self.play_button_rect.center)
        self.screen.blit(text_surface, text_rect)

    def prepare_round(self):
        """Prepare the balloon queue based on current round's config."""
        self.balloons_queue = []
        round_index = self.current_round - 1

        if round_index < len(self.round_spawn_list):
            round_info = self.round_spawn_list[round_index]
            self.spawn_delay = round_info["spawn_delay"]

            for balloon_type, count in round_info["balloons"]:
                for _ in range(count):
                    self.balloons_queue.append(balloon_type)

    def end_game(self):
        """
        Ends the game with a win or a lose case.
        Clears UI.
        Has a restart button.
        Make its clear if win or lose.
        """
        game_over = True
        if self.lives <= 0:
            end_text = self.end_font.render("Game Over!", True, (255, 0, 0))

        else:
            end_text = self.end_font.render("You Win!", True, (0, 255, 0))

        game_stats_text = self.font.render(
            f"You made it {self.current_round - 1} rounds! ", True, (0, 0, 0)
        )
        restart_text = self.font.render(
            "Press R to Restart or Q to Quit", True, (0, 0, 0)
        )

        while game_over:
            pygame.display.flip()
            self.screen.blit(self.background, (0, 0))
            self.screen.blit(end_text, (250, 200))
            self.screen.blit(game_stats_text, (250, 350))
            self.screen.blit(restart_text, (200, 300))

            for event in pygame.event.get():
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_r:
                        # Restart the game
                        self.__init__()
                        self.run()
                        return
                    elif event.key == pygame.K_q:
                        game_over = False

    def run(self):
        """Main game loop"""
        clock = pygame.time.Clock()
        running = True

        while running:
            # Calculate delta time from clock
            dt = clock.tick(60 * self.speed_multiplier)
            self.clock_ticks += dt
            current_time = self.clock_ticks

            # Event handling
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

                # MENU STATE
                if self.state == "menu":
                    if (
                        event.type == pygame.MOUSEBUTTONDOWN
                        and event.button == 1
                    ):
                        if self.play_button.collidepoint(event.pos):
                            self.state = "playing"
                            self.last_spawn_time = current_time
                            self.prepare_round()
                        elif self.ctrl_button.collidepoint(event.pos):
                            self.state = "instructions"

                # INSTRUCTIONS STATE
                elif self.state == "instructions":
                    if (
                        event.type == pygame.MOUSEBUTTONDOWN
                        and event.button == 1
                    ):
                        if self.back_button.collidepoint(event.pos):
                            self.state = "menu"

                # PLAYING STATE
                elif self.state == "playing":
                    # Spacebar to start round
                    if event.type == pygame.KEYDOWN:
                        if (
                            event.key == pygame.K_SPACE
                            and not self.round_started
                        ):
                            self.round_started = True
                            self.last_spawn_time = current_time
                            self.prepare_round()

                    # Click play button to start/slow rounds
                    elif (
                        event.type == pygame.MOUSEBUTTONDOWN
                        and event.button == 1
                    ):
                        if self.play_button_rect.collidepoint(event.pos):
                            if not self.round_started:
                                self.round_started = True
                                self.last_spawn_time = current_time
                                self.prepare_round()
                            else:
                                self.toggle_speed()

                    # Pass everything else to your UI (tower selections, upgrades, etc.)
                    self.ui.handle_event(event)

            # DRAWING
            if self.state == "menu":
                self.draw_menu()

            elif self.state == "instructions":
                self.draw_instructions()

            else:  # self.state == "playing"
                # Background
                self.screen.blit(self.background, (0, 0))

                # Spawn balloons
                if self.round_started and self.balloons_queue:
                    if self.clock_ticks >= self.next_balloon_time:
                        bt = self.balloons_queue.pop(0)
                        if bt == "red":
                            self.balloons.append(RedBalloon(self.waypoints))
                        elif bt == "blue":
                            self.balloons.append(BlueBalloon(self.waypoints))
                        elif bt == "green":
                            self.balloons.append(GreenBalloon(self.waypoints))
                        elif bt == "yellow":
                            self.balloons.append(YellowBalloon(self.waypoints))
                        elif bt == "pink":
                            self.balloons.append(PinkBalloon(self.waypoints))
                        elif bt == "moab":
                            self.balloons.append(MoabBalloon(self.waypoints))
                        adj_delay = self.spawn_delay / self.speed_multiplier
                        self.next_balloon_time = self.clock_ticks + adj_delay

                # Towers fire
                for tower in self.towers:
                    tower.update(self.speed_multiplier)
                    tower.update_angle(self.balloons)
                    popped = tower.attack(self.balloons, current_time)
                    if popped:
                        for bal, rew in popped:
                            self.money += rew
                    if hasattr(tower, "rect") and tower.rect:
                        tower.rect.centerx = int(tower.x)
                        tower.rect.centery = int(tower.y)
                    tower.update()

                # Move & draw balloons
                for balloon in self.balloons[:]:
                    if balloon.move():
                        self.lives -= balloon.damage
                        self.balloons.remove(balloon)
                        continue
                    balloon.draw(self.screen)
                    if balloon.health <= 0:
                        self.money += balloon.reward
                        self.balloons.remove(balloon)

                # Draw towers on top
                self.tower_sprites.draw(self.screen)

                # UI & stats
                self.ui.draw(self.screen)
                self.draw_stats()

                # Round complete?
                if (
                    self.round_started
                    and not self.balloons
                    and not self.balloons_queue
                ):
                    finished = self.current_round
                    self.current_round += 1
                    self.money += 20 * finished
                    self.round_started = False

                # End game?
                if self.current_round > self.last_round or self.lives <= 0:
                    self.end_game()
                    break

            pygame.display.flip()

        pygame.quit()


if __name__ == "__main__":
    game = Game()
    game.run()
