"""Side-on sprite renderer for the 81-760 train and track."""
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
    def _scaled_sprite(image, width, target_height=None):
        if image is None or image.get_width() <= 0:
            return None
        height = (max(1, round(width * image.get_height() / image.get_width()))
                  if target_height is None else max(1, int(target_height)))
        return pygame.transform.smoothscale(image, (max(1, width), height))

    def draw_scene(self, surface, line, train, camera, elapsed):
        width, height = surface.get_size()
        scale = camera.pixels_per_metre
        # Side view: train sits above the rails; track is at the bottom of the scene.
        track_y = int(height * 0.79)
        camera_x = camera.x

        # Dark tunnel wall above the track, with a floor/ballast strip below it.
        pygame.draw.rect(surface, (25, 30, 39), (0, int(height * 0.14), width, track_y - int(height * 0.14)))
        pygame.draw.rect(surface, (48, 51, 58), (0, track_y + 7, width, height - track_y - 7))

        # Side-on rail line and sleepers underneath the train, not over it.
        first_sleeper = int(camera_x / 2.5) * 2.5
        sleeper = first_sleeper
        while sleeper < camera_x + width / scale:
            sx = int((sleeper - camera_x) * scale)
            pygame.draw.line(surface, (95, 89, 80), (sx, track_y - 1), (sx, track_y + 14), 3)
            sleeper += 2.5
        pygame.draw.line(surface, (155, 160, 167), (0, track_y + 1), (width, track_y + 1), 4)
        pygame.draw.line(surface, (85, 90, 98), (0, track_y + 7), (width, track_y + 7), 2)

        # Station markers/platform edge stay beside the track, at rail level.
        for station in line.stations:
            x = int((line.path.total_length - float(station.get("position", 0)) - camera_x) * scale)
            if -160 < x < width + 160:
                pygame.draw.line(surface, (75, 125, 145), (x - 90, track_y - 8), (x + 90, track_y - 8), 4)
                label = self.small_font.render(station.get("name", "Station"), True, (230, 234, 240))
                surface.blit(label, (x - label.get_width() // 2, track_y - 43))
                distance = float(station.get("position", 0)) - train.position
                if distance > 0:
                    dlabel = self.small_font.render(f"{distance:.0f} m", True, (170, 190, 205))
                    surface.blit(dlabel, (x - dlabel.get_width() // 2, track_y - 25))

        # Signal posts stand at the side of the rail line.
        for signal in line.signals:
            x = int((line.path.total_length - signal.position - camera_x) * scale)
            if -20 < x < width + 20:
                pygame.draw.line(surface, (85, 88, 94), (x, track_y - 56), (x, track_y - 1), 5)
                pygame.draw.circle(surface, signal.ASPECTS[signal.aspect], (x, track_y - 56), 8)
                surface.blit(self.small_font.render(signal.name, True, (205, 210, 218)), (x + 10, track_y - 66))

        # Left-facing locomotive leads; the cars trail to its right. Wheels align with the rails.
        loco_x = int((line.path.total_length - train.position - train.loco_length_m - camera_x) * scale)
        loco_width = max(1, round(train.loco_length_m * scale))
        car_width = max(1, round(train.car_length_m * scale))
        loco = self._scaled_sprite(self.loco_image, loco_width)
        # Passenger cars use the same height as the locomotive, but remain 19 m long.
        target_height = loco.get_height() if loco is not None else 48
        car = self._scaled_sprite(self.car_image, car_width, target_height)
        base_y = track_y
        if loco is not None:
            surface.blit(loco, (loco_x, base_y - loco.get_height()))
        else:
            pygame.draw.rect(surface, (205, 210, 215), (loco_x, base_y - 48, loco_width, 48), border_radius=5)
        for wagon in train.wagons:
            if wagon.is_loco:
                continue
            car_x = loco_x + loco_width + (wagon.index - 1) * car_width
            if car is not None:
                surface.blit(car, (car_x, base_y - car.get_height()))
            else:
                pygame.draw.rect(surface, (185, 190, 196), (car_x, base_y - 48, car_width, 48), border_radius=4)

        # Driving HUD.
        pygame.draw.rect(surface, (12, 15, 20), (16, 16, 345, 137), border_radius=8)
        surface.blit(self.font.render("81-760 «Ока»", True, (240, 240, 240)), (30, 25))
        surface.blit(self.font.render(f"Скорость: {train.speed * 3.6:05.1f} км/ч", True, (110, 220, 160)), (30, 56))
        surface.blit(self.small_font.render(f"Путь: {train.position:.0f} м / {line.path.total_length:.0f} м", True, (210, 215, 222)), (30, 89))
        surface.blit(self.small_font.render("W/↑ тяга   S/↓ тормоз   SPACE экстр. тормоз", True, (205, 210, 218)), (30, 119))
