"""One car in the train consist."""
class Wagon:
    def __init__(self, train_type="81-717", index=0):
        self.train_type = train_type
        self.index = index
        self.length_m = 19.2
