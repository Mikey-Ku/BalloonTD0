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
        self.last_round = 50

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
        self.money = 2000
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

    def toggle_speed(self):
        """Toggle between normal and 2x speed."""
        if self.speed_multiplier == 1:
            self.speed_multiplier = 2
        else:
            self.speed_multiplier = 1

    def draw_stats(self):
        """Draw money, lives, round counter, and play/speed button on screen."""
        money_text = self.font.render(f"Money: ${self.money}", True, (0, 0, 0))
        lives_text = self.font.render(f"Lives: {self.lives}", True, (0, 0, 0))
        round_text = self.font.render(
            f"Round {self.current_round}", True, (0, 0, 0)
        )

        self.screen.blit(money_text, (10, 10))
        self.screen.blit(lives_text, (10, 50))
        self.screen.blit(round_text, (10, 570))

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

            # Replace current_time with self.clock_ticks
            current_time = self.clock_ticks

            self.screen.blit(self.background, (0, 0))

            # Event handling
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_SPACE and not self.round_started:
                        self.round_started = True
                        self.last_spawn_time = current_time
                        self.prepare_round()
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if self.play_button_rect.collidepoint(event.pos):
                        if not self.round_started:
                            self.round_started = True
                            self.last_spawn_time = current_time
                            self.prepare_round()
                        else:
                            self.toggle_speed()
                self.ui.handle_event(event)

            # Spawn balloons
            if self.round_started and self.balloons_queue:
                if self.clock_ticks >= self.next_balloon_time:
                    balloon_type = self.balloons_queue.pop(0)
                    if balloon_type == "red":
                        self.balloons.append(RedBalloon(self.waypoints))
                    elif balloon_type == "blue":
                        self.balloons.append(BlueBalloon(self.waypoints))
                    elif balloon_type == "green":
                        self.balloons.append(GreenBalloon(self.waypoints))
                    elif balloon_type == "yellow":
                        self.balloons.append(YellowBalloon(self.waypoints))
                    elif balloon_type == "pink":
                        self.balloons.append(PinkBalloon(self.waypoints))
                    elif balloon_type == "moab":
                        self.balloons.append(MoabBalloon(self.waypoints))
                    # Adjust spawn delay based on speed multiplier
                    adjusted_spawn_delay = (
                        self.spawn_delay / self.speed_multiplier
                    )
                    self.next_balloon_time = (
                        self.clock_ticks + adjusted_spawn_delay
                    )

            # 1) Towers fire first, so pops replace visuals immediately
            for tower in self.towers:
                tower.update(self.speed_multiplier)
                tower.update_angle(self.balloons)
                popped = tower.attack(self.balloons, current_time)
                if popped:
                    for balloon, reward in popped:
                        self.money += reward
                if hasattr(tower, "rect") and tower.rect:
                    tower.rect.centerx = int(tower.x)
                    tower.rect.centery = int(tower.y)
                tower.update()

            # 2) Now move & draw all remaining balloons
            for balloon in self.balloons[:]:
                reached_end = balloon.move()
                if reached_end:
                    self.lives -= balloon.damage
                    self.balloons.remove(balloon)
                    continue

                # draw living balloons
                balloon.draw(self.screen)
                if balloon.health <= 0:
                    # (this handles any stragglers popped by non-tower effects)
                    self.money += balloon.reward
                    self.balloons.remove(balloon)

            # Draw tower sprites on top of balloons
            self.tower_sprites.draw(self.screen)

            # Draw UI and stats
            self.ui.draw(self.screen)
            self.draw_stats()

            pygame.display.flip()

            # round-complete detection:
            if (
                self.round_started
                and not self.balloons
                and not self.balloons_queue
            ):
                # Reward scales: $20 per round number
                round_finished = self.current_round
                self.current_round += 1
                self.money += 20 * round_finished
                self.round_started = False

            # End game or advance round
            if self.current_round > self.last_round or self.lives <= 0:
                self.end_game()
                break

        pygame.quit()


if __name__ == "__main__":
    game = Game()
    game.run()
