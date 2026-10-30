"""Optional lightweight passenger-flow model."""
class PassengerFlow:
    def __init__(self, waiting=0):
        self.waiting = max(0, int(waiting))

    def board(self, free_capacity):
        boarded = min(self.waiting, max(0, int(free_capacity)))
        self.waiting -= boarded
        return boarded
