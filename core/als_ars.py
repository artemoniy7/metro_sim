"""Simplified ALS-ARS onboard speed supervision."""
class AlsArs:
    def __init__(self, default_limit_kmh=60):
        self.default_limit = default_limit_kmh / 3.6
        self.emergency_brake = False

    def speed_limit(self, line, position, train_max_speed):
        limit = min(self.default_limit, train_max_speed)
        for signal in line.signals:
            if signal.position >= position and signal.aspect == "red":
                limit = min(limit, 0.0 if signal.position - position < 45 else 20 / 3.6)
                break
        return max(0.0, limit)
