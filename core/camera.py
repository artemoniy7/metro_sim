"""Side-on camera that keeps the train near the cab and can pan along the consist."""


class Camera:
    def __init__(self, viewport, zoom=2.0):
        self.width, self.height = viewport
        self.zoom = max(0.1, float(zoom))
        self.x = 0.0
        # Positive offset pans from the locomotive toward the following cars.
        self.consist_offset_m = 0.0
        self.focus_screen_x = self.width * 0.36

    @property
    def pixels_per_metre(self):
        return 10.0 * self.zoom

    def zoom_by(self, amount):
        self.zoom = max(0.65, min(3.5, self.zoom + amount))

    def pan(self, direction, train):
        # One key press moves the view by a small, predictable amount.
        self.consist_offset_m += direction * max(2.0, 5.0 / self.zoom)
        max_offset = max(0.0, train.consist_length_m - train.loco_length_m / 2)
        self.consist_offset_m = max(0.0, min(max_offset, self.consist_offset_m))

    def follow(self, train, route_length):
        # Train sprites face left. Increasing consist_offset moves the view
        # toward the cars, so the locomotive shifts toward the left edge.
        cab_world_x = max(0.0, route_length - train.position - train.loco_length_m)
        self.x = max(
            0.0,
            cab_world_x - self.focus_screen_x / self.pixels_per_metre
            + self.consist_offset_m,
        )
