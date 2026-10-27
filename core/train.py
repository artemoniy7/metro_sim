"""Playable train consist with a notched traction/brake controller."""
from core.wagon import Wagon
from core.als_ars import AlsArs


class Train:
    def __init__(self, data=None):
        data = data or {}
        self.name = data.get("name", "81-760")
        self.display_name = data.get("display_name", self.name)
        self.max_speed = float(data.get("max_speed_kmh", 90)) / 3.6
        self.acceleration = float(data.get("acceleration_mps2", 0.9))
        self.service_brake = float(data.get("brake_mps2", 1.15))
        self.emergency_brake = float(data.get("emergency_brake_mps2", 1.4))
        self.jerk_limit = float(data.get("jerk_mps3", 0.45))
        # Per-notch values are configured per train, in m/s².
        self.traction_notches = [float(v) for v in data.get(
            "traction_notches_mps2", [0.25, 0.45, 0.68, self.acceleration]
        )]
        self.brake_notches = [float(v) for v in data.get(
            "brake_notches_mps2", [0.45, 0.75, self.service_brake]
        )]
        self.controller_notch = 0  # -3..-1 = T3..T1, 0 = coast, 1..4 = G1..G4
        car_count = max(1, int(data.get("wagons", 6)))
        self.wagons = [Wagon(self.name, i, is_loco=(i == 0)) for i in range(car_count)]
        self.loco_length_m = float(data.get("loco_length_m", 20.0))
        self.car_length_m = float(data.get("car_length_m", 19.0))
        self.position = 80.0
        self.speed = 0.0
        self.emergency_brake_active = False
        self.acceleration_state = 0.0
        self.brake_applied = False
        self._brake_command_timer = 0.0
        self.BRAKE_RESPONSE_DELAY_S = 1.0
        self.als = AlsArs()

    @property
    def consist_length_m(self):
        if not self.wagons:
            return self.loco_length_m
        return self.loco_length_m + (len(self.wagons) - 1) * self.car_length_m

    @property
    def controller_label(self):
        if self.controller_notch < 0:
            return f"T{abs(self.controller_notch)}"
        if self.controller_notch > 0:
            return f"G{self.controller_notch}"
        return "0 (выбег)"

    def update(self, dt, line):
        if dt <= 0:
            return
        dt = min(dt, 0.1)
        limit = self.als.speed_limit(line, self.position, self.max_speed)

        # The train takes one second to react to a brake command.
        brake_commanded = self.emergency_brake_active or self.controller_notch < 0
        if brake_commanded:
            self._brake_command_timer += dt
        else:
            self._brake_command_timer = 0.0
        self.brake_applied = brake_commanded and self._brake_command_timer >= self.BRAKE_RESPONSE_DELAY_S

        if self.brake_applied:
            if self.emergency_brake_active:
                deceleration = self.emergency_brake
            else:
                # T1 is gentle braking; T3 applies the strongest service braking.
                index = min(len(self.brake_notches) - 1, abs(self.controller_notch) - 1)
                deceleration = self.brake_notches[index]

            # Ramp braking force in gradually instead of changing speed abruptly.
            target_acceleration = -deceleration
            change = self.jerk_limit * dt
            self.acceleration_state += max(
                -change, min(change, target_acceleration - self.acceleration_state)
            )
            self.speed = max(0.0, self.speed + self.acceleration_state * dt)
            if self.speed <= 0.0:
                self.acceleration_state = 0.0
        else:
            # Supervision brakes automatically if the train exceeds its permitted speed.
            if self.speed > limit:
                self.speed = max(limit, self.speed - self.service_brake * dt)
                self.acceleration_state = min(0.0, self.acceleration_state)
            else:
                target_acceleration = 0.0
                if self.controller_notch > 0:
                    index = min(len(self.traction_notches) - 1, self.controller_notch - 1)
                    target_acceleration = self.traction_notches[index]
                    # Traction weakens as speed rises, so the train accelerates
                    # more strongly at low speed and more gently near 80 km/h.
                    speed_kmh = self.speed * 3.6
                    high_speed_fade = max(0.0, min(1.0, (speed_kmh - 40.0) / 40.0))
                    target_acceleration *= 1.0 - 0.45 * high_speed_fade
                if self.speed >= limit:
                    target_acceleration = min(0.0, target_acceleration)
                change = self.jerk_limit * dt
                self.acceleration_state += max(
                    -change, min(change, target_acceleration - self.acceleration_state)
                )
                self.speed = max(0.0, min(limit, self.speed + self.acceleration_state * dt))
                if self.controller_notch == 0 and self.speed > 0:
                    self.speed = max(0.0, self.speed - 0.025 * dt)

        self.position = min(max(0.0, line.path.total_length), self.position + self.speed * dt)
        if self.position >= line.path.total_length:
            self.speed = 0.0
            self.acceleration_state = 0.0
