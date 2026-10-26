"""World-space camera following the leading cab; zoom 0.5 shows twice as much route."""
class Camera:
    def __init__(self, viewport, zoom=0.5):
        self.width, self.height = viewport
        self.zoom = max(0.1, float(zoom))
        self.x = 0.0

    @property
    def pixels_per_metre(self):
        return 4.0 * self.zoom

    def follow(self, train):
        # Keep the leading cab in the left third while showing a wider area ahead.
        cab_screen_x = self.width * 0.34
        self.x = max(0.0, train.position - cab_screen_x / self.pixels_per_metre)
