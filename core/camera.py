"""Camera that follows the active train along the route."""
class Camera:
    def __init__(self, viewport):
        self.width, self.height = viewport
        self.x = 0.0

    def follow(self, train):
        self.x = max(0.0, train.position - self.width * 0.35)
