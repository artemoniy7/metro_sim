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

    @staticmethod
    def _smoothstep(t):
        """Ease elevation changes in and out to avoid sharp kinks at control points."""
        t = max(0.0, min(1.0, t))
        return t * t * (3.0 - 2.0 * t)

    @staticmethod
    def _segment_for_distance(distance, lengths):
        remaining = max(0.0, float(distance))
        for i, length in enumerate(lengths):
            if remaining <= length:
                return i, remaining, length
            remaining -= length
        if lengths:
            return len(lengths) - 1, lengths[-1], lengths[-1]
        return 0, 0.0, 0.0

    def point_at(self, distance):
        if not self.points:
            return (0.0, 0.0)
        if len(self.points) == 1:
            return self.points[0]
        distance = max(0.0, min(float(distance), self.total_length))
        i, local, length = self._segment_for_distance(distance, self.lengths)
        a, b = self.points[i], self.points[i + 1]
        t = local / length if length else 0.0
        # Keep horizontal progress uniform, but ease vertical progress at each
        # control point. This removes the sharp visual change of slope while
        # keeping the route's stations and total distance in their existing places.
        eased_t = self._smoothstep(t)
        return (a[0] + (b[0] - a[0]) * t,
                a[1] + (b[1] - a[1]) * eased_t)

    def grade_acceleration(self, distance, gravity=9.81, max_grade=0.06):
        """Gravity acceleration along the smoothed track profile."""
        if len(self.points) < 2:
            return 0.0
        distance = max(0.0, min(float(distance), self.total_length))
        i, local, length = self._segment_for_distance(distance, self.lengths)
        if length <= 0:
            return 0.0
        a, b = self.points[i], self.points[i + 1]
        t = max(0.0, min(1.0, local / length))
        # Derivative of smoothstep: zero at both ends and smoothest halfway.
        derivative = 6.0 * t * (1.0 - t)
        grade = ((b[1] - a[1]) / length) * derivative
        grade = max(-max_grade, min(max_grade, grade))
        return gravity * grade

    def sample(self, step=32):
        if len(self.points) < 2:
            return self.points[:]
        result, d = [], 0.0
        while d < self.total_length:
            result.append(self.point_at(d))
            d += max(1, step)
        result.append(self.points[-1])
        return result
