"""Trackside signals and their ALS-ARS role."""


class Signal:
    ASPECTS = {
        "red": (220, 55, 55),
        "yellow": (245, 195, 55),
        "green": (65, 205, 110),
        "dark": (48, 51, 58),
    }

    def __init__(self, position=0.0, aspect="green", name="", operational=False,
                 kind="block", lamp_count=2):
        self.position = float(position)
        self.aspect = aspect if aspect in self.ASPECTS else "dark"
        self.name = name
        self.operational = bool(operational)
        self.kind = kind
        self.lamp_count = int(lamp_count)

    def set_aspect(self, aspect):
        if aspect in self.ASPECTS:
            self.aspect = aspect
