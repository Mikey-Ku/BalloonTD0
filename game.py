"""
Main game file that initializes and runs the game loop.
"""

import pygame
from map import Track
from balloon import Balloon
from towers import Tower
from user_interface import GameUI


class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((800, 600))
        pygame.display.set_caption("Balloon TD")

        self.track = Track()
        # Define path waypoints
        path_points = []
        for x, y in path_points:
            self.track.add_waypoint(x, y)

        Balloon.waypoints = self.track.waypoints
        self.balloons = []
        self.towers = []
        self.money = 1000
        self.lives = 100
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
        clock = pygame.time.Clock()
        running = True

        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                self.ui.handle_event(event)

            self.screen.fill((144, 238, 144))  # Light green background

            self.track.draw(self.screen)
            for tower in self.towers:
                pygame.draw.circle(
                    self.screen, (50, 50, 50), (int(tower.x), int(tower.y)), 20
                )
                # Draw tower range
                pygame.draw.circle(
                    self.screen,
                    (100, 100, 100),
                    (int(tower.x), int(tower.y)),
                    int(tower.range),
                    1,
                )

            self.ui.draw(self.screen)
            self.draw_stats()

            pygame.display.flip()
            clock.tick(60)

        pygame.quit()


if __name__ == "__main__":
    game = Game()
    game.run()
