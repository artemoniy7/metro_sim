"""Simplified ALS-ARS speed supervision with braking-distance anticipation."""
import math


class AlsArs:
    def __init__(self, default_limit_kmh=80):
        self.default_limit = default_limit_kmh / 3.6
        self.emergency_brake = False
        self.service_brake = 1.15

    def speed_limit(self, line, position, train_max_speed):
        limit = min(self.default_limit, train_max_speed)
        next_signal = None
        for signal in sorted(line.signals, key=lambda item: item.position):
            if signal.position >= position:
                next_signal = signal
                break
        if next_signal is None:
            return max(0.0, limit)

        distance = max(0.0, next_signal.position - position)
        if next_signal.aspect == "yellow":
            limit = min(limit, 40.0 / 3.6)
        elif next_signal.aspect == "green":
            limit = min(limit, 80.0 / 3.6)
        elif next_signal.aspect == "red":
            # Calculate a safe approach speed using v² = 2*a*s, rather than
            # suddenly dropping the allowed speed close to the signal.
            braking_distance_speed = math.sqrt(2.0 * self.service_brake * max(0.0, distance - 3.0))
            limit = min(limit, braking_distance_speed)
        return max(0.0, limit)
