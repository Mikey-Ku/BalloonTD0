"""
Main game file that initializes and runs the game loop.
"""

import pygame
from map import Track, load_waypoints_from_csv
from balloon import RedBalloon, BlueBalloon
from towers import Tower
from user_interface import GameUI


class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((800, 600))
        pygame.display.set_caption("Balloon TD")

        self.track = Track()
        self.waypoints = load_waypoints_from_csv("waypoints_final.csv")
        self.track.waypoints = self.waypoints

        self.balloons = []
        self.towers = []
        self.money = 1000
        self.lives = 100
        self.round_started = False
        self.balloons_to_spawn = 10
        self.spawn_delay = 500  # milliseconds between spawns
        self.last_spawn_time = 0
        self.ui = GameUI(self)

        # Font for displaying stats
        self.font = pygame.font.SysFont(None, 36)

    def draw_stats(self):
        """Draw money and lives on screen"""
        money_text = self.font.render(f"Money: ${self.money}", True, (0, 0, 0))
        lives_text = self.font.render(f"Lives: {self.lives}", True, (0, 0, 0))
        self.screen.blit(money_text, (10, 10))
        self.screen.blit(lives_text, (10, 50))

    def run(self):
        """Main game loop"""
        clock = pygame.time.Clock()
        running = True

        while running:
            self.screen.fill((255, 255, 255))  # clear screen

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_SPACE:
                        self.round_started = True
                        self.last_spawn_time = pygame.time.get_ticks()

            # spawn balloons
            current_time = pygame.time.get_ticks()
            if self.round_started and self.balloons_to_spawn > 0:
                if current_time - self.last_spawn_time >= self.spawn_delay:
                    self.balloons.append(RedBalloon(self.waypoints))
                    self.balloons_to_spawn -= 1
                    self.last_spawn_time = current_time

            # move + draw balloons
            for balloon in self.balloons[:]:
                reached_end = balloon.move()
                balloon.draw(self.screen)
                if reached_end:
                    self.lives -= balloon.damage
                    self.balloons.remove(balloon)

            # draw track
            self.track.draw(self.screen)

            pygame.display.flip()
            clock.tick(60)

        pygame.quit()


if __name__ == "__main__":
    game = Game()
    game.run()
