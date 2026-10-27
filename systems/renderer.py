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
        self.station_image = self._load_sprite(ASSETS_DIR / "stations" / "line_9" / "altufyevo.png")
        self.vehicle_angles = {};
        self._station_tile_cache = {}
        self.last_render_time = None
        # Cache tunnel tiles so they are not rescaled on every frame.
        self._tunnel_tile_cache = {}

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
        size = (max(1, width), height)
        # Reuse scaled sprites while zoom and target dimensions stay unchanged.
        cache = Renderer.__dict__.get("_sprite_scale_cache")
        if cache is None:
            cache = {}
            Renderer._sprite_scale_cache = cache
        key = (id(image), size)
        if key not in cache:
            cache[key] = pygame.transform.smoothscale(image, size)
            if len(cache) > 256:
                cache.clear()
                cache[key] = pygame.transform.smoothscale(image, size)
        return cache[key]

    @staticmethod
    def _track_offset(world_x):
        """Smooth, shallow test-track rises and dips, measured in world metres."""
        import math
        return (0.45 * math.sin(world_x / 85.0)
                + 0.18 * math.sin(world_x / 38.0 + 0.8))

    def _draw_train_sprite(self, surface, image, scaled_width, scaled_height,
                           left_axle_ratio, right_axle_ratio, axle_y_ratio,
                           left_x, right_x, left_y, right_y, vehicle_key, frame_dt):
        """Rotate a scaled train sprite and anchor its axle midpoint to the rails."""
        import math
        if image is None:
            return
        sprite = pygame.transform.smoothscale(image, (max(1, scaled_width), max(1, scaled_height)))
        dx = right_x - left_x
        dy = right_y - left_y
        target_angle = -math.degrees(math.atan2(dy, max(1e-6, dx)))
        previous_angle = self.vehicle_angles.get(vehicle_key, target_angle)
        angle_delta = (target_angle - previous_angle + 180.0) % 360.0 - 180.0
        smoothing = 1.0 - math.exp(-frame_dt / 0.20) if frame_dt > 0 else 1.0
        angle = previous_angle + angle_delta * smoothing
        self.vehicle_angles[vehicle_key] = angle
        rotated = pygame.transform.rotozoom(sprite, angle, 1.0)
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
        if self.last_render_time is None:
            frame_dt = 1.0 / 60.0
        else:
            frame_dt = max(0.0, min(0.1, elapsed - self.last_render_time))
        self.last_render_time = elapsed
        scale = camera.pixels_per_metre
        base_track_y = int(height * 0.79)
        camera_x = camera.x

        def rail_y_at(screen_x):
            world_x = camera_x + screen_x / scale
            route_position = max(0.0, min(line.path.total_length, line.path.total_length - world_x))
            depth_m = line.path.point_at(route_position)[1]
            return round(base_track_y + (depth_m - 10.0) * 1.35 - self._track_offset(world_x) * scale)

        pygame.draw.rect(surface, (25, 30, 39), (0, 0, width, height))
        tunnel_height = max(1, round(5.5 * scale))
        if self.tunnel_image is not None:
            tunnel_width = max(1, round(tunnel_height * self.tunnel_image.get_width() / self.tunnel_image.get_height()))
            tunnel_key = (id(self.tunnel_image), tunnel_width, tunnel_height)
            if tunnel_key not in self._tunnel_tile_cache:
                self._tunnel_tile_cache = {tunnel_key: pygame.transform.smoothscale(self.tunnel_image, (tunnel_width, tunnel_height))}
            tunnel_tile = self._tunnel_tile_cache[tunnel_key]
            strip_width = 4
            for sx in range(0, width, strip_width):
                world_x = camera_x + sx / scale
                route_position = line.path.total_length - world_x
                track_y = rail_y_at(sx)
                at_station = any(
                    abs(route_position - float(station.get("position", 0)))
                    <= float(station.get("length_m", 155)) / 2
                    for station in line.stations
                )
                if at_station:
                    # Repeat the station photo along the platform, with a taller ceiling
                    # than the regular tunnel so the station feels more spacious.
                    station_height = max(tunnel_height + 1, round(8.5 * scale))
                    station_bottom_extra = max(1, round(0.25 * scale))
                    if self.station_image is not None:
                        station_width = max(1, round(
                            station_height * self.station_image.get_width()
                            / self.station_image.get_height()))
                        station_key = (id(self.station_image), station_width, station_height)
                        if station_key not in self._station_tile_cache:
                            self._station_tile_cache = {
                                station_key: pygame.transform.smoothscale(
                                    self.station_image, (station_width, station_height))
                            }
                        station_tile = self._station_tile_cache[station_key]
                        tile_x = int((world_x * scale) % station_width)
                        src_x = min(station_width - 1, max(0, tile_x))
                        slice_width = min(strip_width, station_width - src_x)
                        if slice_width > 0:
                            surface.blit(
                                station_tile.subsurface((src_x, 0, slice_width, station_height)),
                                (sx, track_y - station_height + station_bottom_extra))
                        if slice_width < strip_width:
                            extra_width = min(strip_width - slice_width, station_width)
                            surface.blit(
                                station_tile.subsurface((0, 0, extra_width, station_height)),
                                (sx + slice_width, track_y - station_height + station_bottom_extra))
                    else:
                        pygame.draw.rect(surface, (142, 24, 34),
                                         (sx, track_y - station_height, strip_width,
                                          station_height + 20))
                else:
                    src_x = int((world_x * scale) % tunnel_width)
                    src_x = min(tunnel_width - 1, max(0, src_x))
                    slice_width = min(strip_width, tunnel_width - src_x)
                    if slice_width > 0:
                        surface.blit(tunnel_tile.subsurface((src_x, 0, slice_width, tunnel_height)), (sx, track_y - tunnel_height))
                        if slice_width < strip_width:
                            extra_width = min(strip_width - slice_width, tunnel_width)
                            surface.blit(tunnel_tile.subsurface((0, 0, extra_width, tunnel_height)), (sx + slice_width, track_y - tunnel_height))
        else:
            # Keep the tunnel dark, but still paint red station sections without an asset.
            for sx in range(0, width, 4):
                route_position = line.path.total_length - (camera_x + sx / scale)
                if any(abs(route_position - float(station.get("position", 0)))
                       <= float(station.get("length_m", 155)) / 2 for station in line.stations):
                    track_y = rail_y_at(sx)
                    pygame.draw.rect(surface, (142, 24, 34),
                                     (sx, track_y - tunnel_height, 4, tunnel_height + 20))

        for sx in range(0, width, 4):
            ex = min(width, sx + 4)
            y1, y2 = rail_y_at(sx), rail_y_at(min(width - 1, ex))
            pygame.draw.polygon(surface, (48, 51, 58), [(sx, y1 + 8), (ex, y2 + 8), (ex, height), (sx, height)])

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
                half_platform = int(float(station.get("length_m", 155)) * scale / 2)
                pygame.draw.line(surface, (205, 55, 65), (x - half_platform, sy - 8), (x + half_platform, sy - 8), 5)
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

        loco_x = (line.path.total_length - train.position - train.loco_length_m - camera_x) * scale
        loco_width = max(1, round(train.loco_length_m * scale))
        car_width = max(1, round(train.car_length_m * scale))
        loco_height = (self._scaled_sprite(self.loco_image, loco_width).get_height()
                       if self._scaled_sprite(self.loco_image, loco_width) is not None else 48)
        car = self._scaled_sprite(self.car_image, car_width, loco_height)
        loco_src_w, loco_src_h = self.loco_image.get_size() if self.loco_image is not None else (1, 1)
        left_ratio, right_ratio = 499 / loco_src_w, 1902 / loco_src_w
        axle_y_ratio = 464 / loco_src_h

        # Eight vehicles: leading cab, six passenger cars, and a reversed cab at the rear.
        vehicle_x = loco_x
        for wagon in train.wagons:
            vehicle_width = loco_width if wagon.is_loco else car_width
            vehicle_image = self.loco_image if wagon.is_loco else self.car_image
            if wagon.is_loco and wagon.index == len(train.wagons) - 1 and vehicle_image is not None:
                vehicle_image = pygame.transform.flip(vehicle_image, True, False)
            # Skip off-screen wagons before doing expensive sprite scaling and rotation.
            if vehicle_x + vehicle_width < -loco_width or vehicle_x > width + loco_width:
                vehicle_x += vehicle_width
                continue
            if vehicle_image is not None:
                if wagon.is_loco:
                    src_w, src_h = vehicle_image.get_size()
                    if wagon.index == len(train.wagons) - 1:
                        vehicle_left_ratio, vehicle_right_ratio = 1 - right_ratio, 1 - left_ratio
                    else:
                        vehicle_left_ratio, vehicle_right_ratio = left_ratio, right_ratio
                    left_x = vehicle_x + vehicle_left_ratio * vehicle_width
                    right_x = vehicle_x + vehicle_right_ratio * vehicle_width
                    left_y, right_y = rail_y_at(left_x), rail_y_at(right_x)
                    self._draw_train_sprite(surface, vehicle_image, vehicle_width, loco_height,
                                            vehicle_left_ratio, vehicle_right_ratio,
                                            axle_y_ratio, left_x, right_x, left_y, right_y,
                                            f"loco_{wagon.index}", frame_dt)
                else:
                    car_sprite = self._scaled_sprite(vehicle_image, vehicle_width, loco_height)
                    if car_sprite is not None:
                        src_w, src_h = self.car_image.get_size()
                        left_ratio_car, right_ratio_car = 334 / src_w, 1898 / src_w
                        left_x = vehicle_x + left_ratio_car * vehicle_width
                        right_x = vehicle_x + right_ratio_car * vehicle_width
                        left_y, right_y = rail_y_at(left_x), rail_y_at(right_x)
                        self._draw_train_sprite(surface, vehicle_image, vehicle_width, loco_height,
                                                left_ratio_car, right_ratio_car, 435 / src_h,
                                                left_x, right_x, left_y, right_y,
                                                f"wagon_{wagon.index}", frame_dt)
            else:
                left_y, right_y = rail_y_at(vehicle_x), rail_y_at(vehicle_x + vehicle_width)
                pygame.draw.polygon(surface, (205, 210, 215) if wagon.is_loco else (185, 190, 196),
                                    [(vehicle_x, left_y - 48),
                                     (vehicle_x + vehicle_width, right_y - 48),
                                     (vehicle_x + vehicle_width, right_y),
                                     (vehicle_x, left_y)])
            vehicle_x += vehicle_width

        # Driving HUD remains fixed to the screen.
        speed_limit_kmh = train.als.speed_limit(line, train.position, train.max_speed) * 3.6
        pygame.draw.rect(surface, (12, 15, 20), (16, 16, 430, 190), border_radius=8)
        surface.blit(self.font.render(f"81-760 «Ока»", True, (240, 240, 240)), (30, 25))
        surface.blit(self.font.render(f"Скорость: {train.speed * 3.6:05.1f} км/ч", True, (110, 220, 160)), (30, 56))
        surface.blit(self.small_font.render(f"Ограничение: {speed_limit_kmh:.0f} км/ч", True, (245, 205, 105)), (30, 89))
        lever_color = (255, 180, 95) if train.controller_notch < 0 else (110, 220, 160)
        surface.blit(self.font.render(f"Ручка: {train.controller_label}", True, lever_color), (30, 115))
        surface.blit(self.small_font.render(f"Путь: {train.position:.0f} м / {line.path.total_length:.0f} м", True, (210, 215, 222)), (30, 147))
        next_station = next((station for station in line.stations
                             if float(station.get("position", 0)) > train.position), None)
        if next_station is not None:
            next_distance = max(0.0, float(next_station["position"]) - train.position)
            next_text = f"До {next_station['name']}: {next_distance / 1000:.2f} км"
        else:
            next_text = "Конечная станция"
        surface.blit(self.small_font.render(next_text, True, (230, 150, 155)), (465, 25))
        surface.blit(self.small_font.render("A/← тормоз   D/→ тяга   SPACE экстр. тормоз", True, (205, 210, 218)), (30, 173))
