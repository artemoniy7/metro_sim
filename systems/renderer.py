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
        """Gentle test-track rises and dips, measured in world metres."""
        # Smooth, broad elevation changes; zero at the ends of each cycle.
        import math
        return (0.62 * math.sin(world_x / 34.0)
                + 0.28 * math.sin(world_x / 13.5 + 0.8))

    def draw_scene(self, surface, line, train, camera, elapsed):
        width, height = surface.get_size()
        scale = camera.pixels_per_metre
        base_track_y = int(height * 0.79)
        camera_x = camera.x

        def rail_y_at(screen_x):
            world_x = camera_x + screen_x / scale
            return int(base_track_y - self._track_offset(world_x) * scale)

        # Dark tunnel backdrop; its lower edge follows the test track's gentle slopes.
        pygame.draw.rect(surface, (25, 30, 39), (0, 0, width, height))
        tunnel_height = max(1, round(5.5 * scale))
        if self.tunnel_image is not None:
            tunnel_width = max(1, round(tunnel_height * self.tunnel_image.get_width() / self.tunnel_image.get_height()))
            tunnel_tile = pygame.transform.smoothscale(self.tunnel_image, (tunnel_width, tunnel_height))
            # Warp the tunnel into narrow vertical strips so its floor follows the slope.
            strip_width = 4
            for sx in range(0, width, strip_width):
                world_x = camera_x + sx / scale
                track_y = int(base_track_y - self._track_offset(world_x) * scale)
                src_x = int((world_x * scale) % tunnel_width)
                src_x = min(tunnel_width - 1, max(0, src_x))
                slice_width = min(strip_width, tunnel_width - src_x)
                if slice_width <= 0:
                    continue
                tunnel_slice = tunnel_tile.subsurface((src_x, 0, slice_width, tunnel_height))
                surface.blit(tunnel_slice, (sx, track_y - tunnel_height))
                # Fill any tiny gap caused by the repeating texture's wrap.
                if slice_width < strip_width:
                    extra = tunnel_tile.subsurface((0, 0, strip_width - slice_width, tunnel_height))
                    surface.blit(extra, (sx + slice_width, track_y - tunnel_height))
        # Fill the ground beneath the varying track line with short sloped strips.
        for sx in range(0, width, 4):
            y = rail_y_at(sx)
            next_y = rail_y_at(min(width - 1, sx + 4))
            pygame.draw.polygon(surface, (48, 51, 58),
                                [(sx, y + 8), (min(width, sx + 4), next_y + 8),
                                 (min(width, sx + 4), height), (sx, height)])

        # Sleepers and rails follow the uneven test track. The train itself stays unwarped.
        sleeper_spacing = 2.5
        first_sleeper = int(camera_x / sleeper_spacing) * sleeper_spacing
        sleeper = first_sleeper
        while sleeper < camera_x + width / scale:
            sx = int((sleeper - camera_x) * scale)
            if 0 <= sx < width:
                sy = rail_y_at(sx)
                pygame.draw.line(surface, (95, 89, 80), (sx, sy - 1), (sx, sy + 14), 3)
            sleeper += sleeper_spacing

        # Draw the rails in short segments so their height follows the elevation profile.
        rail_step = 4
        for sx in range(0, width, rail_step):
            ex = min(width, sx + rail_step)
            y1 = rail_y_at(sx)
            y2 = rail_y_at(min(width - 1, ex))
            pygame.draw.line(surface, (155, 160, 167), (sx, y1 + 1), (ex, y2 + 1), 4)
            pygame.draw.line(surface, (85, 90, 98), (sx, y1 + 7), (ex, y2 + 7), 2)

        # Station platforms and labels sit at the local track height.
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

        # Signal posts follow the track slope; signal heads and labels move with them.
        for signal in line.signals:
            x = int((line.path.total_length - signal.position - camera_x) * scale)
            if -20 < x < width + 20:
                sy = rail_y_at(max(0, min(width - 1, x)))
                pygame.draw.line(surface, (85, 88, 94), (x, sy - 56), (x, sy - 1), 5)
                pygame.draw.circle(surface, signal.ASPECTS[signal.aspect], (x, sy - 56), 8)
                surface.blit(self.small_font.render(signal.name, True, (205, 210, 218)), (x + 10, sy - 66))

        # The train sprites are intentionally not warped; keep their original flat shape.
        loco_x = int((line.path.total_length - train.position - train.loco_length_m - camera_x) * scale)
        loco_width = max(1, round(train.loco_length_m * scale))
        car_width = max(1, round(train.car_length_m * scale))
        loco = self._scaled_sprite(self.loco_image, loco_width)
        target_height = loco.get_height() if loco is not None else 48
        car = self._scaled_sprite(self.car_image, car_width, target_height)
        # Move the whole train vertically as one rigid object. Sample the track near
        # the train's centre so the locomotive and every carriage keep the same y;
        # no sprite is warped, rotated, or independently bent to match the slope.
        car_count = sum(1 for wagon in train.wagons if not wagon.is_loco)
        train_center_x = loco_x + (loco_width + car_count * car_width) // 2
        base_y = rail_y_at(max(0, min(width - 1, train_center_x)))
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

        # Driving HUD remains screen-space and is not affected by track elevation.
        pygame.draw.rect(surface, (12, 15, 20), (16, 16, 345, 137), border_radius=8)
        surface.blit(self.font.render("81-760 «Ока»", True, (240, 240, 240)), (30, 25))
        surface.blit(self.font.render(f"Скорость: {train.speed * 3.6:05.1f} км/ч", True, (110, 220, 160)), (30, 56))
        surface.blit(self.small_font.render(f"Путь: {train.position:.0f} м / {line.path.total_length:.0f} м", True, (210, 215, 222)), (30, 89))
        surface.blit(self.small_font.render("W/↑ тяга   S/↓ тормоз   SPACE экстр. тормоз", True, (205, 210, 218)), (30, 119))
