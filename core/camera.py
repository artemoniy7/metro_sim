"""World-space camera following the left-facing leading cab; zoom 0.5 shows twice as much route."""
class Camera:
    def __init__(self, viewport, zoom=0.5):
        self.width, self.height = viewport
        self.zoom = max(0.1, float(zoom))
        self.x = 0.0

    @property
    def pixels_per_metre(self):
        return 4.0 * self.zoom

    def follow(self, train, route_length):
        # The sprite faces left, so the cab's world X decreases as route progress increases.
        cab_world_x = max(0.0, route_length - train.position - train.loco_length_m)
        cab_screen_x = self.width * 0.34
        self.x = max(0.0, cab_world_x - cab_screen_x / self.pixels_per_metre)
