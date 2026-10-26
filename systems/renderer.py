"""Sprite renderer for the 81-760 train, route, stations and driving HUD."""
from pathlib import Path
import pygame
from settings import ASSETS_DIR


class Renderer:
    def __init__(self):
        pygame.font.init()
        self.font = pygame.font.Font(None, 28)
        self.small_font = pygame.font.Font(None, 21)
        self.loco_image = self._load_sprite(ASSETS_DIR / "trains" / "81-760" / "81-760-loco.png")
        self.car_image = self._load_sprite(ASSETS_DIR / "trains" / "81-760" / "81-760-car.png")

    @staticmethod
    def _load_sprite(path):
        try:
            return pygame.image.load(str(path)).convert_alpha()
        except (pygame.error, OSError):
            return None

    @staticmethod
    def _scaled_sprite(image, width, max_height=105):
        if image is None or image.get_width() <= 0:
            return None
        height = max(1, round(width * image.get_height() / image.get_width()))
        if height > max_height:
            width = max(1, round(width * max_height / height))
            height = max_height
        return pygame.transform.smoothscale(image, (max(1, width), max(1, height)))

    def draw_scene(self, surface, line, train, camera, elapsed):
        width, height = surface.get_size()
        scale = camera.pixels_per_metre
        track_y = int(height * 0.59)
        camera_x = camera.x

        # Tunnel and track.
        pygame.draw.rect(surface, (25, 30, 39), (0, int(height * 0.25), width, int(height * 0.48)))
        pygame.draw.rect(surface, (48, 51, 58), (0, track_y - 16, width, 78))
        pygame.draw.line(surface, (145, 149, 156), (0, track_y + 5), (width, track_y + 5), 5)
        pygame.draw.line(surface, (80, 84, 92), (0, track_y + 20), (width, track_y + 20), 3)
        # Sleepers are placed every 2.5 m in world space.
        first_sleeper = int(camera_x / 2.5) * 2.5
        sleeper = first_sleeper
        while sleeper < camera_x + width / scale:
            sx = int((sleeper - camera_x) * scale)
            pygame.draw.line(surface, (95, 89, 80), (sx, track_y - 3), (sx, track_y + 25), 2)
            sleeper += 2.5

        # Stations are exactly 1 km apart in line_1.json.
        for station in line.stations:
            x = int((line.path.total_length - float(station.get("position", 0)) - camera_x) * scale)
            if -160 < x < width + 160:
                pygame.draw.rect(surface, (75, 125, 145), (x - 60, track_y - 100, 120, 12), border_radius=3)
                label = self.small_font.render(station.get("name", "Station"), True, (230, 234, 240))
                surface.blit(label, (x - label.get_width() // 2, track_y - 130))
                distance = float(station.get("position", 0)) - train.position
                if distance > 0:
                    dlabel = self.small_font.render(f"{distance:.0f} m", True, (170, 190, 205))
                    surface.blit(dlabel, (x - dlabel.get_width() // 2, track_y - 78))

        for signal in line.signals:
            x = int((line.path.total_length - signal.position - camera_x) * scale)
            if -20 < x < width + 20:
                pygame.draw.rect(surface, (85, 88, 94), (x - 3, track_y - 65, 6, 48))
                pygame.draw.circle(surface, signal.ASPECTS[signal.aspect], (x, track_y - 65), 7)
                surface.blit(self.small_font.render(signal.name, True, (205, 210, 218)), (x + 8, track_y - 72))

        # Left-facing locomotive at the front; cars extend to its right.
        loco_x = int((line.path.total_length - train.position - train.loco_length_m - camera_x) * scale)
        loco_width = max(1, round(train.loco_length_m * scale))
        car_width = max(1, round(train.car_length_m * scale))
        loco = self._scaled_sprite(self.loco_image, loco_width)
        car = self._scaled_sprite(self.car_image, car_width)
        base_y = track_y - 15
        if loco is not None:
            surface.blit(loco, (loco_x, base_y - loco.get_height()))
        else:
            pygame.draw.rect(surface, (205, 210, 215), (loco_x, base_y - 38, loco_width, 38), border_radius=5)
        for wagon in train.wagons:
            if wagon.is_loco:
                continue
            car_x = loco_x + loco_width + (wagon.index - 1) * car_width
            if car is not None:
                surface.blit(car, (car_x, base_y - car.get_height()))
            else:
                pygame.draw.rect(surface, (185, 190, 196), (car_x, base_y - 38, car_width, 38), border_radius=4)

        # Driving HUD.
        pygame.draw.rect(surface, (12, 15, 20), (16, 16, 345, 137), border_radius=8)
        surface.blit(self.font.render("81-760 «Ока»", True, (240, 240, 240)), (30, 25))
        surface.blit(self.font.render(f"Скорость: {train.speed * 3.6:05.1f} км/ч", True, (110, 220, 160)), (30, 56))
        surface.blit(self.small_font.render(f"Путь: {train.position:.0f} м / {line.path.total_length:.0f} м", True, (210, 215, 222)), (30, 89))
        surface.blit(self.small_font.render("W/↑ тяга   S/↓ тормоз   SPACE экстр. тормоз", True, (205, 210, 218)), (30, 119))
