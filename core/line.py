"""A metro line: track geometry, stations and signals."""
from core.path import TrackPath
from core.signal import Signal

class Line:
    def __init__(self, data=None):
        data = data or {}
        self.name = data.get("name", "Test line")
        self.color = tuple(data.get("color", [220, 45, 55]))
        self.path = TrackPath(data.get("points", [[0, 350], [500, 350], [1000, 350], [1600, 350]]))
        self.stations = data.get("stations", [])
        self.signals = [Signal(s.get("position", 0), s.get("aspect", "green"), s.get("name", ""))
                        for s in data.get("signals", [])]
