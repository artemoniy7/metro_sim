"""A metro line with passive signals and working station/block signals."""
from core.path import TrackPath
from core.signal import Signal


class Line:
    PASSIVE_SIGNAL_SPACING_M = 275.0

    def __init__(self, data=None):
        data = data or {}
        self.name = data.get("name", "Test line")
        self.color = tuple(data.get("color", [220, 45, 55]))
        self.path = TrackPath(data.get("points", [[0, 350], [500, 350], [1000, 350], [1600, 350]]))
        self.stations = sorted(data.get("stations", []), key=lambda item: float(item.get("position", 0)))
        self.signals = []
        self.traffic_trains = []
        self._create_signals()

    def _create_signals(self):
        """Passive conventional signals every ~275 m, plus working station signals."""
        total = self.path.total_length
        position = self.PASSIVE_SIGNAL_SPACING_M
        index = 1
        while position < total:
            # Do not place conventional signals within a station platform.
            on_platform = any(
                float(station.get("position", 0)) - float(station.get("length_m", 162)) / 2.0
                <= position <=
                float(station.get("position", 0)) + float(station.get("length_m", 162)) / 2.0
                for station in self.stations
            )
            if not on_platform:
                self.signals.append(Signal(
                    position=position, aspect="dark", name=f"П{index}",
                    operational=False, kind="passive", lamp_count=2,
                ))
            position += self.PASSIVE_SIGNAL_SPACING_M
            index += 1

        for index, station in enumerate(self.stations, start=1):
            center = float(station.get("position", 0))
            half_length = float(station.get("length_m", 162)) / 2.0
            entry_position = max(0.0, center - half_length - 50.0)
            exit_position = min(total, center + half_length + 10.0)
            self.signals.append(Signal(
                entry_position, "green", f"С{index}В",
                operational=True, kind="station_entry", lamp_count=2,
            ))
            self.signals.append(Signal(
                exit_position, "green", f"С{index}П",
                operational=True, kind="station_exit", lamp_count=3,
            ))

        # Safety cleanup: no signal head should stand within platform limits.
        self.signals = [
            signal for signal in self.signals
            if not any(
                float(station.get("position", 0)) - float(station.get("length_m", 162)) / 2.0
                <= signal.position <=
                float(station.get("position", 0)) + float(station.get("length_m", 162)) / 2.0
                for station in self.stations
            )
        ]
        self.signals.sort(key=lambda signal: signal.position)

    def update_signals(self, train, train_speed=None):
        """Keep each signal red while its protected block is occupied.

        Blocks are the intervals between consecutive working signals (with the
        next physical signal acting as the far boundary). A block is released
        only when the train's rear-most wheel point passes its far boundary.
        """
        trains = list(train) if isinstance(train, (list, tuple)) else [train]
        occupied_ranges = []
        for item in trains:
            if hasattr(item, "position"):
                front = float(item.position) + float(item.loco_length_m)
                rear = front - float(item.consist_length_m)
            else:
                front = rear = float(item)
            occupied_ranges.append((front, rear))

        operational = sorted(
            (signal for signal in self.signals if signal.operational),
            key=lambda signal: signal.position,
        )
        for signal in self.signals:
            if not signal.operational:
                signal.set_aspect("dark")

        for index, signal in enumerate(operational):
            # The next operational signal bounds this signal's protected block.
            block_start = signal.position
            block_end = (
                operational[index + 1].position
                if index + 1 < len(operational)
                else self.path.total_length
            )

            # Red while any part of the train occupies the block. Never turn
            # a signal green merely because the train passed its own pole.
            occupied = any(
                front >= block_start and rear < block_end
                for front, rear in occupied_ranges
            )
            if occupied:
                signal.set_aspect("red")
            else:
                signal.set_aspect("green")

        # Entry signals show a restrictive approach aspect before the platform.
        # Show an approach aspect for any train nearing a station.
        for front_point, _ in occupied_ranges:
            next_station = next((
                station for station in self.stations
                if float(station.get("position", 0)) >= front_point
            ), None)
            if next_station is not None:
                center = float(next_station.get("position", 0))
                half_length = float(next_station.get("length_m", 162)) / 2.0
                distance_to_platform = center - half_length - front_point
                if 0.0 <= distance_to_platform <= 50.0:
                    for signal in operational:
                        if signal.kind == "station_entry" and signal.position >= front_point:
                            signal.set_aspect("yellow")

    def block_indication(self, train_position):
        """Return an ALS-ARS code using the clear distance to the rear of trains ahead.

        A train occupies the block until its rear clears it. Therefore the
        following train gets a zero code while it is within one full block
        (275 m) of the preceding train's rear, not just its front reference.
        """
        # Treat the beginning of the line as the rear of a virtual queue:
        # all trains (including the player) are compared with trains ahead,
        # but the player can enter the line without being blocked by a bot
        # behind them. Position is the front reference; subtract the full
        # consist length to get the leading train's rear.
        clear_distances = []
        for other in self.traffic_trains:
            if not hasattr(other, "position"):
                continue
            other_position = float(other.position)
            if other_position <= float(train_position) + 1.0:
                continue
            other_length = float(getattr(other, "consist_length_m", 0.0))
            clear_distance = other_position - other_length - float(train_position)
            clear_distances.append(max(0.0, clear_distance))

        traffic_limit = 80
        traffic_blocks = 99
        if clear_distances:
            clear_gap = min(clear_distances)
            traffic_blocks = max(0, int(clear_gap // self.PASSIVE_SIGNAL_SPACING_M))
            # Delay each restriction by one block compared with the previous
            # profile, so braking does not start quite as early.
            if clear_gap <= 0:
                traffic_limit = 0
            elif clear_gap <= self.PASSIVE_SIGNAL_SPACING_M:
                traffic_limit = 40
            elif clear_gap <= 2 * self.PASSIVE_SIGNAL_SPACING_M:
                traffic_limit = 60
            elif clear_gap <= 3 * self.PASSIVE_SIGNAL_SPACING_M:
                traffic_limit = 70

        next_station = next((
            station for station in self.stations
            if float(station.get("position", 0)) >= train_position
        ), None)
        if next_station is not None:
            center = float(next_station.get("position", 0))
            half_length = float(next_station.get("length_m", 162)) / 2.0
            station_start = center - half_length
            station_end = center + half_length
            distance_to_platform = station_start - train_position

            if station_start <= train_position <= station_end:
                if train_position >= center:
                    return min(40, traffic_limit), min(1, traffic_blocks)
                return min(60, traffic_limit), min(1, traffic_blocks)
            if 0.0 <= distance_to_platform <= 50.0:
                return min(60, traffic_limit), min(1, traffic_blocks)
            if 50.0 < distance_to_platform <= 100.0:
                return min(70, traffic_limit), min(2, traffic_blocks)

        block_count = max(1, int(
            (self.path.total_length + self.PASSIVE_SIGNAL_SPACING_M - 1)
            // self.PASSIVE_SIGNAL_SPACING_M
        ))
        block_index = int(max(0.0, train_position) // self.PASSIVE_SIGNAL_SPACING_M)
        blocks_to_end = max(0, block_count - block_index - 1)
        if clear_distances:
            return traffic_limit, traffic_blocks
        if blocks_to_end >= 4:
            return 80, blocks_to_end
        if blocks_to_end == 3:
            return 70, blocks_to_end
        if blocks_to_end == 2:
            return 60, blocks_to_end
        if blocks_to_end == 1:
            return 40, blocks_to_end
        return 0, blocks_to_end
