"""Module that defines the user interface for the game."""

import pygame


class TowerPurchasingUI:
    """Class that handles the user interface for purchasing towers."""

    def __init__(self, rect, text, callback, tower_cost=0):
        """
        Initialize the UI element with a rectangle, text, and callback function.

        Args:
            rect: Tuple (x, y, width, height) for the button
            text: Button text
            callback: Function to call when clicked
            tower_cost: Cost of the tower for display
        """
        self.rect = pygame.Rect(rect)
        self.text = text
        self.callback = callback
        self.font = pygame.font.SysFont(None, 24)
        self.cost = tower_cost
        self.hover = False

    def draw(self, screen, money=0):
        """
        Draw the UI element on the screen.

        Args:
            screen: Pygame surface to draw on
            money: Current player money for color coding
        """
        color = (200, 200, 200)
        pygame.draw.rect(screen, color, self.rect)

    def handle_event(self, event):
        """
        Handle events for the UI element.

        Returns:
            bool: True if the event was handled, False otherwise
        """
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.callback()
                return True
        return False


class GameUI:
    """Manages the game's user interface and tower placement."""

    def __init__(self, game_instance):
        """Initialize the game UI with purchasing buttons and state."""
        self.game = game_instance
        self.selected_tower_type = None
        self.selected_tower = None

        button_width = 140
        button_height = 40
        start_y = game_instance.height - button_height - 10

        self.purchase_buttons = [
            TowerPurchasingUI(
                (10, start_y, button_width, button_height),
                "Dart Tower $100",
                lambda: self.select_tower("dart"),
                100,
            ),
            TowerPurchasingUI(
                (button_width + 20, start_y, button_width, button_height),
                "Sniper Tower $200",
                lambda: self.select_tower("sniper"),
                200,
            ),
        ]

        self.selected_tower_radius = 15

    def select_tower(self, tower_type):
        """Start tower placement if player has enough money."""
        costs = {"dart": 100, "sniper": 200, "bomb": 300}
        cost = costs[tower_type]

        if self.game.money >= cost:
            self.selected_tower_type = tower_type

    def draw(self, screen):
        """Draw all UI elements and tower preview."""
        # Draw purchase buttons
        for button in self.purchase_buttons:
            button.draw(screen, self.game.money)

        # Draw game stats (money, lives, wave)
        stats_text = (
            f"Money: ${self.game.money}  Lives: {self.game.lives}  Wave:"
            f" {self.game.current_wave}"
        )

        # Draw tower preview at mouse position if tower is selected for placement
        if self.selected_tower_type:
            mouse_pos = pygame.mouse.get_pos()
            ranges = {"dart": 120, "sniper": 250, "bomb": 150}

            # Determine if position is valid
            is_valid = self.game.track.is_valid_tower_position(*mouse_pos)

            # Draw range circle
            color = (0, 255, 0) if is_valid else (255, 0, 0)
            pygame.draw.circle(
                screen,
                color,
                mouse_pos,
                ranges[self.selected_tower_type],
                1,  # Just an outline
            )

            # Draw tower placeholder
            pygame.draw.circle(
                screen, color, mouse_pos, self.selected_tower_radius
            )

        # Draw selected tower indicator
        for tower in self.game.towers:
            if tower == self.selected_tower:
                # Draw a highlight circle around the selected tower
                pygame.draw.circle(
                    screen,
                    (255, 255, 0),  # Yellow
                    (int(tower.x), int(tower.y)),
                    self.selected_tower_radius + 5,
                    2,  # Thickness
                )

                # Draw tower range
                pygame.draw.circle(
                    screen,
                    (100, 100, 255),
                    (int(tower.x), int(tower.y)),
                    tower.range,
                    1,  # Just an outline
                )

                # Draw simple upgrade/sell buttons
                font = pygame.font.SysFont(None, 20)

                # Upgrade button
                upgrade_text = f"Upgrade: ${tower.upgrade_cost}"
                upgrade_surface = font.render(upgrade_text, True, (0, 0, 0))
                upgrade_rect = pygame.Rect(10, 40, 150, 30)
                pygame.draw.rect(screen, (200, 200, 200), upgrade_rect)
                pygame.draw.rect(screen, (0, 0, 0), upgrade_rect, 1)
                screen.blit(
                    upgrade_surface, (upgrade_rect.x + 5, upgrade_rect.y + 5)
                )

                # Sell button
                sell_price = int(tower.cost * 0.7)  # 70% of cost
                sell_text = f"Sell: ${sell_price}"
                sell_surface = font.render(sell_text, True, (0, 0, 0))
                sell_rect = pygame.Rect(10, 80, 150, 30)
                pygame.draw.rect(screen, (200, 200, 200), sell_rect)
                pygame.draw.rect(screen, (0, 0, 0), sell_rect, 1)
                screen.blit(sell_surface, (sell_rect.x + 5, sell_rect.y + 5))

                # Store button positions for event handling
                self.upgrade_rect = upgrade_rect
                self.sell_rect = sell_rect

    def handle_event(self, event):
        """Handle UI events including tower placement."""
        # Handle tower placement
        if self.selected_tower_type and event.type == pygame.MOUSEBUTTONUP:
            pos = pygame.mouse.get_pos()
            if self.game.track.is_valid_tower_position(*pos):
                # Create the appropriate tower
                tower_classes = {
                    "dart": DartTower,
                    "sniper": SniperTower,
                    "bomb": BombTower,
                }
                tower_costs = {"dart": 100, "sniper": 200, "bomb": 300}

                tower = tower_classes[self.selected_tower_type]()
                tower.x, tower.y = pos
                tower.position = pos  # For the track's use

                self.game.money -= tower_costs[self.selected_tower_type]
                self.game.towers.append(tower)
                self.selected_tower_type = None
                return True

        # Handle selecting existing towers
        if (
            event.type == pygame.MOUSEBUTTONDOWN
            and not self.selected_tower_type
        ):
            pos = pygame.mouse.get_pos()

            # First check if upgrade/sell buttons were clicked
            if self.selected_tower:
                if hasattr(
                    self, "upgrade_rect"
                ) and self.upgrade_rect.collidepoint(pos):
                    # Upgrade tower if enough money
                    if self.game.money >= self.selected_tower.upgrade_cost:
                        self.game.money -= self.selected_tower.upgrade_cost
                        self.selected_tower.upgrade()
                    return True

                if hasattr(self, "sell_rect") and self.sell_rect.collidepoint(
                    pos
                ):
                    # Sell tower
                    sell_price = int(self.selected_tower.cost * 0.7)
                    self.game.money += sell_price
                    self.game.towers.remove(self.selected_tower)
                    self.selected_tower = None
                    return True

            # Then check if a tower was clicked
            for tower in self.game.towers:
                # Simple circular hit detection
                if (
                    (tower.x - pos[0]) ** 2 + (tower.y - pos[1]) ** 2
                ) <= self.selected_tower_radius**2:
                    self.selected_tower = tower
                    return True

            # If clicked elsewhere, deselect tower
            if self.selected_tower:
                self.selected_tower = None
                return True

        # Handle button clicks
        for button in self.purchase_buttons:
            if button.handle_event(event):
                return True

        return False
