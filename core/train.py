"""Playable train consist with smooth, speed-supervised longitudinal motion."""
from core.wagon import Wagon
from core.als_ars import AlsArs


class Train:
    def __init__(self, data=None):
        data = data or {}
        self.name = data.get("name", "81-760")
        self.max_speed = float(data.get("max_speed_kmh", 90)) / 3.6
        self.acceleration = float(data.get("acceleration_mps2", 0.9))
        self.service_brake = float(data.get("brake_mps2", 1.15))
        self.emergency_brake = float(data.get("emergency_brake_mps2", 1.4))
        self.jerk_limit = float(data.get("jerk_mps3", 0.45))
        car_count = max(1, int(data.get("wagons", 6)))
        self.wagons = [Wagon(self.name, i, is_loco=(i == 0)) for i in range(car_count)]
        self.loco_length_m = float(data.get("loco_length_m", 20.0))
        self.car_length_m = float(data.get("car_length_m", 19.0))
        self.position = 80.0
        self.speed = 0.0
        self.throttle = 0.0
        self.brake = 0.0
        self.emergency_brake_active = False
        self.acceleration_state = 0.0
        self.als = AlsArs()

    @property
    def consist_length_m(self):
        if not self.wagons:
            return self.loco_length_m
        return self.loco_length_m + (len(self.wagons) - 1) * self.car_length_m

    def update(self, dt, line):
        if dt <= 0:
            return
        # Avoid large physics jumps if the window stalls for a moment.
        dt = min(dt, 0.1)
        limit = self.als.speed_limit(line, self.position, self.max_speed)
        # Smoothly start and release traction; no instant speed changes.
        if self.brake > 0:
            deceleration = self.emergency_brake if self.emergency_brake_active else self.service_brake
            self.speed = max(0.0, self.speed - deceleration * min(1.0, self.brake) * dt)
            self.acceleration_state = 0.0
        else:
            # Automatically brake before a restrictive signal / speed restriction.
            if self.speed > limit:
                self.speed = max(limit, self.speed - self.service_brake * dt)
                self.acceleration_state = min(0.0, self.acceleration_state)
            else:
                target_acceleration = self.acceleration * min(1.0, max(0.0, self.throttle))
                if self.speed >= limit:
                    target_acceleration = min(0.0, target_acceleration)
                change = self.jerk_limit * dt
                self.acceleration_state += max(-change, min(change, target_acceleration - self.acceleration_state))
                self.speed = max(0.0, min(limit, self.speed + self.acceleration_state * dt))
                # Rolling resistance gently slows the train when coasting.
                if self.throttle <= 0 and self.speed > 0:
                    self.speed = max(0.0, self.speed - 0.025 * dt)
        self.position = min(max(0.0, line.path.total_length), self.position + self.speed * dt)
        if self.position >= line.path.total_length:
            self.speed = 0.0
            self.acceleration_state = 0.0
