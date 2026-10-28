"""Simple automatic driving for AI metro trains."""
from core.train import Train


class BotTrain:
    """A deliberately simple driver: accelerate, brake for stations, and dwell."""

    def __init__(self, train_data, start_position=0.0):
        self.train = Train(train_data)
        self.train.position = float(start_position)
        self.train.is_bot = True
        self.state = "running"
        self.target_station = None
        self.dwell_timer = 0.0
        self.informer_timer = 0.0
        self.informer_started = False
        self.announcement_requested = False
        self.closed_for_departure = False

    def _next_station(self, line):
        # Keep the target until the train has actually stopped at it. A small
        # overshoot must not make the bot silently skip the station.
        if self.target_station is not None:
            target_position = float(self.target_station.get("position", 0))
            if target_position >= self.train.position - 15.0:
                return self.target_station

        for station in line.stations:
            position = float(station.get("position", 0))
            if position > self.train.position + 3.0:
                return station
        return None

    def update(self, dt, line, audio=None, seconds_to_dispatch=120.0):
        train = self.train
        dt = min(max(0.0, dt), 0.1)
        if dt <= 0:
            return

        # Bot sounds should only be audible near the player's train. Fade them
        # smoothly from full volume nearby to silence beyond 250 metres.
        player_train = next(
            (other for other in getattr(line, "traffic_trains", [])
             if other is not train and not getattr(other, "is_bot", False)),
            None,
        )
        sound_volume = 0.0
        if player_train is not None:
            distance = abs(float(player_train.position) - float(train.position))
            sound_volume = max(0.0, min(1.0, (250.0 - distance) / 200.0))

        if self.state == "dwelling":
            train.controller_notch = 0
            train.speed = 0.0
            train.acceleration_state = 0.0
            train.doors_open = not self.closed_for_departure
            self.dwell_timer -= dt
            if self.informer_started:
                self.informer_timer += dt
                if self.informer_timer >= 1.0 and not self.closed_for_departure:
                    self.closed_for_departure = True
                    train.doors_open = False
                    if audio is not None:
                        close_sound = getattr(audio, "play_door_sound", None)
                        if callable(close_sound) and sound_volume > 0.01:
                            close_sound(volume=sound_volume)
            if self.dwell_timer <= 0.0 and self.closed_for_departure:
                self.state = "running"
                self.target_station = None
                self.informer_started = False
                self.informer_timer = 0.0
                self.closed_for_departure = False
                train.doors_open = False
            else:
                return

        station = self._next_station(line)
        self.target_station = station
        # Keep 2 km/h below the current ALS-ARS indication.
        indication_kmh, _ = line.block_indication(train.position)
        target_speed = max(0.0, float(indication_kmh) - 2.0) / 3.6

        if station is not None:
            distance = float(station.get("position", 0)) - train.position
            speed = max(0.0, train.speed)
            # Be conservative: include reaction time and brake build-up, not
            # only the ideal physical stopping distance.
            effective_brake = max(0.55, train.brake_notches[-1] * 0.75)
            stopping_distance = speed * speed / (2.0 * effective_brake)
            braking_threshold = stopping_distance + speed * 1.8 + 18.0
            if abs(distance) <= 3.0 and speed <= 0.8:
                train.controller_notch = 0
            elif distance <= 3.0:
                train.controller_notch = -3 if speed > 1.0 else -2
            elif speed <= 0.8 and distance > 3.0:
                # If stopped short, creep forward to the platform.
                train.controller_notch = 1
            elif distance <= braking_threshold:
                train.controller_notch = -3 if speed > 4.0 else -2
            elif speed > target_speed + (1.0 / 3.6):
                train.controller_notch = -1
            elif speed < target_speed - (1.0 / 3.6):
                train.controller_notch = 4
            else:
                train.controller_notch = 0

            if abs(distance) <= 3.0 and train.speed <= 0.8:
                train.position = float(station.get("position", train.position))
                train.speed = 0.0
                train.acceleration_state = 0.0
                train.controller_notch = 0
                train.doors_open = True
                self.state = "dwelling"
                self.informer_started = True
                self.informer_timer = 0.0
                # Normally use the configured station dwell; if the next
                # dispatch is close, make a short stop instead.
                planned = float(station.get("dwell_seconds", 20))
                self.dwell_timer = min(planned, max(1.1, seconds_to_dispatch - 3.0))
                if audio is not None:
                    announce = getattr(audio, "toggle_station_announcer", None)
                    if callable(announce) and sound_volume > 0.01:
                        announce(train, volume=sound_volume)
                return
        else:
            # Regulate speed on the open line; braking for stations takes priority.
            speed = max(0.0, train.speed)
            if speed > target_speed + (1.0 / 3.6):
                train.controller_notch = -1
            elif speed < target_speed - (1.0 / 3.6):
                train.controller_notch = 4
            else:
                train.controller_notch = 0

        # Hard following-distance protection: ALS-ARS target speeds alone
        # are not enough to prevent a bot from running into a stopped train.
        # Use the nearest train ahead and calculate a safe approach speed to
        # its rear, leaving a small clearance for the full consist length.
        nearest_gap = None
        for other in getattr(line, "traffic_trains", []):
            if other is train or not hasattr(other, "position"):
                continue
            other_position = float(other.position)
            if other_position <= train.position + 1.0:
                continue
            other_length = float(getattr(other, "consist_length_m", 0.0))
            gap = other_position - other_length - train.position
            if nearest_gap is None or gap < nearest_gap:
                nearest_gap = gap

        if nearest_gap is not None:
            safety_clearance = 18.0
            usable_gap = max(0.0, nearest_gap - safety_clearance)
            safe_speed = (2.0 * 0.65 * usable_gap) ** 0.5
            if nearest_gap <= safety_clearance:
                train.controller_notch = -3 if train.speed > 1.0 else 0
                if train.speed <= 1.0 and nearest_gap <= safety_clearance:
                    train.speed = 0.0
                    train.acceleration_state = 0.0
            elif train.speed > safe_speed:
                train.controller_notch = -3 if train.speed > 4.0 else -2

        train.doors_open = False
        train.update(dt, line)
