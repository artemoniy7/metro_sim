"""Main menu and route setup screens."""
import json
from pathlib import Path
import pygame

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
ASSETS = ROOT / "assets"


class MainMenu:
    BG = (13, 18, 25)
    PANEL = (25, 33, 43)
    PANEL2 = (33, 43, 55)
    TEXT = (240, 243, 247)
    MUTED = (151, 164, 179)
    ACCENT = (218, 38, 55)
    BORDER = (55, 68, 83)

    def __init__(self, size):
        self.width, self.height = size
        self.page = "home"
        self.buttons = {}
        self.hover = {}
        self.line_catalog = self._read_json(DATA / "metro_network.json", {}).get("lines", [])
        self.available_lines = []
        for item in self.line_catalog:
            path = DATA / "lines" / item.get("file", "")
            if not path.is_file():
                continue
            data = self._read_json(path, {})
            # A catalog entry is playable only when its data explicitly identifies
            # the same real metro line. This keeps test routes out of the line list.
            if (data.get("stations") and data.get("points")
                    and (data.get("line_id") == item.get("id")
                         or str(data.get("line_number", "")) == str(item.get("number", "")))):
                self.available_lines.append((item, path, data))
        self.train_options = []
        for filename in ("81-760.json", "81-717.json", "81-740.json"):
            path = DATA / "trains" / filename
            if path.is_file():
                data = self._read_json(path, {})
                self.train_options.append((path, data))
        self.line_index = 0
        self.train_index = 0
        self.start_index = 0
        self.end_index = 1
        self.difficulty = "Обычный"
        self.settings_open = False
        self.volume = 70
        self.fullscreen = True
        font_dir = ASSETS / "ui" / "fonts"
        self.title = self._font(font_dir / "IBMPlexSans-Bold.ttf", 48, True)
        self.heading = self._font(font_dir / "IBMPlexSans-SemiBold.ttf", 27, True)
        self.body = self._font(font_dir / "IBMPlexSans-Regular.ttf", 19)
        self.button_font = self._font(font_dir / "IBMPlexSans-Medium.ttf", 18)
        self.small = self._font(font_dir / "IBMPlexSans-Regular.ttf", 14)
        self.sprites = {}
        for model in ("81-760", "81-777"):
            folder = ASSETS / "trains" / model
            for kind in ("loco", "car"):
                p = folder / f"{model}-{kind}.png"
                if p.is_file():
                    try:
                        self.sprites[(model, kind)] = pygame.image.load(str(p)).convert_alpha()
                    except pygame.error:
                        pass

    @staticmethod
    def _read_json(path, default):
        try:
            with open(path, "r", encoding="utf-8") as file:
                return json.load(file)
        except (OSError, ValueError):
            return default

    @staticmethod
    def _font(path, size, bold=False):
        try:
            return pygame.font.Font(str(path), size)
        except (OSError, pygame.error):
            return pygame.font.SysFont("arial", size, bold=bold)

    @property
    def selected_line(self):
        return self.available_lines[self.line_index] if self.available_lines else (None, None, {})

    @property
    def selected_train(self):
        return self.train_options[self.train_index] if self.train_options else (None, {})

    @property
    def selected_start_position(self):
        stations = self.selected_line[2].get("stations", [])
        return float(stations[self.start_index].get("position", 0)) if stations else 0.0

    def _add_button(self, key, rect):
        self.buttons[key] = rect

    def _button(self, surface, key, label, rect, primary=False, disabled=False):
        self._add_button(key, rect)
        hovered = rect.collidepoint(pygame.mouse.get_pos()) and not disabled
        color = self.ACCENT if primary else (self.PANEL2 if hovered else self.PANEL)
        if disabled:
            color = (28, 34, 42)
        pygame.draw.rect(surface, color, rect, border_radius=9)
        pygame.draw.rect(surface, self.BORDER, rect, 1, border_radius=9)
        text = self.button_font.render(label, True, self.TEXT if not disabled else (100, 109, 120))
        surface.blit(text, text.get_rect(center=rect.center))

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            if self.page == "setup":
                self.page = "home"
            elif self.page == "settings":
                self.page = "home"
            else:
                return "quit"
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return None
        for key, rect in list(self.buttons.items()):
            if not rect.collidepoint(event.pos):
                continue
            if key == "play":
                self.page = "setup"
            elif key == "settings":
                self.page = "settings"
            elif key == "quit":
                return "quit"
            elif key == "back":
                self.page = "home"
            elif key.startswith("line_"):
                index = int(key.split("_")[1])
                if index < len(self.available_lines):
                    self.line_index = index
                    self.start_index = 0
                    self.end_index = max(1, len(self.selected_line[2].get("stations", [])) - 1)
            elif key.startswith("station_"):
                index = int(key.split("_")[1])
                if index == self.start_index:
                    pass
                elif index == self.end_index:
                    pass
                elif index < self.end_index:
                    self.start_index = index
                else:
                    self.end_index = index
            elif key == "start_prev":
                self.start_index = max(0, self.start_index - 1)
                if self.end_index <= self.start_index:
                    self.end_index = min(len(self.selected_line[2]["stations"]) - 1, self.start_index + 1)
            elif key == "start_next":
                self.start_index = min(len(self.selected_line[2]["stations"]) - 2, self.start_index + 1)
            elif key == "end_prev":
                self.end_index = max(self.start_index + 1, self.end_index - 1)
            elif key == "end_next":
                self.end_index = min(len(self.selected_line[2]["stations"]) - 1, self.end_index + 1)
            elif key.startswith("train_"):
                self.train_index = int(key.split("_")[1])
            elif key == "difficulty":
                self.difficulty = {"Лёгкий": "Обычный", "Обычный": "Сложный", "Сложный": "Лёгкий"}[self.difficulty]
            elif key == "start_game":
                return "start"
            elif key == "volume_down":
                self.volume = max(0, self.volume - 10)
            elif key == "volume_up":
                self.volume = min(100, self.volume + 10)
            elif key == "fullscreen":
                self.fullscreen = not self.fullscreen
            break
        return None

    def update(self, dt):
        return None

    def _text(self, surface, value, font, color, pos):
        surface.blit(font.render(str(value), True, color), pos)

    def _background(self, surface):
        surface.fill(self.BG)
        w, h = surface.get_size()
        # Restrained tunnel perspective in the background.
        van = (int(w * .78), int(h * .43))
        for i in range(8):
            x = int(w * (0.42 + i * .075))
            pygame.draw.line(surface, (22, 29, 38), (x, 0), van, 2)
            pygame.draw.line(surface, (22, 29, 38), van, (x, h), 2)
        pygame.draw.rect(surface, self.ACCENT, (int(w*.055), 42, 5, 42), border_radius=2)
        self._text(surface, "METRO SIM", self.title, self.TEXT, (int(w*.07), 35))

    def render(self, surface):
        self.width, self.height = surface.get_size()
        self.buttons.clear()
        self._background(surface)
        if self.page == "home":
            self._render_home(surface)
        elif self.page == "setup":
            self._render_setup(surface)
        else:
            self._render_settings(surface)

    def _render_home(self, surface):
        w, h = surface.get_size()
        x, y = int(w*.075), int(h*.30)
        self._text(surface, "СИМУЛЯТОР МАШИНИСТА", self.heading, self.MUTED, (x, y))
        self._text(surface, "Твоя смена начинается здесь.", self.body, self.TEXT, (x, y+48))
        self._button(surface, "play", "Выбрать маршрут     →", pygame.Rect(x, y+125, 330, 58), True)
        self._button(surface, "settings", "Настройки", pygame.Rect(x, y+198, 330, 50))
        self._button(surface, "quit", "Выход", pygame.Rect(x, y+263, 330, 50))
        # Decorative route line and station nodes.
        points = [(int(w*.58), int(h*.63)), (int(w*.68), int(h*.49)),
                  (int(w*.77), int(h*.56)), (int(w*.87), int(h*.35)),
                  (int(w*.94), int(h*.40))]
        pygame.draw.lines(surface, (214, 8, 59), False, points, 7)
        for px, py in points:
            pygame.draw.circle(surface, self.TEXT, (px, py), 7)
            pygame.draw.circle(surface, (214, 8, 59), (px, py), 4)

    def _render_setup(self, surface):
        w, h = surface.get_size()
        self._text(surface, "Подготовка поездки", self.heading, self.TEXT, (int(w*.055), 105))
        self._text(surface, "1. Ветка", self.body, self.MUTED, (int(w*.055), 151))
        card_y, card_w, gap = 185, min(260, int(w*.205)), 14
        for i, (meta, path, data) in enumerate(self.available_lines):
            x = int(w*.055) + i * (card_w + gap)
            if x + card_w > w*.95:
                break
            rect = pygame.Rect(x, card_y, card_w, 72)
            selected = i == self.line_index
            pygame.draw.rect(surface, self.PANEL2 if selected else self.PANEL, rect, border_radius=9)
            pygame.draw.rect(surface, tuple(meta.get("color", [180,180,180])), (x, card_y, 7, 72), border_radius=4)
            pygame.draw.rect(surface, self.ACCENT if selected else self.BORDER, rect, 2 if selected else 1, border_radius=9)
            self._text(surface, f'{meta.get("number", "?")}  {meta.get("name", data.get("name", "Линия"))}',
                       self.button_font, self.TEXT, (x+18, card_y+12))
            self._text(surface, f'{len(data.get("stations", []))} станций', self.small, self.MUTED, (x+18, card_y+43))
            self._add_button(f"line_{i}", rect)
        meta, path, line = self.selected_line
        stations = line.get("stations", [])
        if not stations:
            return
        self._text(surface, "2. Начало и конец маршрута", self.body, self.MUTED, (int(w*.055), 280))
        start = stations[self.start_index]
        end = stations[self.end_index]
        self._text(surface, "ОТ", self.small, self.MUTED, (int(w*.055), 318))
        self._text(surface, start.get("name", ""), self.button_font, self.TEXT, (int(w*.055), 340))
        self._button(surface, "start_prev", "‹", pygame.Rect(int(w*.055), 371, 42, 34))
        self._button(surface, "start_next", "›", pygame.Rect(int(w*.055)+50, 371, 42, 34))
        self._text(surface, "ДО", self.small, self.MUTED, (int(w*.34), 318))
        self._text(surface, end.get("name", ""), self.button_font, self.TEXT, (int(w*.34), 340))
        self._button(surface, "end_prev", "‹", pygame.Rect(int(w*.34), 371, 42, 34))
        self._button(surface, "end_next", "›", pygame.Rect(int(w*.34)+50, 371, 42, 34))
        # Draw this line's own station geography (coordinates when available).
        # If coordinates are absent, fall back to a line-specific station sequence.
        map_rect = pygame.Rect(int(w*.055), 420, int(w*.89), 82)
        pygame.draw.rect(surface, (19, 26, 35), map_rect, border_radius=9)
        color = tuple(meta.get("color", [214, 8, 59]))
        coords = [(st.get("longitude"), st.get("latitude")) for st in stations]
        has_coords = all(lon is not None and lat is not None for lon, lat in coords)
        if has_coords:
            xs = [float(p[0]) for p in coords]
            ys = [float(p[1]) for p in coords]
            min_x, max_x = min(xs), max(xs)
            min_y, max_y = min(ys), max(ys)
            span_x, span_y = max(max_x-min_x, 0.00001), max(max_y-min_y, 0.00001)
            pad_x, pad_y = 22, 17
            usable_w, usable_h = map_rect.width-2*pad_x, map_rect.height-2*pad_y
            raw = [(map_rect.x+pad_x+(x-min_x)/span_x*usable_w,
                    map_rect.y+pad_y+(max_y-y)/span_y*usable_h) for x,y in zip(xs,ys)]
        else:
            raw = [(map_rect.x+18+i*(map_rect.width-36)/max(1,len(stations)-1),
                    map_rect.centery + (12 if i % 2 else -12)) for i in range(len(stations))]
        route_points = [(int(x), int(y)) for x,y in raw]
        if len(route_points) > 1:
            pygame.draw.lines(surface, (75, 88, 103), False, route_points, 7)
            pygame.draw.lines(surface, color, False, route_points, 4)
        for i, (px, py) in enumerate(route_points):
            active = self.start_index <= i <= self.end_index
            node_color = color if active else (88, 101, 116)
            pygame.draw.circle(surface, node_color, (px,py), 6 if active else 4)
            if i in (self.start_index, self.end_index):
                pygame.draw.circle(surface, self.TEXT, (px,py), 10, 2)
            # All stations can be selected directly on the route.
            hit = pygame.Rect(px-10, py-10, 20, 20)
            self._add_button(f"station_{i}", hit)
            if i in (0, len(stations)-1, self.start_index, self.end_index) or i % max(1, len(stations)//8) == 0:
                label = self.small.render(stations[i].get("name", ""), True, self.TEXT if active else self.MUTED)
                label_x = max(map_rect.x+3, min(px-label.get_width()//2, map_rect.right-label.get_width()-3))
                label_y = map_rect.bottom-19 if py < map_rect.centery else map_rect.y+2
                surface.blit(label, (label_x, label_y))
        self._text(surface, f'{len(stations)} станций  •  нажми на точку, чтобы выбрать станцию',
                   self.small, self.MUTED, (map_rect.x+8, map_rect.bottom+4))
        self._text(surface, "3. Выбери поезд", self.body, self.MUTED, (int(w*.055), 505))
        train_y = 535
        train_w = min(230, int(w*.19))
        for i, (train_path, train) in enumerate(self.train_options):
            x = int(w*.055) + i * (train_w + 16)
            rect = pygame.Rect(x, train_y, train_w, 112)
            selected = i == self.train_index
            pygame.draw.rect(surface, self.PANEL2 if selected else self.PANEL, rect, border_radius=10)
            pygame.draw.rect(surface, self.ACCENT if selected else self.BORDER, rect, 2 if selected else 1, border_radius=10)
            self._draw_train(surface, train.get("name", ""), x+12, train_y-15, train_w-24, 62)
            self._text(surface, train.get("display_name", train.get("name", "Поезд")), self.button_font,
                       self.TEXT, (x+14, train_y+62))
            self._text(surface, f'{train.get("wagons", "?")} ваг.  •  до {train.get("max_speed_kmh", "?")} км/ч',
                       self.small, self.MUTED, (x+14, train_y+87))
            self._add_button(f"train_{i}", rect)
        self._button(surface, "difficulty", f"Сложность: {self.difficulty}",
                     pygame.Rect(int(w*.67), 535, 180, 42))
        self._button(surface, "back", "← Назад", pygame.Rect(int(w*.67), 590, 130, 44))
        self._button(surface, "start_game", "В путь  →", pygame.Rect(int(w*.81), 590, 160, 44), True)

    def _draw_train(self, surface, model, x, y, width, height):
        image = self.sprites.get((model, "loco"))
        if image is None:
            # A clean vector placeholder until a photo/render is supplied.
            body = pygame.Rect(x+8, y+20, width-16, 27)
            pygame.draw.rect(surface, (205, 211, 218), body, border_radius=8)
            pygame.draw.rect(surface, (49, 66, 82), (body.x+12, body.y+5, 24, 13), border_radius=3)
            pygame.draw.rect(surface, (49, 66, 82), (body.right-38, body.y+5, 24, 13), border_radius=3)
            pygame.draw.rect(surface, self.ACCENT, (body.x, body.bottom-7, body.width, 5))
            for wx in (body.x+24, body.right-30):
                pygame.draw.circle(surface, (15, 20, 27), (wx, body.bottom+2), 7)
            return
        scale = min(width / image.get_width(), height / image.get_height())
        scaled = pygame.transform.smoothscale(image, (int(image.get_width()*scale), int(image.get_height()*scale)))
        surface.blit(scaled, (x, y + height - scaled.get_height() + 10))

    def _render_settings(self, surface):
        w, h = surface.get_size()
        panel = pygame.Rect(0, 0, min(520, w-40), 330)
        panel.center = (w//2, h//2)
        pygame.draw.rect(surface, self.PANEL, panel, border_radius=14)
        pygame.draw.rect(surface, self.BORDER, panel, 1, border_radius=14)
        self._text(surface, "Настройки", self.heading, self.TEXT, (panel.x+28, panel.y+25))
        self._text(surface, f'Громкость: {self.volume}%', self.body, self.MUTED, (panel.x+28, panel.y+92))
        self._button(surface, "volume_down", "−", pygame.Rect(panel.x+28, panel.y+130, 54, 42))
        self._button(surface, "volume_up", "+", pygame.Rect(panel.x+94, panel.y+130, 54, 42))
        self._button(surface, "fullscreen", "Полный экран: " + ("Да" if self.fullscreen else "Нет"),
                     pygame.Rect(panel.x+28, panel.y+193, panel.width-56, 44))
        self._button(surface, "back", "Назад", pygame.Rect(panel.x+28, panel.bottom-66, panel.width-56, 42), True)
