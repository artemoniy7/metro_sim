"""Real-time station clock, passenger counts, and boarding simulation."""
from datetime import datetime
import random


class StationSimulation:
    PEAK_HOURS = ((7, 10), (17, 20))

    def __init__(self, stations):
        now = datetime.now()
        self.seconds_of_day = now.hour * 3600 + now.minute * 60 + now.second
        self.stations = stations
        self.passengers = {}
        self._boarding_timers = {}
        self._last_population_update = 0.0
        self.elapsed = 0.0
        self.current_station_index = None
        self.is_peak = self._is_peak()
        for index, station in enumerate(stations):
            self.passengers[index] = random.randint(35, 75) if self.is_peak else random.randint(8, 35)
            self._boarding_timers[index] = 0.0

    def _is_peak(self):
        hour = int(self.seconds_of_day // 3600)
        return any(start <= hour < end for start, end in self.PEAK_HOURS)

    @property
    def clock_text(self):
        seconds = int(self.seconds_of_day) % 86400
        hour, remainder = divmod(seconds, 3600)
        minute, second = divmod(remainder, 60)
        return f"{hour:02d}:{minute:02d}:{second:02d}"

    @property
    def period_text(self):
        return "ЧАС ПИК" if self.is_peak else "ОБЫЧНОЕ ВРЕМЯ"

    def update(self, dt, train, doors_open):
        dt = max(0.0, min(float(dt), 0.1))
        self.elapsed += dt
        self.seconds_of_day = (self.seconds_of_day + dt) % 86400
        was_peak = self.is_peak
        self.is_peak = self._is_peak()
        if self.is_peak != was_peak:
            for index in self.passengers:
                low, high = (35, 75) if self.is_peak else (8, 35)
                self.passengers[index] = random.randint(low, high)

        self._last_population_update += dt
        if self._last_population_update >= 5.0:
            steps = int(self._last_population_update // 5.0)
            self._last_population_update %= 5.0
            low, high = (3, 9) if self.is_peak else (0, 4)
            for index in self.passengers:
                self.passengers[index] = min(
                    180, self.passengers[index] + random.randint(low, high) * steps
                )

        if not doors_open or abs(float(train.speed)) >= 0.05:
            return

        # Board waiting passengers only while stopped with doors open at a platform.
        for index, station in enumerate(self.stations):
            center = float(station.get("position", 0.0))
            half_length = float(station.get("length_m", 162.0)) / 2.0
            if abs(float(train.position) - center) <= half_length + 8.0:
                self._boarding_timers[index] += dt
                if self._boarding_timers[index] >= 0.5:
                    intervals = int(self._boarding_timers[index] / 0.5)
                    self._boarding_timers[index] %= 0.5
                    self.passengers[index] = max(
                        0, self.passengers[index] - intervals * random.randint(1, 3)
                    )
                break

    def station_at_position(self, position, extra_distance=0.0):
        for index, station in enumerate(self.stations):
            center = float(station.get("position", 0.0))
            half_length = float(station.get("length_m", 162.0)) / 2.0
            if abs(float(position) - center) <= half_length + extra_distance:
                return index, station
        return None, None

    def nearest_station(self, position):
        if not self.stations:
            return None, None, float("inf")
        index, station = min(
            enumerate(self.stations),
            key=lambda pair: abs(float(position) - float(pair[1].get("position", 0.0))),
        )
        center = float(station.get("position", 0.0))
        half_length = float(station.get("length_m", 162.0)) / 2.0
        distance = max(0.0, abs(float(position) - center) - half_length)
        return index, station, distance
