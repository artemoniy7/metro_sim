"""ALS-ARS speed codes based on clear blocks and station approach zones."""


class AlsArs:
    def __init__(self, default_limit_kmh=80):
        self.default_limit = default_limit_kmh / 3.6
        self.emergency_brake = False
        self.service_brake = 1.15
        self.indication_kmh = default_limit_kmh
        self.free_blocks_ahead = 0

    def speed_limit(self, line, position, train_max_speed):
        indication, free_blocks = line.block_indication(position)
        self.indication_kmh = float(indication)
        self.free_blocks_ahead = int(free_blocks)
        limit = min(self.default_limit, train_max_speed, indication / 3.6)
        return max(0.0, limit)
