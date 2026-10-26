"""Playable train consist and longitudinal motion. World distances are metres."""
from core.wagon import Wagon
from core.als_ars import AlsArs


class Train:
    def __init__(self, data=None):
        data = data or {}
        self.name = data.get("name", "81-760")
        self.max_speed = float(data.get("max_speed_kmh", 90)) / 3.6
        self.acceleration = float(data.get("acceleration_mps2", 0.9))
        self.service_brake = float(data.get("brake_mps2", 1.15))
        # Six-car consist: one 20 m motor car (loco sprite) and five 19 m cars.
        car_count = max(1, int(data.get("wagons", 6)))
        self.wagons = [Wagon(self.name, i, is_loco=(i == 0))
                       for i in range(car_count)]
        self.loco_length_m = float(data.get("loco_length_m", 20.0))
        self.car_length_m = float(data.get("car_length_m", 19.0))
        self.position = 80.0  # leading left-facing cab, in metres along the route
        self.speed = 0.0      # m/s
        self.throttle = 0.0
        self.brake = 0.0
        self.als = AlsArs()

    @property
    def consist_length_m(self):
        if not self.wagons:
            return self.loco_length_m
        return self.loco_length_m + (len(self.wagons) - 1) * self.car_length_m

    def update(self, dt, line):
        limit = self.als.speed_limit(line, self.position, self.max_speed)
        if self.brake > 0:
            self.speed = max(0.0, self.speed - self.service_brake * self.brake * dt)
        else:
            self.speed = min(limit, self.speed + self.acceleration * self.throttle * dt)
        # The train advances toward the left-facing cab's direction along the route.
        self.position += self.speed * dt
        self.position = min(self.position, max(0.0, line.path.total_length))
        if self.speed > limit:
            self.speed = max(limit, self.speed - self.service_brake * dt)
