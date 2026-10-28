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
        for station in line.stations:
            position = float(station.get("position", 0))
            if position > self.train.position + 12.0:
                return station
        return None

    def update(self, dt, line, audio=None, seconds_to_dispatch=120.0):
        train = self.train
        dt = min(max(0.0, dt), 0.1)
        if dt <= 0:
            return

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
                        if callable(close_sound):
                            close_sound()
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
            stopping_distance = speed * speed / (2.0 * max(0.55, train.brake_notches[-1]))
            if distance <= 3.0 and speed <= 0.8:
                train.controller_notch = 0
            elif speed <= 0.8 and distance > 3.0:
                # Do not hold the brakes forever when the train stopped short
                # of the platform. Creep forward until the stopping point.
                train.controller_notch = 1
            elif distance <= stopping_distance + max(8.0, speed * 1.2):
                train.controller_notch = -3 if speed > 4.0 else -2
            elif speed > target_speed + (1.0 / 3.6):
                train.controller_notch = -1
            elif speed < target_speed - (1.0 / 3.6):
                train.controller_notch = 4
            else:
                train.controller_notch = 0

            if distance <= 3.0 and train.speed <= 0.8:
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
                    if callable(announce):
                        announce(train)
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

        train.doors_open = False
        train.update(dt, line)
