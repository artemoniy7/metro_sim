"""Custom main menu for Metro Sim, drawn directly with Pygame."""
import math
from pathlib import Path

import pygame

from settings import ASSETS_DIR


class MainMenu:
    """A single-window menu with custom-drawn controls and train artwork."""

    BG = (13, 20, 29)
    PANEL = (22, 32, 44)
    PANEL_HOVER = (35, 49, 64)
    TEXT = (239, 244, 248)
    MUTED = (151, 168, 181)
    RED = (218, 40, 53)
    RED_HOVER = (239, 57, 68)
    LINE = (53, 72, 88)

    def __init__(self, size):
        self.width, self.height = size
        self.settings_open = False
        self.elapsed = 0.0
        self.buttons = {}
        self.title_font = pygame.font.SysFont("arial", 56, bold=True)
        self.subtitle_font = pygame.font.SysFont("arial", 22)
        self.button_font = pygame.font.SysFont("arial", 23, bold=True)
        self.small_font = pygame.font.SysFont("arial", 15)
        self.settings_font = pygame.font.SysFont("arial", 30, bold=True)

        train_path = ASSETS_DIR / "trains" / "81-760" / "81-760-loco.png"
        try:
            self.train_image = pygame.image.load(str(train_path)).convert_alpha()
        except (pygame.error, OSError):
            self.train_image = None

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            if self.settings_open:
                self.settings_open = False
            else:
                return "quit"

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.settings_open:
                if self.buttons.get("back", pygame.Rect(0, 0, 0, 0)).collidepoint(event.pos):
                    self.settings_open = False
                return None

            if self.buttons.get("start", pygame.Rect(0, 0, 0, 0)).collidepoint(event.pos):
                return "start"
            if self.buttons.get("settings", pygame.Rect(0, 0, 0, 0)).collidepoint(event.pos):
                self.settings_open = True
            if self.buttons.get("quit", pygame.Rect(0, 0, 0, 0)).collidepoint(event.pos):
                return "quit"
        return None

    def update(self, dt):
        self.elapsed += dt

    def _text(self, surface, text, font, color, position):
        image = font.render(text, True, color)
        surface.blit(image, position)

    def _button(self, surface, key, label, rect, mouse_pos, primary=False):
        self.buttons[key] = rect
        hovered = rect.collidepoint(mouse_pos)
        if primary:
            color = self.RED_HOVER if hovered else self.RED
        else:
            color = self.PANEL_HOVER if hovered else self.PANEL
        pygame.draw.rect(surface, color, rect, border_radius=8)
        if not primary:
            pygame.draw.rect(surface, self.LINE, rect, width=1, border_radius=8)
        text = self.button_font.render(label, True, self.TEXT)
        surface.blit(text, text.get_rect(midleft=(rect.x + 24, rect.centery)))
        if primary:
            arrow = self.button_font.render("›", True, self.TEXT)
            surface.blit(arrow, arrow.get_rect(midright=(rect.right - 22, rect.centery - 1)))

    def render(self, surface):
        width, height = surface.get_size()
        self.width, self.height = width, height
        surface.fill(self.BG)

        # Soft, layered shapes create depth without using a downloaded photo.
        for index in range(8):
            x = int(width * 0.40 + index * width * 0.105)
            color = (15 + index, 24 + index, 34 + index)
            pygame.draw.polygon(
                surface, color,
                [(x, 0), (min(width, x + 170), 0),
                 (min(width, x - 90), height), (max(0, x - 260), height)]
            )

        # Metro-line motif.
        route_y = int(height * 0.19)
        pygame.draw.line(surface, self.LINE, (int(width * 0.48), route_y),
                         (width, route_y), 3)
        for x in (int(width * 0.54), int(width * 0.68), int(width * 0.82), int(width * 0.96)):
            pygame.draw.circle(surface, self.BG, (x, route_y), 7)
            pygame.draw.circle(surface, self.MUTED, (x, route_y), 4)

        # The existing in-game train sprite is intentionally clipped by the
        # right edge, as if the train is entering the menu scene.
        if self.train_image is not None:
            target_height = max(100, int(height * 0.34))
            target_width = int(self.train_image.get_width() * target_height / self.train_image.get_height())
            train = pygame.transform.smoothscale(self.train_image, (target_width, target_height))
            bob = int(math.sin(self.elapsed * 0.65) * 3)
            train_x = int(width * 0.69)
            train_y = int(height * 0.48) + bob
            surface.blit(train, (train_x, train_y))

        # Darken the left side behind the title so it stays readable.
        shade = pygame.Surface((int(width * 0.62), height), pygame.SRCALPHA)
        shade.fill((8, 14, 21, 185))
        surface.blit(shade, (0, 0))

        left = int(width * 0.075)
        top = int(height * 0.19)
        self._text(surface, "METRO", self.title_font, self.TEXT, (left, top))
        title_width = self.title_font.size("METRO")[0]
        self._text(surface, "SIMULATOR", self.title_font, self.RED,
                   (left + title_width + 13, top))
        self._text(surface, "СИМУЛЯТОР МОСКОВСКОГО МЕТРО", self.subtitle_font,
                   self.MUTED, (left + 3, top + 76))

        accent_y = top + 126
        pygame.draw.rect(surface, self.RED, (left + 2, accent_y, 52, 4), border_radius=2)
        self._text(surface, "Почувствуй ритм подземного города",
                   self.subtitle_font, self.TEXT, (left + 2, accent_y + 22))

        mouse_pos = pygame.mouse.get_pos()
        button_width = min(360, int(width * 0.34))
        button_height = 58
        button_x = left
        button_y = int(height * 0.60)
        self._button(surface, "start", "Начать поездку",
                     pygame.Rect(button_x, button_y, button_width, button_height),
                     mouse_pos, primary=True)
        self._button(surface, "settings", "Настройки",
                     pygame.Rect(button_x, button_y + 72, button_width, 52),
                     mouse_pos)
        self._button(surface, "quit", "Выход",
                     pygame.Rect(button_x, button_y + 138, button_width, 52),
                     mouse_pos)

        footer_y = height - 35
        self._text(surface, "METRO SIM  •  EARLY DEVELOPMENT BUILD",
                   self.small_font, (106, 124, 139), (left + 2, footer_y))

        if self.settings_open:
            self._render_settings(surface)

    def _render_settings(self, surface):
        width, height = surface.get_size()
        overlay = pygame.Surface((width, height), pygame.SRCALPHA)
        overlay.fill((3, 8, 13, 190))
        surface.blit(overlay, (0, 0))

        panel = pygame.Rect(0, 0, min(520, width - 40), 300)
        panel.center = (width // 2, height // 2)
        pygame.draw.rect(surface, self.PANEL, panel, border_radius=14)
        pygame.draw.rect(surface, self.LINE, panel, width=1, border_radius=14)

        title = self.settings_font.render("Настройки", True, self.TEXT)
        surface.blit(title, (panel.x + 30, panel.y + 28))
        self._text(surface, "Настройки графики и звука появятся позже.",
                   self.subtitle_font, self.MUTED, (panel.x + 30, panel.y + 91))
        self._text(surface, "Пока игра использует параметры из settings.py.",
                   self.small_font, self.MUTED, (panel.x + 30, panel.y + 126))

        back_rect = pygame.Rect(panel.x + 30, panel.bottom - 78, panel.width - 60, 48)
        self._button(surface, "back", "Назад", back_rect, pygame.mouse.get_pos(), primary=True)
