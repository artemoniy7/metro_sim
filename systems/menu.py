"""Simple full-screen main menu for Metro Sim."""
import pygame


class MainMenu:
    BG = (15, 19, 25)
    PANEL = (27, 33, 42)
    PANEL_HOVER = (39, 47, 58)
    TEXT = (241, 243, 246)
    MUTED = (157, 166, 178)
    ACCENT = (220, 48, 59)
    LINE = (49, 58, 70)

    def __init__(self, size):
        self.width, self.height = size
        self.settings_open = False
        self.buttons = {}
        self.title_font = pygame.font.SysFont("arial", 58, bold=True)
        self.subtitle_font = pygame.font.SysFont("arial", 22)
        self.button_font = pygame.font.SysFont("arial", 22)
        self.small_font = pygame.font.SysFont("arial", 15)
        self.settings_font = pygame.font.SysFont("arial", 30, bold=True)

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
        """Keep the menu interface compatible with the main game loop."""
        pass

    @staticmethod
    def _text(surface, text, font, color, position):
        surface.blit(font.render(text, True, color), position)

    def _button(self, surface, key, label, rect, mouse_pos, primary=False):
        self.buttons[key] = rect
        hovered = rect.collidepoint(mouse_pos)
        color = self.ACCENT if primary else (self.PANEL_HOVER if hovered else self.PANEL)
        if primary and hovered:
            color = (239, 62, 72)
        pygame.draw.rect(surface, color, rect, border_radius=8)
        if not primary:
            pygame.draw.rect(surface, self.LINE, rect, 1, border_radius=8)
        text = self.button_font.render(label, True, self.TEXT)
        surface.blit(text, text.get_rect(midleft=(rect.x + 22, rect.centery)))
        if primary:
            arrow = self.button_font.render("→", True, self.TEXT)
            surface.blit(arrow, arrow.get_rect(midright=(rect.right - 20, rect.centery)))

    def render(self, surface):
        width, height = surface.get_size()
        self.width, self.height = width, height
        self.buttons.clear()
        surface.fill(self.BG)

        # Quiet architectural shapes provide atmosphere without suggesting a specific metro line.
        right = int(width * 0.59)
        for i in range(5):
            inset = i * int(width * 0.035)
            rect = pygame.Rect(right + inset, int(height * 0.14) + i * 14,
                               max(1, width - right - inset * 2), int(height * 0.68) - i * 28)
            if rect.width > 0 and rect.height > 0:
                pygame.draw.rect(surface, (18 + i * 2, 23 + i * 2, 31 + i * 2),
                                 rect, width=2, border_radius=4)
        pygame.draw.line(surface, (37, 44, 54), (right, int(height * 0.82)),
                         (width - 40, int(height * 0.82)), 2)
        pygame.draw.line(surface, (37, 44, 54), (right + 35, int(height * 0.86)),
                         (width - 70, int(height * 0.86)), 1)

        left = int(width * 0.09)
        top = int(height * 0.23)
        pygame.draw.rect(surface, self.ACCENT, (left, top, 5, 38), border_radius=2)
        self._text(surface, "METRO SIM", self.title_font, self.TEXT, (left + 22, top - 6))
        self._text(surface, "СИМУЛЯТОР МАШИНИСТА", self.subtitle_font, self.MUTED,
                   (left + 24, top + 67))
        self._text(surface, "Управляй поездом и следи за движением.", self.subtitle_font,
                   self.TEXT, (left + 24, top + 111))

        button_x = left + 24
        button_y = int(height * 0.57)
        button_width = min(360, int(width * 0.31))
        self._button(surface, "start", "Начать игру",
                     pygame.Rect(button_x, button_y, button_width, 58), pygame.mouse.get_pos(), True)
        self._button(surface, "settings", "Настройки",
                     pygame.Rect(button_x, button_y + 74, button_width, 52), pygame.mouse.get_pos())
        self._button(surface, "quit", "Выход",
                     pygame.Rect(button_x, button_y + 140, button_width, 52), pygame.mouse.get_pos())
        if self.settings_open:
            self._render_settings(surface)

    def _render_settings(self, surface):
        width, height = surface.get_size()
        overlay = pygame.Surface((width, height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 190))
        surface.blit(overlay, (0, 0))
        panel = pygame.Rect(0, 0, min(520, width - 40), 280)
        panel.center = (width // 2, height // 2)
        pygame.draw.rect(surface, self.PANEL, panel, border_radius=12)
        pygame.draw.rect(surface, self.LINE, panel, 1, border_radius=12)
        self._text(surface, "Настройки", self.settings_font, self.TEXT,
                   (panel.x + 30, panel.y + 28))
        self._text(surface, "Параметры графики и звука появятся позже.",
                   self.subtitle_font, self.MUTED, (panel.x + 30, panel.y + 91))
        back_rect = pygame.Rect(panel.x + 30, panel.bottom - 76, panel.width - 60, 46)
        self._button(surface, "back", "Назад", back_rect, pygame.mouse.get_pos(), True)
