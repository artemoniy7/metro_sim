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
        self.door_left_image = self._load_sprite(ASSETS_DIR / "trains" / "81-760" / "81-760-door-left.png")
        self.door_right_image = self._load_sprite(ASSETS_DIR / "trains" / "81-760" / "81-760-door-right.png")
        self.door_open_amount = 0.0
        self.door_indicator_phase = 0.0
        self.tunnel_image = self._load_sprite(ASSETS_DIR / "track" / "tunnel.jpg")
        # Transparent signal sprite; lamp coordinates are in source-image pixels.
        self.signal_image = self._load_sprite(ASSETS_DIR / "track" / "light.png")
        self.signal_lamp_points = {
            # Lamp centers in the full 1024x1536 atlas.
            2: ((437, 101), (437, 190)),
            3: ((363, 451), (363, 585), (363, 724)),
        }
        self.signal_heads = {}
        if self.signal_image is not None:
            atlas_w, atlas_h = self.signal_image.get_size()
            signal_crops = {
                2: (385, 60, 90, 165),
                3: (315, 405, 95, 350),
            }
            for lamp_count, (cx, cy, cw, ch) in signal_crops.items():
                if cx + cw <= atlas_w and cy + ch <= atlas_h:
                    self.signal_heads[lamp_count] = self.signal_image.subsurface(
                        (cx, cy, cw, ch)
                    ).copy()
        self.signal_glow_cache = {}
        self.station_images = {}
        self.legacy_station_image = None
        self._station_asset_line_id = None
        self.vehicle_angles = {}
        self._station_tile_cache = {}
        self.last_render_time = None
        self._tunnel_tile_cache = {}

    def configure_line_station_sprites(self, line_id):
        """Load station textures only from the selected line's asset folder."""
        line_id = str(line_id or "")
        if line_id == self._station_asset_line_id:
            return
        self._station_asset_line_id = line_id
        station_dir = ASSETS_DIR / "stations" / line_id
        self.station_images = {}
        self.legacy_station_image = self._load_sprite(station_dir / "altufyevo.png")
        for station_number in range(1, 100):
            texture = self._load_sprite(station_dir / f"st_{station_number:02d}.png")
            if texture is not None:
                self.station_images[station_number - 1] = texture
        self._station_tile_cache.clear()

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

    def _draw_doors(self, sprite, source_image, vehicle_width, vehicle_height, is_loco, is_rear_cab=False):
        """Draw animated door leaves on passenger cars and both cab cars."""
        if self.door_left_image is None or self.door_right_image is None:
            return

        source_width, source_height = source_image.get_size()
        sx = vehicle_width / source_width
        sy = vehicle_height / source_height
        amount = self.door_open_amount

        if is_loco:
            # Door openings on the front cab sprite.
            openings = ((373, 81, 553, 322), (939, 81, 1119, 322),
                        (1433, 81, 1613, 322), (1897, 81, 2077, 322))
            if is_rear_cab:
                openings = tuple(
                    (source_width - x2, y1, source_width - x1, y2)
                    for x1, y1, x2, y2 in reversed(openings)
                )
            for x1, y1, x2, y2 in openings:
                door_height = max(1, round((y2 - y1) * sy))
                left_width = max(1, round(91 * sx))
                right_width = max(1, round(90 * sx))
                left_door = pygame.transform.smoothscale(
                    self.door_left_image, (left_width, door_height)
                )
                right_door = pygame.transform.smoothscale(
                    self.door_right_image, (right_width, door_height)
                )
                sprite.blit(left_door, (
                    round(x1 * sx - left_door.get_width() * amount),
                    round(y1 * sy)
                ))
                sprite.blit(right_door, (
                    round((x2 - 90) * sx + right_door.get_width() * amount),
                    round(y1 * sy)
                ))
        else:
            # Passenger-car door locations: upper and lower x coordinates
            # supplied for each opening. The two leaves slide apart from
            # the opening's upper/lower x positions as the doors open.
            top_xs = (171, 725, 1261, 1815)
            bottom_xs = (346, 900, 1436, 1990)
            if is_rear_cab:
                top_xs = tuple(source_width - x for x in reversed(bottom_xs))
                bottom_xs = tuple(source_width - x for x in reversed(top_xs))
            door_y = 70
            door_height = max(1, round((298 - door_y) * sy))
            left_width = max(1, round(90 * sx))
            right_width = max(1, round(90 * sx))
            left_door = pygame.transform.smoothscale(
                self.door_left_image, (left_width, door_height)
            )
            right_door = pygame.transform.smoothscale(
                self.door_right_image, (right_width, door_height)
            )
            for top_x, bottom_x in zip(top_xs, bottom_xs):
                sprite.blit(left_door, (
                    round(top_x * sx - left_door.get_width() * amount),
                    round(door_y * sy)
                ))
                sprite.blit(right_door, (
                    round((bottom_x - 90) * sx + right_door.get_width() * amount),
                    round(door_y * sy)
                ))

    def _draw_door_indicators(self, sprite, source_image, vehicle_width, vehicle_height,
                               is_loco, is_rear_cab, elapsed, active):
        if not active:
            return
        # Half a second lit, half a second dark.
        if int(elapsed * 2.0) % 2 == 1:
            return
        source_width, source_height = source_image.get_size()
        sx = vehicle_width / source_width
        sy = vehicle_height / source_height
        points = ((463, 75), (1030, 75), (1525, 75), (1990, 75)) if is_loco else (
            (258, 65), (815, 65), (1349, 65), (1904, 65)
        )
        if is_rear_cab:
            points = tuple((source_width - x, y) for x, y in reversed(points))
        radius = max(2, round(7 * min(sx, sy)))
        for x, y in points:
            center = (round(x * sx), round(y * sy))
            pygame.draw.circle(sprite, (70, 0, 0), center, radius + max(1, radius // 3))
            pygame.draw.circle(sprite, (255, 25, 20), center, radius)
            pygame.draw.circle(sprite, (255, 150, 140), (
                center[0] - max(1, radius // 3), center[1] - max(1, radius // 3)
            ), max(1, radius // 3))

    @staticmethod
    def _track_offset(world_x):
        """Smooth, shallow test-track rises and dips, measured in world metres."""
        import math
        return (0.45 * math.sin(world_x / 85.0)
                + 0.18 * math.sin(world_x / 38.0 + 0.8))

    def draw_scene(self, surface, line, train, camera, elapsed, doors_open=False, door_closing=False, other_trains=None, station_simulation=None, depot_mode=False, depot_route_set=False):
        width, height = surface.get_size()
        if self.last_render_time is None:
            frame_dt = 1.0 / 60.0
        else:
            frame_dt = max(0.0, min(0.1, elapsed - self.last_render_time))
        self.last_render_time = elapsed
        target_door_amount = 1.0 if doors_open else 0.0
        door_step = frame_dt / 4.0
        if self.door_open_amount < target_door_amount:
            self.door_open_amount = min(target_door_amount, self.door_open_amount + door_step)
        elif self.door_open_amount > target_door_amount:
            self.door_open_amount = max(target_door_amount, self.door_open_amount - door_step)
        scale = camera.pixels_per_metre
        base_track_y = int(height * 0.79)
        camera_x = camera.x

        def rail_y_at(screen_x):
            world_x = camera_x + screen_x / scale
            route_position = max(0.0, min(line.path.total_length, line.path.total_length - world_x))
            path_depth = line.path.point_at(route_position)[1]
            depth_m = path_depth
            offset_weight = 1.0

            # Platforms are level, but their elevation must blend into the
            # tunnel gradually. Otherwise the procedural track offset and the
            # route profile create a visible kink right at the station exit.
            transition_m = 180.0
            for item in line.stations:
                center = float(item.get("position", 0))
                half_length = float(item.get("length_m", 162)) / 2.0
                distance = abs(route_position - center)
                station_depth = float(item.get("depth_m", path_depth))
                if distance <= half_length:
                    depth_m = station_depth
                    offset_weight = 0.0
                    break
                if distance < half_length + transition_m:
                    t = (distance - half_length) / transition_m
                    blend = t * t * (3.0 - 2.0 * t)
                    depth_m = station_depth * (1.0 - blend) + path_depth * blend
                    offset_weight = blend
                    break

            return round(base_track_y + (depth_m - 10.0) * 1.35
                         - self._track_offset(world_x) * scale * offset_weight)

        depot_length = float(getattr(line, "depot_length", 0.0))
        ground_y = int(height * 0.58)
        pygame.draw.rect(surface, (25, 30, 39), (0, 0, width, height))
        if depot_length > 0.0:
            # Surface depot scenery is drawn in world coordinates; it scrolls
            # under the exact same camera as the tunnel and station platforms.
            pygame.draw.rect(surface, (112, 164, 194), (0, 0, width, ground_y))
            pygame.draw.rect(surface, (79, 101, 70), (0, ground_y, width, height - ground_y))
            for tree_world in range(35, int(depot_length), 55):
                sx = round((line.path.total_length - tree_world - camera_x) * scale)
                if -60 < sx < width + 60:
                    pygame.draw.rect(surface, (79, 74, 58), (sx - 4, ground_y - 42, 8, 42))
                    pygame.draw.circle(surface, (58, 99, 68), (sx, ground_y - 52), 25)
            shed_world = 95.0
            shed_x = round((line.path.total_length - shed_world - camera_x) * scale)
            shed_w = round(125.0 * scale)
            if -shed_w < shed_x < width:
                pygame.draw.rect(surface, (137, 151, 157),
                                 (shed_x, ground_y - 125, shed_w, 125))
                pygame.draw.rect(surface, (65, 79, 88),
                                 (shed_x, ground_y - 125, shed_w, 125), 3)
                pygame.draw.rect(surface, (43, 53, 61),
                                 (shed_x + 12, ground_y - 83, shed_w - 24, 83))
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
                station_index = next((
                    index for index, station in enumerate(line.stations)
                    if abs(route_position - float(station.get("position", 0)))
                    <= float(station.get("length_m", 162)) / 2
                ), None)
                if depot_length > 0.0 and route_position < depot_length:
                    pygame.draw.rect(surface, (112, 164, 194), (sx, 0, strip_width, ground_y))
                    pygame.draw.rect(surface, (79, 101, 70),
                                     (sx, ground_y, strip_width, max(1, track_y - ground_y)))
                    pygame.draw.rect(surface, (70, 64, 56),
                                     (sx, track_y - 4, strip_width, 18))
                elif station_index is not None:
                    station_height = max(1, round(8.5 * scale))
                    station_bottom_extra = max(1, round(0.25 * scale))
                    station_texture = self.station_images.get(
                        station_index, self.legacy_station_image
                    )
                    if station_texture is not None:
                        station_width = max(1, round(
                            station_height * station_texture.get_width()
                            / station_texture.get_height()
                        ))
                        station_key = (id(station_texture), station_width, station_height)
                        if station_key not in self._station_tile_cache:
                            self._station_tile_cache = {
                                station_key: pygame.transform.smoothscale(
                                    station_texture, (station_width, station_height)
                                )
                            }
                        station_tile = self._station_tile_cache[station_key]
                        tile_world_width = station_width / scale
                        tile_x = int(((world_x % tile_world_width) / tile_world_width) * station_width)
                        src_x = min(station_width - 1, max(0, tile_x))
                        slice_width = min(strip_width, station_width - src_x)
                        if slice_width > 0:
                            surface.blit(
                                station_tile.subsurface((src_x, 0, slice_width, station_height)),
                                (sx, track_y - station_height + station_bottom_extra)
                            )
                        if slice_width < strip_width:
                            extra_width = min(strip_width - slice_width, station_width)
                            surface.blit(
                                station_tile.subsurface((0, 0, extra_width, station_height)),
                                (sx + slice_width, track_y - station_height + station_bottom_extra)
                            )
                    else:
                        pygame.draw.rect(
                            surface, (142, 24, 34),
                            (sx, track_y - station_height, strip_width, station_height + 20)
                        )
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
            for sx in range(0, width, 4):
                route_position = line.path.total_length - (camera_x + sx / scale)
                if depot_length > 0.0 and route_position < depot_length:
                    track_y = rail_y_at(sx)
                    pygame.draw.rect(surface, (112, 164, 194), (sx, 0, 4, ground_y))
                    pygame.draw.rect(surface, (79, 101, 70), (sx, ground_y, 4, max(1, track_y-ground_y)))
                elif any(abs(route_position - float(station.get("position", 0))) <= float(station.get("length_m", 155)) / 2 for station in line.stations):
                    track_y = rail_y_at(sx)
                    pygame.draw.rect(surface, (142, 24, 34), (sx, track_y - tunnel_height, 4, tunnel_height + 20))

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
            if -40 < x < width + 40:
                sy = rail_y_at(max(0, min(width - 1, x)))
                pole_color = (88, 91, 98) if signal.operational else (65, 67, 72)

                # Use simple geometric signals as the primary renderer.
                # Their on-screen size does not change with camera zoom.
                head_width = 18
                head_height = 40
                # Mount the signal on the tunnel wall, not beside the rails.
                # Keep the signal head a fixed pixel size at every zoom level.
                wall_y = sy - tunnel_height + 8
                head_y = wall_y + 5
                bracket_y = head_y + head_height // 2
                pygame.draw.line(
                    surface, pole_color,
                    (x - head_width // 2 - 7, bracket_y),
                    (x - head_width // 2, bracket_y), 3
                )

                body = pygame.Rect(
                    x - head_width // 2, head_y, head_width, head_height
                )
                pygame.draw.rect(surface, (20, 22, 26), body, border_radius=3)
                pygame.draw.rect(surface, pole_color, body, 1, border_radius=3)

                if signal.lamp_count == 2:
                    lamp_aspects = ("red", "green")
                else:
                    lamp_aspects = ("red", "yellow", "green")

                lamp_radius = 5
                for lamp_index, aspect in enumerate(lamp_aspects):
                    lamp_y = head_y + round(
                        (lamp_index + 0.5) * head_height / len(lamp_aspects)
                    )
                    if signal.operational and signal.aspect == aspect:
                        color = signal.ASPECTS[aspect]
                        # Bright center makes the active lamp clearly readable.
                        pygame.draw.circle(surface, color, (x, lamp_y), lamp_radius)
                        pygame.draw.circle(
                            surface, (255, 245, 225),
                            (x - 1, lamp_y - 1), 2
                        )
                    else:
                        pygame.draw.circle(
                            surface, (45, 47, 51), (x, lamp_y), lamp_radius
                        )

                if signal.operational:
                    label = self.small_font.render(
                        signal.name, True, (205, 210, 218)
                    )
                    surface.blit(
                        label, (x + head_width // 2 + 4, head_y - 14)
                    )

        loco_x = (line.path.total_length - train.position - train.loco_length_m - camera_x) * scale
        loco_width = max(1, round(train.loco_length_m * scale))
        car_width = max(1, round(train.car_length_m * scale))
        loco_scaled = self._scaled_sprite(self.loco_image, loco_width)
        loco_height = loco_scaled.get_height() if loco_scaled is not None else 48
        vehicle_x = loco_x
        for wagon in train.wagons:
            vehicle_width = loco_width if wagon.is_loco else car_width
            vehicle_image = self.loco_image if wagon.is_loco else self.car_image
            is_rear_cab = wagon.is_loco and wagon.index == len(train.wagons) - 1
            if is_rear_cab and vehicle_image is not None:
                vehicle_image = pygame.transform.flip(vehicle_image, True, False)
            if vehicle_x + vehicle_width >= -loco_width and vehicle_x <= width + loco_width:
                if vehicle_image is not None:
                    sprite = pygame.transform.smoothscale(vehicle_image, (max(1, vehicle_width), max(1, loco_height)))
                    self._draw_doors(
                        sprite, vehicle_image, vehicle_width, loco_height,
                        is_loco=wagon.is_loco, is_rear_cab=is_rear_cab
                    )
                    self._draw_door_indicators(
                        sprite, vehicle_image, vehicle_width, loco_height,
                        is_loco=wagon.is_loco, is_rear_cab=is_rear_cab,
                        elapsed=elapsed, active=door_closing
                    )
                    center_x = vehicle_x + vehicle_width / 2
                    center_y = rail_y_at(center_x)
                    surface.blit(sprite, (round(vehicle_x), round(center_y - loco_height + 4)))
                else:
                    center_x = vehicle_x + vehicle_width / 2
                    center_y = rail_y_at(center_x)
                    pygame.draw.rect(surface, (205, 210, 215) if wagon.is_loco else (185, 190, 196), (round(vehicle_x), round(center_y - 48 + 4), vehicle_width, 48))
            vehicle_x += vehicle_width

        # Draw AI trains using the same vehicle sprites and shared world camera.
        for bot_train in (other_trains or []):
            bot_x = (line.path.total_length - bot_train.position
                     - bot_train.loco_length_m - camera_x) * scale
            bot_loco_width = max(1, round(bot_train.loco_length_m * scale))
            bot_car_width = max(1, round(bot_train.car_length_m * scale))
            bot_vehicle_x = bot_x
            for wagon in bot_train.wagons:
                vehicle_width = bot_loco_width if wagon.is_loco else bot_car_width
                vehicle_image = self.loco_image if wagon.is_loco else self.car_image
                is_rear_cab = wagon.is_loco and wagon.index == len(bot_train.wagons) - 1
                if is_rear_cab and vehicle_image is not None:
                    vehicle_image = pygame.transform.flip(vehicle_image, True, False)
                if bot_vehicle_x + vehicle_width >= -bot_loco_width and bot_vehicle_x <= width + bot_loco_width:
                    center_y = rail_y_at(bot_vehicle_x + vehicle_width / 2)
                    if vehicle_image is not None:
                        sprite = pygame.transform.smoothscale(
                            vehicle_image, (max(1, vehicle_width), max(1, loco_height))
                        )
                        # AI doors are rendered independently of the player's door animation.
                        if getattr(bot_train, "doors_open", False):
                            saved_door_amount = self.door_open_amount
                            self.door_open_amount = 1.0
                            self._draw_doors(
                                sprite, vehicle_image, vehicle_width, loco_height,
                                is_loco=wagon.is_loco, is_rear_cab=is_rear_cab
                            )
                            self.door_open_amount = saved_door_amount
                        surface.blit(sprite, (round(bot_vehicle_x), round(center_y - loco_height + 4)))
                    else:
                        pygame.draw.rect(
                            surface, (130, 150, 170),
                            (round(bot_vehicle_x), round(center_y - 44), vehicle_width, 44)
                        )
                bot_vehicle_x += vehicle_width
            if -80 < bot_x < width + 80:
                bot_label = self.small_font.render(
                    getattr(bot_train, "display_name", "Бот"),
                    True, (175, 205, 235)
                )
                surface.blit(bot_label, (round(bot_x), max(220, round(rail_y_at(bot_x) - 68))))

        speed_limit_kmh = train.als.speed_limit(line, train.position, train.max_speed) * 3.6
        if depot_mode:
            # A shunting signal is fixed in the depot world, so it moves with
            # the camera rather than being painted as a screen-space icon.
            signal_world = depot_length - 42.0
            signal_x = round((line.path.total_length - signal_world - camera_x) * scale)
            signal_y = round(base_track_y - 100)
            if -30 < signal_x < width + 30:
                pygame.draw.line(surface, (80, 84, 91), (signal_x, signal_y + 24),
                                 (signal_x, base_track_y + 2), 4)
                pygame.draw.rect(surface, (19, 22, 27),
                                 (signal_x - 11, signal_y, 22, 48), border_radius=4)
                lamp = (235, 240, 245) if depot_route_set else (45, 105, 255)
                pygame.draw.circle(surface, lamp, (signal_x, signal_y + 13), 7)
                pygame.draw.circle(surface, (48, 51, 58), (signal_x, signal_y + 34), 6)
        pygame.draw.rect(surface, (12, 15, 20), (16, 16, 455, 245), border_radius=8)
        surface.blit(self.font.render("81-760 «Ока»", True, (240, 240, 240)), (30, 25))
        surface.blit(self.font.render(f"Скорость: {train.speed * 3.6:05.1f} км/ч", True, (110, 220, 160)), (30, 56))
        surface.blit(self.small_font.render(f"АЛС-АРС: {train.als.indication_kmh:.0f} км/ч", True, (245, 205, 105)), (30, 89))
        surface.blit(self.small_font.render(f"Свободно блоков: {train.als.free_blocks_ahead}", True, (170, 195, 215)), (30, 108))
        bot_status = " | ".join(
            f"{getattr(bot, 'display_name', 'Бот')}: {bot.speed * 3.6:.0f} км/ч, {bot.position:.0f} м"
            for bot in (other_trains or [])
        ) or "нет"
        surface.blit(self.small_font.render(f"ИИ-составов: {len(other_trains or [])} ({bot_status})", True, (175, 205, 235)), (30, 130))
        lever_color = (255, 180, 95) if train.controller_notch < 0 else (110, 220, 160)
        surface.blit(self.font.render(f"Ручка: {train.controller_label}", True, lever_color), (30, 115))
        surface.blit(self.small_font.render(f"Путь: {train.position:.0f} м / {line.path.total_length:.0f} м", True, (210, 215, 222)), (30, 147))
        next_station = next((station for station in line.stations if float(station.get("position", 0)) > train.position), None)
        if next_station is not None:
            next_distance = max(0.0, float(next_station["position"]) - train.position)
            next_text = f"До {next_station['name']}: {next_distance / 1000:.2f} км"
        else:
            next_text = "Конечная станция"
        surface.blit(self.small_font.render(next_text, True, (230, 150, 155)), (465, 25))
        controls_text = ("R маршрут   A/← тормоз   D/→ тяга   колесо мыши — масштаб   ←/→ — обзор"
                         if depot_mode else
                         "A/← тормоз   D/→ тяга   SPACE экстр. тормоз   колесо — масштаб")
        surface.blit(self.small_font.render(controls_text, True, (205, 210, 218)), (30, 173))
        if depot_mode:
            status = "МАНЕВРОВЫЙ МАРШРУТ ОТКРЫТ" if depot_route_set else "МАНЕВРОВЫЙ МАРШРУТ ЗАКРЫТ — R"
            surface.blit(self.small_font.render(status, True,
                                                (235, 240, 245) if depot_route_set else (100, 160, 255)),
                         (30, 250))
        if station_simulation is not None:
            surface.blit(self.font.render(f"Время: {station_simulation.clock_text}", True, (245, 245, 245)), (30, 198))
            surface.blit(self.small_font.render(station_simulation.period_text, True,
                                                (255, 190, 100) if station_simulation.is_peak else (150, 210, 230)), (220, 204))
            station_index, nearby_station, station_distance = station_simulation.nearest_station(train.position)
            if nearby_station is not None:
                passenger_count = station_simulation.passengers.get(station_index, 0)
                label = f"Станция: {nearby_station.get('name', '—')} | Ожидают: {passenger_count}"
                surface.blit(self.small_font.render(label, True, (190, 220, 190)), (30, 226))
