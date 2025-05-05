"""Module for managing the user interface in the Balloon Tower Defense game.

This module defines the `GameUI`, `TowerMenu`, and `TowerPurchasingUI` classes,
which handle drawing the UI and processing user interactions.
"""

import pygame
from towers import DartTower, SniperTower, SuperTower, TacTower


class TowerPurchasingUI:
    """Class that handles the user interface for purchasing towers."""

    def __init__(self, rect, text, callback, tower_cost=0):
        """
        Initialize the UI element with a rectangle, text, and callback function.

        Args:
            rect (tuple): Tuple (x, y, width, height) for the button.
            text (str): Button text.
            callback (function): Function to call when clicked.
            tower_cost (int): Cost of the tower for display.
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
            screen (pygame.Surface): Pygame surface to draw on.
            money (int): Current player money for color coding.
        """
        if money >= self.cost:
            color = (150, 255, 150)  # Light green
            text_color = (0, 0, 0)
        else:
            color = (255, 150, 150)  # Light red
            text_color = (100, 100, 100)

        pygame.draw.rect(screen, color, self.rect)
        pygame.draw.rect(screen, (0, 0, 0), self.rect, 2)

        text_surface = self.font.render(self.text, True, text_color)
        text_rect = text_surface.get_rect(center=self.rect.center)
        screen.blit(text_surface, text_rect)

    def handle_event(self, event):
        """
        Handle events for the UI element.

        Args:
            event (pygame.event.Event): The Pygame event to handle.

        Returns:
            bool: True if the event was handled, False otherwise.
        """
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.callback()
                return True
        return False


class TowerMenu:
    """Handles the collapsible tower menu."""

    def __init__(self, rect, game_ui):
        """
        Initialize the tower menu.

        Args:
            rect (tuple): Tuple (x, y, width, height) for the menu.
            game_ui (GameUI): Reference to the game UI instance.
        """
        self.rect = pygame.Rect(rect)
        self.expanded = True
        self.game_ui = game_ui
        self.font = pygame.font.SysFont(None, 24)
        # Initialize toggle button on the left side
        self.toggle_button_rect = pygame.Rect(
            self.rect.x - 30, self.rect.y, 30, 30
        )
        # Initialize reopen button to the right of where the menu would be
        self.reopen_button_rect = pygame.Rect(
            self.rect.x + self.rect.width + 10, self.rect.y, 80, 30
        )

    def draw(self, screen):
        """
        Draw the tower menu.

        Args:
            screen (pygame.Surface): Pygame surface to draw on.
        """
        if self.expanded:
            # Draw toggle button
            pygame.draw.rect(screen, (100, 100, 100), self.toggle_button_rect)
            pygame.draw.rect(screen, (0, 0, 0), self.toggle_button_rect, 2)
            text_surface = self.font.render("<", True, (0, 0, 0))
            text_rect = text_surface.get_rect(
                center=self.toggle_button_rect.center
            )
            screen.blit(text_surface, text_rect)

            # Draw main menu
            pygame.draw.rect(screen, (200, 200, 200), self.rect)
            pygame.draw.rect(screen, (0, 0, 0), self.rect, 2)
            for button in self.game_ui.purchase_buttons:
                button.draw(screen, self.game_ui.game.money)
        else:
            # Only draw reopen button when collapsed
            self.reopen_button_rect.x = 700  # Match play button x-coordinate
            self.reopen_button_rect.y = 60  # Keep same y as expanded menu
            pygame.draw.rect(screen, (200, 200, 200), self.reopen_button_rect)
            pygame.draw.rect(screen, (0, 0, 0), self.reopen_button_rect, 2)
            reopen_text = self.font.render("Menu", True, (0, 0, 0))
            reopen_text_rect = reopen_text.get_rect(
                center=self.reopen_button_rect.center
            )
            screen.blit(reopen_text, reopen_text_rect)

    def handle_event(self, event):
        """
        Handle events for the tower menu.

        Args:
            event (pygame.event.Event): The Pygame event to handle.

        Returns:
            bool: True if the event was handled, False otherwise.
        """
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # Handle toggle button
            if self.toggle_button_rect.collidepoint(event.pos):
                self.expanded = not self.expanded
                return True

            # Handle reopen button when collapsed
            if not self.expanded and self.reopen_button_rect.collidepoint(
                event.pos
            ):
                self.expanded = True
                return True

            # Handle purchase buttons when expanded
            if self.expanded:
                for button in self.game_ui.purchase_buttons:
                    if button.handle_event(event):
                        return True

        return False


class GameUI:
    """Manages the game's user interface and tower placement."""

    def __init__(self, game_instance):
        """
        Initialize the game UI with purchasing buttons and state.

        Args:
            game_instance (Game): The game instance to interact with.
        """
        self.game = game_instance
        self.selected_tower_type = None
        self.selected_tower = None

        button_width = 180
        button_height = 40
        start_y = 70

        self.purchase_buttons = [
            TowerPurchasingUI(
                (610, start_y - 5, button_width, button_height),
                "Dart Monkey $100",
                lambda: self.select_tower("dart"),
                100,
            ),
            TowerPurchasingUI(
                (
                    610,
                    start_y + button_height + 5,
                    button_width,
                    button_height,
                ),
                "Sniper Monkey $200",
                lambda: self.select_tower("sniper"),
                200,
            ),
            TowerPurchasingUI(
                (
                    610,
                    start_y + (2 * button_height) + 15,
                    button_width,
                    button_height,
                ),
                "Tac Shooter $300",
                lambda: self.select_tower("tac"),
                300,
            ),
            TowerPurchasingUI(
                (
                    610,
                    start_y + (3 * button_height) + 25,
                    button_width,
                    button_height,
                ),
                "Super Monkey $2000",
                lambda: self.select_tower("super"),
                2000,
            ),
        ]
        self.tower_menu = TowerMenu((600, 60, button_width + 20, 200), self)

        self.selected_tower_radius = 15
        self.upgrade_rect = None
        self.sell_rect = None

    def select_tower(self, tower_type):
        """
        Start tower placement if player has enough money.

        Args:
            tower_type (str): The type of tower to select.
        """
        costs = {"dart": 100, "sniper": 200, "tac": 300, "super": 2000}
        cost = costs[tower_type]

        if self.game.money >= cost:
            self.selected_tower_type = tower_type

    def draw(self, screen):
        """
        Draw all UI elements and tower preview.

        Args:
            screen (pygame.Surface): Pygame surface to draw on.
        """
        self.tower_menu.draw(screen)
        if self.selected_tower_type:
            mouse_pos = pygame.mouse.get_pos()
            ranges = {"dart": 100, "sniper": 40, "tac": 50, "super": 200}

            is_valid = self.game.track.is_valid_tower_position(*mouse_pos)

            # Draw range circle
            color = (0, 255, 0) if is_valid else (255, 0, 0)
            pygame.draw.circle(
                screen,
                color,
                mouse_pos,
                ranges[self.selected_tower_type],
                1,
            )

            # Draw the actual tower sprite at the mouse position
            tower_classes = {
                "dart": DartTower,
                "sniper": SniperTower,
                "tac": TacTower,
                "super": SuperTower,
            }
            tower_preview = tower_classes[self.selected_tower_type]()
            tower_preview.x, tower_preview.y = mouse_pos
            tower_preview.update_position(*mouse_pos)
            tower_preview.update()
            screen.blit(tower_preview.image, tower_preview.rect)

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
                font = pygame.font.SysFont(None, 20)

                # Upgrade button
                upgrade_text = f"Upgrade: ${tower.upgrade_cost}"
                upgrade_surface = font.render(upgrade_text, True, (0, 0, 0))
                upgrade_rect = pygame.Rect(500, 550, 150, 30)
                pygame.draw.rect(
                    screen, (100, 100, 100), upgrade_rect
                )  # Darker background
                pygame.draw.rect(
                    screen, (50, 50, 50), upgrade_rect, 3
                )  # Thicker border
                screen.blit(
                    upgrade_surface, (upgrade_rect.x + 5, upgrade_rect.y + 5)
                )

                # Sell button
                sell_price = int(tower.cost * 0.7)  # 70% of cost
                sell_text = f"Sell: ${sell_price}"
                sell_surface = font.render(sell_text, True, (0, 0, 0))
                sell_rect = pygame.Rect(650, 550, 150, 30)
                pygame.draw.rect(
                    screen, (100, 100, 100), sell_rect
                )  # Darker background
                pygame.draw.rect(
                    screen, (50, 50, 50), sell_rect, 3
                )  # Thicker border
                screen.blit(sell_surface, (sell_rect.x + 5, sell_rect.y + 5))

                self.upgrade_rect = upgrade_rect
                self.sell_rect = sell_rect

        self.game.draw_stats()  # Ensure play/speed button is drawn

    def handle_event(self, event):
        """
        Handle UI events including tower placement.

        Args:
            event (pygame.event.Event): The Pygame event to handle.

        Returns:
            bool: True if the event was handled, False otherwise.
        """
        if self.tower_menu.handle_event(event):
            return True
        # Handle tower placement
        if self.selected_tower_type and event.type == pygame.MOUSEBUTTONUP:
            pos = pygame.mouse.get_pos()
            if self.game.track.is_valid_tower_position(*pos):
                # Create the appropriate tower
                tower_classes = {
                    "dart": DartTower,
                    "sniper": SniperTower,
                    "tac": TacTower,
                    "super": SuperTower,
                }
                tower_costs = {
                    "dart": 100,
                    "sniper": 200,
                    "tac": 300,
                    "super": 2000,
                }

                tower = tower_classes[self.selected_tower_type]()
                tower.x, tower.y = pos
                tower.position = pos  # For the track's use
                tower.update_position(pos[0], pos[1])

                self.game.money -= tower_costs[self.selected_tower_type]
                self.game.towers.append(tower)
                self.game.track.towers.append(tower)
                # Add the tower to the sprite group
                self.game.tower_sprites.add(tower)
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
                    sell_price = int(self.selected_tower.cost * 0.7)
                    self.game.money += sell_price
                    self.game.towers.remove(self.selected_tower)
                    self.game.track.towers.remove(self.selected_tower)
                    self.game.tower_sprites.remove(self.selected_tower)
                    self.selected_tower = None
                    return True
            for tower in self.game.towers:
                if (
                    (tower.x - pos[0]) ** 2 + (tower.y - pos[1]) ** 2
                ) <= self.selected_tower_radius**2:
                    self.selected_tower = tower
                    return True
            if self.selected_tower:
                self.selected_tower = None
                return True

        return False
