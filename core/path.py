"""Polyline path helpers. Coordinates are expressed in screen/world pixels."""
import math

class TrackPath:
    def __init__(self, points=None):
        self.points = [tuple(p) for p in (points or [])]
        self.lengths = []
        self.total_length = 0.0
        for a, b in zip(self.points, self.points[1:]):
            length = math.dist(a, b)
            self.lengths.append(length)
            self.total_length += length

    def point_at(self, distance):
        if not self.points:
            return (0.0, 0.0)
        distance = max(0.0, min(float(distance), self.total_length))
        for i, length in enumerate(self.lengths):
            if distance <= length:
                a, b = self.points[i], self.points[i + 1]
                t = distance / length if length else 0.0
                return (a[0] + (b[0]-a[0])*t, a[1] + (b[1]-a[1])*t)
            distance -= length
        return self.points[-1]

    def grade_acceleration(self, distance, gravity=9.81, max_grade=0.06):
        """Gravity acceleration along track; screen-down is downhill."""
        if len(self.points) < 2:
            return 0.0
        remaining = max(0.0, min(float(distance), self.total_length))
        for i, length in enumerate(self.lengths):
            if remaining <= length:
                if length <= 0:
                    return 0.0
                a, b = self.points[i], self.points[i + 1]
                grade = (b[1] - a[1]) / length
                grade = max(-max_grade, min(max_grade, grade))
                return gravity * grade
            remaining -= length
        return 0.0

    def sample(self, step=32):
        if len(self.points) < 2:
            return self.points[:]
        result, d = [], 0.0
        while d < self.total_length:
            result.append(self.point_at(d))
            d += max(1, step)
        result.append(self.points[-1])
        return result
