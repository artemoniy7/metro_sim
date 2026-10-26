"""Railway signal aspects and simple aspect selection."""
class Signal:
    ASPECTS = {"red": (220, 55, 55), "yellow": (245, 195, 55), "green": (65, 205, 110)}

    def __init__(self, position=0.0, aspect="red", name=""):
        self.position = float(position)
        self.aspect = aspect if aspect in self.ASPECTS else "red"
        self.name = name

    def set_aspect(self, aspect):
        if aspect in self.ASPECTS:
            self.aspect = aspect
