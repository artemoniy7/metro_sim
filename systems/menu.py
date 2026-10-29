"""Frameless, custom-drawn main menu for Metro Sim."""
import math
import pygame

class MainMenu:
    BG = (11, 17, 25)
    PANEL = (21, 31, 42)
    PANEL_HOVER = (32, 46, 60)
    TEXT = (239, 244, 248)
    MUTED = (143, 160, 174)
    RED = (218, 40, 53)
    RED_HOVER = (239, 57, 68)
    LINE = (46, 64, 79)

    def __init__(self, size):
        self.width, self.height = size
        self.settings_open = False
        self.elapsed = 0.0
        self.buttons = {}
        self.title_font = pygame.font.SysFont("arial", 58, bold=True)
        self.subtitle_font = pygame.font.SysFont("arial", 21)
        self.button_font = pygame.font.SysFont("arial", 22, bold=True)
        self.small_font = pygame.font.SysFont("arial", 14)
        self.settings_font = pygame.font.SysFont("arial", 30, bold=True)
        self.window = None
        self.dragging = False
        self.drag_offset = (0, 0)
        try:
            from pygame._sdl2 import Window
            self.window = Window.from_display_module()
        except (ImportError, AttributeError, pygame.error):
            pass

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            if self.settings_open:
                self.settings_open = False
            else:
                return "quit"

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.buttons.get("close", pygame.Rect(0, 0, 0, 0)).collidepoint(event.pos):
                return "quit"
            if self.buttons.get("minimize", pygame.Rect(0, 0, 0, 0)).collidepoint(event.pos):
                pygame.display.iconify()
                return None

            if event.pos[1] < 42 and event.pos[0] < self.width - 100:
                self.dragging = True
                if self.window is not None:
                    self.drag_offset = (event.pos[0], event.pos[1])
                return None

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

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging = False
        if event.type == pygame.MOUSEMOTION and self.dragging and self.window is not None:
            try:
                current_x, current_y = self.window.position
                self.window.position = (
                    current_x + event.rel[0], current_y + event.rel[1]
                )
            except (pygame.error, AttributeError, TypeError):
                pass
        return None

    def update(self, dt):
        self.elapsed += dt

    @staticmethod
    def _text(surface, text, font, color, position):
        surface.blit(font.render(text, True, color), position)

    def _button(self, surface, key, label, rect, mouse_pos, primary=False):
        self.buttons[key] = rect
        hovered = rect.collidepoint(mouse_pos)
        color = (self.RED_HOVER if hovered else self.RED) if primary else (
            self.PANEL_HOVER if hovered else self.PANEL
        )
        pygame.draw.rect(surface, color, rect, border_radius=8)
        if not primary:
            pygame.draw.rect(surface, self.LINE, rect, width=1, border_radius=8)
        text = self.button_font.render(label, True, self.TEXT)
        surface.blit(text, text.get_rect(midleft=(rect.x + 22, rect.centery)))
        if primary:
            arrow = self.button_font.render("→", True, self.TEXT)
            surface.blit(arrow, arrow.get_rect(midright=(rect.right - 20, rect.centery)))

    def _draw_window_controls(self, surface):
        width = surface.get_width()
        self.buttons["minimize"] = pygame.Rect(width - 76, 8, 28, 26)
        self.buttons["close"] = pygame.Rect(width - 42, 8, 30, 26)
        pygame.draw.line(surface, self.MUTED, (width - 68, 21), (width - 56, 21), 2)
        close = self.buttons["close"]
        hover = close.collidepoint(pygame.mouse.get_pos())
        if hover:
            pygame.draw.rect(surface, self.RED, close, border_radius=5)
        pygame.draw.line(surface, self.TEXT, (close.x + 9, close.y + 7),
                         (close.right - 9, close.bottom - 7), 2)
        pygame.draw.line(surface, self.TEXT, (close.right - 9, close.y + 7),
                         (close.x + 9, close.bottom - 7), 2)

    def render(self, surface):
        width, height = surface.get_size()
        self.width, self.height = width, height
        self.buttons.clear()
        surface.fill(self.BG)

        # Thin framing and abstract tunnel geometry — no train image on the title screen.
        pygame.draw.rect(surface, (17, 27, 38), (0, 0, width, 42))
        pygame.draw.line(surface, self.LINE, (0, 42), (width, 42), 1)
        self._text(surface, "M  /  METRO SIM", self.small_font, self.MUTED, (24, 14))
        self._draw_window_controls(surface)

        # A stylized tunnel of nested arches creates depth on the right.
        cx, cy = int(width * 0.79), int(height * 0.57)
        for i in range(6, 0, -1):
            rw = int(width * (0.13 + i * 0.045))
            rh = int(height * (0.19 + i * 0.075))
            rect = pygame.Rect(cx - rw, cy - rh // 2, rw * 2, rh)
            col = (15 + i * 2, 24 + i * 2, 34 + i * 2)
            pygame.draw.arc(surface, col, rect, math.pi, math.tau, 3)
            pygame.draw.line(surface, col, (rect.left, cy), (rect.left, height), 2)
            pygame.draw.line(surface, col, (rect.right, cy), (rect.right, height), 2)

        # Route line and station nodes, styled like a schematic metro map.
        route_y = int(height * 0.26)
        route_start, route_end = int(width * 0.48), int(width * 0.94)
        pygame.draw.line(surface, self.RED, (route_start, route_y), (route_end, route_y), 4)
        nodes = [route_start, int(width * 0.61), int(width * 0.73),
                 int(width * 0.84), route_end]
        for i, x in enumerate(nodes):
            pulse = 5 if i == 2 and int(self.elapsed * 2) % 2 == 0 else 0
            pygame.draw.circle(surface, self.BG, (x, route_y), 9 + pulse)
            pygame.draw.circle(surface, self.TEXT if i == 2 else self.RED, (x, route_y), 5)
        self._text(surface, "ЛИНИЯ 9", self.small_font, self.MUTED,
                   (route_start, route_y - 29))
        self._text(surface, "25 СТАНЦИЙ", self.small_font, self.MUTED,
                   (route_end - 80, route_y + 18))

        # Subtle red light and track lines at the bottom of the scene.
        glow = pygame.Surface((width // 2, 8), pygame.SRCALPHA)
        pygame.draw.rect(glow, (218, 40, 53, 50), (0, 0, glow.get_width(), 8), border_radius=4)
        surface.blit(glow, (width // 2, int(height * 0.84)))
        pygame.draw.line(surface, (35, 49, 62), (int(width * 0.48), int(height * 0.86)),
                         (width, int(height * 0.86)), 2)
        pygame.draw.line(surface, (35, 49, 62), (int(width * 0.53), int(height * 0.89)),
                         (width, int(height * 0.89)), 1)

        left = int(width * 0.075)
        top = int(height * 0.19)
        self._text(surface, "СИМУЛЯТОР", self.small_font, self.RED, (left + 2, top - 20))
        self._text(surface, "METRO", self.title_font, self.TEXT, (left, top + 5))
        self._text(surface, "SIMULATOR", self.title_font, self.RED,
                   (left, top + 68))
        self._text(surface, "МОСКОВСКОЕ МЕТРО — ТВОЙ МАРШРУТ", self.subtitle_font,
                   self.MUTED, (left + 3, top + 148))
        pygame.draw.rect(surface, self.RED, (left + 3, top + 194, 48, 4), border_radius=2)
        self._text(surface, "Управляй поездом. Соблюдай интервалы.", self.subtitle_font,
                   self.TEXT, (left + 3, top + 216))

        mouse_pos = pygame.mouse.get_pos()
        button_x, button_y = left, int(height * 0.61)
        button_width = min(350, int(width * 0.34))
        self._button(surface, "start", "Начать поездку",
                     pygame.Rect(button_x, button_y, button_width, 56), mouse_pos, primary=True)
        self._button(surface, "settings", "Настройки",
                     pygame.Rect(button_x, button_y + 70, button_width, 50), mouse_pos)
        self._button(surface, "quit", "Выход",
                     pygame.Rect(button_x, button_y + 132, button_width, 50), mouse_pos)

        self._text(surface, "BUILD 01  •  РАННЯЯ ВЕРСИЯ", self.small_font,
                   (99, 117, 132), (left + 2, height - 29))

        if self.settings_open:
            self._render_settings(surface)

    def _render_settings(self, surface):
        width, height = surface.get_size()
        overlay = pygame.Surface((width, height), pygame.SRCALPHA)
        overlay.fill((3, 8, 13, 205))
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
