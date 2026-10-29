"""Simple full-screen main menu for Metro Sim."""
import pygame
from pathlib import Path


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
        self.hover_progress = {"start": 0.0, "settings": 0.0, "quit": 0.0}
        self.pending_action = None
        self.click_progress = 0.0
        self.completed_action = None
        # Use the bundled IBM Plex Sans family, with a system-font fallback.
        font_dir = Path(__file__).resolve().parent.parent / "assets" / "ui" / "fonts"
        self.title_font = self._load_font(font_dir / "IBMPlexSans-Bold.ttf", 58, bold=True)
        self.subtitle_font = self._load_font(font_dir / "IBMPlexSans-Regular.ttf", 22)
        self.button_font = self._load_font(font_dir / "IBMPlexSans-Medium.ttf", 22)
        self.small_font = self._load_font(font_dir / "IBMPlexSans-Regular.ttf", 15)
        self.settings_font = self._load_font(font_dir / "IBMPlexSans-SemiBold.ttf", 30, bold=True)

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            if self.settings_open:
                self.settings_open = False
            else:
                return "quit"

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.settings_open:
                if self.buttons.get("back", pygame.Rect(0, 0, 0, 0)).collidepoint(event.pos):
                    self.pending_action = "back"
                    self.click_progress = 0.0
                return None
            if self.pending_action is not None:
                return None
            for key in ("start", "settings", "quit"):
                if self.buttons.get(key, pygame.Rect(0, 0, 0, 0)).collidepoint(event.pos):
                    self.pending_action = key
                    self.click_progress = 0.0
                    break
        return None

    @staticmethod
    def _load_font(path, size, bold=False):
        try:
            return pygame.font.Font(str(path), size)
        except (FileNotFoundError, pygame.error):
            return pygame.font.SysFont("arial", size, bold=bold)

    def update(self, dt):
        """Animate button movement and return an action after the transition."""
        mouse_pos = pygame.mouse.get_pos()
        for key in self.hover_progress:
            rect = self.buttons.get(key)
            target = 1.0 if rect and rect.collidepoint(mouse_pos) and self.pending_action is None else 0.0
            step = min(1.0, dt * 7.0)
            if self.hover_progress[key] < target:
                self.hover_progress[key] = min(target, self.hover_progress[key] + step)
            else:
                self.hover_progress[key] = max(target, self.hover_progress[key] - step)

        if self.pending_action is not None:
            self.click_progress = min(1.0, self.click_progress + dt / 0.32)
            if self.click_progress >= 1.0:
                action = self.pending_action
                self.pending_action = None
                self.completed_action = action
                if action == "settings":
                    self.settings_open = True
                elif action == "back":
                    self.settings_open = False
                elif action in ("start", "quit"):
                    return action
        return None

    @staticmethod
    def _text(surface, text, font, color, position):
        surface.blit(font.render(text, True, color), position)

    def _button(self, surface, key, label, rect, mouse_pos, primary=False):
        self.buttons[key] = rect
        hovered = rect.collidepoint(mouse_pos)
        hover = self.hover_progress.get(key, 0.0)
        leaving = self.pending_action == key
        click = self.click_progress if leaving else 0.0

        # A restrained slide and scale replace the train animation.
        scale = 1.0 + 0.025 * hover + 0.035 * click
        draw_rect = rect.copy()
        draw_rect.width = int(rect.width * scale)
        draw_rect.height = int(rect.height * scale)
        draw_rect.center = (rect.centerx + int(7 * hover + 42 * click), rect.centery)

        color = self.ACCENT if primary else (self.PANEL_HOVER if hovered else self.PANEL)
        if primary and hovered:
            color = (239, 62, 72)
        pygame.draw.rect(surface, color, draw_rect, border_radius=8)
        if not primary:
            pygame.draw.rect(surface, self.LINE, draw_rect, 1, border_radius=8)

        text = self.button_font.render(label, True, self.TEXT)
        text_rect = text.get_rect(midleft=(draw_rect.x + 22, draw_rect.centery))
        surface.blit(text, text_rect)
        if primary:
            arrow = self.button_font.render("→", True, self.TEXT)
            surface.blit(arrow, arrow.get_rect(midright=(draw_rect.right - 20, draw_rect.centery)))

    def render(self, surface):
        width, height = surface.get_size()
        self.width, self.height = width, height
        self.buttons.clear()
        surface.fill(self.BG)

        # Subtle perspective strokes suggest a tunnel without boxing off the background.
        right = int(width * 0.57)
        vanish_x, vanish_y = int(width * 0.84), int(height * 0.40)
        line_colors = [(19, 24, 32), (22, 28, 37), (26, 32, 41)]
        anchors = [
            ((right, int(height * 0.05)), (width - 18, int(height * 0.01))),
            ((right - 12, int(height * 0.25)), (width - 8, int(height * 0.12))),
            ((right - 28, int(height * 0.52)), (width - 5, int(height * 0.38))),
            ((right - 45, int(height * 0.80)), (width - 20, int(height * 0.72))),
            ((right - 60, int(height * 0.98)), (width - 35, int(height * 0.99))),
        ]
        for i, (a, b) in enumerate(anchors):
            pygame.draw.line(surface, line_colors[i % len(line_colors)], a, (vanish_x, vanish_y), 2)
            pygame.draw.line(surface, line_colors[i % len(line_colors)], (vanish_x, vanish_y), b, 2)

        # A faint red light accent adds depth while keeping the right side understated.
        accent_points = [
            (int(width * 0.76), int(height * 0.13)),
            (int(width * 0.80), int(height * 0.23)),
            (int(width * 0.83), int(height * 0.35)),
            (int(width * 0.85), int(height * 0.47)),
        ]
        pygame.draw.lines(surface, (42, 24, 32), False, accent_points, 2)
        pygame.draw.line(surface, (31, 38, 47), (right, int(height * 0.82)),
                         (width - 40, int(height * 0.82)), 1)

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
