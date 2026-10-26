"""One car in the train consist."""
class Wagon:
    def __init__(self, train_type="81-760", index=0, is_loco=False):
        self.train_type = train_type
        self.index = index
        self.is_loco = is_loco
        self.length_m = 20.0 if is_loco else 19.0
