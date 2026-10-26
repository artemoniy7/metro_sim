"""Train consist and longitudinal motion."""
from core.wagon import Wagon
from core.als_ars import AlsArs

class Train:
    def __init__(self, data=None):
        data = data or {}
        self.name = data.get("name", "81-717")
        self.max_speed = float(data.get("max_speed_kmh", 80)) / 3.6
        self.acceleration = float(data.get("acceleration_mps2", 0.8))
        self.service_brake = float(data.get("brake_mps2", 1.0))
        self.wagons = [Wagon(self.name, i) for i in range(int(data.get("wagons", 6)))]
        self.position = 40.0
        self.speed = 0.0
        self.throttle = 0.0
        self.brake = 0.0
        self.als = AlsArs()

    def update(self, dt, line):
        limit = self.als.speed_limit(line, self.position, self.max_speed)
        if self.brake > 0:
            self.speed = max(0.0, self.speed - self.service_brake * self.brake * dt)
        else:
            self.speed = min(limit, self.speed + self.acceleration * self.throttle * dt)
        self.position += self.speed * dt * 4.0
        if line.path.total_length:
            self.position = min(self.position, line.path.total_length)
        if self.speed > limit:
            self.speed = max(limit, self.speed - self.service_brake * dt)
