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
        self._create_signals()

    def _create_signals(self):
        """Passive conventional signals every ~275 m, plus working station signals."""
        total = self.path.total_length
        position = self.PASSIVE_SIGNAL_SPACING_M
        index = 1
        while position < total:
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

        self.signals.sort(key=lambda signal: signal.position)

    def update_signals(self, train, train_speed=None):
        """Keep each signal red while its protected block is occupied.

        Blocks are the intervals between consecutive working signals (with the
        next physical signal acting as the far boundary). A block is released
        only when the train's rear-most wheel point passes its far boundary.
        """
        if hasattr(train, "position"):
            front_point = float(train.position) + float(train.loco_length_m)
            rear_point = front_point - float(train.consist_length_m)
        else:
            front_point = rear_point = float(train)

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
            occupied = front_point >= block_start and rear_point < block_end
            if occupied:
                signal.set_aspect("red")
            else:
                signal.set_aspect("green")

        # Entry signals show a restrictive approach aspect before the platform.
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
        """Return the simplified ALS-ARS indication in km/h and free block count."""
        next_station = next((
            station for station in self.stations
            if float(station.get("position", 0)) >= train_position
        ), None)
        if next_station is not None:
            center = float(next_station.get("position", 0))
            half_length = float(next_station.get("length_m", 162)) / 2.0
            distance_to_platform = center - half_length - train_position
            if 0.0 <= distance_to_platform <= 50.0:
                return 40, 1
            if -half_length <= train_position - center <= half_length:
                return 40, 1

        block_count = max(1, int((self.path.total_length + self.PASSIVE_SIGNAL_SPACING_M - 1)
                                 // self.PASSIVE_SIGNAL_SPACING_M))
        block_index = int(max(0.0, train_position) // self.PASSIVE_SIGNAL_SPACING_M)
        blocks_ahead = max(0, block_count - block_index - 1)
        if blocks_ahead >= 3:
            return 80, blocks_ahead
        if blocks_ahead == 2:
            return 70, blocks_ahead
        if blocks_ahead == 1:
            return 60, blocks_ahead
        return 0, blocks_ahead
