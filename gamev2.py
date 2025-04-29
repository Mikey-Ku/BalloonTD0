"""
Main game file that initializes and runs the game loop.
"""

import pygame
from mapv2 import load_waypoints_from_csv, Track
from balloon import (
    RedBalloon,
    BlueBalloon,
    GreenBalloon,
    YellowBalloon,
    PinkBalloon,
)
from user_interface import GameUI


class Game:
    def __init__(self):
        # Existing initialization code
        pygame.init()
        self.screen = pygame.display.set_mode((800, 600))
        pygame.display.set_caption("Balloon TD")
        self.background = pygame.image.load("Background.webp").convert()
        self.background = pygame.transform.scale(self.background, (800, 600))
        self.track = Track()
        self.waypoints = load_waypoints_from_csv("equidistant_points.csv")
        self.track.waypoints = self.waypoints
        self.balloons = []
        self.towers = []
        self.tower_sprites = pygame.sprite.Group()
        self.money = 1000
        self.lives = 100
        self.round_started = False
        self.balloons_to_spawn = 10
        self.spawn_delay = 500
        self.last_spawn_time = 0
        self.current_wave = 1
        self.ui = GameUI(self)
        self.font = pygame.font.SysFont(None, 36)
        self.round_started = False
        self.balloons_to_spawn = 0
        self.current_round = 1

        self.rounds_config = [
            {"balloons": [("pink", 5)], "spawn_delay": 200},
        ]

    # Existing methods remain unchanged
    def draw_stats(self):
        """Draw money, lives, and round counter on screen"""
        money_text = self.font.render(f"Money: ${self.money}", True, (0, 0, 0))
        lives_text = self.font.render(f"Lives: {self.lives}", True, (0, 0, 0))
        round_text = self.font.render(
            f"Round {self.current_round}", True, (0, 0, 0)
        )

        self.screen.blit(money_text, (10, 10))
        self.screen.blit(lives_text, (10, 50))
        self.screen.blit(round_text, (650, 10))  # top-right-ish

    def prepare_round(self):
        """Prepare the balloon queue based on current round's config."""
        self.balloons_queue = []
        round_index = self.current_round - 1

        if round_index < len(self.rounds_config):
            round_info = self.rounds_config[round_index]
            self.spawn_delay = round_info["spawn_delay"]

            for balloon_type, count in round_info["balloons"]:
                for _ in range(count):
                    self.balloons_queue.append(balloon_type)

    def run(self):
        """Main game loop"""
        clock = pygame.time.Clock()
        running = True

        while running:
            current_time = pygame.time.get_ticks()
            # Draw background instead of white fill
            self.screen.blit(self.background, (0, 0))

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_SPACE and not self.round_started:
                        self.round_started = True
                        self.last_spawn_time = current_time
                        self.prepare_round()

                # Handle UI events
                self.ui.handle_event(event)

            # spawn balloons
            if self.round_started and self.balloons_queue:
                if current_time - self.last_spawn_time >= self.spawn_delay:
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

                    self.last_spawn_time = current_time

            # move + draw balloons
            for balloon in self.balloons[:]:
                reached_end = balloon.move()
                balloon.draw(self.screen)

                if reached_end:
                    self.lives -= balloon.damage
                    self.balloons.remove(balloon)

                elif balloon.health <= 0:
                    self.money += balloon.reward
                    self.balloons.remove(balloon)

            # End the round when no balloons are left and none are spawning
            if (
                self.round_started
                and not self.balloons_queue
                and len(self.balloons) == 0
            ):
                self.round_started = False
                self.current_round += 1

            # Update tower sprite positions
            for tower in self.towers:
                # Handle tower attacks
                balloons_to_remove = tower.attack(self.balloons, current_time)
                if balloons_to_remove is not None:
                    for balloon in balloons_to_remove:
                        if balloon in self.balloons:
                            self.balloons.remove(balloon)

                # Update sprite position if it has a rect
                if hasattr(tower, "rect") and tower.rect:
                    tower.rect.centerx = int(tower.x)
                    tower.rect.centery = int(tower.y)

            # Draw tower sprites instead of circles
            self.tower_sprites.draw(self.screen)

            # draw UI
            self.ui.draw(self.screen)
            self.draw_stats()

            pygame.display.flip()
            clock.tick(60)

        pygame.quit()


if __name__ == "__main__":
    game = Game()
    game.run()
