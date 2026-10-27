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
        self.tunnel_image = self._load_sprite(ASSETS_DIR / "track" / "tunnel.jpg")
        # Keep a separate, smoothed pitch angle for each car to avoid visual jolts.
        self.vehicle_angles = {}

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

    @staticmethod
    def _track_offset(world_x):
        """Smooth, shallow test-track rises and dips, measured in world metres."""
        import math
        # Long wavelengths and modest amplitudes avoid abrupt-looking changes.
        return (0.45 * math.sin(world_x / 85.0)
                + 0.18 * math.sin(world_x / 38.0 + 0.8))

    @staticmethod
    def _draw_train_sprite(surface, image, scaled_width, scaled_height,
                           left_axle_ratio, right_axle_ratio, axle_y_ratio,
                           left_x, right_x, left_y, right_y):
        """Rotate a scaled train sprite and anchor its axle midpoint to the rails."""
        import math
        if image is None:
            return

        sprite = pygame.transform.smoothscale(
            image, (max(1, scaled_width), max(1, scaled_height))
        )
        dx = right_x - left_x
        dy = right_y - left_y
        target_angle = -math.degrees(math.atan2(dy, max(1e-6, dx)))
        vehicle_key = getattr(image, "_vehicle_key", None)
        # The caller supplies per-vehicle identity via an optional temporary attribute below.
        angle = target_angle
        rotated = pygame.transform.rotozoom(sprite, angle, 1.0)

        # Axle midpoint in source-sprite coordinates, relative to its centre.
        source_mid_x = ((left_axle_ratio + right_axle_ratio) / 2.0 - 0.5) * scaled_width
        source_mid_y = (axle_y_ratio - 0.5) * scaled_height
        rotated_offset = pygame.math.Vector2(source_mid_x, source_mid_y).rotate(angle)

        target_mid_x = (left_x + right_x) / 2.0
        target_mid_y = (left_y + right_y) / 2.0
        draw_x = round(target_mid_x - rotated_offset.x - rotated.get_width() / 2.0)
        draw_y = round(target_mid_y - rotated_offset.y - rotated.get_height() / 2.0)
        surface.blit(rotated, (draw_x, draw_y))

    def draw_scene(self, surface, line, train, camera, elapsed):
        width, height = surface.get_size()
        scale = camera.pixels_per_metre
        base_track_y = int(height * 0.79)
        camera_x = camera.x

        def rail_y_at(screen_x):
            # Keep sub-pixel precision for rotation angles; round only when drawing.
            world_x = camera_x + screen_x / scale
            return base_track_y - self._track_offset(world_x) * scale

        # Tunnel image follows the changing track height, while preserving its texture.
        pygame.draw.rect(surface, (25, 30, 39), (0, 0, width, height))
        tunnel_height = max(1, round(5.5 * scale))
        if self.tunnel_image is not None:
            tunnel_width = max(1, round(tunnel_height * self.tunnel_image.get_width() / self.tunnel_image.get_height()))
            tunnel_tile = pygame.transform.smoothscale(self.tunnel_image, (tunnel_width, tunnel_height))
            strip_width = 4
            for sx in range(0, width, strip_width):
                world_x = camera_x + sx / scale
                track_y = round(base_track_y - self._track_offset(world_x) * scale)
                src_x = int((world_x * scale) % tunnel_width)
                src_x = min(tunnel_width - 1, max(0, src_x))
                slice_width = min(strip_width, tunnel_width - src_x)
                if slice_width > 0:
                    surface.blit(tunnel_tile.subsurface((src_x, 0, slice_width, tunnel_height)), (sx, track_y - tunnel_height))
                    if slice_width < strip_width:
                        extra_width = min(strip_width - slice_width, tunnel_width)
                        surface.blit(tunnel_tile.subsurface((0, 0, extra_width, tunnel_height)), (sx + slice_width, track_y - tunnel_height))

        for sx in range(0, width, 4):
            ex = min(width, sx + 4)
            y1, y2 = rail_y_at(sx), rail_y_at(min(width - 1, ex))
            pygame.draw.polygon(surface, (48, 51, 58),
                                [(sx, y1 + 8), (ex, y2 + 8), (ex, height), (sx, height)])

        # Track sleepers and rails follow the elevation profile.
        sleeper_spacing = 2.5
        sleeper = int(camera_x / sleeper_spacing) * sleeper_spacing
        while sleeper < camera_x + width / scale:
            sx = int((sleeper - camera_x) * scale)
            if 0 <= sx < width:
                sy = rail_y_at(sx)
                pygame.draw.line(surface, (95, 89, 80), (sx, sy - 1), (sx, sy + 14), 3)
            sleeper += sleeper_spacing

        for sx in range(0, width, 4):
            ex = min(width, sx + 4)
            y1, y2 = rail_y_at(sx), rail_y_at(min(width - 1, ex))
            pygame.draw.line(surface, (155, 160, 167), (sx, y1 + 1), (ex, y2 + 1), 4)
            pygame.draw.line(surface, (85, 90, 98), (sx, y1 + 7), (ex, y2 + 7), 2)

        for station in line.stations:
            x = int((line.path.total_length - float(station.get("position", 0)) - camera_x) * scale)
            if -160 < x < width + 160:
                sy = rail_y_at(max(0, min(width - 1, x)))
                pygame.draw.line(surface, (75, 125, 145), (x - 90, sy - 8), (x + 90, sy - 8), 4)
                label = self.small_font.render(station.get("name", "Station"), True, (230, 234, 240))
                surface.blit(label, (x - label.get_width() // 2, sy - 43))
                distance = float(station.get("position", 0)) - train.position
                if distance > 0:
                    dlabel = self.small_font.render(f"{distance:.0f} m", True, (170, 190, 205))
                    surface.blit(dlabel, (x - dlabel.get_width() // 2, sy - 25))

        for signal in line.signals:
            x = int((line.path.total_length - signal.position - camera_x) * scale)
            if -20 < x < width + 20:
                sy = rail_y_at(max(0, min(width - 1, x)))
                pygame.draw.line(surface, (85, 88, 94), (x, sy - 56), (x, sy - 1), 5)
                pygame.draw.circle(surface, signal.ASPECTS[signal.aspect], (x, sy - 56), 8)
                surface.blit(self.small_font.render(signal.name, True, (205, 210, 218)), (x + 10, sy - 66))

        # Place each vehicle by its real axle points. The axle midpoint is anchored
        # directly to the smooth rail profile, so the train cannot sink below the track.
        loco_x = (line.path.total_length - train.position - train.loco_length_m - camera_x) * scale
        loco_width = max(1, round(train.loco_length_m * scale))
        car_width = max(1, round(train.car_length_m * scale))
        loco = self._scaled_sprite(self.loco_image, loco_width)
        loco_height = loco.get_height() if loco is not None else 48
        car = self._scaled_sprite(self.car_image, car_width, loco_height)

        if loco is not None:
            src_w, src_h = self.loco_image.get_size()
            left_ratio, right_ratio = 499 / src_w, 1902 / src_w
            axle_y_ratio = 464 / src_h
            left_x = loco_x + left_ratio * loco_width
            right_x = loco_x + right_ratio * loco_width
            left_y = rail_y_at(left_x)
            right_y = rail_y_at(right_x)
            self._draw_train_sprite(
                surface, self.loco_image, loco_width, loco_height,
                left_ratio, right_ratio, axle_y_ratio,
                left_x, right_x, left_y, right_y
            )
        else:
            left_x = loco_x + loco_width * (499 / 1902)
            left_y = rail_y_at(left_x)
            right_x = loco_x + loco_width
            right_y = rail_y_at(right_x)
            pygame.draw.polygon(surface, (205, 210, 215),
                                [(loco_x, left_y - 48), (loco_x + loco_width, right_y - 48),
                                 (loco_x + loco_width, right_y), (loco_x, left_y)])

        for wagon in train.wagons:
            if wagon.is_loco:
                continue
            car_x = loco_x + loco_width + (wagon.index - 1) * car_width
            if car is not None:
                src_w, src_h = self.car_image.get_size()
                left_ratio, right_ratio = 334 / src_w, 1898 / src_w
                axle_y_ratio = 435 / src_h
                left_x = car_x + left_ratio * car_width
                right_x = car_x + right_ratio * car_width
                left_y = rail_y_at(left_x)
                right_y = rail_y_at(right_x)
                self._draw_train_sprite(
                    surface, self.car_image, car_width, loco_height,
                    left_ratio, right_ratio, axle_y_ratio,
                    left_x, right_x, left_y, right_y
                )
            else:
                left_y = rail_y_at(car_x)
                right_y = rail_y_at(car_x + car_width)
                pygame.draw.polygon(surface, (185, 190, 196),
                                    [(car_x, left_y - 48), (car_x + car_width, right_y - 48),
                                     (car_x + car_width, right_y), (car_x, left_y)])

        # Driving HUD remains fixed to the screen.
        pygame.draw.rect(surface, (12, 15, 20), (16, 16, 345, 137), border_radius=8)
        surface.blit(self.font.render("81-760 «Ока»", True, (240, 240, 240)), (30, 25))
        surface.blit(self.font.render(f"Скорость: {train.speed * 3.6:05.1f} км/ч", True, (110, 220, 160)), (30, 56))
        surface.blit(self.small_font.render(f"Путь: {train.position:.0f} м / {line.path.total_length:.0f} м", True, (210, 215, 222)), (30, 89))
        surface.blit(self.small_font.render("W/↑ тяга   S/↓ тормоз   SPACE экстр. тормоз", True, (205, 210, 218)), (30, 119))
