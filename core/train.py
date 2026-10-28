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
        car_count = max(2, int(data.get("wagons", 8)))
        # Two cab cars at the ends, with six passenger cars between them.
        self.wagons = [Wagon(self.name, i, is_loco=(i == 0 or i == car_count - 1))
                       for i in range(car_count)]
        self.loco_length_m = float(data.get("loco_length_m", 20.0))
        self.car_length_m = float(data.get("car_length_m", 19.0))
        self.position = 0.0
        self.speed = 0.0
        self.emergency_brake_active = False
        self.acceleration_state = 0.0
        self.brake_applied = False
        self._brake_command_timer = 0.0
        self._was_brake_commanded = False
        self.brake_release_timer = 0.0
        self.BRAKE_RELEASE_SOUND_S = 4.0
        self.TRACTION_DELAY_AFTER_RELEASE_S = 1.5
        self.doors_open = False
        self.BRAKE_RESPONSE_DELAY_S = float(data.get("brake_response_delay_s", 0.0))
        # Small rolling/air resistance: noticeable over time, but not a hard brake.
        self.rolling_resistance = 0.012  # m/s² at low speed
        self.speed_resistance = 0.00025  # additional m/s² per m/s
        self.als = AlsArs()

    @property
    def consist_length_m(self):
        if not self.wagons:
            return self.loco_length_m
        return (self.loco_length_m * 2
                + max(0, len(self.wagons) - 2) * self.car_length_m)

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
        grade_acceleration = line.path.grade_acceleration(self.position)
        resistance = self.rolling_resistance + self.speed_resistance * self.speed
        # Positive grade acceleration means gravity helps the train move forward.
        natural_acceleration = grade_acceleration - resistance if self.speed > 0 else grade_acceleration

        # The train takes one second to react to a brake command.
        brake_commanded = self.emergency_brake_active or self.controller_notch < 0
        if self._was_brake_commanded and not brake_commanded:
            # At a stop, play the 4 s release sound, then wait 1.5 s before allowing traction.
            # When releasing the brakes while moving, neither sound nor extra delay is needed.
            if abs(self.speed) < 0.2 / 3.6:
                self.brake_release_timer = (
                    self.BRAKE_RELEASE_SOUND_S + self.TRACTION_DELAY_AFTER_RELEASE_S
                )
            else:
                self.brake_release_timer = 0.0
        if brake_commanded:
            self._brake_command_timer += dt
        else:
            self._brake_command_timer = 0.0
        self._was_brake_commanded = brake_commanded
        self.brake_applied = brake_commanded and self._brake_command_timer >= self.BRAKE_RESPONSE_DELAY_S
        self.brake_release_timer = max(0.0, self.brake_release_timer - dt)

        if self.brake_applied:
            if self.emergency_brake_active:
                deceleration = self.emergency_brake
            else:
                # T1 is gentle braking; T3 applies the strongest service braking.
                index = min(len(self.brake_notches) - 1, abs(self.controller_notch) - 1)
                deceleration = self.brake_notches[index]

            # Ramp braking force in gradually instead of changing speed abruptly.
            # Gravity can help or oppose braking; rolling resistance always slows the train.
            target_acceleration = -deceleration + grade_acceleration - resistance
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
                target_acceleration = natural_acceleration
                if self.controller_notch > 0 and not self.doors_open and self.brake_release_timer <= 0.0:
                    index = min(len(self.traction_notches) - 1, self.controller_notch - 1)
                    traction_acceleration = self.traction_notches[index]
                    # Traction weakens as speed rises, but grade and resistance stay active.
                    speed_kmh = self.speed * 3.6
                    high_speed_fade = max(0.0, min(1.0, (speed_kmh - 40.0) / 40.0))
                    traction_acceleration *= 1.0 - 0.45 * high_speed_fade
                    target_acceleration += traction_acceleration
                if self.speed >= limit:
                    target_acceleration = min(0.0, target_acceleration)
                change = self.jerk_limit * dt
                self.acceleration_state += max(
                    -change, min(change, target_acceleration - self.acceleration_state)
                )
                self.speed = max(0.0, min(limit, self.speed + self.acceleration_state * dt))

        self.position = min(max(0.0, line.path.total_length), self.position + self.speed * dt)
        if self.position >= line.path.total_length:
            self.speed = 0.0
            self.acceleration_state = 0.0
